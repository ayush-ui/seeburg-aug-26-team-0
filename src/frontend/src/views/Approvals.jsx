import { useEffect, useMemo, useState } from 'react';
import Icon from '../components/Icon';
import { RoutingChip, ParkedChip, Chip } from '../components/Chip';
import InvoiceDetail from '../components/InvoiceDetail';
import { api } from '../lib/api';

const money = (v, currency) =>
  `${currency} ${Number(v).toLocaleString('de-DE', { minimumFractionDigits: 2, maximumFractionDigits: 2 })}`;

/**
 * Invoices that passed every rule, or that carry only a variance inside a
 * tolerance band. All of these can be parked; a warning raises who has to
 * approve, it does not block the write.
 */
export default function Approvals({ batch, selected, onSelect, onParked, role }) {
  const outcomes = useMemo(() => batch.outcomes.filter((o) => o.canPark), [batch]);
  const [busy, setBusy] = useState(null);
  const [confirming, setConfirming] = useState(false);

  const pending = outcomes.filter((o) => !o.parked);
  const current = outcomes.find((o) => o.invoice.reference === selected) || outcomes[0];
  const canAct = role === 'clerk' || role === 'manager';

  useEffect(() => {
    if (current && current.invoice.reference !== selected) onSelect(current.invoice.reference);
  }, [current, selected, onSelect]);

  async function park(references) {
    setBusy(references.length > 1 ? 'batch' : references[0]);
    const { token } = await api.approve(references);
    const { results } = await api.park(token, references);
    setBusy(null);
    setConfirming(false);
    onParked(results);
  }

  return (
    <div className="view">
      <div className="queue panel">
        <div className="panel-head">
          <Icon name="inbox" size={16} />
          <span className="t-title">Ready to approve</span>
          <Chip tone="neutral">{outcomes.length}</Chip>
          <span className="spacer" />
          {pending.length > 0 ? (
            <button
              className="btn btn-filled"
              onClick={() => setConfirming(true)}
              disabled={busy !== null || !canAct}
              title={canAct ? undefined : 'Your role cannot approve postings'}
            >
              {busy === 'batch' ? <span className="spinner" /> : <Icon name="check" size={16} />}
              Park {pending.length} in SAP
            </button>
          ) : (
            <Chip tone="success" icon="check">
              All parked
            </Chip>
          )}
        </div>

        <div className="table-scroll">
          <table className="data">
            <thead>
              <tr>
                <th aria-label="Severity" />
                <th>Invoice</th>
                <th>Supplier</th>
                <th>PO</th>
                <th className="num">Gross</th>
                <th>Approval</th>
                <th>Status</th>
              </tr>
            </thead>
            <tbody>
              {outcomes.map((o) => {
                const warn = o.findings.some((f) => f.status === 'WARN');
                const isSelected = current && o.invoice.reference === current.invoice.reference;
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
                      <span data-sev={warn ? 'warn' : 'pass'} />
                    </td>
                    <td className="cell-file">
                      <Icon name="doc" size={14} className="t-faint" />
                      {o.invoice.sourceFile}
                    </td>
                    <td>
                      <span className="mono">{o.invoice.supplier}</span>
                      <span className="t-faint cell-sub">{o.invoice.supplierName}</span>
                    </td>
                    <td className="mono">{o.invoice.purchaseOrder}</td>
                    <td className="num">{money(o.invoice.grossAmount, o.invoice.currency)}</td>
                    <td>
                      <RoutingChip routing={o.requiredApproval} />
                    </td>
                    <td>
                      {o.parked ? (
                        <ParkedChip doc={o.parked} />
                      ) : busy === o.invoice.reference || busy === 'batch' ? (
                        <span className="chip chip-info">
                          <span className="spinner" style={{ width: 10, height: 10 }} />
                          Parking
                        </span>
                      ) : warn ? (
                        <Chip tone="warn" icon="warning">
                          Needs review
                        </Chip>
                      ) : (
                        <Chip tone="success" icon="check">
                          Clean
                        </Chip>
                      )}
                    </td>
                  </tr>
                );
              })}
            </tbody>
          </table>
        </div>
      </div>

      {current ? (
        <InvoiceDetail
          outcome={current}
          busy={busy === current.invoice.reference || busy === 'batch'}
          canAct={canAct}
          onApprove={() => park([current.invoice.reference])}
          actionLabel={`Park ${current.invoice.sourceFile} in SAP`}
        />
      ) : (
        <div className="panel empty">
          <Icon name="check" size={28} />
          <p>Nothing waiting for approval.</p>
        </div>
      )}

      {confirming ? (
        <div className="scrim" role="dialog" aria-modal="true" aria-labelledby="confirm-title">
          <div className="dialog panel">
            <div className="dialog-body">
              <h2 className="t-title-lg" id="confirm-title">
                Park {pending.length} invoices in SAP?
              </h2>
              <p className="t-body-sm t-muted">
                Each invoice is created as a parked supplier invoice with status A. Parked documents
                make no accounting entry, do not consume the purchase order, and can be deleted.
              </p>
              <ul className="confirm-list">
                {pending.map((o) => (
                  <li key={o.invoice.reference}>
                    <span>{o.invoice.sourceFile}</span>
                    <span className="mono t-faint">{o.invoice.purchaseOrder}</span>
                    <span className="num">{money(o.invoice.grossAmount, o.invoice.currency)}</span>
                  </li>
                ))}
              </ul>
            </div>
            <div className="dialog-actions">
              <button className="btn btn-outlined" onClick={() => setConfirming(false)}>
                Cancel
              </button>
              <button
                className="btn btn-filled"
                onClick={() => park(pending.map((o) => o.invoice.reference))}
              >
                <Icon name="check" size={16} />
                Park {pending.length} invoices
              </button>
            </div>
          </div>
        </div>
      ) : null}
    </div>
  );
}
