import { useEffect, useMemo, useRef, useState } from 'react';
import Icon from '../components/Icon';
import { StatusChip, RoutingChip, Chip } from '../components/Chip';
import InvoiceDetail from '../components/InvoiceDetail';
import { api } from '../lib/api';

/**
 * Blocked invoices, worked by the exception team.
 *
 * There is deliberately no park action here. A fixed invoice returns to the
 * approvals queue and goes through the same gate, so the write path stays
 * single.
 */
export default function Exceptions({ batch, selected, onSelect }) {
  const outcomes = useMemo(() => batch.outcomes.filter((o) => !o.canPark), [batch]);
  const current = outcomes.find((o) => o.invoice.reference === selected) || outcomes[0];
  const [tab, setTab] = useState('sop');

  useEffect(() => {
    if (current && current.invoice.reference !== selected) onSelect(current.invoice.reference);
  }, [current, selected, onSelect]);

  if (outcomes.length === 0) {
    return (
      <div className="panel empty">
        <Icon name="check" size={28} />
        <p>No exceptions in this batch.</p>
      </div>
    );
  }

  const failing = current.findings.find((f) => f.status === 'FAIL');

  return (
    <div className="view view-exceptions">
      <div className="queue panel">
        <div className="panel-head">
          <Icon name="flag" size={16} />
          <span className="t-title">Exceptions</span>
          <Chip tone="error" icon="error">
            {outcomes.length}
          </Chip>
          <span className="spacer" />
          <span className="t-body-sm t-muted">Skipped, not posted</span>
        </div>
        <div className="table-scroll">
          <table className="data">
            <thead>
              <tr>
                <th aria-label="Severity" />
                <th>Invoice</th>
                <th>Exception</th>
                <th>SOP</th>
                <th>Escalate to</th>
              </tr>
            </thead>
            <tbody>
              {outcomes.map((o) => {
                const f = o.findings.find((x) => x.status === 'FAIL');
                const isSelected = o.invoice.reference === current.invoice.reference;
                return (
                  <tr
                    key={o.invoice.reference}
                    aria-selected={isSelected}
                    tabIndex={0}
                    onClick={() => onSelect(o.invoice.reference)}
                    onKeyDown={(e) => {
                      if (e.key === 'Enter' || e.key === ' ') {
                        e.preventDefault();
                        onSelect(o.invoice.reference);
                      }
                    }}
                  >
                    <td className="stripe">
                      <span data-sev="error" />
                    </td>
                    <td className="cell-file">
                      <Icon name="doc" size={14} className="t-faint" />
                      {o.invoice.sourceFile}
                    </td>
                    <td>
                      <span className="mono t-faint">{f.ruleId}</span> {f.ruleName}
                    </td>
                    <td className="mono t-muted">{f.sopRef || '—'}</td>
                    <td>
                      <RoutingChip routing={o.requiredApproval} />
                    </td>
                  </tr>
                );
              })}
            </tbody>
          </table>
        </div>
      </div>

      <div className="exception-work">
        <div className="panel exception-headline">
          <div className="panel-head">
            <StatusChip status="FAIL" />
            <span className="t-title">{current.invoice.sourceFile}</span>
            <span className="spacer" />
            <a className="btn btn-text" href={current.invoice.pdfUrl} target="_blank" rel="noreferrer">
              <Icon name="doc" size={14} /> Open PDF
            </a>
          </div>
          <p className="exception-msg t-body">{current.headline}</p>
        </div>

        <div className="tabs-inline" role="tablist" aria-label="Exception workspace">
          <button role="tab" aria-selected={tab === 'sop'} className={`tab-inline ${tab === 'sop' ? 'is-selected' : ''}`} onClick={() => setTab('sop')}>
            <Icon name="flag" size={14} /> Resolution steps
          </button>
          <button role="tab" aria-selected={tab === 'chat'} className={`tab-inline ${tab === 'chat' ? 'is-selected' : ''}`} onClick={() => setTab('chat')}>
            <Icon name="chat" size={14} /> Ask the assistant
          </button>
          <button role="tab" aria-selected={tab === 'detail'} className={`tab-inline ${tab === 'detail' ? 'is-selected' : ''}`} onClick={() => setTab('detail')}>
            <Icon name="doc" size={14} /> Invoice and rules
          </button>
        </div>

        {tab === 'sop' ? <Guidance sopRef={failing?.sopRef} /> : null}
        {tab === 'chat' ? <Chat outcome={current} /> : null}
        {tab === 'detail' ? <InvoiceDetail outcome={current} /> : null}
      </div>
    </div>
  );
}

/** Retrieved from the SOP knowledge base, keyed by the clause the rule named. */
function Guidance({ sopRef }) {
  const [data, setData] = useState(undefined);

  useEffect(() => {
    let live = true;
    setData(undefined);
    api.guidance(sopRef).then((d) => live && setData(d));
    return () => {
      live = false;
    };
  }, [sopRef]);

  if (data === undefined) {
    return (
      <div className="panel empty">
        <span className="spinner" />
        <p className="t-body-sm">Retrieving {sopRef} from the SOP knowledge base…</p>
      </div>
    );
  }
  if (!data) {
    return (
      <div className="panel empty">
        <Icon name="info" size={24} />
        <p className="t-body-sm">No SOP entry is published for this exception type.</p>
      </div>
    );
  }

  return (
    <div className="panel guidance">
      <div className="panel-head">
        <span className="t-title">{data.title}</span>
        <span className="spacer" />
        <Chip tone="info" icon="flag">
          {sopRef}
        </Chip>
      </div>

      <div className="guidance-body">
        <section>
          <h3 className="t-label">Common causes</h3>
          <ul className="bullets">
            {data.causes.map((c) => (
              <li key={c}>{c}</li>
            ))}
          </ul>
        </section>

        <section>
          <h3 className="t-label">Resolution steps</h3>
          <ol className="steps">
            {data.steps.map((s, i) => (
              <li key={s.action}>
                <span className="step-n mono">{i + 1}</span>
                <div>
                  <p className="t-body-sm">{s.action}</p>
                  <p className="t-body-sm t-faint">
                    {s.who} · {s.when}
                  </p>
                </div>
              </li>
            ))}
          </ol>
        </section>

        <section className="policy">
          <Icon name="shield" size={14} />
          <p className="t-body-sm">{data.policy}</p>
        </section>
      </div>
    </div>
  );
}

const SUGGESTIONS = [
  'Why did this fail?',
  'What are the common causes?',
  'What should I do next?',
  'Who has to approve this?',
  'Re-check the purchase order in SAP',
];

/** Chat scoped to one invoice: its findings and SAP context are preloaded. */
function Chat({ outcome }) {
  const [messages, setMessages] = useState([]);
  const [draft, setDraft] = useState('');
  const [busy, setBusy] = useState(false);
  const endRef = useRef(null);

  useEffect(() => {
    setMessages([
      {
        role: 'assistant',
        text: `I have the validation result and the SAP data for ${outcome.invoice.sourceFile} loaded.\n\n${outcome.headline}`,
        citations: [],
      },
    ]);
  }, [outcome.invoice.reference, outcome.headline, outcome.invoice.sourceFile]);

  useEffect(() => {
    endRef.current?.scrollIntoView({ behavior: 'smooth', block: 'end' });
  }, [messages, busy]);

  async function ask(question) {
    if (!question.trim() || busy) return;
    setMessages((m) => [...m, { role: 'user', text: question }]);
    setDraft('');
    setBusy(true);
    const reply = await api.chat(outcome.invoice.reference, question, outcome);
    setBusy(false);
    setMessages((m) => [...m, { role: 'assistant', ...reply }]);
  }

  return (
    <div className="panel chat">
      <div className="chat-log" role="log" aria-live="polite">
        {messages.map((m, i) => (
          <div key={i} className={`bubble bubble-${m.role}`}>
            <p className="t-body">{m.text}</p>
            {m.citations?.length ? (
              <div className="bubble-cites">
                {m.citations.map((c) => (
                  <Chip key={c} tone="info" icon="flag">
                    {c}
                  </Chip>
                ))}
              </div>
            ) : null}
          </div>
        ))}
        {busy ? (
          <div className="bubble bubble-assistant bubble-busy">
            <span className="spinner" />
            <span className="t-body-sm t-muted">Consulting the SOP knowledge base…</span>
          </div>
        ) : null}
        <div ref={endRef} />
      </div>

      <div className="chat-suggestions">
        {SUGGESTIONS.map((s) => (
          <button key={s} className="btn btn-outlined chip-btn" onClick={() => ask(s)} disabled={busy}>
            {s}
          </button>
        ))}
      </div>

      <form
        className="chat-input"
        onSubmit={(e) => {
          e.preventDefault();
          ask(draft);
        }}
      >
        <label className="sr-only" htmlFor="chat-draft">
          Ask about this exception
        </label>
        <input
          id="chat-draft"
          className="input"
          placeholder="Ask about this exception…"
          value={draft}
          onChange={(e) => setDraft(e.target.value)}
          disabled={busy}
        />
        <button className="btn btn-filled" type="submit" disabled={busy || !draft.trim()} aria-label="Send">
          <Icon name="send" size={16} />
        </button>
      </form>
    </div>
  );
}
