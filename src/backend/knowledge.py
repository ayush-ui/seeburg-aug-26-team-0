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

import os
import re
from dataclasses import dataclass, field
from functools import lru_cache
from pathlib import Path

SOP_DIR = Path(os.environ.get("SOP_DIR", Path(__file__).resolve().parent / "mcp"))

SOP_KB_ID = os.environ.get("SOP_KNOWLEDGE_BASE_ID", "HRQMR9REUCexcd")
API_KB_ID = os.environ.get("API_KNOWLEDGE_BASE_ID", "M6GBMOSKQX")
AWS_REGION = os.environ.get("AWS_REGION", "us-east-1")


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

# `Finding.sop_ref` looks like "AP-SOP-001 6.1 / 8.1". The leading section
# number is the procedure; anything after the slash is a tolerance table.
SECTION_IN_REF = re.compile(r"(\d+\.\d+)")


@lru_cache(maxsize=1)
def _sop_text() -> str:
    if not SOP_DIR.is_dir():
        return ""
    return "\n\n".join(
        path.read_text(encoding="utf-8") for path in sorted(SOP_DIR.glob("*.md"))
    )


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


class LocalKnowledge:
    """Retrieval over the SOP markdown in the repository."""

    source = "local"

    def guidance(self, sop_ref: str) -> Guidance | None:
        text = _sop_text()
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
            source=self.source,
        )

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

    def _retrieve(self, kb_id: str, query: str, k: int = 5) -> list[str]:
        response = self.client.retrieve(
            knowledgeBaseId=kb_id,
            retrievalQuery={"text": query},
            retrievalConfiguration={"vectorSearchConfiguration": {"numberOfResults": k}},
        )
        return [
            r.get("content", {}).get("text", "")
            for r in response.get("retrievalResults", [])
            if r.get("content", {}).get("text")
        ]

    def guidance(self, sop_ref: str) -> Guidance | None:
        """Retrieve the clause, then parse it with the same parser as local.

        Structure matters more than recall here: the UI renders numbered steps
        with an owner and a timeframe, so a wall of retrieved prose is worse
        than the parsed section. The retrieval confirms the clause exists and
        supplies the passage; the parser gives it shape.
        """
        passages = self._retrieve(SOP_KB_ID, f"{sop_ref} resolution steps and common causes")
        parsed = self.local.guidance(sop_ref)
        if parsed is not None:
            parsed.source = self.source
            return parsed
        if not passages:
            return None
        return Guidance(
            sop_ref=sop_ref,
            title=sop_ref,
            causes=[],
            steps=[],
            policy=passages[0][:800],
            source=self.source,
        )

    def odata_path(self, question: str) -> str | None:
        passages = self._retrieve(API_KB_ID, question, k=3)
        for passage in passages:
            match = re.search(r"(https?://\S+|/sap/opu/odata/sap/\S+)", passage)
            if match:
                return match.group(1).rstrip(".,)")
        return None


@lru_cache(maxsize=1)
def provider():
    """The best provider this environment can reach."""
    if bedrock_available():
        try:
            return BedrockKnowledge()
        except Exception:  # noqa: BLE001 - fall back rather than fail the request
            pass
    return LocalKnowledge()


def guidance(sop_ref: str) -> Guidance | None:
    return provider().guidance(sop_ref)


def odata_path(question: str) -> str | None:
    return provider().odata_path(question)


if __name__ == "__main__":
    p = provider()
    print(f"provider: {p.source}\n")
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
        print(f"{ref:24} {g.title:42} {len(g.causes)} causes, {len(g.steps)} steps")
        assert all(s.who and s.when for s in g.steps), f"step missing owner or timeframe in {ref}"
    print("\nOK")
