# Changelog

Newest first. Every behavioural change gets an entry.

---

## Intake and the validation panel — `d11fdf6`

**Added** an Intake tab as the entry point to the workspace. Documents can be
dropped on it or chosen from a file picker; the inbox lists what is waiting
with its size and whether it has already been validated or parked. Files are
selected individually and only the selection is processed, so one corrected
invoice can be re-run without repeating the batch.

**Added** three endpoints: `GET /api/inbox`, `POST /api/uploads` (multipart),
and an optional `files` list on `POST /api/batches`. Omitting the list still
processes the whole inbox, so the unattended daily run is unchanged.

**Added** boundary checks on upload: only files whose bytes begin with `%PDF`
are accepted, and only by base name, so an uploaded name cannot choose where on
disk it lands. A file name given to `/api/batches` is resolved against the
inbox and refused if it escapes it.

**Added** reporting for documents that cannot be read. They previously vanished
from the batch; they now appear as a banner above the queues with the reason,
which matters because a newly uploaded document needs Bedrock to extract.

**Fixed** the validation panel showing roughly five of its seventeen rules with
no way to reach the rest. Panels carry `overflow: hidden` for their rounded
corners, and as flex items in a scrolling column they were shrinking to 588px
around 2287px of content — clipping it rather than letting the column scroll.
The same latent bug existed in the reports sidebar.

---

## Live backend — `edba2a5`

**Added** `api.py`, which composes the other modules and owns the approval
state machine: `CREATED → VALIDATED → APPROVED → PARKED`. `/approve` is the
only path that mints a token, the token is bound to the exact references that
passed validation, and `/park` refuses without it. An invoice that failed
validation can never be included, and one failed write does not abandon the
rest of the batch.

**Added** `extract.py`. Bedrock vision when AWS credentials resolve, otherwise
extractions recorded from the documents themselves. Model output is normalised
at the boundary: European decimal commas and several date formats become
`Decimal` and `date` before `rules.py` sees them.

**Added** `knowledge.py`. The Bedrock Knowledge Base when reachable, otherwise
the same SOP markdown the Knowledge Base is built from. Both read one source,
so the guidance is identical either way.

**Added** `agent.py`, the exception assistant and the only genuinely agentic
component. Strands with three read-only tools when Bedrock is reachable; a
deterministic responder over the same finding and SOP clause otherwise. Neither
can overturn a verdict or park anything.

**Added** `reports.py`, building the reports `AP-SOP-001` section 9.3 mandates
from the batch that just ran.

**Changed** SAP reads to run concurrently, one client per invoice. A single MCP
round trip takes several seconds and each invoice's reads are independent, so
wall time now tracks the slowest invoice rather than their sum: **202 seconds
became 76**.

**Added** read caches on the SAP client, keyed by purchase order and by vendor.
These help when a batch repeats a purchase order. On the demo batch every
invoice targets a different one, so only the vendor cache hits and it saves
4 calls of 32.

**Fixed** `docs/ARCHITECTURE.md`, which claimed those caches would cut 32 calls to
about 14. That was never true of this batch. The document now carries measured
numbers.

**Changed** the frontend to select its source at start-up and show which one is
live, so seeded data can never be mistaken for a real posting.

---

## Front end — `d1e2329`

**Added** the workspace: Vite + React, Material 3 tokens per
`challenges/ui-design-direction.md`, dark by default with light switchable,
Roboto vendored locally so the demo needs no network.

- **Approvals** lists every invoice that can be parked, with the original PDF
  beside the extracted fields. The primary action parks the whole batch behind
  one confirmation; a single invoice can also be parked alone. A warning raises
  who must approve rather than blocking the write.
- **Exceptions** is the other team's queue: the failing rule, the SOP clause it
  names, and the resolution steps retrieved for that clause with owner and
  timeframe. A chat panel scoped to one invoice answers from the same finding.
  There is deliberately no park action — a corrected invoice returns to the
  approvals queue and goes through the same gate.
- **Reports** offers what `AP-SOP-001` section 9.3 already mandates, alongside
  the section 10 KPIs.

**Changed** the light-mode success token from `#0f7a66` to `#0a6152`. Contrast
was measured in the running app rather than assumed; the original was 4.43:1,
just under AA.

---

## Knowledge grounding — `99b258d`

**Added** the knowledge layer to the design after reviewing the workshop's own
architecture diagram, which feeds two Bedrock Knowledge Bases from S3. Topic 3
names knowledge grounding as an evaluation dimension and both knowledge bases
were already deployed in the account.

The rules engine is unchanged. Verdicts must not come from a vector search, so
the split is explicit: `rules.py` decides pass or fail and names the governing
SOP clause; retrieval answers only what the clerk should do about it, keyed by
that clause.

**Fixed** two details against the same diagram: the OData call is retried on
transient failure, and SAP sits in its own VPC behind an application load
balancer.

**Added** `docs/architecture.html`, the same content as a standalone page with
four hand-drawn SVG figures, no scripts and no external requests.

---

## SAP write path — `a4e688f`

Proved the write end to end against the demo system: validate, park, read back,
delete. Document `5100001509` was parked with status A, every field read back
correct, then removed. Three defects surfaced that no amount of unit testing
against the specification would have found.

**Fixed** a POST carrying `$format`, which SAP rejects with *"The Data Services
Request contains SystemQueryOptions that are not allowed for this Request
Type"*. Writes now use a bare entity-set path.

**Fixed** handling of a successful DELETE, which answers `204 No Content`. The
MCP tool reports an empty body as prose rather than JSON, so the client raised
on a call that had in fact succeeded.

**Fixed** parked invoices being counted as consuming the purchase order. They
do not. Another team had left eight parked drafts against PO 4500001463, which
made a purchase order with 5 PC open read as 40 PC invoiced and would have
raised a false quantity exception on every invoice in the demo.

---

## SAP layer — `99daabb`

**Added** `sap.py`, routing every SAP call through the MCP server on Bedrock
AgentCore rather than straight to OData, so SAP credentials stay in Secrets
Manager and are never visible to this process.

Field mapping was verified against the live system rather than read off the
specification, which caught two things: an invoice references `InvoicingParty`
(`17401710`), not `Supplier` (`BP1710`); and `NetPriceAmount` is the price for
`NetPriceQuantity` units, not for one.

**Added** a GitHub Actions workflow running both test suites and a gitleaks
scan, and `.env.example` documenting every variable.

---

## Rules engine — `2b09836`

**Added** `rules.py`: 17 validation rules as a pure function with no network,
no clock and no globals, so the whole rule set runs against fixtures without
credentials.

Each `Finding` carries the invoice value, the SAP value, the delta, a
business-English message, the SOP clause and an approval level. Routing
thresholds come from `AP-SOP-001` section 8.1 and live in a table, so a
threshold change is a data edit. That turns a binary pass/fail into *"price is
3.17% over PO, EUR 3.60 — needs AP Manager"*.

A rule that cannot be evaluated reports `NOT_APPLICABLE`, not `FAIL`.

---

## Workshop MCP server — `2625532`

**Changed** the layout: the workshop's MCP server and its CloudFormation
parameters moved to `src/backend/mcp/`.

**Fixed** two log statements that wrote credentials on every run.
`sap_mcp_server.py` logged the full request headers, which contain the
`Authorization: Basic` header — reversible base64 of the SAP username and
password — and the response headers, which contain `x-csrf-token` and
`Set-Cookie`. `deploy_mcp_server.py` printed the whole Cognito config,
including the client secret. Both now log key names only.
