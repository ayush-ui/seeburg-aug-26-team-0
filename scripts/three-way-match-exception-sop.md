# Standard Operating Procedure
# Three-Way Match Exception Handling

| Field | Details |
|---|---|
| **SOP ID** | AP-SOP-001 |
| **Version** | 1.0 |
| **Effective Date** | 2026-08-06 |
| **Last Reviewed** | 2026-08-06 |
| **Owner** | Accounts Payable Department |
| **Approved By** | Finance Controller |
| **Classification** | Internal Use Only |

---

## Table of Contents

1. [Purpose](#1-purpose)
2. [Scope](#2-scope)
3. [Definitions](#3-definitions)
4. [Roles and Responsibilities](#4-roles-and-responsibilities)
5. [Three-Way Match Overview](#5-three-way-match-overview)
6. [Exception Scenarios and Resolution Procedures](#6-exception-scenarios-and-resolution-procedures)
   - 6.1 [Price Variance Exceptions](#61-price-variance-exceptions)
   - 6.2 [Quantity Variance Exceptions](#62-quantity-variance-exceptions)
   - 6.3 [Missing Purchase Order](#63-missing-purchase-order)
   - 6.4 [Missing Goods Receipt](#64-missing-goods-receipt)
   - 6.5 [Duplicate Invoice](#65-duplicate-invoice)
   - 6.6 [Vendor/Supplier Mismatch](#66-vendorsupplier-mismatch)
   - 6.7 [Currency and Exchange Rate Discrepancies](#67-currency-and-exchange-rate-discrepancies)
   - 6.8 [Tax and Freight Discrepancies](#68-tax-and-freight-discrepancies)
   - 6.9 [Partial Deliveries and Invoices](#69-partial-deliveries-and-invoices)
   - 6.10 [Goods Returned or Rejected](#610-goods-returned-or-rejected)
   - 6.11 [PO Amendment Discrepancies](#611-po-amendment-discrepancies)
   - 6.12 [Invoice Received Before Goods](#612-invoice-received-before-goods)
7. [Escalation Matrix](#7-escalation-matrix)
8. [Tolerance Thresholds](#8-tolerance-thresholds)
9. [Documentation and Record Keeping](#9-documentation-and-record-keeping)
10. [Key Performance Indicators](#10-key-performance-indicators)
11. [Related Documents and References](#11-related-documents-and-references)
12. [Revision History](#12-revision-history)

---

## 1. Purpose

This Standard Operating Procedure (SOP) establishes a consistent, controlled process for identifying, investigating, and resolving exceptions that arise during the three-way matching process in Accounts Payable. It ensures that all invoices are validated against Purchase Orders (POs) and Goods Receipts (GRs) before payment is authorized, protecting the organization from financial loss, fraud, and compliance risk.

---

## 2. Scope

This SOP applies to:

- All Accounts Payable (AP) staff responsible for invoice processing
- Procurement and Purchasing teams
- Warehouse and Receiving departments
- Finance Controllers and AP Managers
- All vendor invoices requiring three-way match validation, regardless of value

This SOP does **not** apply to:
- Petty cash transactions
- Employee expense reimbursements (governed by separate SOP HR-EXP-002)
- Utility and recurring service invoices processed under blanket POs with two-way match approval

---

## 3. Definitions

| Term | Definition |
|---|---|
| **Three-Way Match** | The process of comparing a vendor invoice against the corresponding Purchase Order and Goods Receipt to verify accuracy before payment |
| **Purchase Order (PO)** | A legally binding document issued by the buyer to the supplier authorizing the purchase of goods or services at agreed terms |
| **Goods Receipt (GR)** | A document confirming that goods or services have been received and accepted by the organization |
| **Invoice** | A commercial document issued by the vendor requesting payment for goods or services delivered |
| **Price Variance** | A discrepancy between the unit price on the invoice and the unit price agreed on the Purchase Order |
| **Quantity Variance** | A discrepancy between the quantity billed on the invoice and the quantity recorded on the Goods Receipt or PO |
| **Tolerance Threshold** | The acceptable percentage or monetary limit within which a variance is automatically approved without escalation |
| **Exception** | Any discrepancy identified during three-way matching that prevents automatic invoice approval |
| **AP Clerk** | Accounts Payable staff member responsible for first-line invoice processing |
| **AP Manager** | Supervisor responsible for exception escalation and resolution approval |
| **ERP System** | Enterprise Resource Planning system used to record POs, GRs, and invoices (e.g., SAP, Oracle, NetSuite) |
| **Debit Memo** | A document issued to a vendor requesting a credit or adjustment for overbilling or returned goods |

---

## 4. Roles and Responsibilities

### 4.1 AP Clerk
- Receive and register all vendor invoices in the ERP system
- Perform three-way match for each invoice
- Identify and log exceptions
- Contact vendors or internal departments to resolve minor exceptions
- Escalate unresolved exceptions within defined timeframes

### 4.2 AP Manager / Supervisor
- Review and approve exceptions within defined tolerance thresholds
- Authorize exception escalation to Finance Controller
- Monitor exception aging and ensure timely resolution
- Provide guidance on complex or recurring exception types

### 4.3 Procurement / Purchasing Team
- Amend POs when price or quantity changes are validated and approved
- Confirm PO terms with vendors when disputes arise
- Raise emergency or retrospective POs when invoices arrive without a PO

### 4.4 Warehouse / Receiving Team
- Confirm actual quantities received and update GR records
- Raise GR amendments for under- or over-receipts
- Document rejected or returned goods with supporting evidence

### 4.5 Finance Controller
- Approve high-value exceptions above defined thresholds
- Authorize write-offs for unrecoverable variances below materiality limits
- Review exception trends and recommend process improvements

### 4.6 Vendor / Supplier
- Provide credit notes, revised invoices, or supporting documentation as requested
- Respond to AP queries within agreed SLA timeframes (typically 5 business days)

---

## 5. Three-Way Match Overview

### 5.1 Standard Matching Process

```
VENDOR INVOICE
      |
      v
┌─────────────────────────────────────────────────────┐
│              THREE-WAY MATCH CHECK                  │
│                                                     │
│  Invoice  ◄──────► Purchase Order ◄──────► Goods    │
│  Details            Details               Receipt   │
│                                           Details   │
│  • Vendor           • Vendor              • Vendor  │
│  • PO Number        • Line Items          • PO Ref  │
│  • Line Items       • Unit Price          • Qty Rcvd│
│  • Unit Price       • Quantity            • Date    │
│  • Quantity         • Delivery Terms      • Quality │
│  • Total Amount     • Payment Terms                 │
└─────────────────────────────────────────────────────┘
      |                    |
      v                    v
  MATCH ✓             NO MATCH ✗
      |                    |
      v                    v
  APPROVE            EXCEPTION HANDLING
  FOR PAYMENT        (This SOP)
```

### 5.2 Matching Criteria

All three documents must agree on the following fields for a successful match:

1. **Vendor identity** — Vendor name, ID, and bank details match
2. **PO reference number** — Invoice cites a valid, open PO
3. **Line item descriptions** — Goods/services described consistently
4. **Unit price** — Invoice price matches PO agreed price (within tolerance)
5. **Quantity** — Invoice quantity matches GR confirmed quantity (within tolerance)
6. **Currency** — All documents use the same agreed currency
7. **Delivery period** — Goods received within PO validity period

---

## 6. Exception Scenarios and Resolution Procedures

---

### 6.1 Price Variance Exceptions

#### 6.1.1 Description
A price variance occurs when the unit price on the vendor invoice differs from the unit price recorded on the approved Purchase Order.

#### 6.1.2 Common Causes
- Vendor applied a price increase not yet reflected in the PO
- Incorrect pricing on the PO (data entry error)
- Contractual price revision not communicated to AP
- Promotional discount applied by vendor not anticipated in PO
- Currency rounding differences on international invoices

#### 6.1.3 Sub-Scenarios and Resolution Steps

**Scenario A — Invoice price HIGHER than PO price**

| Step | Action | Responsible | Timeframe |
|---|---|---|---|
| 1 | Place invoice on hold in ERP; log exception with variance amount and % | AP Clerk | Same day |
| 2 | Check if a PO amendment or price agreement exists that covers the difference | AP Clerk | Day 1 |
| 3 | If PO amendment exists and is authorized: update PO, clear exception, approve for payment | AP Clerk | Day 1–2 |
| 4 | If no amendment exists: contact Procurement to verify if vendor price increase is valid | AP Clerk | Day 1–2 |
| 5 | If price increase is valid: Procurement raises PO amendment; AP Clerk approves invoice | Procurement / AP Clerk | Day 2–5 |
| 6 | If price increase is NOT valid: AP contacts vendor to request a revised invoice or credit note | AP Clerk | Day 2–5 |
| 7 | If unresolved after 5 business days: escalate to AP Manager | AP Clerk | Day 5 |

**Scenario B — Invoice price LOWER than PO price**

| Step | Action | Responsible | Timeframe |
|---|---|---|---|
| 1 | Verify the lower price is intentional (e.g., discount applied by vendor) | AP Clerk | Day 1 |
| 2 | If intentional discount: obtain written confirmation from vendor; approve invoice at lower price; notify Procurement to amend PO | AP Clerk / Procurement | Day 1–3 |
| 3 | If appears to be a vendor error: contact vendor for confirmation before payment | AP Clerk | Day 1–2 |
| 4 | Do not overpay — pay invoice amount only; Procurement to amend PO accordingly | AP Manager | Day 3–5 |

#### 6.1.4 Tolerance Thresholds (Price Variance)

| Variance Level | Action |
|---|---|
| ≤ 0.5% or ≤ $50 (whichever is lower) | Auto-approve; post variance to price variance GL account |
| 0.5% – 2% or $50 – $500 | AP Clerk approves with documented justification |
| 2% – 5% or $500 – $5,000 | AP Manager approval required |
| > 5% or > $5,000 | Finance Controller approval required; Procurement review mandatory |

---

### 6.2 Quantity Variance Exceptions

#### 6.2.1 Description
A quantity variance occurs when the quantity billed on the invoice does not match the quantity confirmed as received on the Goods Receipt.

#### 6.2.2 Common Causes
- Partial shipment received but vendor invoiced for full PO quantity
- Over-shipment received and accepted by warehouse without PO amendment
- Goods received but GR not yet entered in ERP (timing difference)
- Goods partially rejected at receiving dock
- Unit of measure mismatch (e.g., invoice in units vs. GR in cases)

#### 6.2.3 Sub-Scenarios and Resolution Steps

**Scenario A — Invoice quantity GREATER than GR quantity (overbilling)**

| Step | Action | Responsible | Timeframe |
|---|---|---|---|
| 1 | Hold invoice; confirm GR quantity with Warehouse team | AP Clerk | Day 1 |
| 2 | Check if additional GR is pending (goods in transit or not yet booked) | AP Clerk / Warehouse | Day 1–2 |
| 3 | If pending GR expected: hold invoice pending GR confirmation; set 3-day follow-up | AP Clerk | Day 1–3 |
| 4 | If no further GR expected: pay only for quantity received; request credit note from vendor for balance | AP Clerk | Day 3–5 |
| 5 | Issue Debit Memo for overbilled quantity if vendor does not issue credit note within 5 days | AP Manager | Day 5–7 |

**Scenario B — Invoice quantity LESS than GR quantity (under-billing)**

| Step | Action | Responsible | Timeframe |
|---|---|---|---|
| 1 | Verify GR quantity is correct and goods were actually received in full | AP Clerk / Warehouse | Day 1 |
| 2 | Approve and pay invoice for billed quantity | AP Clerk | Day 1–2 |
| 3 | Notify Procurement of under-billing; monitor for subsequent invoice covering remaining quantity | AP Clerk / Procurement | Day 2 |
| 4 | Accrue liability for received but not invoiced quantity (GR/IR accrual) | Finance / AP Manager | Month-end |

**Scenario C — Unit of Measure (UoM) Mismatch**

| Step | Action | Responsible | Timeframe |
|---|---|---|---|
| 1 | Identify the UoM discrepancy between invoice and GR | AP Clerk | Day 1 |
| 2 | Calculate equivalent quantity using agreed conversion factor | AP Clerk / Procurement | Day 1–2 |
| 3 | If converted quantities match within tolerance: approve with documented conversion note | AP Clerk | Day 2 |
| 4 | If conversion factor is disputed: escalate to Procurement for vendor clarification | AP Manager | Day 2–5 |

#### 6.2.4 Tolerance Thresholds (Quantity Variance)

| Variance Level | Action |
|---|---|
| ≤ 1% of ordered quantity or ≤ 1 unit | Auto-approve; adjust GR or invoice to match |
| 1% – 5% | AP Clerk resolves with Warehouse confirmation |
| 5% – 10% | AP Manager approval; Procurement notified |
| > 10% | Finance Controller approval; formal investigation required |

---

### 6.3 Missing Purchase Order

#### 6.3.1 Description
An invoice is received from a vendor but no valid, open Purchase Order exists in the ERP system to match against.

#### 6.3.2 Common Causes
- Goods or services ordered verbally or via email without a formal PO
- PO raised in a different system or not yet entered in ERP
- PO expired before invoice was submitted
- Invoice submitted against a closed or fully consumed PO

#### 6.3.3 Resolution Steps

| Step | Action | Responsible | Timeframe |
|---|---|---|---|
| 1 | Register invoice in ERP with "On Hold – No PO" status | AP Clerk | Day 1 |
| 2 | Contact the requester/budget owner to confirm the purchase was authorized | AP Clerk | Day 1 |
| 3 | If authorized: request Procurement to raise a retrospective PO referencing invoice | AP Clerk / Procurement | Day 1–3 |
| 4 | If not authorized: notify AP Manager; do not process for payment pending investigation | AP Clerk | Day 1 |
| 5 | Procurement raises PO; AP Clerk links invoice and GR to new PO | Procurement / AP Clerk | Day 3–5 |
| 6 | If retrospective PO not raised within 5 days: escalate to Finance Controller | AP Manager | Day 5 |
| 7 | Document all cases of "no PO" invoices for monthly reporting and trend analysis | AP Manager | Monthly |

> **Policy Note:** Payment must not be made against an invoice without a valid PO unless explicitly approved in writing by the Finance Controller. Repeated "no PO" invoices from the same requester must be reported to their department head.

---

### 6.4 Missing Goods Receipt

#### 6.4.1 Description
An invoice and PO exist and match, but no Goods Receipt has been recorded to confirm the goods or services were delivered.

#### 6.4.2 Common Causes
- Warehouse has not yet booked the GR in ERP despite goods being received
- Goods are still in transit
- Service delivery not formally acknowledged in the system
- GR raised against a different PO number by mistake

#### 6.4.3 Resolution Steps

| Step | Action | Responsible | Timeframe |
|---|---|---|---|
| 1 | Place invoice on hold; check physical receiving records with Warehouse | AP Clerk | Day 1 |
| 2 | If goods physically received: request Warehouse to raise GR immediately | AP Clerk / Warehouse | Day 1–2 |
| 3 | Once GR is posted: complete three-way match and approve invoice | AP Clerk | Day 2–3 |
| 4 | If goods not yet received: hold invoice; communicate expected delivery date to vendor | AP Clerk | Day 1–2 |
| 5 | If goods not received within PO delivery window: notify Procurement to investigate with vendor | AP Clerk / Procurement | Per PO terms |
| 6 | For services: obtain signed service acceptance/completion form from business owner; post GR | Business Owner / AP Clerk | Day 1–5 |
| 7 | If GR cannot be confirmed after 10 business days: escalate to AP Manager and Finance Controller | AP Manager | Day 10 |

---

### 6.5 Duplicate Invoice

#### 6.5.1 Description
The same invoice (same vendor, invoice number, amount, and date) is submitted more than once, either by the vendor or due to internal processing error.

#### 6.5.2 Common Causes
- Vendor resubmits invoice after not receiving payment confirmation
- Invoice received via multiple channels (email, post, portal)
- AP Clerk enters invoice twice in error
- System import duplication

#### 6.5.3 Resolution Steps

| Step | Action | Responsible | Timeframe |
|---|---|---|---|
| 1 | ERP duplicate check flags the invoice; AP Clerk investigates | AP Clerk | Day 1 |
| 2 | Confirm original invoice payment status in ERP | AP Clerk | Day 1 |
| 3 | If original invoice already paid: reject duplicate; notify vendor of payment status | AP Clerk | Day 1 |
| 4 | If original invoice still on hold or pending: reject duplicate; continue processing original | AP Clerk | Day 1 |
| 5 | If duplicate was paid in error: raise recovery request; contact vendor for refund or credit note | AP Manager | Immediately |
| 6 | Document all duplicate instances for fraud monitoring and vendor scorecard | AP Manager | Monthly |

---

### 6.6 Vendor/Supplier Mismatch

#### 6.6.1 Description
The vendor details on the invoice (name, ID, bank account, address) do not match the vendor master record linked to the Purchase Order.

#### 6.6.2 Common Causes
- Vendor has changed their legal name or bank account details
- Invoice issued by a subsidiary or parent company not in vendor master
- Fraudulent invoice submitted by a third party (social engineering / BEC fraud risk)
- Data entry error on PO vendor field

#### 6.6.3 Resolution Steps

| Step | Action | Responsible | Timeframe |
|---|---|---|---|
| 1 | Immediately place invoice on hold; do NOT process payment | AP Clerk | Day 1 |
| 2 | Verify the discrepancy details (name, ID, bank account) | AP Clerk | Day 1 |
| 3 | Contact the vendor using contact details already on file (NOT from the invoice) to verify legitimacy | AP Clerk | Day 1 |
| 4 | If legitimate name/bank change: vendor submits formal change request through vendor portal; AP Manager approves vendor master update | AP Manager / Vendor | Day 1–5 |
| 5 | If potentially fraudulent: escalate to AP Manager and Finance Controller immediately; notify IT Security if BEC fraud suspected | AP Manager / Finance Controller | Immediately |
| 6 | Do not update vendor bank details based solely on an invoice or unsolicited email | All AP Staff | Always |
| 7 | Log all vendor mismatch cases for audit trail | AP Manager | Always |

> **Security Alert:** Changes to vendor bank account details are a primary vector for Business Email Compromise (BEC) fraud. Always verify via independent callback to a known vendor contact before updating payment details.

---

### 6.7 Currency and Exchange Rate Discrepancies

#### 6.7.1 Description
The invoice currency or exchange rate differs from what was agreed on the Purchase Order, resulting in a variance when converted to the functional currency.

#### 6.7.2 Common Causes
- Invoice issued in a different currency than the PO
- Exchange rate used by vendor differs from the rate agreed in the PO or applied by ERP
- Currency fluctuation between PO date and invoice date on contracts without fixed FX rates

#### 6.7.3 Resolution Steps

| Step | Action | Responsible | Timeframe |
|---|---|---|---|
| 1 | Identify the currency mismatch or FX rate discrepancy | AP Clerk | Day 1 |
| 2 | Check PO for agreed currency and any FX rate clauses | AP Clerk / Procurement | Day 1 |
| 3 | If wrong currency on invoice: contact vendor for a reissued invoice in the correct currency | AP Clerk | Day 1–3 |
| 4 | If FX rate variance: apply the ERP system rate on the invoice posting date per company policy | AP Clerk | Day 1–2 |
| 5 | If FX variance results in a material difference (per threshold): escalate to Finance for FX gain/loss treatment | AP Manager / Finance | Day 2–5 |
| 6 | Post FX gain/loss to the designated GL account | Finance / AP Clerk | Day 2–5 |

---

### 6.8 Tax and Freight Discrepancies

#### 6.8.1 Description
The invoice includes tax charges (VAT, GST, sales tax) or freight/shipping costs that do not match what was agreed on the Purchase Order.

#### 6.8.2 Common Causes
- Tax rate changed since PO was raised
- Incorrect tax code applied by vendor
- Freight charges not included in original PO (added by vendor unilaterally)
- Vendor charges for additional services (insurance, handling) not agreed in PO

#### 6.8.3 Resolution Steps

**Tax Discrepancy**

| Step | Action | Responsible | Timeframe |
|---|---|---|---|
| 1 | Verify the applicable tax rate for the transaction type and jurisdiction | AP Clerk / Tax Team | Day 1 |
| 2 | If tax rate is correct but PO has wrong rate: amend PO and approve invoice | Procurement / AP Clerk | Day 1–3 |
| 3 | If vendor has applied wrong tax rate: request revised invoice with correct tax | AP Clerk | Day 1–3 |
| 4 | Ensure tax coding in ERP is correct for accurate reporting | AP Clerk | Day 1–2 |

**Freight / Additional Charges Discrepancy**

| Step | Action | Responsible | Timeframe |
|---|---|---|---|
| 1 | Confirm whether freight/additional charges were part of the original agreement | AP Clerk / Procurement | Day 1 |
| 2 | If agreed but not on PO: Procurement adds freight line to PO; AP approves | Procurement / AP Clerk | Day 1–3 |
| 3 | If NOT agreed: contact vendor to remove unapproved charges or issue credit note | AP Clerk | Day 1–5 |
| 4 | Pay only agreed amount; withhold unapproved charges pending resolution | AP Manager | Day 5 |

---

### 6.9 Partial Deliveries and Invoices

#### 6.9.1 Description
A vendor delivers goods in multiple shipments and submits separate invoices for each partial delivery, or submits one invoice for a partial delivery against a full PO.

#### 6.9.2 Common Causes
- Large orders split into multiple shipments by vendor
- Goods partially available from vendor stock
- Buyer-requested phased delivery schedule

#### 6.9.3 Resolution Steps

| Step | Action | Responsible | Timeframe |
|---|---|---|---|
| 1 | Confirm PO allows partial deliveries and invoicing | AP Clerk | Day 1 |
| 2 | Match each invoice line to the corresponding GR quantity for that shipment only | AP Clerk | Day 1–2 |
| 3 | Approve and pay invoice for the quantity confirmed received on each GR | AP Clerk | Day 2–3 |
| 4 | Track cumulative invoiced and received quantities against total PO quantity | AP Clerk | Ongoing |
| 5 | Flag if cumulative invoiced quantity exceeds cumulative GR quantity | AP Clerk | Ongoing |
| 6 | Close PO only when all goods are received and all invoices are matched and paid | AP Manager / Procurement | On completion |
| 7 | Maintain GR/IR (Goods Receipt / Invoice Receipt) accrual for received-not-invoiced quantities | Finance | Month-end |

---

### 6.10 Goods Returned or Rejected

#### 6.10.1 Description
Goods are returned to the vendor or rejected at receipt, but the vendor has already submitted (or not yet credited) an invoice for those goods.

#### 6.10.2 Common Causes
- Goods failed quality inspection at receiving
- Wrong goods delivered by vendor
- Goods damaged in transit
- Customer return passed back to vendor

#### 6.10.3 Resolution Steps

| Step | Action | Responsible | Timeframe |
|---|---|---|---|
| 1 | Warehouse raises a Return Delivery document in ERP; GR is reversed for returned quantity | Warehouse | Day 1 |
| 2 | AP Clerk is notified of return; invoice is placed on hold or partially held for returned quantity | Warehouse / AP Clerk | Day 1 |
| 3 | AP Clerk contacts vendor to request a credit note for returned goods | AP Clerk | Day 1–2 |
| 4 | If invoice not yet paid: reduce payment by the value of returned goods; pay net amount | AP Clerk | Day 2–3 |
| 5 | If invoice already paid: apply vendor credit note to next invoice, or request cash refund | AP Manager | Day 3–7 |
| 6 | Ensure return delivery and credit note are matched and closed in ERP | AP Clerk | Day 5–10 |
| 7 | If vendor disputes return: escalate to Procurement for commercial resolution | AP Manager / Procurement | Day 5+ |

---

### 6.11 PO Amendment Discrepancies

#### 6.11.1 Description
The PO was amended after the vendor had already shipped goods or issued an invoice, creating a mismatch between the invoice (based on original PO terms) and the amended PO in the system.

#### 6.11.2 Common Causes
- Price or quantity negotiated and amended after vendor confirmed the order
- PO amendment entered in ERP but vendor not yet notified
- Vendor invoices against original PO terms despite receiving amendment notification

#### 6.11.3 Resolution Steps

| Step | Action | Responsible | Timeframe |
|---|---|---|---|
| 1 | Identify which PO version the invoice references | AP Clerk | Day 1 |
| 2 | Check whether amendment was communicated to vendor before goods were shipped | Procurement | Day 1–2 |
| 3 | If vendor was not notified of amendment before shipment: pay per original PO terms; update system accordingly | AP Manager / Finance | Day 2–5 |
| 4 | If vendor was notified and still invoiced at old terms: request revised invoice from vendor | AP Clerk | Day 2–5 |
| 5 | Procurement to ensure future amendments are communicated to vendors in writing before shipment | Procurement | Ongoing |

---

### 6.12 Invoice Received Before Goods

#### 6.12.1 Description
A vendor submits an invoice for goods or services that have not yet been received or confirmed in the system. Also known as a "pre-delivery invoice."

#### 6.12.2 Common Causes
- Vendor invoices on shipment date rather than delivery/acceptance date
- Goods in transit for extended periods (international shipments)
- Services invoiced in advance of completion
- Invoice sent early to meet vendor's own reporting deadlines

#### 6.12.3 Resolution Steps

| Step | Action | Responsible | Timeframe |
|---|---|---|---|
| 1 | Register invoice in ERP with "On Hold – Awaiting GR" status | AP Clerk | Day 1 |
| 2 | Check expected delivery date with Procurement / Warehouse | AP Clerk | Day 1 |
| 3 | Set a review date aligned with expected delivery; do not process for payment until GR is confirmed | AP Clerk | Day 1 |
| 4 | Once GR is posted: release invoice from hold, complete three-way match, approve payment | AP Clerk / Warehouse | On GR receipt |
| 5 | If goods not received by expected date: notify Procurement; hold invoice until delivery confirmed | AP Clerk | Per schedule |
| 6 | For services: obtain written confirmation of service completion before releasing invoice | Business Owner / AP Clerk | On completion |
| 7 | Communicate payment terms to vendor — payment is triggered by GR/acceptance, not by invoice date | Procurement | Per contract |

---

## 7. Escalation Matrix

| Exception Type | Level 1 (AP Clerk) | Level 2 (AP Manager) | Level 3 (Finance Controller) | Trigger for Escalation |
|---|---|---|---|---|
| Price Variance | ≤ 2% or ≤ $500 | 2%–5% or $500–$5,000 | > 5% or > $5,000 | Unresolved at Level 1 after 3 days |
| Quantity Variance | ≤ 5% | 5%–10% | > 10% | Unresolved at Level 1 after 3 days |
| Missing PO | Initial contact | Retrospective PO approval | Payment override approval | No PO raised within 5 days |
| Missing GR | Chase Warehouse | Approve with documented risk | Waiver for strategic vendors | No GR within 10 days |
| Duplicate Invoice | Reject duplicate | Recovery of erroneous payment | Fraud investigation | Suspected intentional duplication |
| Vendor Mismatch | Flag and hold | Approve legitimate changes | Fraud/BEC escalation | Any suspected fraud |
| Currency/FX | Apply system rate | Material FX variance | Policy exception approval | Unresolved after 3 days |
| Returned Goods | Hold/partial pay | Dispute resolution | Write-off approval | Vendor disputes return after 10 days |

### 7.1 Escalation Timeframes

| Escalation Level | Response Time | Resolution Time |
|---|---|---|
| Level 1 → Level 2 | Within 1 business day of escalation | Within 3 business days |
| Level 2 → Level 3 | Within 1 business day of escalation | Within 5 business days |
| Level 3 (Finance Controller) | Same day acknowledgement | Within 10 business days |

---

## 8. Tolerance Thresholds

The following consolidated tolerance table applies across all exception types. Variances within the tolerance are auto-approved with GL posting to the appropriate variance account.

### 8.1 Monetary Tolerance Table

| Category | Auto-Approve (AP Clerk) | Manager Approval | Controller Approval |
|---|---|---|---|
| **Price Variance** | ≤ $50 or ≤ 0.5% | $50–$5,000 or 0.5%–5% | > $5,000 or > 5% |
| **Quantity Variance (value)** | ≤ $100 | $100–$2,500 | > $2,500 |
| **Tax Discrepancy** | ≤ $25 | $25–$500 | > $500 |
| **Freight Discrepancy** | ≤ $50 | $50–$250 | > $250 |
| **FX Variance** | ≤ $50 | $50–$1,000 | > $1,000 |

### 8.2 Notes on Tolerance Application
- Tolerances apply per invoice, not per line item
- Cumulative variances from the same vendor within a 30-day period are reviewed monthly by the AP Manager
- Tolerances may be tightened for vendors with a history of repeated exceptions
- All auto-approved variances are posted to the appropriate variance GL account and reviewed quarterly by Finance

---

## 9. Documentation and Record Keeping

### 9.1 Required Documentation for Every Exception

All exceptions must be documented in the ERP system exception log with the following minimum information:

- [ ] Invoice number, vendor name, and PO number
- [ ] Exception type and description of the discrepancy
- [ ] Dollar value and percentage of variance
- [ ] Date exception was identified and by whom
- [ ] Actions taken at each resolution step
- [ ] Names of all approvers and dates of approval
- [ ] Supporting evidence (emails, credit notes, GR amendments, vendor confirmations)
- [ ] Final resolution outcome and date closed

### 9.2 Retention Policy

| Document Type | Retention Period |
|---|---|
| Invoices and supporting documents | 7 years |
| Exception logs and resolution records | 7 years |
| Vendor correspondence | 7 years |
| PO amendments | 7 years |
| Escalation approvals | 7 years |

All records must be stored in the designated document management system or ERP document attachment functionality. Physical documents must be scanned within 24 hours of receipt.

### 9.3 Reporting

| Report | Frequency | Audience |
|---|---|---|
| Exception Aging Report | Weekly | AP Manager |
| Exception Volume by Type | Monthly | Finance Controller |
| Vendor Exception Scorecard | Monthly | Procurement |
| Tolerance Breach Summary | Monthly | Finance Controller |
| Duplicate Invoice Report | Monthly | Finance Controller / Internal Audit |
| No-PO Invoice Report | Monthly | Department Heads / Finance Controller |
| Annual Exception Trend Analysis | Annually | CFO / Internal Audit |

---

## 10. Key Performance Indicators

The following KPIs are used to measure the effectiveness of the three-way match exception handling process:

| KPI | Target | Measurement Period |
|---|---|---|
| Exception Rate (% of invoices with exceptions) | < 5% | Monthly |
| Exception Resolution Time — Level 1 | ≤ 3 business days | Monthly |
| Exception Resolution Time — Level 2 | ≤ 5 business days | Monthly |
| Exception Resolution Time — Level 3 | ≤ 10 business days | Monthly |
| Duplicate Invoice Rate | < 0.5% | Monthly |
| No-PO Invoice Rate | < 2% | Monthly |
| Vendor Credit Note Recovery Rate | > 90% within 30 days | Monthly |
| Aged Exceptions (> 30 days open) | < 1% of total exceptions | Monthly |
| Price Variance Recovery (overbilled) | > 95% | Quarterly |

---

## 11. Related Documents and References

| Document | Reference |
|---|---|
| Accounts Payable Policy | AP-POL-001 |
| Vendor Master Management SOP | AP-SOP-002 |
| Purchase Order Creation SOP | PROC-SOP-001 |
| Goods Receipt Procedure | WH-SOP-001 |
| Vendor Onboarding and Change Management SOP | PROC-SOP-003 |
| Employee Expense Reimbursement SOP | HR-EXP-002 |
| Fraud and BEC Incident Response Procedure | SEC-INC-001 |
| Financial Signing Authority Matrix | FIN-AUTH-001 |
| Month-End Accruals Procedure | FIN-SOP-003 |

---

## 12. Revision History

| Version | Date | Author | Changes |
|---|---|---|---|
| 1.0 | 2026-08-06 | Accounts Payable Department | Initial release |

---

*This document is subject to periodic review. The AP Manager is responsible for ensuring this SOP remains current and reflects any changes to systems, regulations, or organizational policy. All staff must be notified of updates within 5 business days of approval.*

*For questions or suggested amendments, contact the AP Manager or Finance Controller.*

---

**End of Document — AP-SOP-001 v1.0**
