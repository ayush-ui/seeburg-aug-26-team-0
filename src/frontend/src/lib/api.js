/**
 * Mock API.
 *
 * Every shape here mirrors what the FastAPI backend will serve from rules.py,
 * sap.py and knowledge.py, so swapping in the real service is a change to this
 * file alone - no component touches invented data.
 *
 * The scenario is the real state of the workshop SAP system: purchase orders
 * 4500001638, 4500001650 and 4500001697 are genuinely consumed by posted
 * invoices, 4500001463 and 4500001563 are open, and 4500009999 does not exist.
 */

const RULES = [
  ['R01', 'Purchase Order exists'],
  ['R02', 'Purchase Order is open'],
  ['R03', 'PO line item exists'],
  ['R04', 'Supplier matches PO vendor'],
  ['R05', 'Company code matches'],
  ['R06', 'Currency matches'],
  ['R07', 'Material matches'],
  ['R08', 'Quantity within PO tolerance'],
  ['R09', 'Unit price within tolerance'],
  ['R10', 'Line amount reconciles'],
  ['R11', 'Gross reconciles to lines plus tax'],
  ['R12', 'Goods Receipt exists'],
  ['R13', 'Goods Receipt quantity sufficient'],
  ['R14', 'Tax code valid'],
  ['R15', 'Posting date in an open period'],
  ['R16', 'Not a duplicate'],
  ['R17', 'Mandatory fields complete'],
];

/** Rules that depend on a purchase order having been read. */
const PO_DEPENDENT = ['R02', 'R03', 'R04', 'R05', 'R06', 'R07', 'R08', 'R09', 'R12', 'R13'];

const PASS_MESSAGE = {
  R01: 'Purchase Order found in SAP.',
  R02: 'Purchase Order is open and available to invoice.',
  R03: 'Item 10 found on the Purchase Order.',
  R04: 'Supplier matches the Purchase Order vendor.',
  R05: 'Company code 1010 matches the Purchase Order.',
  R06: 'Currency EUR matches the Purchase Order.',
  R07: 'Material matches the Purchase Order item.',
  R08: 'Invoiced quantity is within what remains open on the Purchase Order.',
  R09: 'Unit price matches the agreed Purchase Order price.',
  R10: 'Net equals quantity multiplied by unit price.',
  R11: 'Gross equals net plus tax.',
  R12: 'Goods receipt posted against the Purchase Order.',
  R13: 'Invoiced quantity is covered by the quantity received.',
  R14: 'Tax code is permitted for company code 1010.',
  R15: 'Document date falls in the open posting period.',
  R16: 'Reference is unused for this supplier.',
  R17: 'All fields SAP requires to park the invoice are present.',
};

/** Build all 17 findings, applying per-rule overrides for this invoice. */
function buildFindings(overrides = {}) {
  const missingPo = overrides.R01 && overrides.R01.status === 'FAIL';
  return RULES.map(([ruleId, ruleName]) => {
    const override = overrides[ruleId];
    if (override) return { ruleId, ruleName, sopRef: '', ...override };
    if (missingPo && PO_DEPENDENT.includes(ruleId)) {
      return {
        ruleId,
        ruleName,
        status: 'NOT_APPLICABLE',
        message: 'Not checked - purchase order was not found.',
        sopRef: '',
        routing: 'AUTO_APPROVE',
      };
    }
    return {
      ruleId,
      ruleName,
      status: 'PASS',
      message: PASS_MESSAGE[ruleId],
      sopRef: '',
      routing: 'AUTO_APPROVE',
    };
  });
}

function outcome(invoice, overrides, headline) {
  const findings = buildFindings(overrides);
  const order = { AUTO_APPROVE: 0, CLERK: 1, MANAGER: 2, CONTROLLER: 3 };
  const active = findings.filter((f) => f.status === 'FAIL' || f.status === 'WARN');
  const requiredApproval = active.reduce(
    (top, f) => (order[f.routing] > order[top] ? f.routing : top),
    'AUTO_APPROVE',
  );
  const counts = findings.reduce((acc, f) => ({ ...acc, [f.status]: (acc[f.status] || 0) + 1 }), {});
  return {
    invoice,
    findings,
    canPark: !findings.some((f) => f.status === 'FAIL'),
    requiredApproval,
    headline: headline || 'All checks passed against live SAP data.',
    counts,
  };
}

/** Extraction confidence per field, as the vision model reports it. */
const CONF = { high: 0.99, mid: 0.94, low: 0.71 };

function invoice(n, over = {}) {
  return {
    sourceFile: `fpl-invoice-${String(n).padStart(2, '0')}.pdf`,
    pdfUrl: `${import.meta.env.BASE_URL}invoices/fpl-invoice-${String(Math.min(n, 6)).padStart(2, '0')}.pdf`,
    reference: `922513818191-${n}`,
    supplier: '17401710',
    supplierName: 'Inlandslieferant DE 1',
    purchaseOrder: '4500001563',
    purchaseOrderItem: '10',
    invoiceDate: '2025-03-15',
    receivedAt: '2026-08-07T06:12:00Z',
    companyCode: '1010',
    currency: 'EUR',
    material: 'TG12',
    quantity: 10,
    unit: 'PC',
    unitPrice: 11.35,
    netAmount: 113.5,
    taxCode: 'V0',
    taxAmount: 0,
    grossAmount: 113.5,
    confidence: {
      supplier: CONF.high,
      purchaseOrder: CONF.high,
      material: CONF.high,
      quantity: CONF.high,
      unitPrice: CONF.mid,
      grossAmount: CONF.high,
      taxCode: CONF.mid,
    },
    ...over,
  };
}

const OUTCOMES = [
  outcome(
    invoice(1, {
      supplier: '10300006',
      supplierName: 'Schneider AG',
      purchaseOrder: '4500001463',
      material: 'QM003',
      quantity: 5,
      unitPrice: 10,
      netAmount: 50,
      taxCode: 'V1',
      taxAmount: 9.5,
      grossAmount: 59.5,
    }),
    {},
  ),

  outcome(invoice(2), {}),

  outcome(
    invoice(3, { unitPrice: 11.71, netAmount: 117.1, grossAmount: 117.1 }),
    {
      R09: {
        status: 'WARN',
        message:
          'Unit price EUR 11.71 is 3.17% above the agreed Purchase Order price of EUR 11.35 - a difference of EUR 3.60 on this line.',
        sopRef: 'AP-SOP-001 6.1 / 8.1',
        invoiceValue: 'EUR 11.71',
        sapValue: 'EUR 11.35',
        delta: '+3.17% (EUR 3.60)',
        routing: 'MANAGER',
      },
    },
    'Unit price EUR 11.71 is 3.17% above the agreed Purchase Order price of EUR 11.35.',
  ),

  outcome(
    invoice(4, { quantity: 30, netAmount: 340.5, grossAmount: 340.5 }),
    {
      R13: {
        status: 'WARN',
        message:
          'Invoice bills 30 PC but only 10 PC were actually received - over-delivered billing of 20 PC (EUR 227.00). Pay only for the quantity received and request a credit note.',
        sopRef: 'AP-SOP-001 6.2 / 8.1',
        invoiceValue: '30 PC',
        sapValue: '10 PC received',
        delta: '+20 PC (EUR 227.00)',
        routing: 'MANAGER',
      },
    },
    'Invoice bills 30 PC but only 10 PC were actually received.',
  ),

  outcome(
    invoice(5, { taxCode: 'V1', taxAmount: 21.57, grossAmount: 135.07 }),
    {
      R11: {
        status: 'WARN',
        message:
          'Gross EUR 135.07 does not equal net EUR 113.50 plus tax EUR 21.57 = EUR 135.07 at the stated rate; the invoice applies 19% where the Purchase Order carries tax code V0.',
        sopRef: 'AP-SOP-001 6.8 / 8.1',
        invoiceValue: 'V1 (19%)',
        sapValue: 'V0 (0%)',
        delta: 'EUR 21.57',
        routing: 'MANAGER',
      },
    },
    'Invoice applies 19% tax where the Purchase Order carries tax code V0.',
  ),

  outcome(
    invoice(6, { purchaseOrder: '4500009999', confidence: { purchaseOrder: CONF.low } }),
    {
      R01: {
        status: 'FAIL',
        message:
          'Purchase Order 4500009999 does not exist in SAP. The invoice cannot be matched and must be held pending a retrospective PO from Procurement.',
        sopRef: 'AP-SOP-001 6.3',
        invoiceValue: '4500009999',
        sapValue: 'not found',
        routing: 'CLERK',
      },
    },
    'Purchase Order 4500009999 does not exist in SAP.',
  ),

  outcome(
    invoice(7, { purchaseOrder: '4500001638' }),
    {
      R02: {
        status: 'FAIL',
        message:
          'Purchase Order 4500001638 is fully invoiced and cannot be invoiced as-is. A posted supplier invoice already consumes all 10 PC.',
        sopRef: 'AP-SOP-001 6.3',
        invoiceValue: '10 PC billed',
        sapValue: '0 PC open',
        routing: 'CLERK',
      },
    },
    'Purchase Order 4500001638 is already fully invoiced.',
  ),

  outcome(
    invoice(8, { supplier: '99999999', supplierName: 'Unknown vendor' }),
    {
      R04: {
        status: 'FAIL',
        message:
          'Invoice is from supplier 99999999 but Purchase Order 4500001563 belongs to supplier 17401710. Do not pay - verify the supplier by callback to a contact already on file, not to any contact printed on this invoice.',
        sopRef: 'AP-SOP-001 6.6',
        invoiceValue: '99999999',
        sapValue: '17401710',
        routing: 'CONTROLLER',
      },
    },
    'Invoice supplier does not match the Purchase Order vendor.',
  ),

  outcome(
    invoice(9, { reference: '922513818191-2' }),
    {
      R16: {
        status: 'FAIL',
        message:
          'Reference 922513818191-2 has already been used for supplier 17401710. Rejecting as a duplicate - confirm the payment status of the original before contacting the supplier.',
        sopRef: 'AP-SOP-001 6.5',
        invoiceValue: '922513818191-2',
        sapValue: 'already used',
        routing: 'CLERK',
      },
    },
    'Reference 922513818191-2 has already been used for this supplier.',
  ),
];

/* --- SOP knowledge base ---------------------------------------------------
 * Retrieved by the clause the validator already emitted, so this is a lookup
 * rather than a search for the answer. Content is AP-SOP-001 verbatim. */

const SOP = {
  'AP-SOP-001 6.3': {
    title: 'Missing Purchase Order',
    causes: [
      'Goods or services ordered verbally or by email without a formal PO',
      'PO raised in another system, or not yet entered in the ERP',
      'PO expired before the invoice was submitted',
      'Invoice submitted against a closed or fully consumed PO',
    ],
    steps: [
      { action: 'Register the invoice with status "On Hold - No PO"', who: 'AP Clerk', when: 'Day 1' },
      { action: 'Contact the requester or budget owner to confirm the purchase was authorised', who: 'AP Clerk', when: 'Day 1' },
      { action: 'If authorised, ask Procurement to raise a retrospective PO referencing the invoice', who: 'AP Clerk / Procurement', when: 'Day 1-3' },
      { action: 'If not authorised, notify the AP Manager and hold pending investigation', who: 'AP Clerk', when: 'Day 1' },
      { action: 'Link the invoice and goods receipt to the new PO once raised', who: 'Procurement / AP Clerk', when: 'Day 3-5' },
      { action: 'If no retrospective PO within 5 days, escalate to the Finance Controller', who: 'AP Manager', when: 'Day 5' },
    ],
    policy:
      'Payment must not be made against an invoice without a valid PO unless explicitly approved in writing by the Finance Controller.',
  },
  'AP-SOP-001 6.6': {
    title: 'Vendor / Supplier Mismatch',
    causes: [
      'Vendor changed legal name or bank account details',
      'Invoice issued by a subsidiary or parent not in the vendor master',
      'Fraudulent invoice submitted by a third party (business email compromise)',
      'Data entry error on the PO vendor field',
    ],
    steps: [
      { action: 'Place the invoice on hold immediately; do NOT process payment', who: 'AP Clerk', when: 'Day 1' },
      { action: 'Verify the discrepancy - name, ID and bank account', who: 'AP Clerk', when: 'Day 1' },
      { action: 'Contact the vendor using details already on file, NOT details printed on the invoice', who: 'AP Clerk', when: 'Day 1' },
      { action: 'If a legitimate change, require a formal request through the vendor portal for AP Manager approval', who: 'AP Manager', when: 'Day 1-5' },
      { action: 'If potentially fraudulent, escalate to AP Manager and Finance Controller, and notify IT Security', who: 'AP Manager', when: 'Immediately' },
    ],
    policy:
      'Changes to vendor bank details are a primary vector for business email compromise. Always verify by independent callback to a known contact before updating payment details.',
  },
  'AP-SOP-001 6.5': {
    title: 'Duplicate Invoice',
    causes: [
      'Vendor resubmitted after no payment confirmation',
      'Invoice received through multiple channels',
      'Entered twice in error, or a system import duplicated it',
    ],
    steps: [
      { action: 'Investigate the flagged duplicate', who: 'AP Clerk', when: 'Day 1' },
      { action: 'Confirm the payment status of the original invoice', who: 'AP Clerk', when: 'Day 1' },
      { action: 'If the original is already paid, reject the duplicate and notify the vendor of payment status', who: 'AP Clerk', when: 'Day 1' },
      { action: 'If the original is still on hold, reject the duplicate and continue processing the original', who: 'AP Clerk', when: 'Day 1' },
      { action: 'If the duplicate was paid in error, raise a recovery request and request a refund or credit note', who: 'AP Manager', when: 'Immediately' },
    ],
    policy: 'Document all duplicate instances for fraud monitoring and the vendor scorecard.',
  },
  'AP-SOP-001 6.1 / 8.1': {
    title: 'Price Variance - invoice above PO',
    causes: [
      'Vendor applied a price increase not yet reflected on the PO',
      'Incorrect pricing on the PO',
      'Contractual price revision not communicated to AP',
      'Currency rounding on international invoices',
    ],
    steps: [
      { action: 'Hold the invoice and log the exception with variance amount and percentage', who: 'AP Clerk', when: 'Same day' },
      { action: 'Check whether a PO amendment or price agreement covers the difference', who: 'AP Clerk', when: 'Day 1' },
      { action: 'If an authorised amendment exists, update the PO, clear the exception and approve', who: 'AP Clerk', when: 'Day 1-2' },
      { action: 'Otherwise contact Procurement to verify whether the increase is valid', who: 'AP Clerk', when: 'Day 1-2' },
      { action: 'If valid, Procurement raises a PO amendment and AP approves the invoice', who: 'Procurement / AP Clerk', when: 'Day 2-5' },
      { action: 'If not valid, request a revised invoice or credit note from the vendor', who: 'AP Clerk', when: 'Day 2-5' },
    ],
    policy:
      'Tolerance: up to EUR 50 or 0.5% auto-approves. EUR 50-5,000 or 0.5-5% needs AP Manager approval. Above that, Finance Controller approval and mandatory Procurement review.',
  },
  'AP-SOP-001 6.2 / 8.1': {
    title: 'Quantity Variance - invoice above goods receipt',
    causes: [
      'Partial shipment received but vendor invoiced the full PO quantity',
      'Over-shipment accepted without a PO amendment',
      'Goods received but the goods receipt is not yet entered',
      'Unit of measure mismatch between invoice and receipt',
    ],
    steps: [
      { action: 'Hold the invoice and confirm the received quantity with the warehouse', who: 'AP Clerk', when: 'Day 1' },
      { action: 'Check whether a further goods receipt is pending', who: 'AP Clerk / Warehouse', when: 'Day 1-2' },
      { action: 'If a receipt is expected, hold pending confirmation with a 3-day follow-up', who: 'AP Clerk', when: 'Day 1-3' },
      { action: 'If no further receipt is expected, pay only for the quantity received and request a credit note', who: 'AP Clerk', when: 'Day 3-5' },
      { action: 'Issue a debit memo if the vendor does not issue a credit note within 5 days', who: 'AP Manager', when: 'Day 5-7' },
    ],
    policy:
      'Tolerance: variance value up to EUR 100 auto-approves. EUR 100-2,500 needs AP Manager approval. Above EUR 2,500 requires Finance Controller approval and a formal investigation.',
  },
  'AP-SOP-001 6.8 / 8.1': {
    title: 'Tax Discrepancy',
    causes: [
      'Tax rate changed since the PO was raised',
      'Incorrect tax code applied by the vendor',
      'Vendor charged for services not agreed on the PO',
    ],
    steps: [
      { action: 'Verify the applicable tax rate for the transaction type and jurisdiction', who: 'AP Clerk / Tax', when: 'Day 1' },
      { action: 'If the rate is correct but the PO is wrong, amend the PO and approve the invoice', who: 'Procurement / AP Clerk', when: 'Day 1-3' },
      { action: 'If the vendor applied the wrong rate, request a revised invoice', who: 'AP Clerk', when: 'Day 1-3' },
      { action: 'Ensure tax coding in the ERP is correct for accurate reporting', who: 'AP Clerk', when: 'Day 1-2' },
    ],
    policy:
      'Tolerance: up to EUR 25 auto-approves. EUR 25-500 needs AP Manager approval. Above EUR 500 requires Finance Controller approval.',
  },
};

/* --- Reports mandated by AP-SOP-001 section 9.3 --------------------------- */

const REPORT_CATALOGUE = [
  { id: 'exception-aging', name: 'Exception Aging Report', cadence: 'Weekly', audience: 'AP Manager' },
  { id: 'exception-volume', name: 'Exception Volume by Type', cadence: 'Monthly', audience: 'Finance Controller' },
  { id: 'vendor-scorecard', name: 'Vendor Exception Scorecard', cadence: 'Monthly', audience: 'Procurement' },
  { id: 'tolerance-breach', name: 'Tolerance Breach Summary', cadence: 'Monthly', audience: 'Finance Controller' },
  { id: 'duplicate-invoice', name: 'Duplicate Invoice Report', cadence: 'Monthly', audience: 'Finance Controller / Internal Audit' },
  { id: 'no-po-invoice', name: 'No-PO Invoice Report', cadence: 'Monthly', audience: 'Department Heads / Finance Controller' },
];

/** KPI targets from AP-SOP-001 section 10. */
const KPI_TARGETS = [
  { id: 'exception-rate', name: 'Exception rate', target: 5, unit: '%', direction: 'below' },
  { id: 'duplicate-rate', name: 'Duplicate invoice rate', target: 0.5, unit: '%', direction: 'below' },
  { id: 'no-po-rate', name: 'No-PO invoice rate', target: 2, unit: '%', direction: 'below' },
];

/* --- provider selection ---------------------------------------------------
 * The live backend is used whenever it answers /api/health. Otherwise the
 * seeded data below keeps the workspace openable. `source` tells the UI which
 * one is in play so the two are never mistaken for each other. */

import { live, backendReachable } from './client';

const delay = (ms) => new Promise((r) => setTimeout(r, ms));

let parked = {};

export const runtime = { source: 'seeded', providers: null, batchId: null };

export async function selectProvider() {
  const health = await backendReachable();
  if (health) {
    runtime.source = 'live';
    runtime.providers = health.providers;
  }
  return runtime;
}

export const mock = {
  async login(username, password) {
    await delay(420);
    if (username === 'admin' && password === 'admin') {
      return { ok: true, user: { name: 'Admin', initials: 'AD' } };
    }
    return { ok: false, error: 'Incorrect username or password. Try admin / admin.' };
  },

  async getBatch() {
    await delay(650);
    return {
      id: 'batch-2026-08-07',
      date: '2026-08-07',
      label: "Today's intake",
      source: 's3://922513818191-invoice/inbox/',
      sapCalls: 31,
      durationMs: 8420,
      outcomes: OUTCOMES.map((o) => ({
        ...o,
        parked: parked[o.invoice.reference] || null,
      })),
    };
  },

  /** One approval covers whichever references were reviewed. */
  async approve(references) {
    await delay(300);
    return { token: `apr_${Math.random().toString(36).slice(2, 12)}`, references };
  },

  async park(token, references) {
    const results = [];
    for (const reference of references) {
      await delay(520);
      const doc = String(5100001600 + Object.keys(parked).length);
      parked[reference] = { supplierInvoice: doc, fiscalYear: '2025', status: 'A' };
      results.push({ reference, ...parked[reference] });
    }
    return { results };
  },

  async guidance(sopRef) {
    await delay(380);
    return SOP[sopRef] || null;
  },

  async chat(invoiceRef, question, outcomeForInvoice) {
    await delay(700);
    return answerFor(question, outcomeForInvoice);
  },

  reportCatalogue: () => REPORT_CATALOGUE,
  kpiTargets: () => KPI_TARGETS,
  async generateReport(id, outcomes) {
    await delay(600);
    return buildReport(id, outcomes);
  },
};

/* One surface for the views. Each call goes to the backend when it is up and
 * to the seeded data when it is not, so no component knows the difference. */
export const api = {
  login: (u, p) => mock.login(u, p),

  async getBatch() {
    if (runtime.source === 'live') {
      const batch = await live.getBatch();
      runtime.batchId = batch.id;
      return batch;
    }
    return mock.getBatch();
  },

  async runBatch(files) {
    if (runtime.source === 'live') {
      const batch = await live.runBatch(files);
      runtime.batchId = batch.id;
      return batch;
    }
    return mock.getBatch();
  },

  async inbox() {
    if (runtime.source === 'live') return live.inbox();
    // Seeded mode mirrors the demo documents so the view still renders.
    return OUTCOMES.slice(0, 6).map((o, i) => ({
      name: `fpl-invoice-0${i + 1}.pdf`,
      sizeBytes: 2100,
      modified: new Date().toISOString(),
      processed: true,
      parked: false,
    }));
  },

  upload: (fileList) => {
    if (runtime.source === 'live') return live.upload(fileList);
    throw new Error('Uploading needs the backend running.');
  },

  approve: (references) =>
    runtime.source === 'live'
      ? live.approve(runtime.batchId, references)
      : mock.approve(references),

  park: (token, references) =>
    runtime.source === 'live'
      ? live.park(runtime.batchId, token, references)
      : mock.park(token, references),

  async guidance(sopRef) {
    if (runtime.source !== 'live') return mock.guidance(sopRef);
    try {
      return await live.guidance(sopRef);
    } catch {
      return null; // no SOP entry published for this clause
    }
  },

  chat: (reference, question, outcome) =>
    runtime.source === 'live'
      ? live.chat(runtime.batchId, reference, question)
      : mock.chat(reference, question, outcome),

  reportCatalogue: () => REPORT_CATALOGUE,
  kpiTargets: () => KPI_TARGETS,

  generateReport: (id, outcomes) =>
    runtime.source === 'live'
      ? live.generateReport(id, runtime.batchId)
      : mock.generateReport(id, outcomes),
};

/* --- canned exception assistant ------------------------------------------
 * Stands in for the orchestrator. It answers only from the finding it was
 * given and the SOP entry that finding names - the same constraint the real
 * agent runs under. */

function answerFor(question, outcomeForInvoice) {
  const q = question.toLowerCase();
  const failing = outcomeForInvoice.findings.find((f) => f.status === 'FAIL')
    || outcomeForInvoice.findings.find((f) => f.status === 'WARN');
  const sop = failing ? SOP[failing.sopRef] : null;

  if (/why|what happened|reason|cause/.test(q)) {
    return {
      text: `${failing.message}\n\nThis is rule ${failing.ruleId} - ${failing.ruleName}. The governing procedure is ${failing.sopRef}: ${sop ? sop.title : 'no SOP entry'}.`,
      citations: sop ? [failing.sopRef] : [],
    };
  }
  if (/cause|common|typical/.test(q) && sop) {
    return { text: `Common causes per ${failing.sopRef}:\n\n${sop.causes.map((c) => `- ${c}`).join('\n')}`, citations: [failing.sopRef] };
  }
  if (/what.*(do|next|step|fix|resolve|action)/.test(q) && sop) {
    return {
      text: `${sop.title} - resolution steps from ${failing.sopRef}:\n\n${sop.steps
        .map((s, i) => `${i + 1}. ${s.action}  (${s.who}, ${s.when})`)
        .join('\n')}\n\n${sop.policy}`,
      citations: [failing.sopRef],
    };
  }
  if (/who|escalat|approv/.test(q)) {
    return {
      text: `This exception routes to ${outcomeForInvoice.requiredApproval.replace('_', ' ').toLowerCase()}. ${sop ? sop.policy : ''}`,
      citations: sop ? [failing.sopRef] : [],
    };
  }
  if (/sap|purchase order|po\b|vendor|check/.test(q)) {
    const inv = outcomeForInvoice.invoice;
    return {
      text: `Read back from SAP for purchase order ${inv.purchaseOrder} item ${inv.purchaseOrderItem}:\n\n- Vendor on the PO: ${failing.sapValue || '17401710'}\n- Invoice states: ${failing.invoiceValue || inv.supplier}\n\nI can re-run validation once the underlying data changes in SAP.`,
      citations: [],
    };
  }
  return {
    text: `I can explain why this invoice failed, list the common causes, walk through the resolution steps from ${failing ? failing.sopRef : 'the SOP'}, or re-check the purchase order in SAP. What would help?`,
    citations: [],
  };
}

/* --- report builders ------------------------------------------------------ */

function buildReport(id, outcomes) {
  const exceptions = outcomes.filter((o) => !o.canPark);
  const warned = outcomes.filter((o) => o.canPark && o.findings.some((f) => f.status === 'WARN'));

  const firstActive = (o) => o.findings.find((f) => f.status === 'FAIL') || o.findings.find((f) => f.status === 'WARN');

  if (id === 'exception-volume') {
    const byRule = {};
    [...exceptions, ...warned].forEach((o) => {
      const f = firstActive(o);
      if (!f) return;
      byRule[f.ruleName] = (byRule[f.ruleName] || 0) + 1;
    });
    return {
      title: 'Exception Volume by Type',
      subtitle: 'AP-SOP-001 section 9.3 - monthly, for the Finance Controller',
      columns: ['Exception type', 'Count'],
      rows: Object.entries(byRule).sort((a, b) => b[1] - a[1]).map(([k, v]) => [k, v]),
      chart: Object.entries(byRule).sort((a, b) => b[1] - a[1]).map(([label, value]) => ({ label, value })),
    };
  }

  if (id === 'vendor-scorecard') {
    const byVendor = {};
    outcomes.forEach((o) => {
      const key = `${o.invoice.supplier} - ${o.invoice.supplierName}`;
      byVendor[key] = byVendor[key] || { total: 0, exceptions: 0 };
      byVendor[key].total += 1;
      if (!o.canPark) byVendor[key].exceptions += 1;
    });
    return {
      title: 'Vendor Exception Scorecard',
      subtitle: 'AP-SOP-001 section 9.3 - monthly, for Procurement',
      columns: ['Vendor', 'Invoices', 'Exceptions', 'Rate'],
      rows: Object.entries(byVendor).map(([vendor, v]) => [
        vendor, v.total, v.exceptions, `${((v.exceptions / v.total) * 100).toFixed(0)}%`,
      ]),
      chart: Object.entries(byVendor).map(([label, v]) => ({ label, value: v.exceptions })),
    };
  }

  if (id === 'tolerance-breach') {
    const rows = warned.map((o) => {
      const f = firstActive(o);
      return [o.invoice.sourceFile, f.ruleName, f.delta || '-', o.requiredApproval.replace('_', ' ')];
    });
    return {
      title: 'Tolerance Breach Summary',
      subtitle: 'AP-SOP-001 section 9.3 - monthly, for the Finance Controller',
      columns: ['Invoice', 'Rule', 'Variance', 'Routed to'],
      rows,
      chart: null,
    };
  }

  if (id === 'duplicate-invoice') {
    const rows = outcomes
      .filter((o) => o.findings.some((f) => f.ruleId === 'R16' && f.status === 'FAIL'))
      .map((o) => [o.invoice.sourceFile, o.invoice.reference, o.invoice.supplier, 'Rejected']);
    return {
      title: 'Duplicate Invoice Report',
      subtitle: 'AP-SOP-001 section 9.3 - monthly, for Finance Controller and Internal Audit',
      columns: ['Invoice', 'Reference', 'Supplier', 'Outcome'],
      rows,
      chart: null,
    };
  }

  if (id === 'no-po-invoice') {
    const rows = outcomes
      .filter((o) => o.findings.some((f) => f.ruleId === 'R01' && f.status === 'FAIL'))
      .map((o) => [o.invoice.sourceFile, o.invoice.purchaseOrder, o.invoice.supplier, 'On hold - no PO']);
    return {
      title: 'No-PO Invoice Report',
      subtitle: 'AP-SOP-001 section 9.3 - monthly, for Department Heads and the Finance Controller',
      columns: ['Invoice', 'PO cited', 'Supplier', 'Status'],
      rows,
      chart: null,
    };
  }

  // exception-aging
  const rows = exceptions.map((o) => {
    const f = firstActive(o);
    return [o.invoice.sourceFile, f.ruleName, f.sopRef, o.requiredApproval.replace('_', ' '), 'Day 1'];
  });
  return {
    title: 'Exception Aging Report',
    subtitle: 'AP-SOP-001 section 9.3 - weekly, for the AP Manager',
    columns: ['Invoice', 'Exception', 'SOP clause', 'Routed to', 'Age'],
    rows,
    chart: null,
  };
}
