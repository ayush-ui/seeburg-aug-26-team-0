"""Turn an invoice document into a structured `Invoice`.

This is the one place a language model genuinely earns its keep: reading a
supplier's PDF layout, which no parser can be written for in advance. It is a
single structured-output call, not an agent loop - there is nothing to decide,
only something to read.

Two providers, chosen by what the environment can reach:

    Bedrock - Claude on Bedrock, reading the PDF directly.
    Cached  - extractions recorded from a previous Bedrock run, keyed by file
              name. Used when Bedrock is unreachable.

Everything the model returns is normalised and re-typed here before it goes
anywhere near `rules.py`: German decimal commas become Decimal, dates become
date. The model reads; it does not get to hand back a float.
"""

from __future__ import annotations

import json
import os
import re
from concurrent.futures import ThreadPoolExecutor
from dataclasses import dataclass
from datetime import date
from decimal import Decimal, InvalidOperation
from functools import lru_cache
from pathlib import Path

from dotenv import load_dotenv

from rules import Invoice

# The ids below are read at import, and credentials come from the same file.
# api.py has already called this; the repeat is a no-op and stops this module
# reporting "cached" when running directly with credentials configured.
load_dotenv()

CACHE_PATH = Path(os.environ.get("EXTRACTION_CACHE", Path(__file__).resolve().parent / "extractions.json"))
MODEL_ID = os.environ.get("BEDROCK_MODEL_ID", "us.anthropic.claude-sonnet-4-5-20250929-v1:0")
AWS_REGION = os.environ.get("AWS_REGION", "us-east-1")
# Concurrent vision reads. Kept modest deliberately: these are large multimodal
# requests and Bedrock throttles them per account, so raising it past the size
# of a normal batch buys nothing and risks ThrottlingException.
EXTRACT_CONCURRENCY = int(os.environ.get("EXTRACT_CONCURRENCY", "6"))

PROMPT = """Read this supplier invoice and return one JSON object, nothing else.

Keys, all required:
  supplier              vendor number as printed, digits only
  purchase_order        purchase order number referenced
  purchase_order_item   PO line item, usually "10"
  invoice_date          ISO yyyy-mm-dd
  company_code          usually "1010"
  currency              ISO code, e.g. "EUR"
  material              material number
  quantity              number
  unit                  unit of measure, e.g. "PC"
  unit_price            number
  net_amount            number
  tax_code              e.g. "V0" or "V1"
  tax_amount            number
  gross_amount          number
  confidence            object mapping each key above to 0.0-1.0

Write every number as a plain decimal with a dot separator: "113.50", never
"113,50" and never "1.234,56". If a value is not printed on the document, use
null and give it a confidence of 0.0. Do not infer a value from another field.
"""


class ExtractionError(RuntimeError):
    """The document could not be read into a complete invoice."""


@dataclass
class Extraction:
    invoice: Invoice
    confidence: dict[str, float]
    source: str


# --------------------------------------------------------------------------
# Normalisation - the boundary where model output becomes typed data
# --------------------------------------------------------------------------

_THOUSANDS = re.compile(r"(?<=\d)[ .](?=\d{3}\b)")


def to_decimal(value, field: str) -> Decimal:
    """Parse a money or quantity value, tolerating European formatting.

    "113,50" -> 113.50 and "1.234,56" -> 1234.56. Decimal all the way through:
    rules 10 and 11 reconcile arithmetic exactly, and a float would invent an
    exception that does not exist.
    """
    if isinstance(value, Decimal):
        return value
    if isinstance(value, int):
        return Decimal(value)
    if isinstance(value, float):
        # Round-trip through str so 0.1 does not arrive as 0.1000000000000000055.
        return Decimal(str(value))
    if value is None:
        raise ExtractionError(f"{field} is missing from the document")

    text = str(value).strip().replace(" ", " ")
    text = re.sub(r"[^\d,.\- ]", "", text)
    if "," in text and "." in text:
        # Whichever separator comes last is the decimal point.
        text = text.replace(".", "").replace(",", ".") if text.rfind(",") > text.rfind(".") else text.replace(",", "")
    elif "," in text:
        text = text.replace(",", ".")
    text = _THOUSANDS.sub("", text).replace(" ", "")

    try:
        return Decimal(text)
    except InvalidOperation as exc:
        raise ExtractionError(f"{field} is not a number: {value!r}") from exc


def to_date(value, field: str = "invoice_date") -> date:
    if isinstance(value, date):
        return value
    if not value:
        raise ExtractionError(f"{field} is missing from the document")
    text = str(value).strip()
    for pattern in ("%Y-%m-%d", "%d.%m.%Y", "%d/%m/%Y", "%d-%m-%Y"):
        try:
            return date.fromisoformat(text) if pattern == "%Y-%m-%d" else __import__("datetime").datetime.strptime(text, pattern).date()
        except ValueError:
            continue
    raise ExtractionError(f"{field} is not a recognisable date: {value!r}")


def build_invoice(raw: dict, source_file: str, reference: str) -> Invoice:
    """Type and validate one extraction. Raises rather than guessing."""
    required = ("supplier", "purchase_order", "currency", "company_code")
    missing = [k for k in required if not raw.get(k)]
    if missing:
        raise ExtractionError(f"{source_file}: could not read {', '.join(missing)}")

    return Invoice(
        source_file=source_file,
        reference=reference,
        supplier=str(raw["supplier"]).strip(),
        purchase_order=str(raw["purchase_order"]).strip(),
        purchase_order_item=str(raw.get("purchase_order_item") or "10").strip(),
        invoice_date=to_date(raw.get("invoice_date")),
        company_code=str(raw["company_code"]).strip(),
        currency=str(raw["currency"]).strip().upper(),
        material=str(raw.get("material") or "").strip(),
        quantity=to_decimal(raw.get("quantity"), "quantity"),
        unit=str(raw.get("unit") or "PC").strip().upper(),
        unit_price=to_decimal(raw.get("unit_price"), "unit_price"),
        net_amount=to_decimal(raw.get("net_amount"), "net_amount"),
        tax_code=str(raw.get("tax_code") or "").strip().upper(),
        tax_amount=to_decimal(raw.get("tax_amount") or 0, "tax_amount"),
        gross_amount=to_decimal(raw.get("gross_amount"), "gross_amount"),
    )


# --------------------------------------------------------------------------
# Providers
# --------------------------------------------------------------------------


def bedrock_available() -> bool:
    try:
        import boto3  # noqa: PLC0415
    except ImportError:
        return False
    try:
        return boto3.Session().get_credentials() is not None
    except Exception:  # noqa: BLE001
        return False


class BedrockExtractor:
    """Claude on Bedrock, reading the PDF bytes directly."""

    source = "bedrock"

    def __init__(self):
        import boto3  # noqa: PLC0415

        self.client = boto3.client("bedrock-runtime", region_name=AWS_REGION)

    def read(self, pdf: Path) -> dict:
        response = self.client.converse(
            modelId=MODEL_ID,
            messages=[
                {
                    "role": "user",
                    "content": [
                        {"document": {"format": "pdf", "name": "invoice", "source": {"bytes": pdf.read_bytes()}}},
                        {"text": PROMPT},
                    ],
                }
            ],
            inferenceConfig={"maxTokens": 1200, "temperature": 0},
        )
        text = response["output"]["message"]["content"][0]["text"]
        match = re.search(r"\{.*\}", text, re.DOTALL)
        if not match:
            raise ExtractionError(f"{pdf.name}: model returned no JSON object")
        return json.loads(match.group(0))


class CachedExtractor:
    """Extractions recorded from an earlier Bedrock run.

    This is a demo safety net, not a substitute: it only answers for documents
    that have already been read once. An unknown file raises rather than
    inventing values.
    """

    source = "cached"

    def __init__(self, path: Path = CACHE_PATH):
        self.path = path

    @property
    @lru_cache(maxsize=1)  # noqa: B019 - one instance per process
    def _data(self) -> dict:
        if not self.path.is_file():
            return {}
        return json.loads(self.path.read_text(encoding="utf-8"))

    def read(self, pdf: Path) -> dict:
        raw = self._data.get(pdf.name)
        if raw is None:
            raise ExtractionError(
                f"{pdf.name}: no cached extraction, and Bedrock is unreachable. "
                "Run with AWS credentials to read new documents."
            )
        return raw


@lru_cache(maxsize=1)
def extractor():
    if bedrock_available():
        try:
            return BedrockExtractor()
        except Exception:  # noqa: BLE001
            pass
    return CachedExtractor()


def extract(pdf: Path, reference: str) -> Extraction:
    """Read one document into a typed invoice."""
    engine = extractor()
    raw = engine.read(pdf)
    confidence = {k: float(v) for k, v in (raw.get("confidence") or {}).items()}
    return Extraction(
        invoice=build_invoice(raw, pdf.name, reference),
        confidence=confidence,
        source=engine.source,
    )


def extract_batch(pdfs: list[Path], prefix: str, start: int = 1) -> list[Extraction]:
    """Read a batch. One unreadable document does not stop the others.

    Each document is an independent Bedrock call taking the better part of ten
    seconds, and no document's reading depends on any other's, so they run
    concurrently exactly as the SAP reads in `api.run_batch` do. Wall time then
    tracks the slowest single document instead of the sum of all of them.

    Order is part of the contract: the caller zips the results back against the
    file list, and the reference number is fixed by a document's position, not
    by which one happens to finish first. `ThreadPoolExecutor.map` yields in
    input order, so both hold.
    """
    if not pdfs:
        return []

    # Build the extractor before the pool rather than inside a worker. It is
    # cached, but the cache is not atomic, and threads racing it would each
    # construct their own client.
    extractor()

    def read(index: int) -> Extraction:
        try:
            return extract(pdfs[index], f"{prefix}-{index + start}")
        except Exception as exc:  # noqa: BLE001 - recorded against its document
            # Concurrency makes Bedrock throttling a real outcome, and it must
            # not sink the whole batch when one document trips it.
            reason = str(exc) if isinstance(exc, ExtractionError) else f"{type(exc).__name__}: {exc}"
            return Extraction(invoice=None, confidence={}, source=reason)

    with ThreadPoolExecutor(max_workers=min(EXTRACT_CONCURRENCY, len(pdfs))) as pool:
        return list(pool.map(read, range(len(pdfs))))


if __name__ == "__main__":
    # Normalisation is the part that silently corrupts money, so it gets checked.
    assert to_decimal("113,50", "x") == Decimal("113.50")
    assert to_decimal("1.234,56", "x") == Decimal("1234.56")
    assert to_decimal("1,234.56", "x") == Decimal("1234.56")
    assert to_decimal("59.50", "x") == Decimal("59.50")
    assert to_decimal("EUR 113,50", "x") == Decimal("113.50")
    assert to_decimal(0.1, "x") + to_decimal(0.2, "x") == Decimal("0.3")
    assert to_date("2025-03-15") == date(2025, 3, 15)
    assert to_date("15.03.2025") == date(2025, 3, 15)

    for bad in (None, "not a number"):
        try:
            to_decimal(bad, "quantity")
        except ExtractionError:
            pass
        else:
            raise AssertionError(f"expected ExtractionError for {bad!r}")

    print(f"extractor: {extractor().source}")
    print("normalisation OK")

    # extract_batch runs concurrently, so the things concurrency breaks
    # silently get checked: result order, and the reference number that is
    # bound to a document's position rather than to when it finished.
    class _StubExtractor:
        source = "stub"

        def read(self, pdf: Path) -> dict:
            if "unreadable" in pdf.name:
                raise ExtractionError(f"{pdf.name}: could not read supplier")
            return {
                "supplier": "10300006", "purchase_order": "4500001463",
                "purchase_order_item": "10", "invoice_date": "2025-03-15",
                "company_code": "1010", "currency": "EUR", "material": "M-1",
                "quantity": "1", "unit": "PC", "unit_price": "10.00",
                "net_amount": "10.00", "tax_code": "V0", "tax_amount": "0",
                "gross_amount": "10.00", "confidence": {"supplier": 1.0},
            }

    extractor = lambda: _StubExtractor()  # noqa: E731 - swapped in for the check

    paths = [Path(f"invoice-{n:02d}.pdf") for n in range(1, 8)]
    paths.insert(3, Path("unreadable.pdf"))
    batch = extract_batch(paths, "PRE", start=3)

    assert len(batch) == len(paths), f"expected {len(paths)} results, got {len(batch)}"
    readable = [(p, e) for p, e in zip(paths, batch) if p.name != "unreadable.pdf"]
    assert all(e.invoice.source_file == p.name for p, e in readable), "results came back out of order"
    assert [e.invoice.reference for _, e in readable] == [
        f"PRE-{i + 3}" for i, p in enumerate(paths) if p.name != "unreadable.pdf"
    ], "reference numbering drifted from document position"

    failed = batch[3]
    assert failed.invoice is None, "the unreadable document should not have produced an invoice"
    assert "could not read supplier" in failed.source, f"failure reason lost: {failed.source}"
    assert extract_batch([], "PRE") == [], "an empty batch should not open a pool"

    print(f"extract_batch: {len(batch)} documents, order and numbering OK, 1 failure recorded")
