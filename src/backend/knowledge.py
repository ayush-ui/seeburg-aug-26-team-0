"""Knowledge grounding: the SOP procedures and the OData API specifications.

Two providers, chosen at import time by what the environment can actually
reach:

    Bedrock  - the two Knowledge Bases the workshop deploys, queried with
               bedrock-agent-runtime.retrieve. Used when boto3 and AWS
               credentials are both available.
    Local    - the same SOP markdown the Knowledge Base is built from, parsed
               out of the repository. Used otherwise.

The fallback is not a mock. Both providers read the same source document, so
the guidance a clerk sees is identical; only the retrieval mechanism differs.
That keeps the demo working on a laptop with no AWS credentials, and the
Bedrock path switches on by itself the moment credentials exist.

Retrieval never decides whether an invoice passes. It is keyed by the SOP
clause `rules.py` has already named, which makes it a lookup rather than a
search for the answer.
"""

from __future__ import annotations

import logging
import os
import re
from dataclasses import dataclass, field
from functools import lru_cache
from pathlib import Path

from dotenv import load_dotenv

# The ids below are read at import, so the file has to be loaded before them.
# api.py has already called this; the repeat is a no-op and makes running this
# module directly pick up the same configuration the server uses.
load_dotenv()

log = logging.getLogger("ap.knowledge")

SOP_DIR = Path(os.environ.get("SOP_DIR", Path(__file__).resolve().parent / "mcp"))

# The API knowledge base holds OpenAPI specifications, so an entity path is a
# JSON key: "/A_PurchaseOrder('{PurchaseOrder}')": { ... }. Matching bare URLs
# instead returned the help.sap.com documentation links that litter the same
# JSON - a plausible-looking answer to the wrong question.
ODATA_PATH = re.compile(r"\"(/(?:sap/opu/odata/sap/)?[A-Za-z_][^\"\s]*)\"\s*:")

SOP_KB_ID = os.environ.get("SOP_KNOWLEDGE_BASE_ID", "HRQMR9REUC")
API_KB_ID = os.environ.get("API_KNOWLEDGE_BASE_ID", "M6GBMOSKQX")
AWS_REGION = os.environ.get("AWS_REGION", "us-east-1")

# Normally the repository copy answers and the SOP knowledge base is only the
# fallback, because the managed chunker splits step tables away from their
# headings and a partial procedure is worse than a complete one. Set this to
# show retrieval actually driving the answer - the passages are still scoped
# to one document and parsed one at a time, so the clause stays correct, but
# it may carry fewer steps than the repository copy of the same clause.
FORCE_SOP_RETRIEVAL = os.environ.get("FORCE_SOP_RETRIEVAL", "").strip().lower() in {"1", "true", "yes"}


@dataclass
class Step:
    action: str
    who: str
    when: str


@dataclass
class Guidance:
    """One SOP clause, ready to render."""

    sop_ref: str
    title: str
    causes: list[str] = field(default_factory=list)
    steps: list[Step] = field(default_factory=list)
    policy: str = ""
    source: str = "local"

    def as_dict(self) -> dict:
        return {
            "sopRef": self.sop_ref,
            "title": self.title,
            "causes": self.causes,
            "steps": [{"action": s.action, "who": s.who, "when": s.when} for s in self.steps],
            "policy": self.policy,
            "source": self.source,
        }


def bedrock_available() -> bool:
    """True when boto3 is installed and credentials actually resolve."""
    try:
        import boto3  # noqa: PLC0415
    except ImportError:
        return False
    try:
        return boto3.Session().get_credentials() is not None
    except Exception:  # noqa: BLE001 - any credential resolution failure means no
        return False


# --------------------------------------------------------------------------
# Local provider - parses the SOP markdown that the Knowledge Base indexes
# --------------------------------------------------------------------------

# `Finding.sop_ref` looks like "AP-SOP-001 6.1 / 8.1": the document, then the
# procedure section, then optionally a tolerance table.
SOP_ID_IN_REF = re.compile(r"AP-SOP-\d+")
SECTION_IN_REF = re.compile(r"(\d+\.\d+)")
# Each SOP carries its own id in the header table on the first page.
SOP_ID_IN_DOC = re.compile(r"\*\*SOP ID\*\*\s*\|\s*(AP-SOP-\d+)")


@lru_cache(maxsize=1)
def _documents() -> dict[str, tuple[str, str]]:
    """SOP id -> (file name, text), for every SOP markdown in SOP_DIR.

    Keyed by document rather than concatenated, because both SOPs number their
    sections from 1: "6.1" is Price Variance in AP-SOP-001 and Automated ERP
    Checks in AP-SOP-002. One namespace loses whichever file sorts first.

    The file name is kept because it is what the knowledge base reports as
    `_document_title`, which is the only way to scope a retrieved passage back
    to the document its reference names.
    """
    if not SOP_DIR.is_dir():
        return {}
    documents: dict[str, tuple[str, str]] = {}
    for path in sorted(SOP_DIR.glob("*.md")):
        text = path.read_text(encoding="utf-8")
        match = SOP_ID_IN_DOC.search(text)
        documents[match.group(1) if match else path.stem] = (path.name, text)
    return documents


def _document_for(sop_ref: str) -> str:
    """The document a reference names, or all of them when it names none."""
    documents = _documents()
    match = SOP_ID_IN_REF.search(sop_ref or "")
    if match and match.group(0) in documents:
        return documents[match.group(0)][1]
    return "\n\n".join(text for _, text in documents.values())


def _document_file(sop_ref: str) -> str | None:
    """The file name behind a reference, as the knowledge base titles it."""
    match = SOP_ID_IN_REF.search(sop_ref or "")
    entry = _documents().get(match.group(0)) if match else None
    return entry[0] if entry else None


def _split_sections(text: str) -> dict[str, tuple[str, str]]:
    """Map "6.1" -> (title, body) for every numbered subsection."""
    sections: dict[str, tuple[str, str]] = {}
    pattern = re.compile(r"^###\s+(\d+\.\d+)\s+(.+?)\s*$", re.MULTILINE)
    matches = list(pattern.finditer(text))
    for i, match in enumerate(matches):
        end = matches[i + 1].start() if i + 1 < len(matches) else len(text)
        sections[match.group(1)] = (match.group(2), text[match.end() : end])
    return sections


def _table_rows(body: str) -> list[list[str]]:
    """Rows of the first markdown table in a block, minus header and rule line."""
    rows: list[list[str]] = []
    for line in body.splitlines():
        line = line.strip()
        if not line.startswith("|"):
            if rows:
                break
            continue
        cells = [c.strip() for c in line.strip("|").split("|")]
        if all(set(c) <= {"-", ":"} for c in cells):
            continue
        rows.append(cells)
    return rows[1:] if rows else []


def _bullets(body: str, heading: str) -> list[str]:
    match = re.search(rf"####\s+\d+\.\d+\.\d+\s+{heading}(.*?)(?=####|\Z)", body, re.DOTALL)
    if not match:
        return []
    return [
        line.strip()[2:].strip()
        for line in match.group(1).splitlines()
        if line.strip().startswith("- ")
    ]


def _parse(text: str, sop_ref: str, source: str) -> Guidance | None:
    """Build a Guidance from SOP text, whatever supplied it.

    Both providers run this: the local one over the repository copy, the
    Bedrock one over the passages the Knowledge Base returned. The clerk sees
    the same structure either way, so the retrieval mechanism is the only
    thing that differs.
    """
    if not text:
        return None
    numbers = SECTION_IN_REF.findall(sop_ref or "")
    if not numbers:
        return None

    sections = _split_sections(text)
    section = next((n for n in numbers if n in sections), None)
    if section is None:
        return None

    title, body = sections[section]
    steps = [
        Step(action=row[1], who=row[2], when=row[3])
        for row in _table_rows(body)
        if len(row) >= 4 and row[0].isdigit()
    ]

    # A policy note, or the tolerance table the reference also cites.
    policy = ""
    note = re.search(r"^>\s+\*\*(?:Policy Note|Security Alert):\*\*\s*(.+?)$", body, re.MULTILINE)
    if note:
        policy = note.group(1).strip()
    else:
        tolerance = next((n for n in numbers if n.startswith("8.")), None)
        if tolerance and tolerance in sections:
            rows = _table_rows(sections[tolerance][1])
            policy = " ".join(f"{r[0]}: {r[1]}." for r in rows if len(r) >= 2)

    return Guidance(
        sop_ref=sop_ref,
        title=title,
        causes=_bullets(body, "Common Causes"),
        steps=steps,
        policy=policy,
        source=source,
    )


class LocalKnowledge:
    """Retrieval over the SOP markdown in the repository."""

    source = "local"

    def guidance(self, sop_ref: str) -> Guidance | None:
        return _parse(_document_for(sop_ref), sop_ref, self.source)

    def odata_path(self, question: str) -> str | None:
        """The local provider has no API index; the six fixed reads cover the rules."""
        return None


# --------------------------------------------------------------------------
# Bedrock provider
# --------------------------------------------------------------------------


class BedrockKnowledge:
    """The deployed Knowledge Bases, queried through bedrock-agent-runtime."""

    source = "bedrock"

    def __init__(self):
        import boto3  # noqa: PLC0415

        self.client = boto3.client("bedrock-agent-runtime", region_name=AWS_REGION)
        self.local = LocalKnowledge()
        # Probe once, at construction. A wrong knowledge base id or a missing
        # bedrock:Retrieve permission then falls back to local while the
        # provider is being chosen, rather than 500ing the first clerk who
        # opens an exception.
        self._retrieve(SOP_KB_ID, "three-way match exception", k=1)

    def _retrieve(self, kb_id: str, query: str, k: int = 5, document: str | None = None) -> list[str]:
        # Both workshop knowledge bases are type MANAGED, which rejects
        # vectorSearchConfiguration outright. A customer-managed vector store
        # would need that key instead; the ValidationException says which.
        response = self.client.retrieve(
            knowledgeBaseId=kb_id,
            retrievalQuery={"text": query},
            retrievalConfiguration={"managedSearchConfiguration": {"numberOfResults": k}},
        )
        results = response.get("retrievalResults", [])
        if document:
            # Sections 6.1 to 6.3 exist in both SOPs, so a passage from the
            # wrong document parses cleanly as the right clause and reads as
            # authoritative. Scope to the document the reference names.
            results = [
                r for r in results
                if (r.get("metadata") or {}).get("_document_title") == document
            ]
        return [
            r.get("content", {}).get("text", "")
            for r in results
            if r.get("content", {}).get("text")
        ]

    def guidance(self, sop_ref: str) -> Guidance | None:
        """The repository copy first, the Knowledge Base when it is absent.

        Retrieval is deliberately not the structural source, and running this
        against the live knowledge base is what settled it. The managed
        chunker splits the step tables away from their "### 6.6" heading, and
        the top-scoring chunk for a 6.6 query was 6.5.3. Reassembling
        passages into a clause produced the right title above another
        clause's steps - "Vendor/Supplier Mismatch" over the goods-receipt
        procedure - which would show a clerk the wrong instructions for a
        fraud-adjacent exception.

        The repository copy is the same document the knowledge base indexes,
        whole and scoped to one SOP, so it answers whenever it is deployed.
        That also means the common path makes no network call at all. The
        knowledge base answers when the markdown is not deployed beside the
        code, and it is the only source `odata_path` has.
        """
        parsed = self.local.guidance(sop_ref)
        if parsed is not None and parsed.steps and not FORCE_SOP_RETRIEVAL:
            return parsed

        try:
            passages = self._retrieve(
                SOP_KB_ID,
                f"{sop_ref} resolution steps and common causes",
                document=_document_file(sop_ref),
            )
        except Exception:  # noqa: BLE001 - a retrieval outage is not a verdict
            log.warning("SOP knowledge base retrieval failed for %s", sop_ref, exc_info=True)
            return parsed

        # One passage at a time. Concatenating them is what let one chunk's
        # heading capture another chunk's step table.
        candidates = [_parse(p, sop_ref, self.source) for p in passages]
        best = max(
            (c for c in candidates if c is not None and c.steps),
            key=lambda c: len(c.steps),
            default=None,
        )
        return best or parsed

    def odata_path(self, question: str) -> str | None:
        try:
            passages = self._retrieve(API_KB_ID, question, k=3)
        except Exception:  # noqa: BLE001 - no path is a usable answer; a 500 is not
            log.warning("API knowledge base retrieval failed", exc_info=True)
            return None
        for passage in passages:
            match = ODATA_PATH.search(passage)
            if match:
                return match.group(1)
        return None


@lru_cache(maxsize=1)
def provider():
    """The best provider this environment can reach."""
    if bedrock_available():
        try:
            return BedrockKnowledge()
        except Exception as exc:  # noqa: BLE001 - fall back rather than fail the request
            log.warning("Knowledge base %s unreachable (%s); using the repo SOP copy", SOP_KB_ID, exc)
    return LocalKnowledge()


def guidance(sop_ref: str) -> Guidance | None:
    return provider().guidance(sop_ref)


def odata_path(question: str) -> str | None:
    return provider().odata_path(question)


if __name__ == "__main__":
    p = provider()
    print(f"provider: {p.source}, documents: {sorted(_documents())}\n")
    for ref in (
        "AP-SOP-001 6.3",
        "AP-SOP-001 6.6",
        "AP-SOP-001 6.5",
        "AP-SOP-001 6.1 / 8.1",
        "AP-SOP-001 6.2 / 8.1",
        "AP-SOP-001 6.8 / 8.1",
    ):
        g = guidance(ref)
        assert g is not None, f"no guidance found for {ref}"
        assert g.steps, f"no resolution steps parsed for {ref}"
        print(f"{ref:24} {g.source:14} {g.title:42} {len(g.causes)} causes, {len(g.steps)} steps")
        assert all(s.who and s.when for s in g.steps), f"step missing owner or timeframe in {ref}"

    # Both SOPs have a section 6.1. The reference has to pick the right document.
    if len(_documents()) > 1:
        one, two = guidance("AP-SOP-001 6.1"), guidance("AP-SOP-002 6.1")
        assert one and two, "both SOP documents must resolve"
        assert one.title != two.title, f"6.1 resolved to {one.title!r} for both documents"
        print(f"\nAP-SOP-001 6.1 -> {one.title}\nAP-SOP-002 6.1 -> {two.title}")

    # The Bedrock branch selects itself only where credentials exist, so its
    # three outcomes are exercised here against a stub client. Without this the
    # path ships untested and the first time anyone sees it run is on stage.
    class _StubClient:
        def __init__(self, passages, error=None, title="three-way-match-exception-sop.md"):
            self.passages, self.error, self.calls, self.title = passages, error, 0, title

        def retrieve(self, **_):
            self.calls += 1
            if self.error:
                raise self.error
            return {
                "retrievalResults": [
                    {"content": {"text": t}, "metadata": {"_document_title": self.title}}
                    for t in self.passages
                ]
            }

    class _NoLocal:
        """Stands in for a deployment without the SOP markdown beside the code."""

        source = "local"

        def guidance(self, sop_ref):
            return None

    def _stub(passages, error=None, local=None, title="three-way-match-exception-sop.md"):
        kb = object.__new__(BedrockKnowledge)  # __init__ probes AWS; this must not
        kb.client = _StubClient(passages, error, title)
        kb.local = LocalKnowledge() if local is None else local
        return kb

    _, document = _documents()["AP-SOP-001"]
    clause = document[document.index("### 6.3 ") : document.index("### 6.4 ")]

    def _forcing(value, call):
        """Both modes are checked on every run, whatever the environment says."""
        global FORCE_SOP_RETRIEVAL  # noqa: PLW0603 - the flag under test
        previous, FORCE_SOP_RETRIEVAL = FORCE_SOP_RETRIEVAL, value
        try:
            return call()
        finally:
            FORCE_SOP_RETRIEVAL = previous

    # Flag off: the repo copy answers without touching the knowledge base.
    served = _stub([clause])
    local_hit = _forcing(False, lambda: served.guidance("AP-SOP-001 6.3"))
    assert local_hit and local_hit.source == "local", f"repo copy should answer: {local_hit}"
    assert served.client.calls == 0, "the knowledge base was queried when the repo copy already answered"

    # Flag on: retrieval drives the answer, still scoped and parsed per passage.
    forced_stub = _stub([clause])
    forced = _forcing(True, lambda: forced_stub.guidance("AP-SOP-001 6.3"))
    assert forced and forced.source == "bedrock", f"forced retrieval should answer: {forced}"
    assert forced_stub.client.calls == 1, "forced retrieval did not query the knowledge base"

    # Flag on, clause not retrievable: the repo copy still covers the clerk.
    empty_stub = _stub([])
    degraded = _forcing(True, lambda: empty_stub.guidance("AP-SOP-001 6.3"))
    assert degraded and degraded.source == "local", f"forced retrieval must still degrade: {degraded}"

    # Without the markdown deployed, the knowledge base answers.
    kb_hit = _stub([clause], local=_NoLocal()).guidance("AP-SOP-001 6.3")
    assert kb_hit and kb_hit.source == "bedrock", f"knowledge base should answer: {kb_hit}"
    assert len(kb_hit.steps) == len(local_hit.steps), "retrieved clause lost steps"

    # Regression: a heading in one chunk must never adopt another chunk's step
    # table. Concatenating passages produced "Vendor/Supplier Mismatch" above
    # the goods-receipt procedure against the live knowledge base.
    heading_only = "### 6.6 Vendor/Supplier Mismatch\n\n#### 6.6.1 Description\n\nVendor differs from the PO.\n"
    other_table = document[document.index("### 6.4 ") : document.index("### 6.5 ")]
    fabricated = _stub([heading_only, other_table], local=_NoLocal()).guidance("AP-SOP-001 6.6")
    assert fabricated is None, f"steps fabricated across chunks: {fabricated and fabricated.title}"

    outage = _stub([], error=RuntimeError("AccessDeniedException")).guidance("AP-SOP-001 6.3")
    assert outage and outage.source == "local", f"an outage must degrade, not raise: {outage and outage.source}"
    assert _stub([], error=RuntimeError("boom")).odata_path("vendor bank details") is None

    # Regression: the OpenAPI specifications are full of help.sap.com links.
    # Only a path key answers "which OData path"; a documentation URL does not.
    noise = '{"description": "see [Expand](https://help.sap.com/doc/x/OdataV2.pdf#page=63)"}'
    assert _stub([noise]).odata_path("purchase order") is None, "documentation link returned as an OData path"
    spec = '{"paths": {"/A_PurchaseOrder(\'{PurchaseOrder}\')": {"get": {}}}}'
    assert _stub([spec]).odata_path("purchase order") == "/A_PurchaseOrder('{PurchaseOrder}')"

    # A passage from the other SOP must not answer for this one. Sections 6.1
    # to 6.3 exist in both, and the rules cite all three from AP-SOP-001.
    _, other_document = _documents()["AP-SOP-002"]
    foreign = other_document[other_document.index("### 6.1 ") : other_document.index("### 6.2 ")]
    crossed = _stub(
        [foreign], local=_NoLocal(), title="duplicate-invoice-exception-sop.md"
    ).guidance("AP-SOP-001 6.1")
    assert crossed is None, f"a passage from AP-SOP-002 answered for AP-SOP-001: {crossed and crossed.title}"

    print(f"\nbedrock stub: repo-copy={local_hit.source} (0 calls), kb-fallback={kb_hit.source}, "
          f"cross-chunk={fabricated}, cross-document={crossed}, outage={outage.source}")
    print(f"FORCE_SOP_RETRIEVAL={FORCE_SOP_RETRIEVAL}")
    print("\nOK")
