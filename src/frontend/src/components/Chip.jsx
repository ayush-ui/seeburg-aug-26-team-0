import Icon from './Icon';

/**
 * Status chip. Colour is never the only signal - every chip carries an icon
 * and a word, so it survives greyscale printing and colour vision deficiency.
 */

const STYLE = {
  PASS: { cls: 'chip-success', icon: 'check', label: 'Pass' },
  WARN: { cls: 'chip-warn', icon: 'warning', label: 'Warn' },
  FAIL: { cls: 'chip-error', icon: 'error', label: 'Fail' },
  NOT_APPLICABLE: { cls: 'chip-neutral', icon: 'skip', label: 'Not checked' },
};

const ROUTING = {
  AUTO_APPROVE: { cls: 'chip-success', icon: 'check', label: 'Auto' },
  CLERK: { cls: 'chip-info', icon: 'person', label: 'AP Clerk' },
  MANAGER: { cls: 'chip-warn', icon: 'shield', label: 'AP Manager' },
  CONTROLLER: { cls: 'chip-error', icon: 'shield', label: 'Controller' },
};

export function StatusChip({ status }) {
  const s = STYLE[status] || STYLE.NOT_APPLICABLE;
  return (
    <span className={`chip ${s.cls}`}>
      <Icon name={s.icon} size={12} />
      {s.label}
    </span>
  );
}

export function RoutingChip({ routing }) {
  const r = ROUTING[routing] || ROUTING.AUTO_APPROVE;
  return (
    <span className={`chip ${r.cls}`}>
      <Icon name={r.icon} size={12} />
      {r.label}
    </span>
  );
}

export function ParkedChip({ doc }) {
  return (
    <span className="chip chip-success" title={`Parked as ${doc.supplierInvoice} FY ${doc.fiscalYear}`}>
      <Icon name="check" size={12} />
      Parked {doc.supplierInvoice}
    </span>
  );
}

export function Chip({ tone = 'neutral', icon, children }) {
  return (
    <span className={`chip chip-${tone}`}>
      {icon ? <Icon name={icon} size={12} /> : null}
      {children}
    </span>
  );
}
