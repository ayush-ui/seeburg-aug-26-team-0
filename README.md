# AP Copilot — Autonomous SAP Accounts Payable

**DMI Hackathon 2026 · Topic 3, provided by AWS**

A clerk drops a batch of supplier invoices in. The system reads each one,
validates it against **live SAP S/4HANA data** through an MCP server, and after
**a single human approval** parks a Supplier Invoice (MIR7) for every invoice
that passes. Failures are skipped and explained in plain business language,
with the resolution steps their own SOP prescribes.

> **The model reads. Code judges. A human approves.**
>
> Extraction is a language model's job. Every accept-or-reject decision is a
> deterministic pure function — so the same batch produces the same verdict
> twice, and changing a tolerance is a one-line data edit. Retrieval explains
> what to *do* about an exception; it never decides one.

---

## What it does

| | |
|---|---|
| **Intake** | Drop PDFs in or pick them from the inbox, choose which to run |
| **Validate** | 17 business rules per invoice against live purchase order and goods receipt data |
| **Approve** | One gate for the whole batch, enforced server-side by a single-use token |
| **Park** | A reversible draft invoice per passing invoice — no accounting entry, no PO consumed |
| **Exceptions** | A separate queue with the failing rule, its SOP clause, resolution steps, and a chat scoped to that invoice |
| **Reports** | The six reports `AP-SOP-001` section 9.3 already mandates, built from the batch that just ran |

Measured on the six-invoice demo batch: **32 SAP calls, 76 seconds**, 5 parked
and 1 exception.

---

## Requirements

- **Python 3.11+**
- **Node 20+**
- A `.env` file — copy `.env.example` and fill it in. Ask a teammate for the
  real values; they are never committed.

The workspace runs without AWS credentials. SAP access goes through Cognito
machine-to-machine auth, not IAM. Bedrock-backed features (vision extraction,
Knowledge Base retrieval, the Strands agent) each fall back to a working local
provider and switch over automatically when credentials appear. `GET
/api/health` reports which provider is live, and the header shows it.

---

## Install

```bash
git clone https://github.com/ayush-ui/seeburg-aug-26-team-0.git
cd seeburg-aug-26-team-0
```

Backend:

```bash
pip install -r src/backend/requirements.txt
```

Frontend:

```bash
npm install --prefix src/frontend
```

Environment:

```bash
cp .env.example .env
```

Then fill in `.env`. See **Configuration** below for what each value is.

---

## Run

Two terminals.

**Backend** — serves the API on port 8000:

```bash
python -m uvicorn api:app --port 8000 --app-dir src/backend
```

**Frontend** — serves the workspace on port 5173:

```bash
npm run dev --prefix src/frontend
```

Open **http://localhost:5173** and sign in with `admin` / `admin`.

> The sign-in is a demo stub — no token, no server-side check. It is not a
> security boundary and is not presented as one.

The first batch takes around 75 seconds because it genuinely reads every
document and validates each against SAP. The header shows a green **Live SAP**
chip when the backend is reachable, and an amber **Seeded data** chip when it
is not — the workspace still opens either way, so a demo survives the backend
going down.

### Try it

1. **Intake** — tick the invoices you want, press *Process N invoices*
2. **Approvals** — pick a row; the original PDF sits beside the extracted
   fields with their SAP field names and extraction confidence
3. *Show all 17 rules* — the full validation, including rules reported as
   *not checked* rather than failed
4. **Park N in SAP** — one confirmation, then real parked document numbers
5. **Exceptions** — pick the failing invoice, then *Ask the assistant*
6. **Reports** — generate any report; KPIs are measured against the SOP targets

---

## Tests

Both suites run in about a second with no network and no credentials:

```bash
cd src/backend && python test_rules.py && python test_sap.py
```

Live smoke tests, which do reach SAP:

```bash
cd src/backend && python sap.py          # read-only
cd src/backend && python knowledge.py    # SOP parsing
cd src/backend && python agent.py        # exception assistant
```

CI runs both suites plus a secret scan on every push.

---

## Configuration

Every variable is documented in [`.env.example`](.env.example). The ones that
matter:

| Variable | What it is |
|---|---|
| `MCP_URL_CUSTOM` | The MCP server on Bedrock AgentCore that fronts SAP |
| `COGNITO_TOKEN_ENDPOINT_CUSTOM` | Machine-to-machine token endpoint |
| `COGNITO_CLIENT_ID_CUSTOM` / `..._SECRET_CUSTOM` | Client credentials for that endpoint |
| `SAP_BASE_URL` | Base path for the OData services |
| `SAP_POSTING_DATE` | Must fall in an open posting period. `2025-03-15` on this system — today's date fails |
| `INVOICE_REFERENCE_PREFIX` | Your AWS account id. Each posting is tagged `<prefix>-<n>`, unique per team and per invoice |
| `INVOICE_SEQUENCE_START` | Bump it to get fresh references after a run, or the duplicate check trips |

**SAP credentials are not in here.** They live in AWS Secrets Manager and are
read only by the MCP server, so this process never sees a SAP password.

---

## Tech stack

**Backend** — Python, FastAPI, `requests`. No ORM and no database: batch state
is in memory, deliberately, for a two-day build.

**SAP access** — OData v2 through a Model Context Protocol server running on
Amazon Bedrock AgentCore Runtime, authenticated with Cognito client
credentials.

**AI** — Claude Sonnet 4.5 on Amazon Bedrock for document extraction; Bedrock
Knowledge Bases for SOP and OData-specification retrieval; a Strands agent for
the exception assistant. Each has a local fallback.

**Frontend** — Vite, React, Material 3 design tokens, dark by default with
light switchable. Roboto is vendored rather than fetched, so the demo works
offline. No component library and no CSS framework.

**CI** — GitHub Actions: both test suites and a gitleaks scan.

---

## Documentation

| | |
|---|---|
| [`docs/ARCHITECTURE.md`](docs/ARCHITECTURE.md) | The authoritative design: components, agents, the exact call sequence, the approval state machine, and the measured call budget |
| [`docs/architecture.html`](docs/architecture.html) | The same content as a standalone page with hand-drawn diagrams — open it straight from disk, no server needed |
| [`docs/LESSONS-LEARNED.md`](docs/LESSONS-LEARNED.md) | What broke and why: a dead managed MCP server, a POST that rejects `$format`, parked drafts wrongly consuming purchase orders, and the optimisation that turned out to be the wrong one. Read this before debugging anything SAP-shaped |
| [`AGENTS.md`](AGENTS.md) | Working instructions: conventions, commit rules, and what to update after every change |
| [`CHANGELOG.md`](CHANGELOG.md) | What shipped, newest first |
| [`ROADMAP.md`](ROADMAP.md) | What is next, and what we are deliberately not building |

---

## Repository layout

```
Invoices/                 The inbox the backend reads
docs/                     Architecture, lessons learned, standalone page
src/backend/
  rules.py                17 validation rules. Pure — no network, no clock
  sap.py                  Every SAP read and the single write, over MCP
  extract.py              Document to typed invoice
  knowledge.py            SOP clause to resolution steps
  agent.py                The exception assistant
  reports.py              SOP section 9.3 reports
  api.py                  FastAPI, and the approval state machine
  mcp/                    The MCP server deployed to Bedrock AgentCore
src/frontend/             Vite + React workspace
```

---

## Safety

Every write is a **parked** document (`SupplierInvoiceStatus = "A"`). A parked
invoice creates no accounting entry, does not consume the purchase order, and
can be deleted — which is what makes this safe to run against a SAP system
shared with other teams. Nothing is ever posted for payment.

Each posting is tagged `<account-id>-<n>`, unique per team and per invoice, so
nothing collides between participants.

---

## Team

| Name | GitHub |
|---|---|
| Shrikant Dubale | [@shrikant-d](https://github.com/shrikant-d) |

<!-- Add remaining team members here, and a demo video link once recorded.
     Do not commit the video itself - host it externally. -->
