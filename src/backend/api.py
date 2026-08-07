"""HTTP surface for the AP workspace.

Composition only. The decisions live elsewhere:

    extract.py    document  -> Invoice
    sap.py        Invoice   -> SapContext, and the single write
    rules.py      Invoice + SapContext -> Findings
    knowledge.py  SOP clause -> resolution steps
    agent.py      the exception chat, when Bedrock is reachable

The approval gate is a state machine here, not a prompt instruction. A batch
moves CREATED -> VALIDATED -> APPROVED -> PARKED, `/approve` is the only path
that mints a token, and the token is bound to the exact set of references that
passed validation. If the batch changed after validation the token no longer
matches and the write is refused.

    uvicorn api:app --reload --port 8000
"""

from __future__ import annotations

import logging
import os
import secrets
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from dataclasses import dataclass, field
from datetime import date, datetime, timezone
from decimal import Decimal
from pathlib import Path

from dotenv import load_dotenv
from fastapi import FastAPI, File, HTTPException, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from pydantic import BaseModel

load_dotenv()

import extract  # noqa: E402
import knowledge  # noqa: E402
from rules import Routing, Status, evaluate_batch  # noqa: E402
from sap import SapClient, SapError, reference_for  # noqa: E402

log = logging.getLogger("ap.api")
logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s %(message)s")

INVOICE_DIR = Path(os.environ.get("INVOICE_DIR", Path(__file__).resolve().parents[2] / "Invoices"))
REFERENCE_PREFIX = os.environ.get("INVOICE_REFERENCE_PREFIX", "000000000000")
# Keeps a demo re-run from colliding with references already used in SAP.
SEQUENCE_START = int(os.environ.get("INVOICE_SEQUENCE_START", "1"))
# Concurrent SAP reads. Each MCP round trip takes seconds, so this is the
# single biggest lever on how long a batch takes.
READ_CONCURRENCY = int(os.environ.get("SAP_READ_CONCURRENCY", "6"))

app = FastAPI(title="AP Copilot", version="1.0")
app.add_middleware(
    CORSMiddleware,
    allow_origins=os.environ.get("CORS_ORIGINS", "http://localhost:5173").split(","),
    allow_methods=["*"],
    allow_headers=["*"],
)


# --------------------------------------------------------------------------
# Serialisation
# --------------------------------------------------------------------------


def money(value: Decimal) -> float:
    """Decimal is exact through the rules; JSON only has to display it."""
    return float(value)


def invoice_json(inv, confidence: dict, pdf_name: str) -> dict:
    return {
        "sourceFile": inv.source_file,
        "pdfUrl": f"/api/invoices/{pdf_name}",
        "reference": inv.reference,
        "supplier": inv.supplier,
        "supplierName": SUPPLIER_NAMES.get(inv.supplier, "Supplier"),
        "purchaseOrder": inv.purchase_order,
        "purchaseOrderItem": inv.purchase_order_item,
        "invoiceDate": inv.invoice_date.isoformat(),
        "companyCode": inv.company_code,
        "currency": inv.currency,
        "material": inv.material,
        "quantity": money(inv.quantity),
        "unit": inv.unit,
        "unitPrice": money(inv.unit_price),
        "netAmount": money(inv.net_amount),
        "taxCode": inv.tax_code,
        "taxAmount": money(inv.tax_amount),
        "grossAmount": money(inv.gross_amount),
        "confidence": confidence,
    }


SUPPLIER_NAMES = {
    "10300006": "Inlandslieferant DE 6",
    "17401710": "Inlandslieferant DE 1",
}


def finding_json(f) -> dict:
    return {
        "ruleId": f.rule_id,
        "ruleName": f.rule_name,
        "status": f.status.name,
        "message": f.message,
        "sopRef": f.sop_ref,
        "invoiceValue": f.invoice_value,
        "sapValue": f.sap_value,
        "delta": f.delta,
        "routing": f.routing.name,
    }


def outcome_json(outcome, confidence: dict, parked: dict | None) -> dict:
    return {
        "invoice": invoice_json(outcome.invoice, confidence, outcome.invoice.source_file),
        "findings": [finding_json(f) for f in outcome.findings],
        "canPark": outcome.can_park,
        "requiredApproval": outcome.required_approval.name,
        "headline": outcome.headline,
        "counts": {k.upper(): v for k, v in outcome.counts.items()},
        "parked": parked,
    }


# --------------------------------------------------------------------------
# Batch state
# --------------------------------------------------------------------------


@dataclass
class Batch:
    id: str
    label: str
    state: str = "CREATED"
    outcomes: list = field(default_factory=list)
    confidence: dict = field(default_factory=dict)
    parked: dict = field(default_factory=dict)
    failures: list = field(default_factory=list)
    sap_calls: int = 0
    duration_ms: int = 0
    extraction_source: str = "unknown"
    knowledge_source: str = "unknown"
    token: str | None = None
    token_references: frozenset[str] = frozenset()

    def as_dict(self) -> dict:
        return {
            "id": self.id,
            "date": date.today().isoformat(),
            "label": self.label,
            "state": self.state,
            "source": str(INVOICE_DIR),
            "sapCalls": self.sap_calls,
            "durationMs": self.duration_ms,
            "providers": {
                "extraction": self.extraction_source,
                "knowledge": self.knowledge_source,
                "sap": "mcp",
            },
            "unreadable": self.failures,
            "outcomes": [
                outcome_json(o, self.confidence.get(o.invoice.reference, {}), self.parked.get(o.invoice.reference))
                for o in self.outcomes
            ],
        }


BATCHES: dict[str, Batch] = {}


def inbox_files() -> list[Path]:
    return sorted(INVOICE_DIR.glob("*.pdf"))


def resolve(names: list[str]) -> list[Path]:
    """Map file names onto the inbox. A name that escapes the inbox, or
    that is not there, is refused rather than silently skipped."""
    inbox = INVOICE_DIR.resolve()
    paths = []
    for name in names:
        path = (INVOICE_DIR / name).resolve()
        if path.parent != inbox or not path.is_file():
            raise HTTPException(404, f"No such invoice in the inbox: {name}")
        paths.append(path)
    return paths


def run_batch(names: list[str] | None = None) -> Batch:
    """Validate the selected documents against live SAP.

    `names` selects which files in the inbox to process; the whole inbox
    runs when it is omitted, which is what the daily scheduled run does.
    """
    started = time.monotonic()
    label = "Today's intake" if names is None else f"Selected: {len(names)} invoices"
    batch = Batch(id=f"batch-{datetime.now(timezone.utc):%Y-%m-%d-%H%M%S}", label=label)

    pdfs = resolve(names) if names is not None else inbox_files()
    if not pdfs:
        raise HTTPException(404, f"No invoices found in {INVOICE_DIR}")

    extractions = extract.extract_batch(pdfs, REFERENCE_PREFIX, SEQUENCE_START)
    batch.extraction_source = extract.extractor().source
    batch.knowledge_source = knowledge.provider().source

    invoices, confidence = [], {}
    for pdf, ex in zip(pdfs, extractions, strict=True):
        if ex.invoice is None:
            # An unreadable document is reported, not silently dropped.
            batch.failures.append({"sourceFile": pdf.name, "reason": ex.source})
            continue
        invoices.append(ex.invoice)
        confidence[ex.invoice.reference] = ex.confidence

    # One MCP round trip costs several seconds, and each invoice's reads are
    # independent of every other invoice's, so they run concurrently. Wall time
    # then tracks the slowest single invoice rather than the sum of all of them.
    # Each worker gets its own client because the MCP session id is per client.
    clients = [SapClient() for _ in invoices]
    contexts: list = [None] * len(invoices)

    def read(index: int):
        return index, clients[index].build_context(invoices[index])

    with ThreadPoolExecutor(max_workers=min(READ_CONCURRENCY, len(invoices) or 1)) as pool:
        futures = [pool.submit(read, i) for i in range(len(invoices))]
        for future in as_completed(futures):
            try:
                index, context = future.result()
            except SapError as exc:
                # A SAP outage is a fault, not a verdict - say so rather than
                # reporting every invoice as failing validation.
                log.error("SAP read failed: %s", exc)
                raise HTTPException(502, f"SAP is unreachable: {exc}") from exc
            contexts[index] = context

    batch.outcomes = evaluate_batch(invoices, contexts)
    batch.confidence = confidence
    batch.sap_calls = sum(c.call_count for c in clients)
    batch.duration_ms = int((time.monotonic() - started) * 1000)
    batch.state = "VALIDATED"

    BATCHES[batch.id] = batch
    log.info(
        "%s: %d invoices, %d parkable, %d SAP calls, %dms",
        batch.id,
        len(batch.outcomes),
        sum(o.can_park for o in batch.outcomes),
        batch.sap_calls,
        batch.duration_ms,
    )
    return batch


def get_batch(batch_id: str) -> Batch:
    batch = BATCHES.get(batch_id)
    if batch is None:
        raise HTTPException(404, f"Unknown batch {batch_id}")
    return batch


# --------------------------------------------------------------------------
# Routes
# --------------------------------------------------------------------------


class ApproveRequest(BaseModel):
    references: list[str]


class ParkRequest(BaseModel):
    token: str
    references: list[str]


class ChatRequest(BaseModel):
    batchId: str
    reference: str
    question: str


@app.get("/api/health")
def health() -> dict:
    return {
        "ok": True,
        "providers": {
            "extraction": extract.extractor().source,
            "knowledge": knowledge.provider().source,
            "sap": "mcp",
        },
    }


class BatchRequest(BaseModel):
    files: list[str] | None = None


@app.get("/api/inbox")
def inbox() -> list[dict]:
    """What is waiting to be processed, and what has already been parked."""
    parked_files = {
        o.invoice.source_file
        for b in BATCHES.values()
        for o in b.outcomes
        if o.invoice.reference in b.parked
    }
    seen = {o.invoice.source_file for b in BATCHES.values() for o in b.outcomes}
    out = []
    for path in inbox_files():
        stat = path.stat()
        out.append({
            "name": path.name,
            "sizeBytes": stat.st_size,
            "modified": datetime.fromtimestamp(stat.st_mtime, timezone.utc).isoformat(),
            "processed": path.name in seen,
            "parked": path.name in parked_files,
        })
    return out


@app.post("/api/uploads")
async def upload(files: list[UploadFile] = File(...)) -> dict:
    """Accept dropped documents into the inbox.

    Only PDFs, and only by base name - an uploaded name never gets to
    choose where on disk it lands.
    """
    INVOICE_DIR.mkdir(parents=True, exist_ok=True)
    saved, rejected = [], []
    for upload_file in files:
        name = Path(upload_file.filename or "").name
        if not name.lower().endswith(".pdf"):
            rejected.append({"name": name or "(unnamed)", "reason": "not a PDF"})
            continue
        data = await upload_file.read()
        if not data.startswith(b"%PDF"):
            rejected.append({"name": name, "reason": "not a readable PDF"})
            continue
        (INVOICE_DIR / name).write_bytes(data)
        saved.append(name)
        log.info("uploaded %s (%d bytes)", name, len(data))
    return {"saved": saved, "rejected": rejected}


@app.post("/api/batches")
def create_batch(body: BatchRequest | None = None) -> dict:
    return run_batch(body.files if body else None).as_dict()


@app.get("/api/batches/latest")
def latest_batch() -> dict:
    if BATCHES:
        return BATCHES[max(BATCHES)].as_dict()
    return run_batch().as_dict()


@app.get("/api/batches/{batch_id}")
def read_batch(batch_id: str) -> dict:
    return get_batch(batch_id).as_dict()


@app.post("/api/batches/{batch_id}/approve")
def approve(batch_id: str, body: ApproveRequest) -> dict:
    """The only path that mints an approval token.

    A batch that was never validated cannot be approved, and an invoice that
    failed validation can never be included.
    """
    batch = get_batch(batch_id)
    if batch.state not in ("VALIDATED", "APPROVED", "PARKED"):
        raise HTTPException(409, f"Batch {batch_id} is {batch.state}; validate it first")

    parkable = {o.invoice.reference for o in batch.outcomes if o.can_park}
    requested = set(body.references)
    blocked = requested - parkable
    if blocked:
        raise HTTPException(422, f"These invoices failed validation and cannot be parked: {sorted(blocked)}")
    if not requested:
        raise HTTPException(422, "No invoices selected")

    batch.token = f"apr_{secrets.token_urlsafe(12)}"
    batch.token_references = frozenset(requested)
    batch.state = "APPROVED"
    log.info("%s approved for %d invoices", batch_id, len(requested))
    return {"token": batch.token, "references": sorted(requested)}


@app.post("/api/batches/{batch_id}/park")
def park(batch_id: str, body: ParkRequest) -> dict:
    """The single write. Unreachable without a token from /approve."""
    batch = get_batch(batch_id)
    if not batch.token or not secrets.compare_digest(body.token, batch.token):
        raise HTTPException(403, "A valid approval token is required before anything is written to SAP")
    if not set(body.references) <= batch.token_references:
        raise HTTPException(403, "The approval does not cover these invoices")

    client = SapClient()
    by_reference = {o.invoice.reference: o for o in batch.outcomes}
    results, skipped = [], []

    for reference in body.references:
        outcome = by_reference.get(reference)
        if outcome is None or not outcome.can_park:
            skipped.append({"reference": reference, "reason": "failed validation"})
            continue
        try:
            parked = client.park(outcome.invoice)
        except SapError as exc:
            # One failed write does not abandon the rest of the batch.
            log.error("park failed for %s: %s", reference, exc)
            skipped.append({"reference": reference, "reason": str(exc)})
            continue
        record = {
            "reference": reference,
            "supplierInvoice": parked.supplier_invoice,
            "fiscalYear": parked.fiscal_year,
            "status": parked.status,
        }
        batch.parked[reference] = record
        results.append(record)

    # The token is single use.
    batch.token = None
    batch.token_references = frozenset()
    batch.state = "PARKED"
    return {"results": results, "skipped": skipped}


@app.get("/api/guidance")
def guidance(sopRef: str) -> dict:  # noqa: N803 - query name matches the client
    found = knowledge.guidance(sopRef)
    if found is None:
        raise HTTPException(404, f"No SOP entry published for {sopRef}")
    return found.as_dict()


@app.post("/api/chat")
def chat(body: ChatRequest) -> dict:
    batch = get_batch(body.batchId)
    outcome = next((o for o in batch.outcomes if o.invoice.reference == body.reference), None)
    if outcome is None:
        raise HTTPException(404, f"Unknown invoice {body.reference}")

    import agent  # noqa: PLC0415 - imported lazily so a missing Strands install cannot break the rest

    return agent.answer(body.question, outcome)


@app.get("/api/invoices/{name}")
def invoice_pdf(name: str):
    """Serve a source document. The name is resolved against the invoice
    directory only - a path outside it is refused rather than served."""
    path = (INVOICE_DIR / name).resolve()
    if path.parent != INVOICE_DIR.resolve() or not path.is_file():
        raise HTTPException(404, "No such invoice")
    return FileResponse(path, media_type="application/pdf")


@app.get("/api/reports/{report_id}")
def report(report_id: str, batchId: str) -> dict:  # noqa: N803
    from reports import build  # noqa: PLC0415

    return build(report_id, get_batch(batchId).outcomes)


@app.get("/api/reports")
def report_catalogue() -> list[dict]:
    from reports import CATALOGUE  # noqa: PLC0415

    return CATALOGUE


if __name__ == "__main__":
    import uvicorn

    uvicorn.run("api:app", host="127.0.0.1", port=int(os.environ.get("PORT", "8000")), reload=False)
