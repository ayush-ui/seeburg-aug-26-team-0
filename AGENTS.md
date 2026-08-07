# AGENTS.md

Instructions and context for anyone — human or agent — working on this
repository. Read this before changing anything.

---

## 1. What this is

**Autonomous SAP Accounts Payable.** DMI Hackathon 2026, Topic 3 (provided by
AWS). A clerk drops a batch of supplier invoices in, the system extracts and
validates every one against live SAP S/4HANA data, and after a single human
approval it parks a Supplier Invoice (MIR7) for each that passes. Failures are
skipped and explained in plain business language.

The challenge brief is `challenges/topic-3-aws.md` in
`dmi-hackathons/hackathon-seeburg-2026`. `docs/ARCHITECTURE.md` here is the
authoritative design document; `docs/architecture.html` is the same content as
a standalone page.

### The one principle everything follows

> **The model reads. Code judges. A human approves.**

Language models read scanned documents well and explain situations well. They
are unreliable at arithmetic, at applying a tolerance table the same way twice,
and at never inventing a purchase order. So:

- **Extraction** is a model's job (`extract.py`).
- **Every accept/reject decision** is a deterministic pure function
  (`rules.py`). It has no network, no clock and no globals.
- **Retrieval never produces a verdict** (`knowledge.py`). It is keyed by the
  SOP clause the rules engine has *already* named, making it a lookup rather
  than a search for the answer.
- **Nothing is written to SAP** without an approval token from the server.

If a change would move a decision out of `rules.py` and into a prompt, it is
the wrong change. Push back or ask.

---

## 2. Repository layout

```
README.md                Start here: install, run, and where everything is.
AGENTS.md                This file. Instructions for anyone working here.
CLAUDE.md                Imports AGENTS.md.
CHANGELOG.md             What shipped, newest first.
ROADMAP.md               What is next, and what is deliberately not being done.
docs/ARCHITECTURE.md     Authoritative design. Update when the design changes.
docs/LESSONS-LEARNED.md  What broke, what fixed it, what we cannot do.
docs/architecture.html   Standalone architecture page, self-contained.
Invoices/                The inbox the backend reads. Demo documents live here.
SOP/ (in src/backend/mcp) AP-SOP-001 and the duplicate-invoice SOP.

src/backend/
  rules.py               17 validation rules. Pure. The heart of the project.
  sap.py                 Every SAP read and the single write, over MCP.
  extract.py             Document -> typed Invoice.
  knowledge.py           SOP clause -> resolution steps.
  agent.py               The exception assistant. The only agentic component.
  reports.py             The reports AP-SOP-001 section 9.3 mandates.
  api.py                 FastAPI. Composition and the approval state machine.
  fixtures.py            Synthetic invoices and SAP context for tests.
  test_rules.py          22 tests. No network.
  test_sap.py            23 tests. Recorded payloads, no network.
  extractions.json       Fallback extractions when Bedrock is unreachable.
  mcp/                   The MCP server deployed to Bedrock AgentCore.

src/frontend/            Vite + React.
  src/lib/api.js         Provider selection: live backend or seeded data.
  src/lib/client.js      The live backend client.
  src/views/             Intake, Approvals, Exceptions, Reports.
  src/styles/tokens.css  Material 3 tokens. All colour lives here.
```

---

## 3. Running it

```bash
# backend
cd src/backend && python -m uvicorn api:app --port 8000

# frontend, separate terminal
npm run dev --prefix src/frontend
```

Then `http://localhost:5173`, sign in `admin` / `admin`.

Tests — both run in about a second, with no network and no credentials:

```bash
cd src/backend && python test_rules.py && python test_sap.py
```

Live smoke tests, which do reach SAP:

```bash
cd src/backend && python sap.py          # read-only
cd src/backend && python knowledge.py    # SOP parsing, and the knowledge base
cd src/backend && python extract.py      # normalisation and batch ordering
cd src/backend && python agent.py        # exception assistant
```

`knowledge.py` and `extract.py` run fully without credentials — the Bedrock
branches are exercised against a stub client, so the parsing, the fallbacks and
the batch ordering are all checked offline. With credentials they additionally
probe the live knowledge base, and `agent.py` makes real model calls.

`knowledge.py` checks both settings of `FORCE_SOP_RETRIEVAL` on every run,
whatever the environment says, so neither mode can rot unnoticed.

---

## 4. Rules for changing code

### Money and numbers

**`Decimal`, never `float`, anywhere near an amount or a quantity.** Rules 10
and 11 reconcile arithmetic exactly; a float rounding artifact invents an
exception that does not exist. Model output is normalised to `Decimal` at the
boundary in `extract.py` and the type is the guard from there on.

Invoices print European format (`113,50`, `1.234,56`). Normalise at extraction,
never downstream.

### Verdicts

- A rule that cannot be evaluated is `NOT_APPLICABLE`, not `FAIL`. An invoice
  with a missing purchase order reports one failure and ten not-checked, not
  eleven failures.
- `FAIL` blocks the write. `WARN` raises the required approval level and still
  parks.
- Approval routing comes from the tolerance table in `rules.py`, which is data
  transcribed from `AP-SOP-001` section 8.1. Change the table, not the branches.

### SAP

- Everything goes through the MCP server. Never call OData directly; the
  backend must never hold a SAP credential.
- Writes are always `SupplierInvoiceStatus = "A"` (parked). Never post for
  payment. A parked document creates no accounting entry and does not consume
  the purchase order, which is what makes this safe on a shared system.
- Every posting carries `<account-id>-<n>`, capped at SAP's 16 characters.
- A "not found" is a verdict for `rules.py` to give. A backend outage is a
  fault and must raise.

### Frontend

- **No raw hex in components.** Every colour comes from a token in
  `tokens.css`. Both themes are defined; both must stay AA (4.5:1) — measure it
  in the browser, do not assume.
- **Status is never colour alone.** Every chip carries an icon and a word, and
  rows carry a severity stripe, so the queues read in greyscale.
- Money is right-aligned with `tabular-nums`. Columns exist to be compared.
- Follow `challenges/ui-design-direction.md`: Material 3, dark default with
  light switchable, `#B71818` primary, `#263BF1` secondary, teal for success,
  Roboto. Roboto is vendored, not fetched — the demo must work offline.
- Panels use `overflow: hidden`. As flex items in a scrolling column they must
  carry `flex: none`, or they shrink and clip their content instead of letting
  the column scroll. This bug has already been shipped once.

### Tests

Non-trivial logic leaves one runnable check behind. Both suites must pass
offline; anything needing network belongs in a `__main__` smoke test, not in
the suite. CI runs both plus a gitleaks scan.

---

## 5. Commit rules

**One logical change per commit.** Do not batch unrelated edits. Several small
files that change together for one reason are fine; two features in one commit
are not.

**Subject line:** imperative mood, no trailing period, under about 72
characters. `Add invoice intake`, not `Added intake stuff.`

**Body:** explain *why*, and what you learned. If a defect was found by running
something, say what you ran and what it returned. Wrap at 78 characters. If the
change is genuinely obvious, no body is needed.

**Never add AI attribution.** No `Co-Authored-By: Claude`, no "generated by"
trailers, nothing of the sort. These repositories are cloned and analysed after
the event; authorship reads as the team's own.

**Never commit secrets.** `.env` is gitignored and must stay that way.
`.env.example` documents every variable with empty values. Before pushing, the
CI gitleaks job is a backstop, not a substitute for looking at
`git status --short`.

**Do not amend or force-push** shared history.

---

## 6. What to update after every commit

This is not optional. A commit that changes behaviour and leaves these stale is
an incomplete commit.

| File | Update when |
|---|---|
| `CHANGELOG.md` | **Every** behavioural change. Newest entry first. Say what changed and why, in a sentence a teammate can read cold. |
| `ROADMAP.md` | Something planned ships, becomes unnecessary, or a new gap appears. Move the item, do not delete it silently. |
| `docs/LESSONS-LEARNED.md` | A defect took more than a few minutes to understand, a workaround was needed, an architectural decision was reversed, or a limitation was discovered. |
| `docs/ARCHITECTURE.md` | Any change to components, data flow, call sequence, or the numbers it quotes. **Never leave a claimed number unmeasured** — this document has already carried a figure that was never true. |
| `docs/architecture.html` | Whenever `docs/ARCHITECTURE.md` changes. The two must agree. |
| `.env.example` | A new environment variable is introduced. |
| `README.md` | Setup, usage, or the tech stack changes. |

A documentation-only commit is fine and often correct. Keep it separate from
the code change when the code change is already large.

---

## 7. Constraints worth knowing before you start

- **Bedrock may be unreachable.** Extraction, SOP guidance and the Strands
  chat each have a working fallback and select their provider automatically.
  `GET /api/health` reports which is live, and the UI shows it. Do not remove
  the fallbacks; do not present seeded data as live.
- **SOP guidance reads the repository copy on purpose**, even when the
  Knowledge Base is reachable. The managed chunker splits a clause's step table
  away from its heading, so retrieval returns correct clauses with incomplete
  procedures. Do not "fix" this by preferring retrieval without re-chunking the
  S3 documents first, and never reassemble passages into one blob — that
  produced a correct clause title above another clause's steps. See
  `docs/LESSONS-LEARNED.md` §10.
- **Retrieved passages must stay scoped to one document.** Sections 6.1 to 6.3
  exist in both SOPs and the rules cite all three from `AP-SOP-001`, so an
  unscoped passage parses cleanly as the wrong clause.
- **Modules that read configuration at import must call `load_dotenv()`
  themselves.** `extract.py` and `knowledge.py` both do. Relying on `api.py`
  having loaded it first makes them report the wrong provider when run
  directly.
- **A single MCP round trip takes several seconds.** Reads are run
  concurrently for that reason. Adding a sequential read to `build_context`
  costs real demo time.
- **The SAP system is shared.** Other teams leave parked drafts against the
  same purchase orders. Parked documents do not consume a PO and are excluded
  from invoiced quantity — do not "simplify" that away.
- **`admin` / `admin` is a stub**, not a security boundary. There is no token
  and no server-side check. Say so in any documentation that mentions it.
- **Batch state is in memory.** Restarting the backend loses it.

See `docs/LESSONS-LEARNED.md` before debugging anything SAP-shaped; most of the
sharp edges are already written down there.
