"""The exception assistant.

This is the one component that is genuinely agentic. Answering "what do I do
about this invoice" needs a loop: decide whether to pull the SOP clause,
re-read the purchase order, or re-run validation, then decide again with what
came back. Extraction is a single call and validation is a pure function -
neither is an agent, and dressing them up as one would only make them slower
and less reproducible.

Two providers:

    Strands  - a Strands agent on Bedrock with three tools. Used when the
               strands SDK is installed and AWS credentials resolve.
    Grounded - a deterministic responder over the same finding and the same
               SOP clause. Used otherwise.

Both are constrained the same way, and it is the important constraint: the
assistant may explain and cite, but it may not overturn a verdict and it may
not park anything. Fixing an invoice means correcting the underlying SAP data
and re-validating, after which the invoice returns to the approvals queue and
goes through the one approval gate like everything else.
"""

from __future__ import annotations

import os
from functools import lru_cache

import knowledge
from rules import Status

MODEL_ID = os.environ.get("BEDROCK_MODEL_ID", "us.anthropic.claude-sonnet-4-5-20250929-v1:0")
AWS_REGION = os.environ.get("AWS_REGION", "us-east-1")

SYSTEM_PROMPT = """You are an SAP Accounts Payable exception assistant.

An invoice has already been validated by a deterministic rules engine. You are
given its findings. Your job is to help a clerk resolve the exception.

Rules you must follow:
- Never overturn a verdict. The rules engine decides pass or fail, not you. If
  asked whether the invoice can be paid, restate what the finding says.
- Never invent a procedure. Call sop_guidance for the clause the finding names
  and answer from what it returns. If it returns nothing, say so.
- Never claim to have changed anything in SAP. You can read, not write.
- Cite the SOP clause whenever you give resolution steps.
- Be concise and concrete. Name the owner and the timeframe for each step.
"""


def _finding(outcome):
    """The finding the conversation is about: the failure, else the warning."""
    return next(
        (f for f in outcome.findings if f.status is Status.FAIL),
        next((f for f in outcome.findings if f.status is Status.WARN), None),
    )


def strands_available() -> bool:
    try:
        import strands  # noqa: F401, PLC0415
    except ImportError:
        return False
    try:
        import boto3  # noqa: PLC0415

        return boto3.Session().get_credentials() is not None
    except Exception:  # noqa: BLE001
        return False


# --------------------------------------------------------------------------
# Strands provider
# --------------------------------------------------------------------------


def _build_strands_agent(outcome):
    """A Strands agent scoped to one invoice, with three read-only tools."""
    from strands import Agent, tool  # noqa: PLC0415
    from strands.models import BedrockModel  # noqa: PLC0415

    invoice = outcome.invoice

    @tool
    def sop_guidance(sop_ref: str) -> str:
        """Retrieve the resolution procedure for a SOP clause, such as
        "AP-SOP-001 6.3". Returns the common causes, the numbered steps with
        their owner and timeframe, and any policy note."""
        found = knowledge.guidance(sop_ref)
        if found is None:
            return f"No SOP entry is published for {sop_ref}."
        steps = "\n".join(
            f"{i}. {s.action} ({s.who}, {s.when})" for i, s in enumerate(found.steps, 1)
        )
        causes = "\n".join(f"- {c}" for c in found.causes)
        return f"{found.title}\n\nCommon causes:\n{causes}\n\nSteps:\n{steps}\n\n{found.policy}"

    @tool
    def read_purchase_order() -> str:
        """Re-read this invoice's purchase order, its item and its goods
        receipts from SAP. Read-only."""
        from sap import SapClient, SapError  # noqa: PLC0415

        try:
            client = SapClient()
            header = client.get_po_header(invoice.purchase_order)
            if header is None:
                return f"Purchase order {invoice.purchase_order} does not exist in SAP."
            item = client.get_po_item(invoice.purchase_order, invoice.purchase_order_item)
            receipts = client.get_goods_receipts(invoice.purchase_order, invoice.purchase_order_item)
            return (
                f"Purchase order {header.purchase_order}: vendor {header.supplier}, "
                f"company code {header.company_code}, currency {header.currency}, "
                f"deleted={header.is_deleted}, blocked={header.is_blocked}.\n"
                f"Item {invoice.purchase_order_item}: {item.material}, ordered {item.quantity} "
                f"{item.unit} at {item.net_price}, already invoiced {item.already_invoiced_quantity}.\n"
                f"Goods receipts: {[(g.movement_type, str(g.quantity)) for g in receipts]}"
            )
        except SapError as exc:
            return f"SAP read failed: {exc}"

    @tool
    def revalidate() -> str:
        """Re-run all 17 validation rules against current SAP data. Reports the
        new result; it does not change anything and it cannot park."""
        from rules import evaluate  # noqa: PLC0415
        from sap import SapClient, SapError  # noqa: PLC0415

        try:
            client = SapClient()
            findings = evaluate(invoice, client.build_context(invoice))
        except SapError as exc:
            return f"SAP read failed: {exc}"
        failures = [f for f in findings if f.status is Status.FAIL]
        if not failures:
            return "All rules now pass. The invoice moves back to the approvals queue and still needs approval before anything is written."
        return "Still failing:\n" + "\n".join(f"{f.rule_id} {f.rule_name}: {f.message}" for f in failures)

    context = "\n".join(
        f"{f.rule_id} {f.rule_name}: {f.status.name} - {f.message}"
        + (f" [invoice {f.invoice_value} vs SAP {f.sap_value}]" if f.invoice_value else "")
        + (f" [{f.sop_ref}]" if f.sop_ref else "")
        for f in outcome.findings
        if f.status in (Status.FAIL, Status.WARN)
    )

    return Agent(
        model=BedrockModel(model_id=MODEL_ID, region_name=AWS_REGION),
        tools=[sop_guidance, read_purchase_order, revalidate],
        system_prompt=(
            f"{SYSTEM_PROMPT}\n\n"
            f"Invoice {invoice.source_file}, reference {invoice.reference}, "
            f"purchase order {invoice.purchase_order} item {invoice.purchase_order_item}, "
            f"supplier {invoice.supplier}, gross {invoice.currency} {invoice.gross_amount}.\n\n"
            f"Findings:\n{context}\n\n"
            f"Required approval level: {outcome.required_approval.name}."
        ),
    )


def _strands_answer(question: str, outcome) -> dict:
    agent = _build_strands_agent(outcome)
    result = agent(question)
    text = result.message["content"][0]["text"]
    finding = _finding(outcome)
    citations = [finding.sop_ref] if finding and finding.sop_ref and finding.sop_ref in text else []
    return {"text": text, "citations": citations, "source": "strands"}


# --------------------------------------------------------------------------
# Grounded fallback
# --------------------------------------------------------------------------


def _grounded_answer(question: str, outcome) -> dict:
    """Deterministic responses over the same finding and the same SOP clause.

    Not a language model, and it does not pretend to be: it routes the question
    to a section of the retrieved SOP entry. Every sentence it returns comes
    from the finding or from the SOP document.
    """
    q = question.lower()
    finding = _finding(outcome)
    if finding is None:
        return {
            "text": "Every rule passed for this invoice, so there is no exception to resolve.",
            "citations": [],
            "source": "grounded",
        }

    guide = knowledge.guidance(finding.sop_ref) if finding.sop_ref else None
    cite = [finding.sop_ref] if finding.sop_ref else []

    if any(w in q for w in ("cause", "common", "typical", "why does this happen")):
        if guide and guide.causes:
            causes = "\n".join(f"- {c}" for c in guide.causes)
            return {"text": f"Common causes per {finding.sop_ref}:\n\n{causes}", "citations": cite, "source": "grounded"}

    if any(w in q for w in ("what should", "what do", "next", "step", "fix", "resolve", "action", "how do")):
        if guide and guide.steps:
            steps = "\n".join(f"{i}. {s.action}  ({s.who}, {s.when})" for i, s in enumerate(guide.steps, 1))
            policy = f"\n\n{guide.policy}" if guide.policy else ""
            return {
                "text": f"{guide.title} - resolution steps from {finding.sop_ref}:\n\n{steps}{policy}",
                "citations": cite,
                "source": "grounded",
            }

    if any(w in q for w in ("who", "escalate", "approve", "sign off")):
        level = outcome.required_approval.name.replace("_", " ").lower()
        policy = f"\n\n{guide.policy}" if guide and guide.policy else ""
        return {"text": f"This exception routes to {level}.{policy}", "citations": cite, "source": "grounded"}

    if any(w in q for w in ("sap", "purchase order", "po ", "vendor", "check", "re-read", "reread")):
        inv = outcome.invoice
        return {
            "text": (
                f"Purchase order {inv.purchase_order} item {inv.purchase_order_item}, "
                f"read during validation:\n\n"
                f"- Invoice states: {finding.invoice_value or inv.supplier}\n"
                f"- SAP holds: {finding.sap_value or 'no value'}\n"
                f"{f'- Difference: {finding.delta}' if finding.delta else ''}\n\n"
                "Correct the underlying data in SAP and re-validate; the invoice then returns "
                "to the approvals queue and still needs approval before anything is written."
            ),
            "citations": [],
            "source": "grounded",
        }

    if any(w in q for w in ("why", "what happened", "reason", "fail")):
        title = f" - {guide.title}" if guide else ""
        return {
            "text": (
                f"{finding.message}\n\nThis is rule {finding.rule_id}, {finding.rule_name}. "
                f"The governing procedure is {finding.sop_ref}{title}."
            ),
            "citations": cite,
            "source": "grounded",
        }

    return {
        "text": (
            f"I can explain why this invoice failed, list the common causes, walk through the "
            f"resolution steps from {finding.sop_ref or 'the SOP'}, say who has to approve it, "
            "or show what SAP holds for this purchase order. What would help?"
        ),
        "citations": [],
        "source": "grounded",
    }


@lru_cache(maxsize=1)
def _use_strands() -> bool:
    return strands_available()


def answer(question: str, outcome) -> dict:
    if _use_strands():
        try:
            return _strands_answer(question, outcome)
        except Exception as exc:  # noqa: BLE001 - a chat failure must not break the workspace
            return {
                **_grounded_answer(question, outcome),
                "note": f"Agent unavailable, answered from the SOP directly ({type(exc).__name__}).",
            }
    return _grounded_answer(question, outcome)


if __name__ == "__main__":
    import fixtures
    from rules import evaluate_batch

    invoices, contexts = fixtures.workshop_batch()
    failing = [o for o in evaluate_batch(invoices, contexts) if not o.can_park][0]

    print(f"provider: {'strands' if _use_strands() else 'grounded'}\n")
    for question in (
        "Why did this fail?",
        "What are the common causes?",
        "What should I do next?",
        "Who has to approve this?",
    ):
        reply = answer(question, failing)
        print(f"Q: {question}\nA: {reply['text'][:180].strip()}...\n   cites={reply['citations']}\n")
        assert reply["text"], "empty answer"

    steps = answer("What should I do next?", failing)
    assert "AP-SOP-001" in steps["text"], "resolution steps must cite the SOP clause"
    assert steps["citations"], "resolution steps must carry a citation"
    print("OK")
