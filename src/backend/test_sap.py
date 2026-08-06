"""Offline tests for the SAP layer.

No network and no credentials: OData responses are recorded payloads, so this
runs in CI. The live path is covered by `python sap.py`, which is a read-only
smoke test against the demo purchase order.

    python test_sap.py          # or: pytest test_sap.py
"""

from datetime import date
from decimal import Decimal

from rules import Status, evaluate
from sap import (
    Config,
    ParkResult,
    SapClient,
    SapError,
    odata_date,
    parse_odata_date,
    reference_for,
    sap_message,
)

D = Decimal

CONFIG = Config(
    mcp_url="https://example.invalid/mcp",
    token_endpoint="https://example.invalid/token",
    client_id="id",
    client_secret="secret",
    scope="",
    sap_base_url="https://sap.invalid/sap/opu/odata/sap",
    company_code="1010",
    currency="EUR",
    posting_date=date(2025, 3, 15),
    reference_prefix="000000000000",
    valid_tax_codes=frozenset({"V0", "V1"}),
    open_period=(date(2025, 1, 1), date(2025, 12, 31)),
)

# Recorded from the live system: PO 4500001563 item 10.
PO_HEADER = {"d": {
    "PurchaseOrder": "4500001563",
    "InvoicingParty": "17401710",
    "Supplier": "BP1710",
    "CompanyCode": "1010",
    "DocumentCurrency": "EUR",
    "PurchasingDocumentDeletionCode": "",
    "ReleaseIsNotCompleted": False,
}}

PO_ITEM = {"d": {
    "PurchaseOrder": "4500001563",
    "PurchaseOrderItem": "10",
    "Material": "TG12",
    "OrderQuantity": "10",
    "PurchaseOrderQuantityUnit": "PC",
    "NetPriceAmount": "11.35",
    "NetPriceQuantity": "1",
    "TaxCode": "V0",
    "InvoiceIsGoodsReceiptBased": True,
}}

MATERIAL_DOCS = {"d": {"results": [{
    "PurchaseOrder": "4500001563",
    "PurchaseOrderItem": "10",
    "QuantityInEntryUnit": "10",
    "EntryUnit": "PC",
    "GoodsMovementType": "101",
}]}}

NOT_FOUND = {"error": {"message": {"value": "Resource not found for the segment 'A_PurchaseOrder'"}}}


class FakeClient(SapClient):
    """SapClient with the transport replaced by a lookup table."""

    def __init__(self, responses: dict[str, object]):
        super().__init__(CONFIG)
        self.responses = responses
        self.paths: list[str] = []

    def odata(self, path, method="GET", body=None):  # noqa: D102
        self.paths.append(path)
        self.call_count += 1
        for fragment, payload in self.responses.items():
            if fragment in path:
                if isinstance(payload, Exception):
                    raise payload
                return payload
        return {"d": {"results": []}}


def default_client() -> FakeClient:
    return FakeClient({
        "A_PurchaseOrder('": PO_HEADER,
        "A_PurchaseOrderItem(": PO_ITEM,
        "A_MaterialDocumentItem": MATERIAL_DOCS,
        "A_SuplrInvcItemPurOrdRef": {"d": {"results": []}},
        "A_SupplierInvoice?": {"d": {"results": []}},
    })


# --- date conversion ------------------------------------------------------


def test_odata_date_matches_the_documented_value():
    # The lab documents /Date(1741996800000)/ as 2025-03-15.
    assert odata_date(date(2025, 3, 15)) == "/Date(1741996800000)/"


def test_odata_date_round_trips():
    for day in (date(2025, 1, 1), date(2025, 3, 15), date(2025, 12, 31)):
        assert parse_odata_date(odata_date(day)) == day


def test_parse_odata_date_tolerates_missing_values():
    assert parse_odata_date(None) is None
    assert parse_odata_date("") is None


# --- references -----------------------------------------------------------


def test_reference_fits_sap_sixteen_character_limit():
    assert reference_for("922513818191", 1) == "922513818191-1"
    assert len(reference_for("922513818191", 99)) == 15


def test_over_long_reference_is_rejected_before_sap_sees_it():
    try:
        reference_for("a" * 20, 1)
    except SapError as exc:
        assert "16-character" in str(exc)
    else:
        raise AssertionError("expected SapError")


# --- error messages -------------------------------------------------------


def test_sap_message_unwraps_the_odata_envelope():
    assert "not found" in sap_message(NOT_FOUND).lower()


def test_sap_message_includes_inner_error_details():
    payload = {"error": {
        "message": {"value": "Posting failed"},
        "innererror": {"errordetails": [
            {"message": "Posting period 008 2026 is not open", "severity": "error"},
            {"message": "cosmetic note", "severity": "info"},
        ]},
    }}
    text = sap_message(payload)
    assert "Posting failed" in text
    assert "Posting period 008 2026 is not open" in text
    assert "cosmetic note" not in text


# --- field mapping --------------------------------------------------------


def test_header_maps_invoicing_party_not_supplier():
    """An invoice references InvoicingParty (17401710). `Supplier` on the same
    purchase order is the business-partner number (BP1710) and would never
    match, so mapping the wrong field fails every vendor check."""
    header = default_client().get_po_header("4500001563")
    assert header.supplier == "17401710"
    assert header.company_code == "1010"
    assert not header.is_deleted


def test_missing_purchase_order_reads_back_as_none():
    """R01's job, not an exception - a missing PO must not abort the batch."""
    client = FakeClient({"A_PurchaseOrder('": SapError(sap_message(NOT_FOUND))})
    assert client.get_po_header("4500009999") is None


def test_other_sap_failures_still_raise():
    client = FakeClient({"A_PurchaseOrder('": SapError("Backend system unavailable")})
    try:
        client.get_po_header("4500001563")
    except SapError as exc:
        assert "unavailable" in str(exc)
    else:
        raise AssertionError("a real SAP failure must not be swallowed")


def test_price_is_divided_by_the_price_quantity():
    """NetPriceAmount is the price for NetPriceQuantity units. A material priced
    at 250.00 per 100 costs 2.50 each; not dividing overstates it 100x and every
    invoice would fail the price check."""
    item_per_100 = {"d": dict(PO_ITEM["d"], NetPriceAmount="250.00", NetPriceQuantity="100")}
    client = FakeClient({"A_PurchaseOrderItem(": item_per_100})
    assert client.get_po_item("4500001563", "10").net_price == D("2.50")


def test_price_quantity_of_one_is_unchanged():
    assert default_client().get_po_item("4500001563", "10").net_price == D("11.35")


def test_goods_receipts_keep_only_movement_101_and_102():
    docs = {"d": {"results": [
        dict(MATERIAL_DOCS["d"]["results"][0]),
        dict(MATERIAL_DOCS["d"]["results"][0], GoodsMovementType="102", QuantityInEntryUnit="4"),
        dict(MATERIAL_DOCS["d"]["results"][0], GoodsMovementType="543", QuantityInEntryUnit="7"),
    ]}}
    client = FakeClient({"A_MaterialDocumentItem": docs})
    receipts = client.get_goods_receipts("4500001563", "10")
    assert [gr.movement_type for gr in receipts] == ["101", "102"]


def test_used_references_are_scoped_to_the_prefix_and_vendor():
    client = FakeClient({"A_SupplierInvoice?": {"d": {"results": [
        {"SupplierInvoiceIDByInvcgParty": "000000000000-1"},
        {"SupplierInvoiceIDByInvcgParty": ""},
    ]}}})
    assert client.get_used_references("17401710") == frozenset({"000000000000-1"})
    path = client.paths[0]
    assert "InvoicingParty eq '17401710'" in path
    assert "startswith(SupplierInvoiceIDByInvcgParty,'000000000000')" in path


# --- context assembly -----------------------------------------------------


def _invoice(**overrides):
    import fixtures

    defaults = dict(
        source_file="t.pdf", seq=1, supplier="17401710", purchase_order="4500001563",
        material="TG12", quantity="10", unit_price="11.35", tax_code="V0", tax_amount="0.00",
    )
    return fixtures.invoice(**{**defaults, **overrides})


def test_build_context_feeds_the_rules_a_clean_pass():
    client = default_client()
    findings = evaluate(_invoice(), client.build_context(_invoice()))
    flagged = [f.rule_id for f in findings if f.status is not Status.PASS]
    assert not flagged, f"unexpected findings: {flagged}"


def test_build_context_skips_dependent_reads_when_the_po_is_missing():
    """No purchase order means no item and no receipts to read. Spending calls
    on them would be wasted latency on every failing invoice in a batch."""
    client = FakeClient({
        "A_PurchaseOrder('": SapError(sap_message(NOT_FOUND)),
        "A_SupplierInvoice?": {"d": {"results": []}},
    })
    invoice = _invoice(purchase_order="4500009999")
    context = client.build_context(invoice)

    assert context.po_header is None
    assert context.po_item is None
    assert context.goods_receipts == []
    assert not any("A_MaterialDocumentItem" in p for p in client.paths)

    findings = {f.rule_id: f for f in evaluate(invoice, context)}
    assert findings["R01"].status is Status.FAIL
    assert findings["R12"].status is Status.NOT_APPLICABLE


# --- the write ------------------------------------------------------------


def test_park_body_is_a_parked_deep_insert():
    captured = {}

    class Recorder(FakeClient):
        def odata(self, path, method="GET", body=None):
            if method == "POST":
                captured.update({"path": path, "body": body})
                return {"d": {"SupplierInvoice": "5100001500", "FiscalYear": "2025",
                              "SupplierInvoiceStatus": "A"}}
            return super().odata(path, method, body)

    result = Recorder({}).park(_invoice())
    body = captured["body"]

    assert isinstance(result, ParkResult)
    assert (result.supplier_invoice, result.fiscal_year) == ("5100001500", "2025")

    # Reversible write: parked, never posted.
    assert body["SupplierInvoiceStatus"] == "A"
    # Dates must sit in an open period, not today.
    assert body["DocumentDate"] == body["PostingDate"] == "/Date(1741996800000)/"
    assert body["TaxIsCalculatedAutomatically"] is True
    assert body["InvoicingParty"] == "17401710"

    line = body["to_SuplrInvcItemPurOrdRef"][0]
    assert line["PurchaseOrder"] == "4500001563"
    assert line["PurchaseOrderItem"] == "10"
    assert line["SupplierInvoiceItemAmount"] == "113.50"
    assert line["QuantityInPurchaseOrderUnit"] == "10"


def test_post_carries_no_system_query_options():
    """SAP rejects a write that carries $format: "The Data Services Request
    contains SystemQueryOptions that are not allowed for this Request Type"."""
    captured = {}

    class Recorder(FakeClient):
        def odata(self, path, method="GET", body=None):
            if method == "POST":
                captured["path"] = path
                return {"d": {"SupplierInvoice": "1", "FiscalYear": "2025"}}
            return super().odata(path, method, body)

    Recorder({}).park(_invoice())
    assert "$" not in captured["path"]


def test_empty_success_response_is_not_an_error():
    """A successful DELETE answers 204 No Content and the MCP tool reports the
    empty body as prose, not JSON. That is success, not a parse failure."""

    class Transport(SapClient):
        def __init__(self, text):
            super().__init__(CONFIG)
            self._initialised = True
            self.text = text

        def _rpc(self, method, params=None):
            return {"content": [{"text": self.text}]}

    assert Transport("Request successful. Status: 204").odata("x", "DELETE") == {}
    assert Transport("Request successful. Status: 200").odata("x", "DELETE") == {}

    try:
        Transport("<html>gateway timeout</html>").odata("x")
    except SapError as exc:
        assert "non-JSON" in str(exc)
    else:
        raise AssertionError("genuine garbage must still raise")


def test_parked_invoices_do_not_consume_the_purchase_order():
    """A parked document is a draft: no accounting entry, no PO consumption.
    Counting other teams' drafts would make an open PO look fully invoiced and
    raise a false quantity exception on every later invoice."""
    refs = {"d": {"results": [
        {"SupplierInvoice": "5100001500", "FiscalYear": "2025", "QuantityInPurchaseOrderUnit": "5"},
        {"SupplierInvoice": "5100001501", "FiscalYear": "2025", "QuantityInPurchaseOrderUnit": "5"},
        {"SupplierInvoice": "5100001210", "FiscalYear": "2023", "QuantityInPurchaseOrderUnit": "10"},
    ]}}
    statuses = {"d": {"results": [
        {"SupplierInvoice": "5100001500", "FiscalYear": "2025", "SupplierInvoiceStatus": "A"},
        {"SupplierInvoice": "5100001501", "FiscalYear": "2025", "SupplierInvoiceStatus": "A"},
        {"SupplierInvoice": "5100001210", "FiscalYear": "2023", "SupplierInvoiceStatus": "5"},
    ]}}
    client = FakeClient({
        "$select=SupplierInvoice,FiscalYear,SupplierInvoiceStatus": statuses,
        "A_SuplrInvcItemPurOrdRef": refs,
    })
    # Only the posted document counts: 10, not 20.
    assert client.get_invoiced_quantity("4500001463", "10") == D("10")


def test_invoiced_quantity_skips_the_status_lookup_when_nothing_references_the_po():
    client = FakeClient({"A_SuplrInvcItemPurOrdRef": {"d": {"results": []}}})
    assert client.get_invoiced_quantity("4500001563", "10") == D("0")
    assert len(client.paths) == 1


def test_status_lookup_is_batched():
    """One request per 20 keys, so a heavily used PO does not build a URL SAP
    will reject for length."""
    refs = {"d": {"results": [
        {"SupplierInvoice": f"51000015{n:02d}", "FiscalYear": "2025",
         "QuantityInPurchaseOrderUnit": "1"}
        for n in range(45)
    ]}}
    client = FakeClient({
        "$select=SupplierInvoice,FiscalYear,SupplierInvoiceStatus": {"d": {"results": []}},
        "A_SuplrInvcItemPurOrdRef": refs,
    })
    client.get_invoiced_quantity("4500001463", "10")
    lookups = [p for p in client.paths if "SupplierInvoiceStatus" in p]
    assert len(lookups) == 3  # 45 keys -> ceil(45/20)


def test_park_never_omits_the_unique_reference():
    """Without it the shared system's duplicate check collides between teams."""
    captured = {}

    class Recorder(FakeClient):
        def odata(self, path, method="GET", body=None):
            if method == "POST":
                captured.update(body)
                return {"d": {"SupplierInvoice": "1", "FiscalYear": "2025"}}
            return super().odata(path, method, body)

    Recorder({}).park(_invoice(seq=7))
    assert captured["SupplierInvoiceIDByInvcgParty"] == "000000000000-7"


if __name__ == "__main__":
    tests = [v for k, v in sorted(globals().items()) if k.startswith("test_")]
    failed = 0
    for test in tests:
        try:
            test()
            print(f"  ok   {test.__name__}")
        except AssertionError as exc:
            failed += 1
            print(f"  FAIL {test.__name__}: {exc}")
    print(f"\n{len(tests) - failed}/{len(tests)} passed")
    raise SystemExit(1 if failed else 0)
