# Lessons learned

What did not work, what fixed it, and what we still cannot do. Written for the
next person to hit the same wall.

The theme running through most of it: **the specification was right about
shapes and wrong about behaviour.** Every defect below was found by calling the
live system, and none of them would have been found by reading the OData
specification more carefully.

---

## 1. The managed AWS-for-SAP MCP server was dead

**What happened.** Lab 06 builds on the AWS-managed MCP server from Lab 05. Its
Cognito token endpoint issued tokens fine, but every JSON-RPC call returned:

```
-32010  Runtime initialization time exceeded. Please make sure that
        initialization completes in 120s.
-32010  Runtime health check failed or timed out.
```

The container never came up. Nothing on our side could fix it.

**What we did.** Switched to the custom MCP server from Labs 03/04, which was
also deployed in the account and is healthy — FastMCP 1.29.0, exposing a single
generic `invoke_sap_odata_service` tool. Topic 3 names MCP as a constraint but
does not require the managed server, so Challenge Fit is unaffected.

**Consequence.** `sap.py` is written against a single generic OData tool rather
than a rich tool surface. That turned out to suit us: one tool, any URL, any
method, and the mapping logic stays in our code where it can be tested.

**If you hit this.** `Config.from_env(suffix)` selects the deployment.
`_CUSTOM` is the working one; drop the suffix to target the managed server if
it is ever revived.

---

## 2. A POST carrying `$format` is rejected

**What happened.** The first real park attempt failed with:

```
The Data Services Request contains SystemQueryOptions
that are not allowed for this Request Type
```

Reads use `?$format=json` happily. Writes do not permit system query options at
all.

**Fix.** Writes use a bare entity-set path. The `Accept` header already asks
for JSON.

**Cost.** Would have failed on the first live posting, in front of the jury.
Found only because we ran an actual park.

---

## 3. A successful DELETE looked like a failure

**What happened.** Deleting a parked document raised
`SAP returned a non-JSON response: Request successful. Status: 204`. SAP
answers a successful DELETE with `204 No Content`, and the workshop's MCP tool
reports an empty body as prose rather than JSON, so the client raised on a call
that had already succeeded.

This cost real confusion: the delete *had* worked server-side, so we spent time
hunting an orphaned document that never existed.

**Fix.** `EMPTY_SUCCESS` matches `Request successful. Status: 2xx` and returns
`{}`. Genuine garbage still raises.

**Lesson.** When a tool wraps HTTP, its success representation is part of the
contract. Do not assume JSON in, JSON out.

---

## 4. Parked invoices were consuming purchase orders

The most valuable defect found, and the one most likely to have wrecked the
demo.

**What happened.** PO 4500001463 has 5 PC ordered. `get_invoiced_quantity`
reported **40 PC already invoiced**, so every invoice against it raised a
quantity exception.

The cause was another team. Eight *parked* drafts from a different
participant's account referenced that purchase order, and we were counting
them.

**Why it matters.** A parked invoice is a draft. It creates no accounting entry
and does not consume the purchase order — which is precisely why parking is
safe on a shared system. Counting drafts contradicts the reason parking was
chosen in the first place.

**Fix.** `get_invoiced_quantity` now excludes status `A`. The item rows carry
no status and there is no navigation from item to header, so the status join is
a second batched read (20 keys per request, to keep the `$filter` URL short).

**Result.** PO 4500001463 went from "40 invoiced, -35 open" to "0 invoiced,
5 open". Three of the five demo purchase orders are still genuinely fully
invoiced by *posted* documents — those warnings are real and worth demoing.

---

## 5. Two field mappings the specification would not have given us

**`InvoicingParty`, not `Supplier`.** PO 4500001563 carries
`Supplier: "BP1710"` and `InvoicingParty: "17401710"`. An invoice references
the latter. Mapping `Supplier` would have failed the vendor check on every
single invoice — and vendor mismatch escalates to Controller as a fraud signal,
so the demo would have looked alarming and wrong.

**`NetPriceAmount` is per `NetPriceQuantity`.** It is the price for
`NetPriceQuantity` units, not for one. It happens to be 1 for these materials,
so the bug would have stayed hidden until a material priced per 100 appeared,
then failed every price check by a factor of 100. There is a regression test
for it.

---

## 6. Caching was the wrong optimisation

**What happened.** `ARCHITECTURE.md` claimed two read caches would cut a
six-invoice batch "from roughly 32 calls to about 14". The caches had been
documented but never built. When implemented and measured, they saved **4 calls
of 32**, and wall time did not move: 202 seconds before, 202 seconds after.

Every invoice in the batch targets a *different* purchase order, so the PO
cache never hits. Only the vendor cache does.

**The actual problem.** A single MCP round trip takes roughly seven seconds.
Call count was never the lever.

**Fix.** Run the reads concurrently — each invoice's reads are independent, one
client per worker because the MCP session id is per client. **202 seconds
became 76.**

**Two lessons.** Measure before optimising; the obvious lever was the wrong
one. And never write a performance number into a document before the code
exists to produce it — that figure sat in `ARCHITECTURE.md` as an assertion for
several commits, and correcting it is now an entry in the changelog.

---

## 7. Panels were clipping their own content

**What happened.** Expanding the validation panel to all 17 rules showed about
five, with no way to reach the rest and no scrollbar.

**Cause.** `.panel` carries `overflow: hidden` to get rounded corners. As a
flex item in a scrolling column it shrank to 588px around 2287px of content, so
the overflow was hidden rather than scrolled, and the column never grew enough
to scroll itself.

```
before   panel h=588   scrollH=2287   clipped
after    panel h=2359  scrollH=2359   intact, column scrolls 816 → 3029
```

**Fix.** `flex: none` on panels inside scrolling columns. The reports sidebar
had the same latent bug.

**Lesson.** `overflow: hidden` plus flex shrink hides content silently. Measure
`scrollHeight` against `clientHeight` in the browser rather than reasoning
about the cascade.

---

## 8. Credentials were being written to logs

The workshop code we inherited logged secrets on every run:

- `sap_mcp_server.py` logged the full request headers, including
  `Authorization: Basic` — reversible base64 of the SAP username and password —
  and the response headers, containing `x-csrf-token` and `Set-Cookie`.
- `deploy_mcp_server.py` printed the entire Cognito configuration, including
  the client secret.

Both now log key names only. Nothing needed rotating because no secret value
was ever committed, but the code would have written them into CloudWatch on
every single call.

---

## 9. Two things we were wrong about

Recorded because both were stated confidently and both were false.

**The SOP files did not differ.** `diff -q` reported the copies in `SOP/` and
`src/backend/mcp/` as different. They are byte-identical apart from line
endings — same length, same 26 sections. Nothing needed reconciling.

**The design tool's output contradicted the brief.** `ui-ux-pro-max`
recommended "Exaggerated Minimalism", oversized type, massive whitespace, a
navy and green palette and Inter. `challenges/ui-design-direction.md` mandates
the opposite: restrained, compact, Material 3, `#B71818` / `#263BF1`, Roboto.
We kept only the Data-Dense Dashboard pattern and the accessibility checklist.
A generated recommendation does not outrank a stated requirement.

---

## 10. The Bedrock paths were broken in three different ways

They had never run. Credentials arrived on 7 August and all three failed, each
for a different reason. Recorded in the order they surfaced, because each one
was hidden behind the previous.

**`boto3` was not in `requirements.txt`.** Every Bedrock provider checks
`import boto3` and falls back on `ImportError`, so all three paths selected
their local fallback on every machine, silently and by design. The fallbacks
worked, `/api/health` reported honestly, and nothing looked wrong. That is
exactly why the real defects underneath survived to the last day.

**The retrieval call was malformed.** Both workshop knowledge bases are type
`MANAGED`, and a managed knowledge base rejects `vectorSearchConfiguration`:

```
ValidationException: Incompatible configuration: vectorSearchConfiguration
is not supported for managed knowledge bases. Use managedSearchConfiguration
instead.
```

Worth noting what this error was *not*: not credentials, not a permission, not
a wrong knowledge base id. Both ids were correct and `ACTIVE` all along. The
error is precise and names its own fix — but only something holding
credentials could ever see it.

**Retrieval returned the wrong procedure.** This one was ours, and it is the
one that mattered. Passages were joined into a single blob before parsing, so
the section splitter took a heading from one chunk and a step table from
another. "Vendor/Supplier Mismatch" came back above the goods-receipt
procedure; "Tax and Freight Discrepancies" came back above `AP-SOP-002`'s
duplicate-payment recovery steps. A clerk would have been shown the wrong
instructions for a fraud-adjacent exception, under a heading that looked
right.

**Lesson.** A fallback that is good enough to demo is good enough to hide a
broken primary path indefinitely. The fallback here is not a mock — it reads
the same document — which made it *more* dangerous, not less, because there
was no visible degradation to prompt anyone to look.

### Why the repository copy still answers

Once retrieval worked, it was worse than what it replaced. The managed chunker
splits a clause's step table away from its `### 6.6` heading, and for a 6.6
query the top-scoring chunk was 6.5.3. Parsing passages individually stops the
fabrication but then returns partial procedures — 3 of 7 steps for 6.3, 2 of 5
for 6.2.

So the repository copy is authoritative and the knowledge base is the
fallback, which also means the common path makes no network call at all.
`FORCE_SOP_RETRIEVAL=1` flips it for a demo. This is not retrieval being
useless: the API knowledge base has no local equivalent and is the only source
for `odata_path`.

### Sections 6.1 to 6.3 exist in both SOPs

Found while adding the force flag, and it would have been a live defect.
`AP-SOP-001 6.1` is Price Variance; `AP-SOP-002 6.1` is Automated ERP System
Checks. The rules cite 6.1, 6.2 and 6.3 from `AP-SOP-001`, so a passage from
the duplicate-invoice SOP parses cleanly as the wrong clause and reads as
authoritative.

Two fixes: the local parser now keys sections by document instead of
concatenating both files into one namespace — previously the right answer won
only by alphabetical accident — and retrieved passages are filtered on the
`_document_title` metadata.

### A URL is not an answer

`odata_path` matched `https?://\S+` first, so it returned
`https://help.sap.com/doc/.../OdataV2.pdf#page=64)"` — trailing punctuation
included. The API knowledge base holds OpenAPI specifications, where the
answer is a JSON key: `"/A_PurchaseOrder('{PurchaseOrder}')"`. A regex broad
enough to match anything will match the wrong thing confidently.

### `load_dotenv()` is not inherited

`extract.py` and `knowledge.py` both read configuration into module constants
at import, but neither called `load_dotenv()`. They worked under the server
only because `api.py` loads the file before importing them. Run either
directly and it reported `cached`, or used a stale knowledge base id, with a
correctly filled `.env` sitting beside it. The first vision benchmark this
produced was six cache reads at 0.0s each, reported as passing.

**Lesson.** A module whose behaviour depends on import order will eventually
be imported in the other order, and a timing of 0.0s deserves suspicion rather
than celebration.

---

## Architectural decisions and why

| Decision | Reason |
|---|---|
| **Verdicts are a pure function, not a prompt** | Reproducible, unit-testable, and a threshold change is a data edit. A model asked to apply a tolerance table will eventually apply it differently. |
| **Retrieval is keyed by the clause the rules named** | Makes it a lookup rather than a search for the answer, so retrieval cannot drift the verdict. Worst case it returns unhelpful guidance beside a correct decision. |
| **Only the chat is an agent** | It is the only part with a real loop — decide whether to pull the SOP, re-read SAP, or re-validate, then decide again. Extraction is one call; validation is a function. |
| **Approval is a state machine, not an instruction** | A prompt instruction is a suggestion. The token is minted only by `/approve`, is single-use, and is bound to the exact references that passed. |
| **No park action in the Exceptions tab** | A corrected invoice returns to the approvals queue and goes through the same gate. One write path, not two. |
| **Every provider has a fallback** | The development machine has no AWS credentials. The system must demo without them and must never present seeded data as live — hence the source indicator in the header. |
| **`Decimal` everywhere near money** | Rules 10 and 11 reconcile arithmetic exactly. A float artifact invents an exception that does not exist, in front of a jury. |

---

## Workarounds currently in place

| Workaround | Why | Remove when |
|---|---|---|
| Custom MCP server instead of the managed one | The managed runtime fails its health check | The managed deployment is repaired |
| `extractions.json` fallback | Bedrock vision needs AWS credentials, which not every machine has | Kept permanently — it is the offline demo path |
| SOP markdown parsed locally instead of Knowledge Base retrieval | Retrieval returns partial step tables; the managed chunker splits a clause from its table | The S3 documents are re-chunked so a clause and its steps stay together |
| Grounded responder instead of the Strands agent | `strands-agents` need not be installed, and the agent needs credentials | Kept permanently — same reason as the extraction cache |
| Retrieved passages filtered on `_document_title` | Sections 6.1–6.3 exist in both SOPs, so a passage from the wrong one parses as the right clause | The knowledge base exposes the SOP id as retrievable metadata |
| Status join in batches of 20 | `A_SuplrInvcItemPurOrdRef` carries no status and offers no navigation to its header | SAP exposes the status on the item, which it will not |
| `admin` / `admin` | Real auth costs hours and scores nothing here | Never, for this event |

---

## Limitations

Things a judge might reasonably ask about.

- **SOP retrieval is a fallback, not the live path.** The repository copy of
  the clause answers, because the managed chunker returns partial step tables.
  `FORCE_SOP_RETRIEVAL=1` makes retrieval drive the answer; the clause stays
  correct but may carry fewer steps. The API knowledge base has no local
  equivalent and is genuinely live.
- **A newly uploaded, unseen document cannot be processed without Bedrock.**
  The extraction cache only answers for documents already recorded. The batch
  reports it explicitly rather than silently returning nothing.
- **Document scoping depends on the SOP markdown being deployed.** Retrieved
  passages are filtered on the source file name, and the mapping from
  `AP-SOP-001` to that file name is built by reading the local documents. A
  deployment without them cannot scope, and sections 6.1–6.3 are ambiguous
  across the two SOPs.
- **Vision extraction was verified once, on six documents.** All 84 fields
  matched the recorded extractions exactly. That is one run against one set of
  invoices from one supplier, not a measured accuracy rate.
- **One purchase order line per invoice.** `Invoice` models a single line.
  Real Factory Price List invoices carry several.
- **Batch state is in memory.** Restarting the backend loses it.
- **81 seconds for six invoices** with Bedrock vision and Knowledge Base
  retrieval both live, over 33 SAP calls. Still dominated by MCP round-trip
  latency: extraction is about 17s of it, and was 49s before `extract_batch`
  was made concurrent. Without credentials the cached extractions make it 76s.
- **No retry on transient SAP failures** in this client.
- **`admin` / `admin` is not authentication.** No token, no server-side check.
- **Tolerance thresholds are written in USD in the SOP** and applied to
  whatever currency the invoice carries. Fine for a EUR-only demo; wrong the
  moment a second currency appears.
- **Three of the five demo purchase orders are genuinely fully invoiced.** The
  warnings they produce are real, not staged — but it does mean a clean
  five-of-five demo is not available without new purchase orders.
