"""Synthetic invoice batches and the SAP state they are validated against.

No real supplier data, no PII, no bank details - the challenge requires
synthetic demo data only. Account-id placeholders are zeros so nothing real is
committed.

`workshop_batch()` mirrors the six demo invoices: five that reconcile cleanly
and one referencing a purchase order that does not exist.

`variance_batch()` adds the cases that show the tolerance engine doing more
than PASS/FAIL - a price variance inside tolerance, one that needs a manager,
an over-delivery, a vendor mismatch, a duplicate reference and a closed
posting period.
"""

from datetime import date
from decimal import Decimal

from rules import GoodsReceipt, Invoice, PoHeader, PoItem, SapContext

D = Decimal

ACCOUNT = "000000000000"  # placeholder; the real run uses the AWS account id
DOC_DATE = date(2025, 3, 15)  # inside the open posting period
COMPANY = "1010"
CURRENCY = "EUR"


def invoice(
    source_file: str,
    seq: int,
    supplier: str,
    purchase_order: str,
    material: str,
    quantity: str,
    unit_price: str,
    tax_code: str,
    tax_amount: str,
    *,
    item: str = "10",
    net_amount: str | None = None,
    gross_amount: str | None = None,
    invoice_date: date = DOC_DATE,
    company_code: str = COMPANY,
    currency: str = CURRENCY,
    reference: str | None = None,
) -> Invoice:
    """Build one invoice. Net and gross default to the arithmetically correct
    values so a test only states the numbers it deliberately breaks."""
    net = D(net_amount) if net_amount is not None else D(quantity) * D(unit_price)
    gross = D(gross_amount) if gross_amount is not None else net + D(tax_amount)
    return Invoice(
        source_file=source_file,
        reference=reference or f"{ACCOUNT}-{seq}",
        supplier=supplier,
        purchase_order=purchase_order,
        purchase_order_item=item,
        invoice_date=invoice_date,
        company_code=company_code,
        currency=currency,
        material=material,
        quantity=D(quantity),
        unit="PC",
        unit_price=D(unit_price),
        net_amount=net,
        tax_code=tax_code,
        tax_amount=D(tax_amount),
        gross_amount=gross,
    )


def context(
    purchase_order: str,
    supplier: str,
    material: str,
    quantity: str,
    net_price: str,
    *,
    item: str = "10",
    received: str | None = None,
    already_invoiced: str = "0",
    used_references: frozenset[str] = frozenset(),
    **header_flags: bool,
) -> SapContext:
    """SAP state for one invoice. `received` defaults to the full PO quantity,
    i.e. the goods receipt is complete."""
    receipts = []
    gr_qty = D(received) if received is not None else D(quantity)
    if gr_qty > 0:
        receipts.append(
            GoodsReceipt(
                purchase_order=purchase_order,
                purchase_order_item=item,
                quantity=gr_qty,
                unit="PC",
                movement_type="101",
            )
        )
    return SapContext(
        po_header=PoHeader(
            purchase_order=purchase_order,
            supplier=supplier,
            company_code=COMPANY,
            currency=CURRENCY,
            **header_flags,
        ),
        po_item=PoItem(
            purchase_order=purchase_order,
            item=item,
            material=material,
            quantity=D(quantity),
            unit="PC",
            net_price=D(net_price),
            already_invoiced_quantity=D(already_invoiced),
        ),
        goods_receipts=receipts,
        used_references=used_references,
    )


# The five purchase orders that exist in the demo system, plus the one that
# does not. (purchase_order, supplier, material, quantity, unit_price)
DEMO_POS = [
    ("4500001463", "10300006", "QM003", "5", "10.00", "V1", "9.50"),
    ("4500001563", "17401710", "TG12", "10", "11.35", "V0", "0.00"),
    ("4500001638", "17401710", "TG12", "10", "11.35", "V0", "0.00"),
    ("4500001650", "17401710", "TG12", "10", "11.35", "V0", "0.00"),
    ("4500001697", "17401710", "TG12", "10", "11.35", "V0", "0.00"),
]


def workshop_batch() -> tuple[list[Invoice], list[SapContext]]:
    """Six invoices: five clean, one against a purchase order that does not exist."""
    invoices, contexts = [], []
    for seq, (po, supplier, material, qty, price, tax_code, tax) in enumerate(DEMO_POS, 1):
        invoices.append(
            invoice(f"fpl-invoice-{seq:02d}.pdf", seq, supplier, po, material, qty, price, tax_code, tax)
        )
        contexts.append(context(po, supplier, material, qty, price))

    # Looks like a normal invoice; the purchase order simply is not in SAP.
    invoices.append(
        invoice("fpl-invoice-06.pdf", 6, "17401710", "4500009999", "TG12", "10", "11.35", "V0", "0.00")
    )
    contexts.append(SapContext())
    return invoices, contexts


def variance_batch() -> tuple[list[Invoice], list[SapContext]]:
    """Exception cases that exercise the tolerance bands and the hard blocks."""
    po, supplier, material, qty, price = "4500001563", "17401710", "TG12", "10", "11.35"
    invoices, contexts = [], []

    def add(inv: Invoice, ctx: SapContext) -> None:
        invoices.append(inv)
        contexts.append(ctx)

    # Price 0.35% over the PO and EUR 0.40 in total: inside the auto-approve band.
    add(
        invoice("variance-price-minor.pdf", 11, supplier, po, material, qty, "11.39", "V0", "0.00"),
        context(po, supplier, material, qty, price),
    )
    # Price 3.17% over the PO: outside auto-approve, needs an AP Manager.
    add(
        invoice("variance-price-manager.pdf", 12, supplier, po, material, qty, "11.71", "V0", "0.00"),
        context(po, supplier, material, qty, price),
    )
    # Partial delivery, full invoice: 30 billed against 10 received. The
    # over-billed 20 PC are worth EUR 227.00, above the clerk limit.
    add(
        invoice("variance-overdelivery.pdf", 13, supplier, po, material, "30", price, "V0", "0.00"),
        context(po, supplier, material, "30", price, received="10"),
    )
    # Invoice from a supplier that does not own the purchase order.
    add(
        invoice("exception-vendor-mismatch.pdf", 14, "99999999", po, material, qty, price, "V0", "0.00"),
        context(po, supplier, material, qty, price),
    )
    # Reference already consumed for this vendor in SAP.
    add(
        invoice("exception-duplicate.pdf", 15, supplier, po, material, qty, price, "V0", "0.00"),
        context(po, supplier, material, qty, price, used_references=frozenset({f"{ACCOUNT}-15"})),
    )
    # Document dated outside the open posting period.
    add(
        invoice(
            "exception-closed-period.pdf", 16, supplier, po, material, qty, price, "V0", "0.00",
            invoice_date=date(2026, 8, 6),
        ),
        context(po, supplier, material, qty, price),
    )
    return invoices, contexts
