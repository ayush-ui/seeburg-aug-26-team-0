"""Deterministic three-way-match validation for supplier invoices.

Pure by design: no network, no SAP client, no clock, no globals. Everything a
rule needs arrives inside `SapContext`, so the whole rule set runs against
fixtures with no credentials and no VPN. The agent extracts; this module
judges. Judgement stays reproducible and diffable.

Routing thresholds come from AP-SOP-001 (Three-Way Match Exception Handling),
section 8.1 "Monetary Tolerance Table". They live in `TOLERANCES` as data, so
changing a threshold is a one-line edit, not a code change.
"""

from dataclasses import dataclass, field
from datetime import date
from decimal import Decimal
from enum import IntEnum

D = Decimal
ZERO = D("0")


class Status(IntEnum):
    """Outcome of a single rule."""

    PASS = 0
    WARN = 1  # variance inside an escalation band; parkable with approval
    FAIL = 2  # blocks parking of this invoice
    NOT_APPLICABLE = 3  # could not be evaluated (an upstream rule failed)


class Routing(IntEnum):
    """Who must sign off. Ordered, so `max()` gives the highest demand."""

    AUTO_APPROVE = 0
    CLERK = 1
    MANAGER = 2
    CONTROLLER = 3


@dataclass(frozen=True)
class Tolerance:
    """One row of AP-SOP-001 section 8.1."""

    auto_abs: Decimal
    manager_abs: Decimal
    auto_pct: Decimal | None = None
    manager_pct: Decimal | None = None


# AP-SOP-001 section 8.1. Amounts are in document currency units; the SOP is
# written in USD but the thresholds are applied to whatever currency the
# invoice carries.
# ponytail: no FX normalisation, add a rate lookup when a non-EUR batch appears.
TOLERANCES = {
    "price": Tolerance(
        auto_abs=D("50"), auto_pct=D("0.5"), manager_abs=D("5000"), manager_pct=D("5")
    ),
    "quantity": Tolerance(auto_abs=D("100"), manager_abs=D("2500")),
    "tax": Tolerance(auto_abs=D("25"), manager_abs=D("500")),
}


def band(category: str, abs_variance: Decimal, pct_variance: Decimal | None = None) -> Routing:
    """Map a variance onto an approval level using the SOP tolerance table.

    The SOP writes the auto-approve row as "<= 0.5% or <= $50 (whichever is
    lower)". "Whichever is lower" means the stricter limit governs, so both
    conditions must hold to auto-approve. Escalation to Controller triggers if
    *either* limit is breached. Money path: prefer the conservative reading.
    """
    t = TOLERANCES[category]
    abs_variance = abs(abs_variance)
    pct_variance = abs(pct_variance) if pct_variance is not None else None

    within_auto = abs_variance <= t.auto_abs
    if t.auto_pct is not None and pct_variance is not None:
        within_auto = within_auto and pct_variance <= t.auto_pct
    if within_auto:
        return Routing.AUTO_APPROVE

    over_manager = abs_variance > t.manager_abs
    if t.manager_pct is not None and pct_variance is not None:
        over_manager = over_manager or pct_variance > t.manager_pct
    return Routing.CONTROLLER if over_manager else Routing.MANAGER


@dataclass(frozen=True)
class Finding:
    """One rule's verdict on one invoice."""

    rule_id: str
    rule_name: str
    status: Status
    message: str
    sop_ref: str = ""
    invoice_value: str = ""
    sap_value: str = ""
    delta: str = ""
    routing: Routing = Routing.AUTO_APPROVE


# --------------------------------------------------------------------------
# Inputs
# --------------------------------------------------------------------------


@dataclass
class Invoice:
    """Fields extracted from the supplier's PDF, already normalised.

    Amounts are Decimal, never float: rules 10 and 11 are pure arithmetic
    reconciliation and a float rounding artifact would invent an exception that
    does not exist. German invoices print "113,50"; convert at extraction, the
    type here is the guard.
    """

    source_file: str
    reference: str  # SupplierInvoiceIDByInvcgParty, e.g. "922513818191-1"
    supplier: str
    purchase_order: str
    purchase_order_item: str
    invoice_date: date
    company_code: str
    currency: str
    material: str
    quantity: Decimal
    unit: str
    unit_price: Decimal
    net_amount: Decimal
    tax_code: str
    tax_amount: Decimal
    gross_amount: Decimal


@dataclass
class PoHeader:
    purchase_order: str
    supplier: str
    company_code: str
    currency: str
    is_deleted: bool = False
    is_blocked: bool = False
    is_fully_invoiced: bool = False


@dataclass
class PoItem:
    purchase_order: str
    item: str
    material: str
    quantity: Decimal
    unit: str
    net_price: Decimal
    already_invoiced_quantity: Decimal = ZERO
    gr_based_invoice_verification: bool = True


@dataclass
class GoodsReceipt:
    purchase_order: str
    purchase_order_item: str
    quantity: Decimal
    unit: str
    movement_type: str  # 101 receipt, 102 reversal


@dataclass
class SapContext:
    """Everything read from SAP before evaluation. Reads happen elsewhere."""

    po_header: PoHeader | None = None
    po_item: PoItem | None = None
    goods_receipts: list[GoodsReceipt] = field(default_factory=list)
    valid_tax_codes: frozenset[str] = frozenset({"V0", "V1"})
    open_period: tuple[date, date] = (date(2025, 1, 1), date(2025, 12, 31))
    # References already consumed for this vendor: prior SAP documents plus any
    # invoice processed earlier in the current batch. The caller adds to this
    # as it walks the batch, which is what catches an in-batch collision.
    used_references: frozenset[str] = frozenset()


# --------------------------------------------------------------------------
# Rules
# --------------------------------------------------------------------------

MANDATORY_FIELDS = (
    "reference",
    "supplier",
    "purchase_order",
    "purchase_order_item",
    "company_code",
    "currency",
    "tax_code",
)


def _na(rule_id: str, rule_name: str, because: str) -> Finding:
    return Finding(
        rule_id=rule_id,
        rule_name=rule_name,
        status=Status.NOT_APPLICABLE,
        message=f"Not checked - {because}.",
    )


def _money(value: Decimal, currency: str) -> str:
    return f"{currency} {value:,.2f}"


def _pct(value: Decimal) -> str:
    return f"{value:+.2f}%"


def evaluate(inv: Invoice, sap: SapContext) -> list[Finding]:
    """Run every rule against one invoice. Order of the returned list is stable."""
    findings: list[Finding] = []
    header, item = sap.po_header, sap.po_item

    # --- R01 Purchase Order exists -------------------------------------
    if header is None:
        findings.append(
            Finding(
                "R01",
                "Purchase Order exists",
                Status.FAIL,
                f"Purchase Order {inv.purchase_order} does not exist in SAP. "
                "The invoice cannot be matched and must be held pending a "
                "retrospective PO from Procurement.",
                sop_ref="AP-SOP-001 6.3",
                invoice_value=inv.purchase_order,
                sap_value="not found",
                routing=Routing.CLERK,
            )
        )
    else:
        findings.append(
            Finding(
                "R01",
                "Purchase Order exists",
                Status.PASS,
                f"Purchase Order {header.purchase_order} found in SAP.",
                invoice_value=inv.purchase_order,
                sap_value=header.purchase_order,
            )
        )

    no_header = "purchase order was not found"

    # --- R02 Purchase Order is open ------------------------------------
    if header is None:
        findings.append(_na("R02", "Purchase Order is open", no_header))
    else:
        blockers = [
            name
            for name, flag in (
                ("marked for deletion", header.is_deleted),
                ("blocked", header.is_blocked),
                ("fully invoiced", header.is_fully_invoiced),
            )
            if flag
        ]
        if blockers:
            findings.append(
                Finding(
                    "R02",
                    "Purchase Order is open",
                    Status.FAIL,
                    f"Purchase Order {header.purchase_order} is {' and '.join(blockers)} "
                    "and cannot be invoiced as-is.",
                    sop_ref="AP-SOP-001 6.3",
                    sap_value=", ".join(blockers),
                    routing=Routing.CLERK,
                )
            )
        else:
            findings.append(
                Finding(
                    "R02",
                    "Purchase Order is open",
                    Status.PASS,
                    "Purchase Order is open and available to invoice.",
                    sap_value="open",
                )
            )

    # --- R03 PO line item exists ---------------------------------------
    if header is None:
        findings.append(_na("R03", "PO line item exists", no_header))
    elif item is None:
        findings.append(
            Finding(
                "R03",
                "PO line item exists",
                Status.FAIL,
                f"Item {inv.purchase_order_item} does not exist on Purchase Order "
                f"{inv.purchase_order}.",
                sop_ref="AP-SOP-001 6.3",
                invoice_value=inv.purchase_order_item,
                sap_value="not found",
                routing=Routing.CLERK,
            )
        )
    else:
        findings.append(
            Finding(
                "R03",
                "PO line item exists",
                Status.PASS,
                f"Item {item.item} found on Purchase Order {item.purchase_order}.",
                invoice_value=inv.purchase_order_item,
                sap_value=item.item,
            )
        )

    no_item = "purchase order item was not found"

    # --- R04 Supplier matches ------------------------------------------
    # Escalates straight to Controller: a vendor that does not match the PO is
    # the primary Business Email Compromise vector (AP-SOP-001 6.6).
    if header is None:
        findings.append(_na("R04", "Supplier matches PO vendor", no_header))
    elif inv.supplier != header.supplier:
        findings.append(
            Finding(
                "R04",
                "Supplier matches PO vendor",
                Status.FAIL,
                f"Invoice is from supplier {inv.supplier} but Purchase Order "
                f"{header.purchase_order} belongs to supplier {header.supplier}. "
                "Do not pay - verify the supplier by callback to a contact already "
                "on file, not to any contact printed on this invoice.",
                sop_ref="AP-SOP-001 6.6",
                invoice_value=inv.supplier,
                sap_value=header.supplier,
                routing=Routing.CONTROLLER,
            )
        )
    else:
        findings.append(
            Finding(
                "R04",
                "Supplier matches PO vendor",
                Status.PASS,
                f"Supplier {inv.supplier} matches the Purchase Order vendor.",
                invoice_value=inv.supplier,
                sap_value=header.supplier,
            )
        )

    # --- R05 Company code matches --------------------------------------
    if header is None:
        findings.append(_na("R05", "Company code matches", no_header))
    elif inv.company_code != header.company_code:
        findings.append(
            Finding(
                "R05",
                "Company code matches",
                Status.FAIL,
                f"Invoice is booked to company code {inv.company_code} but the "
                f"Purchase Order belongs to {header.company_code}.",
                invoice_value=inv.company_code,
                sap_value=header.company_code,
                routing=Routing.CLERK,
            )
        )
    else:
        findings.append(
            Finding(
                "R05",
                "Company code matches",
                Status.PASS,
                f"Company code {inv.company_code} matches the Purchase Order.",
                invoice_value=inv.company_code,
                sap_value=header.company_code,
            )
        )

    # --- R06 Currency matches ------------------------------------------
    if header is None:
        findings.append(_na("R06", "Currency matches", no_header))
    elif inv.currency != header.currency:
        findings.append(
            Finding(
                "R06",
                "Currency matches",
                Status.FAIL,
                f"Invoice is in {inv.currency} but the Purchase Order was agreed in "
                f"{header.currency}. Request a reissued invoice in the agreed currency.",
                sop_ref="AP-SOP-001 6.7",
                invoice_value=inv.currency,
                sap_value=header.currency,
                routing=Routing.CLERK,
            )
        )
    else:
        findings.append(
            Finding(
                "R06",
                "Currency matches",
                Status.PASS,
                f"Currency {inv.currency} matches the Purchase Order.",
                invoice_value=inv.currency,
                sap_value=header.currency,
            )
        )

    # --- R07 Material matches ------------------------------------------
    if item is None:
        findings.append(_na("R07", "Material matches", no_item if header else no_header))
    elif inv.material != item.material:
        findings.append(
            Finding(
                "R07",
                "Material matches",
                Status.FAIL,
                f"Invoice bills material {inv.material} but Purchase Order item "
                f"{item.item} is for material {item.material}.",
                invoice_value=inv.material,
                sap_value=item.material,
                routing=Routing.CLERK,
            )
        )
    else:
        findings.append(
            Finding(
                "R07",
                "Material matches",
                Status.PASS,
                f"Material {inv.material} matches the Purchase Order item.",
                invoice_value=inv.material,
                sap_value=item.material,
            )
        )

    # --- R08 Quantity within tolerance ---------------------------------
    if item is None:
        findings.append(_na("R08", "Quantity within PO tolerance", no_item if header else no_header))
    else:
        open_qty = item.quantity - item.already_invoiced_quantity
        over = inv.quantity - open_qty
        if over <= ZERO:
            findings.append(
                Finding(
                    "R08",
                    "Quantity within PO tolerance",
                    Status.PASS,
                    f"Invoiced {inv.quantity:g} {inv.unit} against {open_qty:g} "
                    f"{item.unit} still open on the Purchase Order.",
                    invoice_value=f"{inv.quantity:g} {inv.unit}",
                    sap_value=f"{open_qty:g} {item.unit} open",
                )
            )
        else:
            value = over * item.net_price
            routing = band("quantity", value)
            findings.append(
                Finding(
                    "R08",
                    "Quantity within PO tolerance",
                    Status.PASS if routing is Routing.AUTO_APPROVE else Status.WARN,
                    f"Invoice bills {inv.quantity:g} {inv.unit} but only "
                    f"{open_qty:g} {item.unit} remain open on the Purchase Order - "
                    f"over-billed by {over:g} {item.unit} "
                    f"({_money(value, inv.currency)}).",
                    sop_ref="AP-SOP-001 6.2 / 8.1",
                    invoice_value=f"{inv.quantity:g} {inv.unit}",
                    sap_value=f"{open_qty:g} {item.unit} open",
                    delta=f"+{over:g} {item.unit} ({_money(value, inv.currency)})",
                    routing=routing,
                )
            )

    # --- R09 Unit price within tolerance -------------------------------
    if item is None:
        findings.append(_na("R09", "Unit price within tolerance", no_item if header else no_header))
    elif item.net_price == ZERO:
        findings.append(_na("R09", "Unit price within tolerance", "purchase order price is zero"))
    else:
        diff = inv.unit_price - item.net_price
        pct = diff / item.net_price * D("100")
        value = abs(diff) * inv.quantity
        if diff == ZERO:
            findings.append(
                Finding(
                    "R09",
                    "Unit price within tolerance",
                    Status.PASS,
                    f"Unit price {_money(inv.unit_price, inv.currency)} matches the "
                    "Purchase Order price.",
                    invoice_value=_money(inv.unit_price, inv.currency),
                    sap_value=_money(item.net_price, inv.currency),
                )
            )
        else:
            routing = band("price", value, pct)
            direction = "above" if diff > ZERO else "below"
            findings.append(
                Finding(
                    "R09",
                    "Unit price within tolerance",
                    Status.PASS if routing is Routing.AUTO_APPROVE else Status.WARN,
                    f"Unit price {_money(inv.unit_price, inv.currency)} is "
                    f"{abs(pct):.2f}% {direction} the agreed Purchase Order price of "
                    f"{_money(item.net_price, inv.currency)} - a difference of "
                    f"{_money(abs(value), inv.currency)} on this line.",
                    sop_ref="AP-SOP-001 6.1 / 8.1",
                    invoice_value=_money(inv.unit_price, inv.currency),
                    sap_value=_money(item.net_price, inv.currency),
                    delta=f"{_pct(pct)} ({_money(diff * inv.quantity, inv.currency)})",
                    routing=routing,
                )
            )

    # --- R10 Line amount = quantity x unit price -----------------------
    expected_net = (inv.quantity * inv.unit_price).quantize(D("0.01"))
    if expected_net == inv.net_amount.quantize(D("0.01")):
        findings.append(
            Finding(
                "R10",
                "Line amount reconciles",
                Status.PASS,
                f"Net {_money(inv.net_amount, inv.currency)} equals {inv.quantity:g} "
                f"x {_money(inv.unit_price, inv.currency)}.",
                invoice_value=_money(inv.net_amount, inv.currency),
                sap_value=_money(expected_net, inv.currency),
            )
        )
    else:
        findings.append(
            Finding(
                "R10",
                "Line amount reconciles",
                Status.FAIL,
                f"Invoice net of {_money(inv.net_amount, inv.currency)} does not equal "
                f"{inv.quantity:g} x {_money(inv.unit_price, inv.currency)} = "
                f"{_money(expected_net, inv.currency)}. The invoice is internally "
                "inconsistent - request a corrected document.",
                invoice_value=_money(inv.net_amount, inv.currency),
                sap_value=_money(expected_net, inv.currency),
                delta=_money(inv.net_amount - expected_net, inv.currency),
                routing=Routing.CLERK,
            )
        )

    # --- R11 Gross = net + tax -----------------------------------------
    expected_gross = (inv.net_amount + inv.tax_amount).quantize(D("0.01"))
    gross_diff = inv.gross_amount.quantize(D("0.01")) - expected_gross
    if gross_diff == ZERO:
        findings.append(
            Finding(
                "R11",
                "Gross reconciles to lines plus tax",
                Status.PASS,
                f"Gross {_money(inv.gross_amount, inv.currency)} equals net "
                f"{_money(inv.net_amount, inv.currency)} plus tax "
                f"{_money(inv.tax_amount, inv.currency)}.",
                invoice_value=_money(inv.gross_amount, inv.currency),
                sap_value=_money(expected_gross, inv.currency),
            )
        )
    else:
        routing = band("tax", gross_diff)
        findings.append(
            Finding(
                "R11",
                "Gross reconciles to lines plus tax",
                Status.PASS if routing is Routing.AUTO_APPROVE else Status.WARN,
                f"Gross {_money(inv.gross_amount, inv.currency)} does not equal net "
                f"{_money(inv.net_amount, inv.currency)} plus tax "
                f"{_money(inv.tax_amount, inv.currency)} = "
                f"{_money(expected_gross, inv.currency)}.",
                sop_ref="AP-SOP-001 6.8 / 8.1",
                invoice_value=_money(inv.gross_amount, inv.currency),
                sap_value=_money(expected_gross, inv.currency),
                delta=_money(gross_diff, inv.currency),
                routing=routing,
            )
        )

    # --- R12 Goods Receipt exists --------------------------------------
    received = sum(
        (gr.quantity if gr.movement_type == "101" else -gr.quantity)
        for gr in sap.goods_receipts
    ) or ZERO
    if item is None:
        findings.append(_na("R12", "Goods Receipt exists", no_item if header else no_header))
    elif not item.gr_based_invoice_verification:
        findings.append(
            _na("R12", "Goods Receipt exists", "purchase order item is not GR-based")
        )
    elif received <= ZERO:
        findings.append(
            Finding(
                "R12",
                "Goods Receipt exists",
                Status.FAIL,
                f"No goods receipt is posted against Purchase Order "
                f"{inv.purchase_order} item {inv.purchase_order_item}. The three-way "
                "match cannot complete until the warehouse confirms delivery.",
                sop_ref="AP-SOP-001 6.4",
                sap_value="no GR",
                routing=Routing.CLERK,
            )
        )
    else:
        findings.append(
            Finding(
                "R12",
                "Goods Receipt exists",
                Status.PASS,
                f"Goods receipt posted for {received:g} {item.unit}.",
                sap_value=f"{received:g} {item.unit} received",
            )
        )

    # --- R13 GR quantity sufficient ------------------------------------
    if item is None:
        findings.append(_na("R13", "Goods Receipt quantity sufficient", no_item if header else no_header))
    elif not item.gr_based_invoice_verification:
        findings.append(
            _na("R13", "Goods Receipt quantity sufficient", "purchase order item is not GR-based")
        )
    elif received <= ZERO:
        findings.append(_na("R13", "Goods Receipt quantity sufficient", "no goods receipt exists"))
    else:
        over = inv.quantity - received
        if over <= ZERO:
            findings.append(
                Finding(
                    "R13",
                    "Goods Receipt quantity sufficient",
                    Status.PASS,
                    f"Invoiced {inv.quantity:g} {inv.unit} is covered by {received:g} "
                    f"{item.unit} received.",
                    invoice_value=f"{inv.quantity:g} {inv.unit}",
                    sap_value=f"{received:g} {item.unit}",
                )
            )
        else:
            value = over * item.net_price
            routing = band("quantity", value)
            findings.append(
                Finding(
                    "R13",
                    "Goods Receipt quantity sufficient",
                    Status.PASS if routing is Routing.AUTO_APPROVE else Status.WARN,
                    f"Invoice bills {inv.quantity:g} {inv.unit} but only {received:g} "
                    f"{item.unit} were actually received - over-delivered billing of "
                    f"{over:g} {item.unit} ({_money(value, inv.currency)}). Pay only "
                    "for the quantity received and request a credit note.",
                    sop_ref="AP-SOP-001 6.2 / 8.1",
                    invoice_value=f"{inv.quantity:g} {inv.unit}",
                    sap_value=f"{received:g} {item.unit}",
                    delta=f"+{over:g} {item.unit} ({_money(value, inv.currency)})",
                    routing=routing,
                )
            )

    # --- R14 Tax code valid --------------------------------------------
    if inv.tax_code in sap.valid_tax_codes:
        findings.append(
            Finding(
                "R14",
                "Tax code valid",
                Status.PASS,
                f"Tax code {inv.tax_code} is permitted for company code "
                f"{inv.company_code}.",
                invoice_value=inv.tax_code,
                sap_value=", ".join(sorted(sap.valid_tax_codes)),
            )
        )
    else:
        findings.append(
            Finding(
                "R14",
                "Tax code valid",
                Status.FAIL,
                f"Tax code {inv.tax_code} is not permitted for company code "
                f"{inv.company_code}. Permitted: "
                f"{', '.join(sorted(sap.valid_tax_codes))}.",
                sop_ref="AP-SOP-001 6.8",
                invoice_value=inv.tax_code,
                sap_value=", ".join(sorted(sap.valid_tax_codes)),
                routing=Routing.CLERK,
            )
        )

    # --- R15 Posting date in an open period ----------------------------
    period_start, period_end = sap.open_period
    if period_start <= inv.invoice_date <= period_end:
        findings.append(
            Finding(
                "R15",
                "Posting date in an open period",
                Status.PASS,
                f"Document date {inv.invoice_date:%Y-%m-%d} falls in the open posting "
                f"period.",
                invoice_value=f"{inv.invoice_date:%Y-%m-%d}",
                sap_value=f"{period_start:%Y-%m-%d} to {period_end:%Y-%m-%d}",
            )
        )
    else:
        findings.append(
            Finding(
                "R15",
                "Posting date in an open period",
                Status.FAIL,
                f"Document date {inv.invoice_date:%Y-%m-%d} is outside the open "
                f"posting period ({period_start:%Y-%m-%d} to {period_end:%Y-%m-%d}). "
                "SAP will reject the posting.",
                invoice_value=f"{inv.invoice_date:%Y-%m-%d}",
                sap_value=f"{period_start:%Y-%m-%d} to {period_end:%Y-%m-%d}",
                routing=Routing.CLERK,
            )
        )

    # --- R16 Duplicate invoice reference -------------------------------
    # Scoped per vendor, and `used_references` also carries references consumed
    # earlier in this same batch - that is what catches an in-batch collision.
    if inv.reference in sap.used_references:
        findings.append(
            Finding(
                "R16",
                "Not a duplicate",
                Status.FAIL,
                f"Reference {inv.reference} has already been used for supplier "
                f"{inv.supplier}. Rejecting as a duplicate - confirm the payment "
                "status of the original before contacting the supplier.",
                sop_ref="AP-SOP-001 6.5",
                invoice_value=inv.reference,
                sap_value="already used",
                routing=Routing.CLERK,
            )
        )
    else:
        findings.append(
            Finding(
                "R16",
                "Not a duplicate",
                Status.PASS,
                f"Reference {inv.reference} is unused for supplier {inv.supplier}.",
                invoice_value=inv.reference,
            )
        )

    # --- R17 Mandatory fields complete ---------------------------------
    missing = [name for name in MANDATORY_FIELDS if not getattr(inv, name)]
    if inv.gross_amount <= ZERO:
        missing.append("gross_amount")
    if missing:
        findings.append(
            Finding(
                "R17",
                "Mandatory fields complete",
                Status.FAIL,
                "SAP requires fields that the invoice does not supply: "
                f"{', '.join(missing)}.",
                invoice_value=f"missing: {', '.join(missing)}",
                routing=Routing.CLERK,
            )
        )
    else:
        findings.append(
            Finding(
                "R17",
                "Mandatory fields complete",
                Status.PASS,
                "All fields SAP requires to park the invoice are present.",
            )
        )

    return findings


# --------------------------------------------------------------------------
# Batch outcome
# --------------------------------------------------------------------------


@dataclass
class Outcome:
    """What the agent should do with one invoice, and how to say why."""

    invoice: Invoice
    findings: list[Finding]

    @property
    def failures(self) -> list[Finding]:
        return [f for f in self.findings if f.status is Status.FAIL]

    @property
    def warnings(self) -> list[Finding]:
        return [f for f in self.findings if f.status is Status.WARN]

    @property
    def can_park(self) -> bool:
        """A FAIL blocks the write-back. A WARN does not - it raises the bar."""
        return not self.failures

    @property
    def required_approval(self) -> Routing:
        return max(
            (f.routing for f in self.findings if f.status in (Status.FAIL, Status.WARN)),
            default=Routing.AUTO_APPROVE,
        )

    @property
    def headline(self) -> str:
        if self.failures:
            return self.failures[0].message
        if self.warnings:
            return self.warnings[0].message
        return "All checks passed against live SAP data."

    @property
    def counts(self) -> dict[str, int]:
        return {
            status.name.lower(): sum(1 for f in self.findings if f.status is status)
            for status in Status
        }


def evaluate_batch(invoices: list[Invoice], contexts: list[SapContext]) -> list[Outcome]:
    """Evaluate a whole batch, threading used references between invoices.

    A failure on one invoice never stops the others - that is the point of the
    batch flow. Each invoice's reference is added to the pool afterwards so a
    later invoice reusing it trips R16.
    """
    outcomes: list[Outcome] = []
    consumed: set[str] = set()
    for inv, ctx in zip(invoices, contexts, strict=True):
        scoped = SapContext(
            po_header=ctx.po_header,
            po_item=ctx.po_item,
            goods_receipts=ctx.goods_receipts,
            valid_tax_codes=ctx.valid_tax_codes,
            open_period=ctx.open_period,
            used_references=ctx.used_references | frozenset(consumed),
        )
        outcomes.append(Outcome(invoice=inv, findings=evaluate(inv, scoped)))
        consumed.add(inv.reference)
    return outcomes
