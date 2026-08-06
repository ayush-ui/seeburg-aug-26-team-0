"""The reports AP-SOP-001 section 9.3 already mandates, built from a batch.

Nothing here is invented. Every report in `CATALOGUE` appears in the SOP's
reporting table with the cadence and audience the SOP specifies, and the KPI
targets come from section 10.
"""

from __future__ import annotations

from rules import Status

CATALOGUE = [
    {"id": "exception-aging", "name": "Exception Aging Report", "cadence": "Weekly", "audience": "AP Manager"},
    {"id": "exception-volume", "name": "Exception Volume by Type", "cadence": "Monthly", "audience": "Finance Controller"},
    {"id": "vendor-scorecard", "name": "Vendor Exception Scorecard", "cadence": "Monthly", "audience": "Procurement"},
    {"id": "tolerance-breach", "name": "Tolerance Breach Summary", "cadence": "Monthly", "audience": "Finance Controller"},
    {"id": "duplicate-invoice", "name": "Duplicate Invoice Report", "cadence": "Monthly", "audience": "Finance Controller / Internal Audit"},
    {"id": "no-po-invoice", "name": "No-PO Invoice Report", "cadence": "Monthly", "audience": "Department Heads / Finance Controller"},
]

# AP-SOP-001 section 10.
KPI_TARGETS = [
    {"id": "exception-rate", "name": "Exception rate", "target": 5.0, "unit": "%"},
    {"id": "duplicate-rate", "name": "Duplicate invoice rate", "target": 0.5, "unit": "%"},
    {"id": "no-po-rate", "name": "No-PO invoice rate", "target": 2.0, "unit": "%"},
]


def _first_active(outcome):
    return next(
        (f for f in outcome.findings if f.status is Status.FAIL),
        next((f for f in outcome.findings if f.status is Status.WARN), None),
    )


def _rule_failed(outcome, rule_id: str) -> bool:
    return any(f.rule_id == rule_id and f.status is Status.FAIL for f in outcome.findings)


def build(report_id: str, outcomes: list) -> dict:
    exceptions = [o for o in outcomes if not o.can_park]
    warned = [o for o in outcomes if o.can_park and any(f.status is Status.WARN for f in o.findings)]

    if report_id == "exception-volume":
        counts: dict[str, int] = {}
        for outcome in exceptions + warned:
            finding = _first_active(outcome)
            if finding:
                counts[finding.rule_name] = counts.get(finding.rule_name, 0) + 1
        ordered = sorted(counts.items(), key=lambda kv: -kv[1])
        return {
            "title": "Exception Volume by Type",
            "subtitle": "AP-SOP-001 section 9.3 - monthly, for the Finance Controller",
            "columns": ["Exception type", "Count"],
            "rows": [[name, n] for name, n in ordered],
            "chart": [{"label": name, "value": n} for name, n in ordered],
        }

    if report_id == "vendor-scorecard":
        by_vendor: dict[str, dict] = {}
        for outcome in outcomes:
            key = outcome.invoice.supplier
            entry = by_vendor.setdefault(key, {"total": 0, "exceptions": 0})
            entry["total"] += 1
            if not outcome.can_park:
                entry["exceptions"] += 1
        return {
            "title": "Vendor Exception Scorecard",
            "subtitle": "AP-SOP-001 section 9.3 - monthly, for Procurement",
            "columns": ["Vendor", "Invoices", "Exceptions", "Rate"],
            "rows": [
                [vendor, v["total"], v["exceptions"], f"{v['exceptions'] / v['total'] * 100:.0f}%"]
                for vendor, v in by_vendor.items()
            ],
            "chart": [{"label": vendor, "value": v["exceptions"]} for vendor, v in by_vendor.items()],
        }

    if report_id == "tolerance-breach":
        rows = []
        for outcome in warned:
            finding = _first_active(outcome)
            rows.append([
                outcome.invoice.source_file,
                finding.rule_name,
                finding.delta or "-",
                outcome.required_approval.name.replace("_", " ").title(),
            ])
        return {
            "title": "Tolerance Breach Summary",
            "subtitle": "AP-SOP-001 section 9.3 - monthly, for the Finance Controller",
            "columns": ["Invoice", "Rule", "Variance", "Routed to"],
            "rows": rows,
            "chart": None,
        }

    if report_id == "duplicate-invoice":
        return {
            "title": "Duplicate Invoice Report",
            "subtitle": "AP-SOP-001 section 9.3 - monthly, for Finance Controller and Internal Audit",
            "columns": ["Invoice", "Reference", "Supplier", "Outcome"],
            "rows": [
                [o.invoice.source_file, o.invoice.reference, o.invoice.supplier, "Rejected"]
                for o in outcomes
                if _rule_failed(o, "R16")
            ],
            "chart": None,
        }

    if report_id == "no-po-invoice":
        return {
            "title": "No-PO Invoice Report",
            "subtitle": "AP-SOP-001 section 9.3 - monthly, for Department Heads and the Finance Controller",
            "columns": ["Invoice", "PO cited", "Supplier", "Status"],
            "rows": [
                [o.invoice.source_file, o.invoice.purchase_order, o.invoice.supplier, "On hold - no PO"]
                for o in outcomes
                if _rule_failed(o, "R01")
            ],
            "chart": None,
        }

    rows = []
    for outcome in exceptions:
        finding = _first_active(outcome)
        rows.append([
            outcome.invoice.source_file,
            finding.rule_name,
            finding.sop_ref or "-",
            outcome.required_approval.name.replace("_", " ").title(),
            "Day 1",
        ])
    return {
        "title": "Exception Aging Report",
        "subtitle": "AP-SOP-001 section 9.3 - weekly, for the AP Manager",
        "columns": ["Invoice", "Exception", "SOP clause", "Routed to", "Age"],
        "rows": rows,
        "chart": None,
    }


def kpis(outcomes: list) -> list[dict]:
    total = max(len(outcomes), 1)
    measured = {
        "exception-rate": sum(1 for o in outcomes if not o.can_park) / total * 100,
        "duplicate-rate": sum(1 for o in outcomes if _rule_failed(o, "R16")) / total * 100,
        "no-po-rate": sum(1 for o in outcomes if _rule_failed(o, "R01")) / total * 100,
    }
    return [{**k, "value": round(measured[k["id"]], 1)} for k in KPI_TARGETS]
