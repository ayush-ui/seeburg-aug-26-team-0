import { useState } from 'react';
import Icon from './Icon';
import { StatusChip, RoutingChip, ParkedChip } from './Chip';

/**
 * The document beside the data. An AP clerk approving a posting needs to see
 * the original page and the extracted fields at once - that comparison is the
 * whole reason a human is in this loop.
 */

const money = (v, currency) =>
  `${currency} ${Number(v).toLocaleString('de-DE', { minimumFractionDigits: 2, maximumFractionDigits: 2 })}`;

function Confidence({ value }) {
  if (value === undefined) return null;
  const low = value < 0.85;
  return (
    <span className={`conf ${low ? 'conf-low' : ''}`} title={`Extraction confidence ${Math.round(value * 100)}%`}>
      {Math.round(value * 100)}%
    </span>
  );
}

function FieldRow({ label, value, sapField, confidence }) {
  return (
    <tr>
      <th scope="row">
        {label}
        {sapField ? <span className="mono t-faint field-map">{sapField}</span> : null}
      </th>
      <td>
        {value}
        <Confidence value={confidence} />
      </td>
    </tr>
  );
}

export default function InvoiceDetail({ outcome, onApprove, busy, canAct, actionLabel = 'Approve and park' }) {
  const [showAll, setShowAll] = useState(false);
  const { invoice, findings } = outcome;

  const active = findings.filter((f) => f.status === 'FAIL' || f.status === 'WARN');
  const shown = showAll ? findings : active;
  const counts = outcome.counts || {};

  return (
    <div className="detail">
      <div className="detail-doc panel">
        <div className="panel-head">
          <Icon name="doc" size={16} />
          <span className="t-title">{invoice.sourceFile}</span>
          <span className="spacer" />
          <a className="btn btn-icon" href={invoice.pdfUrl} target="_blank" rel="noreferrer" aria-label="Open the PDF in a new tab">
            <Icon name="download" size={16} />
          </a>
        </div>
        {/* Height is reserved before the PDF loads so nothing shifts. */}
        <div className="pdf-frame">
          <object data={`${invoice.pdfUrl}#toolbar=0&view=FitH`} type="application/pdf" aria-label={`Scanned invoice ${invoice.sourceFile}`}>
            <div className="empty">
              <Icon name="doc" size={28} />
              <p className="t-body-sm">
                Preview unavailable in this browser.{' '}
                <a href={invoice.pdfUrl} target="_blank" rel="noreferrer">
                  Open the PDF
                </a>
              </p>
            </div>
          </object>
        </div>
      </div>

      <div className="detail-side">
        <div className="panel">
          <div className="panel-head">
            <span className="t-title">Extracted and mapped</span>
            <span className="spacer" />
            <RoutingChip routing={outcome.requiredApproval} />
          </div>
          <table className="fields">
            <tbody>
              <FieldRow label="Supplier" sapField="InvoicingParty" value={`${invoice.supplier} · ${invoice.supplierName}`} confidence={invoice.confidence?.supplier} />
              <FieldRow label="Purchase order" sapField="PurchaseOrder" value={`${invoice.purchaseOrder} / ${invoice.purchaseOrderItem}`} confidence={invoice.confidence?.purchaseOrder} />
              <FieldRow label="Material" sapField="Material" value={invoice.material} confidence={invoice.confidence?.material} />
              <FieldRow label="Quantity" sapField="QuantityInPurchaseOrderUnit" value={`${invoice.quantity} ${invoice.unit}`} confidence={invoice.confidence?.quantity} />
              <FieldRow label="Unit price" value={money(invoice.unitPrice, invoice.currency)} confidence={invoice.confidence?.unitPrice} />
              <FieldRow label="Net" sapField="SupplierInvoiceItemAmount" value={money(invoice.netAmount, invoice.currency)} />
              <FieldRow label="Tax" sapField="TaxCode" value={`${invoice.taxCode} · ${money(invoice.taxAmount, invoice.currency)}`} confidence={invoice.confidence?.taxCode} />
              <FieldRow label="Gross" sapField="InvoiceGrossAmount" value={<strong>{money(invoice.grossAmount, invoice.currency)}</strong>} confidence={invoice.confidence?.grossAmount} />
              <FieldRow label="Document date" sapField="DocumentDate" value={invoice.invoiceDate} />
              <FieldRow label="Reference" sapField="SupplierInvoiceIDByInvcgParty" value={<span className="mono">{invoice.reference}</span>} />
            </tbody>
          </table>
        </div>

        <div className="panel">
          <div className="panel-head">
            <span className="t-title">Validation</span>
            <span className="t-body-sm t-muted">
              {counts.PASS || 0} pass · {counts.WARN || 0} warn · {counts.FAIL || 0} fail
              {counts.NOT_APPLICABLE ? ` · ${counts.NOT_APPLICABLE} not checked` : ''}
            </span>
            <span className="spacer" />
            <button className="btn btn-text" onClick={() => setShowAll((v) => !v)} aria-expanded={showAll}>
              {showAll ? 'Show findings only' : `Show all 17 rules`}
            </button>
          </div>

          <div className="findings">
            {shown.length === 0 ? (
              <div className="empty">
                <Icon name="check" size={24} />
                <p className="t-body-sm">Every rule passed against live SAP data.</p>
              </div>
            ) : (
              shown.map((f) => (
                <div key={f.ruleId} className={`finding sev-${f.status.toLowerCase()}`}>
                  <div className="finding-head">
                    <span className="mono t-faint">{f.ruleId}</span>
                    <span className="t-body-sm finding-name">{f.ruleName}</span>
                    <span className="spacer" />
                    <StatusChip status={f.status} />
                  </div>
                  <p className="t-body-sm finding-msg">{f.message}</p>
                  {/* The triple that is the product: what the invoice says, what
                      SAP says, and the gap between them. */}
                  {f.invoiceValue || f.sapValue ? (
                    <div className="compare">
                      <div>
                        <span className="t-label">Invoice</span>
                        <span className="mono">{f.invoiceValue || '—'}</span>
                      </div>
                      <Icon name="chevron" size={14} className="compare-arrow" />
                      <div>
                        <span className="t-label">SAP</span>
                        <span className="mono">{f.sapValue || '—'}</span>
                      </div>
                      {f.delta ? (
                        <div className="compare-delta">
                          <span className="t-label">Delta</span>
                          <span className="mono">{f.delta}</span>
                        </div>
                      ) : null}
                    </div>
                  ) : null}
                  {f.sopRef ? (
                    <p className="t-body-sm t-faint finding-sop">
                      <Icon name="flag" size={12} /> {f.sopRef}
                    </p>
                  ) : null}
                </div>
              ))
            )}
          </div>
        </div>

        {onApprove ? (
          <div className="detail-action">
            {outcome.parked ? (
              <ParkedChip doc={outcome.parked} />
            ) : (
              <button
                className="btn btn-filled btn-lg"
                onClick={onApprove}
                disabled={busy || !canAct}
                title={canAct ? undefined : 'Your role cannot approve postings'}
              >
                {busy ? <span className="spinner" /> : <Icon name="check" size={16} />}
                {busy ? 'Parking in SAP' : actionLabel}
              </button>
            )}
          </div>
        ) : null}
      </div>
    </div>
  );
}
