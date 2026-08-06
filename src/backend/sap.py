"""SAP access for the invoice agent, routed through the MCP server.

Every SAP call goes through the Model Context Protocol server running on
Bedrock AgentCore, never straight to OData. The MCP server holds the SAP
credentials in Secrets Manager, so nothing here ever sees a SAP password.

This module does two things and nothing else:

    build_context(invoice) -> SapContext   the reads that feed the rules
    park(invoice)          -> ParkResult   the single write, always status A

Field mapping was verified against the live system, not guessed from the spec:
`InvoicingParty` (not `Supplier`) is what an invoice references, and a PO item
price is `NetPriceAmount` per `NetPriceQuantity` units - dividing matters when
a material is priced per 100.
"""

from __future__ import annotations

import json
import os
import re
import uuid
from dataclasses import dataclass
from datetime import date, datetime, timezone
from decimal import Decimal

import requests

from rules import GoodsReceipt, Invoice, PoHeader, PoItem, SapContext

D = Decimal
TIMEOUT = 180
ODATA_DATE = re.compile(r"/Date\((-?\d+)\)/")
EMPTY_SUCCESS = re.compile(r"^Request successful\. Status: 2\d\d$")
PARKED = "A"  # SupplierInvoiceStatus for a held/draft document
STATUS_BATCH = 20  # keys per status lookup, keeps the $filter URL short


class SapError(RuntimeError):
    """A SAP or MCP call failed. Carries the business message where SAP gave one."""


# --------------------------------------------------------------------------
# Configuration
# --------------------------------------------------------------------------


@dataclass(frozen=True)
class Config:
    mcp_url: str
    token_endpoint: str
    client_id: str
    client_secret: str
    scope: str
    sap_base_url: str
    company_code: str
    currency: str
    posting_date: date
    reference_prefix: str
    valid_tax_codes: frozenset[str]
    open_period: tuple[date, date]

    @classmethod
    def from_env(cls, suffix: str = "_CUSTOM") -> Config:
        """Read configuration from the environment.

        `suffix` selects which MCP deployment to talk to; the custom server
        exposes one generic `invoke_sap_odata_service` tool, which is the
        contract this module is written against.
        """

        def need(name: str) -> str:
            value = os.environ.get(name, "")
            if not value:
                raise SapError(f"{name} is not set - copy .env.example to .env and fill it in")
            return value

        posting = date.fromisoformat(os.environ.get("SAP_POSTING_DATE", "2025-03-15"))
        period = os.environ.get("SAP_OPEN_PERIOD", f"{posting.year}-01-01:{posting.year}-12-31")
        start, _, end = period.partition(":")

        return cls(
            mcp_url=need(f"MCP_URL{suffix}"),
            token_endpoint=need(f"COGNITO_TOKEN_ENDPOINT{suffix}"),
            client_id=need(f"COGNITO_CLIENT_ID{suffix}"),
            client_secret=need(f"COGNITO_CLIENT_SECRET{suffix}"),
            scope=os.environ.get(f"COGNITO_SCOPE{suffix}", ""),
            sap_base_url=need("SAP_BASE_URL").rstrip("/"),
            company_code=os.environ.get("SAP_COMPANY_CODE", "1010"),
            currency=os.environ.get("SAP_CURRENCY", "EUR"),
            posting_date=posting,
            reference_prefix=need("INVOICE_REFERENCE_PREFIX"),
            valid_tax_codes=frozenset(
                os.environ.get("SAP_VALID_TAX_CODES", "V0,V1").split(",")
            ),
            open_period=(date.fromisoformat(start), date.fromisoformat(end)),
        )


# --------------------------------------------------------------------------
# MCP transport
# --------------------------------------------------------------------------


class SapClient:
    """Thin MCP client. One token and one MCP session are reused per instance."""

    def __init__(self, config: Config | None = None):
        self.config = config or Config.from_env()
        self._token: str | None = None
        self._session = uuid.uuid4().hex * 2  # AgentCore requires >= 33 chars
        self._initialised = False
        self.call_count = 0  # observability: how many SAP reads a batch cost

    # --- plumbing ---------------------------------------------------------

    def _bearer(self) -> str:
        if self._token:
            return self._token
        data = {
            "grant_type": "client_credentials",
            "client_id": self.config.client_id,
            "client_secret": self.config.client_secret,
        }
        if self.config.scope:
            data["scope"] = self.config.scope
        response = requests.post(
            self.config.token_endpoint,
            data=data,
            headers={"Content-Type": "application/x-www-form-urlencoded"},
            timeout=30,
        )
        if response.status_code != 200:
            raise SapError(f"Cognito token request failed: HTTP {response.status_code}")
        self._token = response.json()["access_token"]
        return self._token

    @staticmethod
    def _parse_rpc(body: str) -> dict:
        """streamable-http answers as SSE: `event: message` then `data: {...}`."""
        for line in body.splitlines():
            if line.startswith("data:"):
                return json.loads(line[5:].strip())
        return json.loads(body)

    def _rpc(self, method: str, params: dict | None = None) -> dict:
        response = requests.post(
            self.config.mcp_url,
            headers={
                "authorization": f"Bearer {self._bearer()}",
                "Content-Type": "application/json",
                "Accept": "application/json, text/event-stream",
                "X-Amzn-Bedrock-AgentCore-Runtime-Session-Id": self._session,
            },
            json={"jsonrpc": "2.0", "id": 1, "method": method, "params": params or {}},
            timeout=TIMEOUT,
        )
        if response.status_code != 200:
            raise SapError(f"MCP call failed: HTTP {response.status_code}")
        payload = self._parse_rpc(response.text)
        if "error" in payload:
            raise SapError(f"MCP error: {payload['error'].get('message', payload['error'])}")
        return payload["result"]

    def _ensure_initialised(self) -> None:
        if self._initialised:
            return
        self._rpc(
            "initialize",
            {
                "protocolVersion": "2024-11-05",
                "capabilities": {},
                "clientInfo": {"name": "dmi-invoice-agent", "version": "1.0"},
            },
        )
        self._initialised = True

    def odata(self, path: str, method: str = "GET", body: dict | None = None) -> dict:
        """Call one SAP OData path through the MCP server's generic tool."""
        self._ensure_initialised()
        self.call_count += 1
        arguments = {
            "odata_api_url": f"{self.config.sap_base_url}/{path}",
            "http_method": method,
        }
        if body is not None:
            arguments["request_body"] = json.dumps(body)

        result = self._rpc("tools/call", {"name": "invoke_sap_odata_service", "arguments": arguments})
        text = result["content"][0]["text"]

        # A successful DELETE answers 204 No Content, and the MCP tool reports
        # an empty body as plain prose rather than JSON. That is a success.
        if EMPTY_SUCCESS.match(text.strip()):
            return {}

        try:
            payload = json.loads(text)
        except json.JSONDecodeError as exc:
            raise SapError(f"SAP returned a non-JSON response: {text[:300]}") from exc

        if "error" in payload:
            raise SapError(sap_message(payload))
        return payload

    # --- reads ------------------------------------------------------------

    def get_po_header(self, purchase_order: str) -> PoHeader | None:
        """None when the purchase order does not exist - that is rule R01's job,
        not an exception. Any other SAP failure still raises."""
        try:
            raw = self.odata(
                f"API_PURCHASEORDER_PROCESS_SRV/A_PurchaseOrder('{purchase_order}')?$format=json"
            )["d"]
        except SapError as exc:
            if _is_not_found(exc):
                return None
            raise
        return PoHeader(
            purchase_order=raw["PurchaseOrder"],
            supplier=raw["InvoicingParty"],
            company_code=raw["CompanyCode"],
            currency=raw["DocumentCurrency"],
            is_deleted=bool(raw.get("PurchasingDocumentDeletionCode")),
            is_blocked=bool(raw.get("ReleaseIsNotCompleted")),
        )

    def get_po_item(self, purchase_order: str, item: str) -> PoItem | None:
        try:
            raw = self.odata(
                f"API_PURCHASEORDER_PROCESS_SRV/A_PurchaseOrderItem"
                f"(PurchaseOrder='{purchase_order}',PurchaseOrderItem='{item}')?$format=json"
            )["d"]
        except SapError as exc:
            if _is_not_found(exc):
                return None
            raise

        # NetPriceAmount is the price for NetPriceQuantity units, not for one.
        price_qty = D(raw.get("NetPriceQuantity") or "1")
        unit_price = D(raw["NetPriceAmount"]) / (price_qty if price_qty else D("1"))

        return PoItem(
            purchase_order=raw["PurchaseOrder"],
            item=raw["PurchaseOrderItem"],
            material=raw.get("Material", ""),
            quantity=D(raw["OrderQuantity"]),
            unit=raw["PurchaseOrderQuantityUnit"],
            net_price=unit_price,
            already_invoiced_quantity=self.get_invoiced_quantity(purchase_order, item),
            gr_based_invoice_verification=bool(raw.get("InvoiceIsGoodsReceiptBased")),
        )

    def get_goods_receipts(self, purchase_order: str, item: str) -> list[GoodsReceipt]:
        """Movement 101 receipts and 102 reversals for one PO line."""
        raw = self.odata(
            "API_MATERIAL_DOCUMENT_SRV/A_MaterialDocumentItem"
            f"?$filter=PurchaseOrder eq '{purchase_order}' and PurchaseOrderItem eq '{item}'"
            "&$format=json"
        )
        return [
            GoodsReceipt(
                purchase_order=row["PurchaseOrder"],
                purchase_order_item=row["PurchaseOrderItem"],
                quantity=D(row["QuantityInEntryUnit"]),
                unit=row["EntryUnit"],
                movement_type=row["GoodsMovementType"],
            )
            for row in raw.get("d", {}).get("results", [])
            if row.get("GoodsMovementType") in ("101", "102")
        ]

    def get_invoiced_quantity(self, purchase_order: str, item: str) -> Decimal:
        """How much of this PO line has genuinely been invoiced.

        Parked invoices are excluded. A parked document is a draft: it creates
        no accounting entry and does not consume the purchase order, which is
        exactly why parking is safe on a shared system. Counting them would
        make a PO look consumed because another team left drafts against it,
        and every invoice after that would raise a false quantity exception.

        The item rows carry no status, and there is no navigation from the item
        to its header, so the status join is a second batched read.
        """
        rows = self.odata(
            "API_SUPPLIERINVOICE_PROCESS_SRV/A_SuplrInvcItemPurOrdRef"
            f"?$filter=PurchaseOrder eq '{purchase_order}' and PurchaseOrderItem eq '{item}'"
            "&$format=json"
        ).get("d", {}).get("results", [])
        if not rows:
            return D("0")

        parked = self._parked_invoices(
            {(row["SupplierInvoice"], row["FiscalYear"]) for row in rows}
        )
        return sum(
            (D(row.get("QuantityInPurchaseOrderUnit") or "0")
             for row in rows
             if (row["SupplierInvoice"], row["FiscalYear"]) not in parked),
            D("0"),
        )

    def _parked_invoices(self, keys: set[tuple[str, str]]) -> set[tuple[str, str]]:
        """Which of these supplier invoices are still parked (status A)."""
        ordered = sorted(keys)
        parked: set[tuple[str, str]] = set()
        for start in range(0, len(ordered), STATUS_BATCH):
            chunk = ordered[start:start + STATUS_BATCH]
            clause = " or ".join(
                f"(SupplierInvoice eq '{inv}' and FiscalYear eq '{year}')"
                for inv, year in chunk
            )
            raw = self.odata(
                "API_SUPPLIERINVOICE_PROCESS_SRV/A_SupplierInvoice"
                f"?$filter={clause}"
                "&$select=SupplierInvoice,FiscalYear,SupplierInvoiceStatus&$format=json"
            )
            parked.update(
                (row["SupplierInvoice"], row["FiscalYear"])
                for row in raw.get("d", {}).get("results", [])
                if row.get("SupplierInvoiceStatus") == PARKED
            )
        return parked

    def get_used_references(self, invoicing_party: str) -> frozenset[str]:
        """References already consumed for this vendor, scoped to our prefix.

        Rule R16 is per-vendor: the same reference under a different vendor is
        not a duplicate. Filtering by prefix keeps the response small on a
        system shared with other teams.
        """
        prefix = self.config.reference_prefix
        raw = self.odata(
            "API_SUPPLIERINVOICE_PROCESS_SRV/A_SupplierInvoice"
            f"?$filter=InvoicingParty eq '{invoicing_party}'"
            f" and startswith(SupplierInvoiceIDByInvcgParty,'{prefix}')"
            "&$select=SupplierInvoiceIDByInvcgParty&$format=json"
        )
        return frozenset(
            row["SupplierInvoiceIDByInvcgParty"]
            for row in raw.get("d", {}).get("results", [])
            if row.get("SupplierInvoiceIDByInvcgParty")
        )

    def build_context(self, invoice: Invoice) -> SapContext:
        """Every read the rules need for one invoice, in one call.

        A missing purchase order short-circuits: without it there is nothing to
        read items or receipts against, and the rules report those as
        NOT_APPLICABLE rather than as failures.
        """
        header = self.get_po_header(invoice.purchase_order)
        item = receipts = None
        if header is not None:
            item = self.get_po_item(invoice.purchase_order, invoice.purchase_order_item)
            receipts = self.get_goods_receipts(invoice.purchase_order, invoice.purchase_order_item)

        return SapContext(
            po_header=header,
            po_item=item,
            goods_receipts=receipts or [],
            valid_tax_codes=self.config.valid_tax_codes,
            open_period=self.config.open_period,
            used_references=self.get_used_references(invoice.supplier),
        )

    # --- the single write -------------------------------------------------

    def park(self, invoice: Invoice) -> ParkResult:
        """Park a Supplier Invoice (MIR7) against its purchase order.

        Always status "A" (parked). A parked invoice does not consume the PO,
        creates no accounting entry, and can be deleted - which is what makes
        the write safe to run against a shared demo system.
        """
        body = {
            "CompanyCode": self.config.company_code,
            "DocumentDate": odata_date(self.config.posting_date),
            "PostingDate": odata_date(self.config.posting_date),
            "SupplierInvoiceIDByInvcgParty": invoice.reference,
            "InvoicingParty": invoice.supplier,
            "DocumentCurrency": invoice.currency,
            "InvoiceGrossAmount": f"{invoice.gross_amount:.2f}",
            "SupplierInvoiceStatus": "A",
            "TaxIsCalculatedAutomatically": True,
            "to_SuplrInvcItemPurOrdRef": [
                {
                    "SupplierInvoiceItem": "1",
                    "PurchaseOrder": invoice.purchase_order,
                    "PurchaseOrderItem": invoice.purchase_order_item,
                    "TaxCode": invoice.tax_code,
                    "DocumentCurrency": invoice.currency,
                    "SupplierInvoiceItemAmount": f"{invoice.net_amount:.2f}",
                    "QuantityInPurchaseOrderUnit": f"{invoice.quantity:g}",
                    "PurchaseOrderQuantityUnit": invoice.unit,
                }
            ],
        }
        # No $format on a POST: SAP rejects system query options on writes with
        # "The Data Services Request contains SystemQueryOptions that are not
        # allowed for this Request Type". The Accept header already asks JSON.
        raw = self.odata(
            "API_SUPPLIERINVOICE_PROCESS_SRV/A_SupplierInvoice",
            method="POST",
            body=body,
        )["d"]
        return ParkResult(
            source_file=invoice.source_file,
            reference=invoice.reference,
            supplier_invoice=raw["SupplierInvoice"],
            fiscal_year=raw["FiscalYear"],
            status=raw.get("SupplierInvoiceStatus", "A"),
        )

    def delete_parked(self, supplier_invoice: str, fiscal_year: str) -> None:
        """Remove a parked document. Only ever called on documents we parked."""
        self.odata(
            "API_SUPPLIERINVOICE_PROCESS_SRV/A_SupplierInvoice"
            f"(SupplierInvoice='{supplier_invoice}',FiscalYear='{fiscal_year}')",
            method="DELETE",
        )


@dataclass(frozen=True)
class ParkResult:
    source_file: str
    reference: str
    supplier_invoice: str
    fiscal_year: str
    status: str


# --------------------------------------------------------------------------
# Helpers
# --------------------------------------------------------------------------


def odata_date(value: date) -> str:
    """SAP OData V2 wants /Date(milliseconds-since-epoch)/, UTC midnight."""
    stamp = datetime(value.year, value.month, value.day, tzinfo=timezone.utc)
    return f"/Date({int(stamp.timestamp() * 1000)})/"


def parse_odata_date(value: str | None) -> date | None:
    match = ODATA_DATE.search(value or "")
    if not match:
        return None
    return datetime.fromtimestamp(int(match.group(1)) / 1000, tz=timezone.utc).date()


def sap_message(payload: dict) -> str:
    """Pull the human-readable message out of a SAP OData error envelope."""
    error = payload.get("error", {})
    message = error.get("message")
    if isinstance(message, dict):
        message = message.get("value")
    details = error.get("innererror", {}).get("errordetails") or []
    extra = [d.get("message", "") for d in details if d.get("severity") == "error"]
    return " | ".join(filter(None, [message, *extra])) or json.dumps(error)[:300]


def _is_not_found(exc: SapError) -> bool:
    text = str(exc).lower()
    return "not found" in text or "does not exist" in text or "no data" in text


def reference_for(prefix: str, sequence: int) -> str:
    """SupplierInvoiceIDByInvcgParty is capped at 16 characters."""
    reference = f"{prefix}-{sequence}"
    if len(reference) > 16:
        raise SapError(f"Reference {reference!r} exceeds SAP's 16-character limit")
    return reference


if __name__ == "__main__":
    # Live smoke test against the demo purchase order. Reads only - no writes.
    from dotenv import load_dotenv

    load_dotenv()
    client = SapClient()

    header = client.get_po_header("4500001563")
    print(f"header        {header}")
    assert header is not None and header.supplier == "17401710"

    item = client.get_po_item("4500001563", "10")
    print(f"item          {item}")
    assert item is not None and item.material == "TG12"

    receipts = client.get_goods_receipts("4500001563", "10")
    print(f"receipts      {receipts}")
    assert any(gr.movement_type == "101" for gr in receipts)

    print(f"used refs     {sorted(client.get_used_references('17401710'))}")

    missing = client.get_po_header("4500009999")
    print(f"missing PO    {missing}")
    assert missing is None, "a non-existent PO must read back as None, not raise"

    print(f"\nOK - {client.call_count} SAP calls")
