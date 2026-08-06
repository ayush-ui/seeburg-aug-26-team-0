"""Regression net for the validation rules.

Runs in under a second with no SAP, no AWS and no network - so a threshold can
be changed at 2am and the consequences are visible immediately.

    python test_rules.py        # or: pytest test_rules.py
"""

from datetime import date
from decimal import Decimal

import fixtures
from rules import Routing, Status, band, evaluate, evaluate_batch

D = Decimal


def _by_id(findings) -> dict[str, object]:
    return {f.rule_id: f for f in findings}


# --- the tolerance table itself -------------------------------------------


def test_price_band_edges():
    # Inside both limits: auto-approve.
    assert band("price", D("40"), D("0.4")) is Routing.AUTO_APPROVE
    # Percentage breaches while the absolute amount does not: still escalates,
    # because "whichever is lower" means the stricter limit governs.
    assert band("price", D("40"), D("0.6")) is Routing.MANAGER
    # Absolute breaches while the percentage does not.
    assert band("price", D("60"), D("0.1")) is Routing.MANAGER
    # Either limit past the manager band goes to the controller.
    assert band("price", D("60"), D("6")) is Routing.CONTROLLER
    assert band("price", D("6000"), D("0.1")) is Routing.CONTROLLER


def test_quantity_and_tax_bands():
    assert band("quantity", D("100")) is Routing.AUTO_APPROVE
    assert band("quantity", D("101")) is Routing.MANAGER
    assert band("quantity", D("2501")) is Routing.CONTROLLER
    assert band("tax", D("25")) is Routing.AUTO_APPROVE
    assert band("tax", D("26")) is Routing.MANAGER
    assert band("tax", D("501")) is Routing.CONTROLLER


def test_band_is_sign_agnostic():
    assert band("price", D("-60"), D("-0.6")) is Routing.MANAGER


# --- the demo batch -------------------------------------------------------


def test_clean_invoices_pass_every_rule():
    invoices, contexts = fixtures.workshop_batch()
    outcomes = evaluate_batch(invoices, contexts)

    for outcome in outcomes[:5]:
        failed = [f.rule_id for f in outcome.findings if f.status is not Status.PASS]
        assert not failed, f"{outcome.invoice.source_file} unexpectedly flagged {failed}"
        assert outcome.can_park
        assert outcome.required_approval is Routing.AUTO_APPROVE
        assert len(outcome.findings) == 17


def test_missing_po_fails_once_and_skips_the_rest():
    """The failing invoice must report 1 FAIL, not 13. Rules that depend on a
    purchase order are NOT_APPLICABLE when there is no purchase order to read."""
    invoices, contexts = fixtures.workshop_batch()
    outcome = evaluate_batch(invoices, contexts)[5]
    rules = _by_id(outcome.findings)

    assert rules["R01"].status is Status.FAIL
    assert not outcome.can_park
    assert outcome.counts["fail"] == 1
    assert outcome.counts["not_applicable"] == 10
    assert outcome.counts["pass"] == 6

    # Rules needing no SAP read still run, even with SAP effectively absent.
    for rule_id in ("R10", "R11", "R14", "R15", "R16", "R17"):
        assert rules[rule_id].status is Status.PASS

    assert "4500009999" in outcome.headline
    assert "does not exist" in outcome.headline


def test_batch_summary_is_five_pass_one_fail():
    invoices, contexts = fixtures.workshop_batch()
    outcomes = evaluate_batch(invoices, contexts)
    assert sum(o.can_park for o in outcomes) == 5
    assert sum(not o.can_park for o in outcomes) == 1


# --- exception intelligence ----------------------------------------------


def test_price_variance_inside_tolerance_is_not_an_exception():
    invoices, contexts = fixtures.variance_batch()
    outcome = evaluate_batch(invoices, contexts)[0]
    assert _by_id(outcome.findings)["R09"].status is Status.PASS
    assert outcome.can_park
    assert outcome.required_approval is Routing.AUTO_APPROVE


def test_price_variance_routes_to_manager_and_explains_itself():
    invoices, contexts = fixtures.variance_batch()
    outcome = evaluate_batch(invoices, contexts)[1]
    finding = _by_id(outcome.findings)["R09"]

    assert finding.status is Status.WARN
    assert finding.routing is Routing.MANAGER
    assert "3.17% above" in finding.message
    assert "AP-SOP-001" in finding.sop_ref
    # A WARN raises the approval bar but does not block the write-back.
    assert outcome.can_park
    assert outcome.required_approval is Routing.MANAGER


def test_over_delivery_is_caught_against_the_goods_receipt():
    invoices, contexts = fixtures.variance_batch()
    outcome = evaluate_batch(invoices, contexts)[2]
    rules = _by_id(outcome.findings)

    # Within the PO quantity, so R08 is happy; the goods receipt is what fails.
    assert rules["R08"].status is Status.PASS
    assert rules["R13"].status is Status.WARN
    assert rules["R13"].routing is Routing.MANAGER
    assert "only 10 PC were actually received" in rules["R13"].message
    assert "EUR 227.00" in rules["R13"].message


def test_vendor_mismatch_escalates_to_controller():
    invoices, contexts = fixtures.variance_batch()
    outcome = evaluate_batch(invoices, contexts)[3]
    finding = _by_id(outcome.findings)["R04"]

    assert finding.status is Status.FAIL
    assert finding.routing is Routing.CONTROLLER
    assert not outcome.can_park
    assert "callback" in finding.message


def test_duplicate_reference_is_rejected():
    invoices, contexts = fixtures.variance_batch()
    outcome = evaluate_batch(invoices, contexts)[4]
    assert _by_id(outcome.findings)["R16"].status is Status.FAIL
    assert not outcome.can_park


def test_closed_posting_period_is_caught_before_sap_rejects_it():
    invoices, contexts = fixtures.variance_batch()
    outcome = evaluate_batch(invoices, contexts)[5]
    finding = _by_id(outcome.findings)["R15"]
    assert finding.status is Status.FAIL
    assert "outside the open" in finding.message


def test_in_batch_duplicate_reference_is_caught():
    """Two invoices in one upload carrying the same reference: the second trips
    R16 even though SAP has never seen either."""
    invoices, contexts = fixtures.workshop_batch()
    invoices[1].reference = invoices[0].reference

    outcomes = evaluate_batch(invoices, contexts)
    assert _by_id(outcomes[0].findings)["R16"].status is Status.PASS
    assert _by_id(outcomes[1].findings)["R16"].status is Status.FAIL


# --- arithmetic -----------------------------------------------------------


def test_line_arithmetic_mismatch_is_caught():
    inv = fixtures.invoice(
        "broken-line.pdf", 20, "17401710", "4500001563", "TG12", "10", "11.35", "V0", "0.00",
        net_amount="113.00",
    )
    ctx = fixtures.context("4500001563", "17401710", "TG12", "10", "11.35")
    rules = _by_id(evaluate(inv, ctx))
    assert rules["R10"].status is Status.FAIL
    assert "internally inconsistent" in rules["R10"].message


def test_gross_mismatch_routes_by_tax_band():
    inv = fixtures.invoice(
        "broken-gross.pdf", 21, "10300006", "4500001463", "QM003", "5", "10.00", "V1", "9.50",
        gross_amount="89.50",  # EUR 30.00 more than net + tax
    )
    ctx = fixtures.context("4500001463", "10300006", "QM003", "5", "10.00")
    rules = _by_id(evaluate(inv, ctx))
    assert rules["R11"].status is Status.WARN
    assert rules["R11"].routing is Routing.MANAGER


def test_decimal_arithmetic_does_not_invent_an_exception():
    """0.1 + 0.2 != 0.3 in binary floating point. Three lines of 0.10 that sum
    to 0.30 must reconcile exactly, or the demo shows a phantom exception."""
    inv = fixtures.invoice(
        "float-trap.pdf", 22, "17401710", "4500001563", "TG12", "3", "0.10", "V0", "0.00"
    )
    ctx = fixtures.context("4500001563", "17401710", "TG12", "3", "0.10")
    rules = _by_id(evaluate(inv, ctx))
    assert rules["R10"].status is Status.PASS
    assert rules["R11"].status is Status.PASS


def test_tax_code_not_permitted_for_company_code():
    inv = fixtures.invoice(
        "bad-tax-code.pdf", 23, "17401710", "4500001563", "TG12", "10", "11.35", "V9", "0.00"
    )
    ctx = fixtures.context("4500001563", "17401710", "TG12", "10", "11.35")
    assert _by_id(evaluate(inv, ctx))["R14"].status is Status.FAIL


def test_blocked_po_cannot_be_invoiced():
    inv = fixtures.invoice(
        "blocked-po.pdf", 24, "17401710", "4500001563", "TG12", "10", "11.35", "V0", "0.00"
    )
    ctx = fixtures.context("4500001563", "17401710", "TG12", "10", "11.35", is_blocked=True)
    finding = _by_id(evaluate(inv, ctx))["R02"]
    assert finding.status is Status.FAIL
    assert "blocked" in finding.message


def test_missing_goods_receipt_blocks_the_three_way_match():
    inv = fixtures.invoice(
        "no-gr.pdf", 25, "17401710", "4500001563", "TG12", "10", "11.35", "V0", "0.00"
    )
    ctx = fixtures.context("4500001563", "17401710", "TG12", "10", "11.35", received="0")
    rules = _by_id(evaluate(inv, ctx))
    assert rules["R12"].status is Status.FAIL
    # R13 cannot be judged when there is no receipt to judge against.
    assert rules["R13"].status is Status.NOT_APPLICABLE


def test_already_invoiced_quantity_reduces_what_is_open():
    """Second invoice against a PO already half consumed."""
    inv = fixtures.invoice(
        "second-invoice.pdf", 26, "17401710", "4500001563", "TG12", "10", "11.35", "V0", "0.00"
    )
    ctx = fixtures.context(
        "4500001563", "17401710", "TG12", "10", "11.35", already_invoiced="9"
    )
    finding = _by_id(evaluate(inv, ctx))["R08"]
    assert finding.status is Status.WARN  # 9 PC over, EUR 102.15 - past the clerk limit
    assert finding.routing is Routing.MANAGER


def test_every_invoice_gets_all_seventeen_rules():
    for builder in (fixtures.workshop_batch, fixtures.variance_batch):
        invoices, contexts = builder()
        for outcome in evaluate_batch(invoices, contexts):
            assert len(outcome.findings) == 17
            assert len({f.rule_id for f in outcome.findings}) == 17


def test_failures_never_stop_the_batch():
    """One bad invoice in the middle must not affect the ones after it."""
    good_inv, good_ctx = fixtures.workshop_batch()
    bad_inv, bad_ctx = fixtures.variance_batch()
    invoices = [good_inv[0], bad_inv[3], good_inv[1]]
    contexts = [good_ctx[0], bad_ctx[3], good_ctx[1]]

    outcomes = evaluate_batch(invoices, contexts)
    assert [o.can_park for o in outcomes] == [True, False, True]


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
