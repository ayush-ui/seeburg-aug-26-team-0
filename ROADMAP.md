# Roadmap

What is done, what is next, and what is deliberately out of scope. Items move
between sections rather than being deleted, so the reasoning survives.

---

## Done

| | |
|---|---|
| MCP server on Bedrock AgentCore | Deployed, verified live |
| `rules.py` — 17 validation rules | 22 tests, no network |
| `sap.py` — reads and the single write | 23 tests; park and delete proven against SAP |
| `extract.py` — document to typed invoice | Bedrock vision, with a recorded fallback |
| `knowledge.py` — SOP retrieval | Bedrock KB, falling back to the SOP markdown |
| `agent.py` — exception assistant | Strands when reachable, grounded responder otherwise |
| `api.py` — approval state machine | Token-gated write, batch reported per invoice |
| `reports.py` — SOP section 9.3 reports | Built from the batch that just ran |
| Front end — Intake, Approvals, Exceptions, Reports | Live against the backend |
| CI — both suites plus a gitleaks scan | GitHub Actions |
| `ARCHITECTURE.md` and `docs/architecture.html` | Kept in step |

---

## Next — submission requirements

These are explicit scoring criteria in
`checklists/members.md` and `templates/SUBMISSION_CHECKLIST.md`, and they are
currently the cheapest points available.

- [ ] **`README.md`** — project description, tech stack, setup, usage, team
      members with GitHub links, demo video link. The checklist notes that a
      well-documented project scores significantly higher than a feature-rich
      undocumented one.
- [ ] **`/result/` folder** — outputs for the example prompts, clearly
      labelled and viewable. Listed under Completeness; currently absent.
- [ ] **Add `hackmaster-dmi` as a read-only collaborator** — required of every
      hackathon repository for post-event analysis.
- [ ] **Demo video** — hosted externally and linked, never committed.

---

## Next — product

- [ ] **Verify the Bedrock paths.** Extraction, Knowledge Base retrieval and
      the Strands agent are code-complete but have never run: the development
      machine has no AWS credentials. They need one pass from an environment
      that has them, ideally the workshop VS Code Server. Until then their
      fallbacks are what actually runs.
- [ ] **Multi-line invoices.** `Invoice` currently models one purchase order
      line. Real Factory Price List invoices carry several. This touches
      `rules.py`, the park payload and the detail view.
- [ ] **Persist batches.** State is in memory and is lost when the backend
      restarts. SQLite would be enough.
- [ ] **Scheduled daily run.** The unattended path already exists — `POST
      /api/batches` with no file list processes the whole inbox. It needs a
      trigger and somewhere to put the result.
- [ ] **Correction suggestions.** Named as a stretch goal in the brief. The
      SOP already supplies the procedure; proposing the specific corrected
      field value is the missing piece.

---

## Next — engineering

- [ ] **Cut batch latency further.** 76 seconds for six invoices, dominated by
      several seconds per MCP round trip. Concurrency took it from 202; the
      next lever is either fewer reads per invoice or an OData `$batch`
      request.
- [ ] **Retry transient SAP failures** in `sap.py`. The workshop's MCP server
      retries internally; this client does not.
- [ ] **Observability panel.** Pass and fail counts and time saved are named
      as a tie-breaker in the brief. The data exists — `sapCalls`,
      `durationMs`, the per-rule counts — but nothing aggregates it across
      runs.
- [ ] **Pre-commit hooks** — `ruff` and a formatter. Listed under Code Quality.

---

## Deliberately not doing

| | Why |
|---|---|
| **Real authentication** | `admin` / `admin` is a demo stub. Real auth costs hours and scores nothing in this brief. It is documented as a stub wherever it appears. |
| **Inbound Delivery (VL31N)** | Creation over OData is environment-dependent. The workshop documents it as a production next step rather than a lab action, and we follow that. |
| **Posting invoices for payment** | Writes are always parked (status `A`). A parked document creates no accounting entry and does not consume the purchase order, which is what makes this safe on a system shared with other teams. |
| **Making the validator an agent** | It would be slower, non-reproducible and impossible to unit test. Verdicts stay deterministic. |
| **Building our own MCP server from scratch** | The workshop's server already exposes a generic OData tool and is deployed. The managed AWS-for-SAP server is the documented alternative, and is unhealthy in this account — see `LESSONS-LEARNED.md`. |
