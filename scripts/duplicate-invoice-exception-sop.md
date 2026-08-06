# Standard Operating Procedure
# Duplicate Invoice Identification and Exception Handling

| Field | Details |
|---|---|
| **SOP ID** | AP-SOP-002 |
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
5. [Duplicate Invoice Risk Overview](#5-duplicate-invoice-risk-overview)
6. [Duplicate Detection Methods](#6-duplicate-detection-methods)
7. [Duplicate Invoice Scenarios and Resolution Procedures](#7-duplicate-invoice-scenarios-and-resolution-procedures)
   - 7.1 [Exact Duplicate — Same Invoice Number, Same Vendor, Same Amount](#71-exact-duplicate--same-invoice-number-same-vendor-same-amount)
   - 7.2 [Near Duplicate — Same Amount, Different Invoice Number](#72-near-duplicate--same-amount-different-invoice-number)
   - 7.3 [Same Invoice Number, Different Amount](#73-same-invoice-number-different-amount)
   - 7.4 [Duplicate Across Multiple Submission Channels](#74-duplicate-across-multiple-submission-channels)
   - 7.5 [Vendor Resubmission After Non-Payment Complaint](#75-vendor-resubmission-after-non-payment-complaint)
   - 7.6 [Duplicate Due to ERP System Import Error](#76-duplicate-due-to-erp-system-import-error)
   - 7.7 [Duplicate Invoice from Vendor Subsidiary or Related Entity](#77-duplicate-invoice-from-vendor-subsidiary-or-related-entity)
   - 7.8 [Duplicate Detected After Payment Has Been Made](#78-duplicate-detected-after-payment-has-been-made)
   - 7.9 [Intentional Duplicate — Suspected Fraud](#79-intentional-duplicate--suspected-fraud)
   - 7.10 [Recurring / Periodic Invoice Misidentified as Duplicate](#710-recurring--periodic-invoice-misidentified-as-duplicate)
8. [Pre-Payment Duplicate Verification Checklist](#8-pre-payment-duplicate-verification-checklist)
9. [Escalation Matrix](#9-escalation-matrix)
10. [Recovery Procedures for Duplicate Payments Already Made](#10-recovery-procedures-for-duplicate-payments-already-made)
11. [Preventive Controls](#11-preventive-controls)
12. [Documentation and Record Keeping](#12-documentation-and-record-keeping)
13. [Key Performance Indicators](#13-key-performance-indicators)
14. [Related Documents and References](#14-related-documents-and-references)
15. [Revision History](#15-revision-history)

---

## 1. Purpose

This Standard Operating Procedure (SOP) establishes a structured, consistent process for identifying, investigating, and resolving potential duplicate invoices within the Accounts Payable function. It defines the controls, verification steps, and escalation paths required to prevent double payments to vendors, protect the organization from financial loss and fraud, and ensure the integrity of financial records.

---

## 2. Scope

This SOP applies to:

- All Accounts Payable (AP) staff responsible for invoice receipt, registration, and processing
- AP Managers and Finance Controllers responsible for exception approvals
- Procurement staff involved in PO and vendor management
- Internal Audit for monitoring and testing duplicate payment controls
- All vendor invoices processed through the organization's ERP system, regardless of value or payment method

This SOP does **not** apply to:
- Employee expense reimbursements (governed by HR-EXP-002)
- Payroll processing
- Intercompany transactions (governed by FIN-SOP-005)

---

## 3. Definitions

| Term | Definition |
|---|---|
| **Duplicate Invoice** | An invoice that has been submitted more than once for the same goods or services already covered by a previously received or paid invoice |
| **Exact Duplicate** | An invoice that is identical in vendor, invoice number, date, and amount to an invoice already in the system |
| **Near Duplicate** | An invoice that shares key attributes (vendor, amount, PO reference, line items) with an existing invoice but differs in one field such as invoice number or date |
| **Double Payment** | A situation in which the same liability is paid twice, resulting in an overpayment to a vendor |
| **Duplicate Detection** | The automated or manual process of identifying invoices that may represent the same underlying liability |
| **Fuzzy Matching** | A technique used to identify near-duplicate invoices by comparing key fields with allowance for minor differences |
| **Invoice Hold** | A status applied in the ERP system that prevents an invoice from being approved or paid pending investigation |
| **Debit Memo** | A document issued to a vendor requesting repayment or credit for an overpayment or duplicate payment |
| **Vendor Statement Reconciliation** | The process of comparing the organization's vendor ledger balance against the vendor's own statement of account |
| **BEC Fraud** | Business Email Compromise fraud, where an attacker impersonates a vendor or internal employee to redirect payments |
| **GR/IR Account** | Goods Receipt / Invoice Receipt clearing account used to track received-but-not-invoiced and invoiced-but-not-received liabilities |

---

## 4. Roles and Responsibilities

### 4.1 AP Clerk
- Register all incoming invoices in the ERP system promptly
- Run or review system duplicate alerts before approving any invoice
- Perform manual duplicate checks where system alerts are not conclusive
- Place suspected duplicates on hold immediately
- Contact vendors to clarify invoice status
- Escalate unresolved duplicates to the AP Manager within defined timeframes

### 4.2 AP Manager / Supervisor
- Review all duplicate exception cases escalated by AP Clerks
- Authorize invoice approval or rejection decisions above clerk authority
- Approve vendor credit note requests and debit memos
- Monitor duplicate payment KPIs and trends
- Review vendor resubmission patterns and initiate vendor conversations
- Approve recovery actions for confirmed duplicate payments

### 4.3 Finance Controller
- Approve write-offs for unrecoverable duplicate payments
- Authorize fraud escalations and investigations
- Review and sign off on monthly and quarterly duplicate payment reports
- Ensure adequacy of system controls and periodic audits

### 4.4 Internal Audit
- Conduct periodic (at least annual) duplicate payment audits
- Review ERP duplicate detection configuration
- Report findings and recommendations to Finance Controller and CFO
- Test the effectiveness of controls defined in this SOP

### 4.5 IT / ERP System Administrator
- Configure and maintain duplicate invoice detection rules in the ERP system
- Ensure system alerts are active and functioning correctly
- Investigate and resolve system-caused duplicate entries
- Provide audit logs upon request

### 4.6 Vendor / Supplier
- Submit invoices through the designated channel only
- Respond to AP duplicate queries within 5 business days
- Issue credit notes promptly for confirmed duplicate payments
- Maintain clear invoice numbering to avoid confusion

---

## 5. Duplicate Invoice Risk Overview

### 5.1 Why Duplicate Invoices Occur

Duplicate invoices arise from a combination of vendor behavior, process gaps, and system weaknesses:

```
SOURCES OF DUPLICATE INVOICES
                                                    
  VENDOR SIDE               INTERNAL SIDE           
  ──────────────            ──────────────────────── 
  • Resubmission after      • Multiple submission    
    delayed payment           channels (email, post, 
  • Billing system errors     portal, EDI)          
  • Subsidiary invoicing    • AP Clerk data entry   
    same PO                   error                 
  • Invoice numbering       • System import         
    resets                    duplication           
  • Fraudulent              • Scanning/OCR errors   
    resubmission            • Decentralized AP      
                              processing teams      
```

### 5.2 Financial and Operational Impact

| Risk | Impact |
|---|---|
| Double payment to vendor | Direct cash loss |
| Overstated expenses | Misstated financial statements |
| Tax overclaiming (VAT/GST) | Regulatory penalty risk |
| Fraud enablement | Reputational and legal risk |
| Vendor relationship strain | Disputes over credit recovery |
| Audit findings | Compliance and governance risk |

---

## 6. Duplicate Detection Methods

### 6.1 Automated ERP System Checks

The ERP system must be configured to flag invoices that match on any of the following field combinations:

| Check | Fields Compared | Action on Match |
|---|---|---|
| **Exact Duplicate** | Vendor ID + Invoice Number + Invoice Date + Amount | Hard block — invoice cannot be posted |
| **Same Invoice Number** | Vendor ID + Invoice Number | Warning alert — AP Clerk must confirm |
| **Same Amount + Vendor** | Vendor ID + Invoice Amount (within ±1%) + Invoice Date (within 30 days) | Warning alert — AP Clerk must investigate |
| **Same PO + Same Period** | PO Number + Invoice Period + Amount | Warning alert |
| **Same Bank Reference** | Payment reference + amount + date | Warning alert |

### 6.2 Manual Verification Steps

When automated checks produce an alert or where system checks may not cover all scenarios, AP Clerks must perform manual checks:

1. Search ERP by vendor name and invoice number for any existing entry
2. Search by invoice amount and vendor within a 90-day window
3. Review vendor payment history for recent payments of similar value
4. Check the vendor statement (if available) to confirm the invoice is not already cleared
5. Verify PO reference — confirm the PO line item has not already been fully invoiced

### 6.3 Vendor Statement Reconciliation

- Perform vendor statement reconciliations at least quarterly for all vendors with monthly invoice volumes > 10
- Reconcile all vendors with invoice value > $50,000/month monthly
- Use the reconciliation to identify any invoices paid by the organization but not reflected on the vendor statement, and vice versa

---

## 7. Duplicate Invoice Scenarios and Resolution Procedures

---

### 7.1 Exact Duplicate — Same Invoice Number, Same Vendor, Same Amount

#### 7.1.1 Description
An invoice is received that is identical in all key fields (vendor, invoice number, invoice date, amount, and PO reference) to an invoice already registered in the ERP system.

#### 7.1.2 Common Causes
- Vendor sent invoice via email and also via postal mail
- Vendor resubmitted after not receiving acknowledgement
- AP Clerk inadvertently entered the same invoice twice
- Automated invoice import processed the same file twice

#### 7.1.3 Resolution Steps

| Step | Action | Responsible | Timeframe |
|---|---|---|---|
| 1 | ERP system flags hard duplicate block; AP Clerk investigates alert | AP Clerk | Same day |
| 2 | Confirm the original invoice exists in the system and its payment status | AP Clerk | Day 1 |
| 3 | If original is **unpaid/pending**: reject the duplicate entry; continue processing original only | AP Clerk | Day 1 |
| 4 | If original is **already paid**: reject the duplicate; notify vendor that invoice is already settled; provide payment reference | AP Clerk | Day 1 |
| 5 | Document the duplicate instance in the exception log with reason for rejection | AP Clerk | Day 1 |
| 6 | If the duplicate arrived via a different channel (e.g., portal vs. email): notify vendor to use only the designated submission channel | AP Clerk | Day 1–2 |

---

### 7.2 Near Duplicate — Same Amount, Different Invoice Number

#### 7.2.1 Description
An invoice is received from the same vendor for the same (or very similar) amount within a short time window, but with a different invoice number. This may represent a legitimate second invoice or a disguised duplicate.

#### 7.2.2 Common Causes
- Vendor reissued invoice with a new number after claiming the original was lost
- Vendor billing system generated a new invoice number for the same transaction
- Legitimate second invoice for a separate but identically priced delivery
- Fraudulent resubmission with altered invoice number to evade system detection

#### 7.2.3 Resolution Steps

| Step | Action | Responsible | Timeframe |
|---|---|---|---|
| 1 | ERP system raises a warning alert; AP Clerk places new invoice on hold | AP Clerk | Day 1 |
| 2 | Compare all line items, PO references, GR references, and delivery dates of both invoices | AP Clerk | Day 1 |
| 3 | If line items and PO/GR references are identical: treat as duplicate; contact vendor to confirm | AP Clerk | Day 1–2 |
| 4 | If vendor confirms it is a reissue of the original: reject the newer invoice; retain the original | AP Clerk | Day 2–3 |
| 5 | If vendor claims both are legitimate: request supporting evidence (two separate delivery notes, GRs) | AP Clerk | Day 2–3 |
| 6 | If two valid GRs confirm two separate deliveries: approve both invoices; ensure each matches a distinct GR | AP Manager | Day 3–5 |
| 7 | If vendor cannot provide supporting evidence: reject the second invoice; escalate to AP Manager if vendor disputes | AP Manager | Day 5 |

---

### 7.3 Same Invoice Number, Different Amount

#### 7.3.1 Description
An invoice is received with the same invoice number as an existing entry but with a different amount. This may indicate a corrected/revised invoice or an attempt to extract a higher payment.

#### 7.3.2 Common Causes
- Vendor issued a revised invoice to correct an error on the original
- Vendor added additional charges (freight, tax) not on the original
- Data entry error on the original invoice posting
- Fraudulent alteration of invoice amount

#### 7.3.3 Resolution Steps

| Step | Action | Responsible | Timeframe |
|---|---|---|---|
| 1 | ERP flags same invoice number with amount mismatch; hold both versions | AP Clerk | Day 1 |
| 2 | Contact vendor to confirm which version is correct | AP Clerk | Day 1–2 |
| 3 | If vendor confirms it is a **corrected invoice**: cancel the original entry; post the revised invoice; complete three-way match | AP Clerk | Day 2–3 |
| 4 | If vendor confirms original is correct: reject the second entry; process original | AP Clerk | Day 2–3 |
| 5 | If the amount difference is higher and vendor cannot explain: escalate to AP Manager; do not pay either version until resolved | AP Manager | Day 3–5 |
| 6 | If fraud is suspected: escalate immediately to Finance Controller and IT Security | AP Manager | Immediately |

---

### 7.4 Duplicate Across Multiple Submission Channels

#### 7.4.1 Description
The same invoice is received through more than one submission channel simultaneously or within a short period (e.g., email and vendor portal, email and post, EDI and email).

#### 7.4.2 Common Causes
- Vendor is uncertain which channel to use and submits via multiple routes
- Vendor's accounts receivable team submits via email while an automated system also sends via EDI
- Internal staff forward a vendor email to AP creating a second copy

#### 7.4.3 Resolution Steps

| Step | Action | Responsible | Timeframe |
|---|---|---|---|
| 1 | On receipt of invoice via any secondary channel, check ERP for an existing entry before registering | AP Clerk | Day 1 |
| 2 | If duplicate found: register only one instance; attach all received copies to the single ERP entry for audit trail | AP Clerk | Day 1 |
| 3 | Notify vendor in writing of the approved submission channel; request they cease using alternative channels for this invoice | AP Clerk | Day 1–2 |
| 4 | Update vendor communication preferences in vendor master record | AP Clerk / AP Manager | Day 2–3 |
| 5 | If the same vendor repeatedly submits via multiple channels: escalate to Procurement for formal vendor communication | AP Manager / Procurement | Ongoing |

---

### 7.5 Vendor Resubmission After Non-Payment Complaint

#### 7.5.1 Description
A vendor contacts AP to report non-payment of an invoice and resubmits it. The original invoice may or may not exist in the system, and may or may not have been paid.

#### 7.5.2 Common Causes
- Genuine non-receipt of original invoice by AP
- Original invoice lost in spam filter or misdirected
- Invoice posted but payment delayed beyond agreed terms
- Invoice paid but to wrong bank account (possible fraud)
- Vendor's AR records show outstanding balance due to reconciliation lag

#### 7.5.3 Resolution Steps

| Step | Action | Responsible | Timeframe |
|---|---|---|---|
| 1 | Search ERP for the original invoice by vendor, invoice number, and amount | AP Clerk | Day 1 |
| 2 | **If original invoice found and PAID**: provide vendor with payment date, amount, and bank reference; request vendor to reconcile their records | AP Clerk | Day 1 |
| 3 | **If original invoice found and UNPAID**: investigate why payment was delayed; do not register resubmission; process the original | AP Clerk / AP Manager | Day 1–3 |
| 4 | **If original invoice NOT found in system**: register the resubmitted invoice; confirm GR and PO match; process for payment | AP Clerk | Day 1–3 |
| 5 | Before registering any resubmission: verify vendor bank details using contact details already on file — do NOT use bank details provided in the resubmitted invoice without independent verification | AP Clerk | Day 1 |
| 6 | If vendor insists payment was not received but ERP shows paid: involve Finance to trace the payment through the bank | AP Manager / Finance | Day 3–5 |
| 7 | If payment was sent to a wrong account: notify Finance Controller and IT Security immediately; initiate bank recall if possible | Finance Controller | Immediately |

---

### 7.6 Duplicate Due to ERP System Import Error

#### 7.6.1 Description
The ERP system or an automated invoice processing tool (OCR, EDI, AP automation software) imports the same invoice twice due to a technical error, creating two entries in the system.

#### 7.6.2 Common Causes
- Batch import job run twice due to a processing failure and retry
- OCR tool scanned the same document from two different inboxes
- EDI file retransmitted by vendor's system after timeout
- AP automation tool failed to mark invoice as processed before retry

#### 7.6.3 Resolution Steps

| Step | Action | Responsible | Timeframe |
|---|---|---|---|
| 1 | AP Clerk identifies two system entries for the same invoice | AP Clerk | Day 1 |
| 2 | Confirm both entries are system-generated (same timestamp range, identical data) | AP Clerk / IT | Day 1 |
| 3 | Cancel/void the duplicate system entry; retain the first registered entry | AP Clerk | Day 1 |
| 4 | Notify IT/ERP Admin of the import error for root cause investigation | AP Clerk | Day 1 |
| 5 | IT Admin reviews the import job logs and applies fix to prevent recurrence | IT / ERP Admin | Day 1–5 |
| 6 | Document the system error and resolution in the exception log | AP Clerk | Day 1 |
| 7 | If the same system error recurs: escalate to Finance Controller and IT Management | AP Manager | Ongoing |

---

### 7.7 Duplicate Invoice from Vendor Subsidiary or Related Entity

#### 7.7.1 Description
An invoice is received from a vendor's subsidiary, parent company, or related entity for the same goods or services already invoiced by the primary vendor entity.

#### 7.7.2 Common Causes
- Vendor restructured and invoicing entity changed mid-contract
- Consolidated invoice from parent company overlaps with subsidiary invoice
- Different vendor master records exist for related entities; system does not link them
- Vendor billing mistake — same transaction invoiced by two entities

#### 7.7.3 Resolution Steps

| Step | Action | Responsible | Timeframe |
|---|---|---|---|
| 1 | Identify that the invoicing entity differs from the PO vendor entity | AP Clerk | Day 1 |
| 2 | Check vendor master for known related entities linked to the PO vendor | AP Clerk | Day 1 |
| 3 | Search for existing invoices covering the same PO, period, and goods/services across all related vendor records | AP Clerk | Day 1–2 |
| 4 | If duplicate confirmed across entities: contact vendor to determine which entity should be the correct billing party | AP Clerk / Procurement | Day 2–3 |
| 5 | Pay only one invoice; reject or request cancellation of the duplicate from the other entity | AP Manager | Day 3–5 |
| 6 | Update vendor master to flag related entities and prevent future duplicate risk | AP Manager / IT | Day 5 |
| 7 | Notify Procurement to ensure future POs specify the correct legal invoicing entity | Procurement | Ongoing |

---

### 7.8 Duplicate Detected After Payment Has Been Made

#### 7.8.1 Description
A duplicate payment is identified after both invoices have already been paid. The vendor has received payment twice for the same goods or services.

#### 7.8.2 Common Causes
- Duplicate not caught by system or manual checks before payment
- Payment made in two different AP processing cycles
- Manual payment processed outside of normal ERP workflow
- Vendor statement reconciliation reveals the overpayment

#### 7.8.3 Resolution Steps

| Step | Action | Responsible | Timeframe |
|---|---|---|---|
| 1 | Confirm the duplicate payment by reviewing both payment records in ERP and bank statements | AP Manager | Day 1 |
| 2 | Calculate the exact overpayment amount including any applicable taxes | AP Manager | Day 1 |
| 3 | Contact vendor immediately; provide evidence of both payments and request credit note or refund | AP Manager | Day 1–2 |
| 4 | Agree recovery method with vendor: cash refund, credit note applied to next invoice, or offset against outstanding balance | AP Manager / Procurement | Day 2–5 |
| 5 | If vendor agrees to credit note: apply to the next invoice in ERP; close the overpayment | AP Clerk | On receipt |
| 6 | If vendor agrees to cash refund: provide bank details; ensure refund is posted to correct GL | AP Clerk / Finance | On receipt |
| 7 | If vendor does not respond within 10 business days: escalate to AP Manager for formal written demand | AP Manager | Day 10 |
| 8 | If vendor refuses to refund after 20 business days: escalate to Finance Controller; consider legal/commercial recovery options | Finance Controller | Day 20 |
| 9 | Root cause analysis: identify how the duplicate payment passed all controls; implement corrective action | AP Manager / Finance Controller | Within 30 days |
| 10 | Report overpayment and recovery status to Finance Controller in monthly exception report | AP Manager | Monthly |

---

### 7.9 Intentional Duplicate — Suspected Fraud

#### 7.9.1 Description
Evidence suggests that a duplicate invoice was submitted deliberately, either by a vendor or an internal employee, with the intent to cause a double payment for financial gain.

#### 7.9.2 Indicators of Potential Fraud
- Duplicate invoices with subtly altered details (slightly different amounts, dates, or invoice numbers)
- New or recently changed vendor bank details on the duplicate invoice
- Resubmission shortly before a payment run with urgency pressure applied
- Duplicate submitted to a different AP contact than the original
- Pattern of duplicates from the same vendor over multiple periods
- Internal employee approving their own duplicate entries

#### 7.9.3 Resolution Steps

| Step | Action | Responsible | Timeframe |
|---|---|---|---|
| 1 | Do NOT contact the vendor or the employee suspect — preserve the element of surprise | AP Manager | Immediately |
| 2 | Place invoice on hold silently; do not reject or approve | AP Manager | Immediately |
| 3 | Escalate to Finance Controller and Head of Internal Audit immediately | AP Manager | Same day |
| 4 | Finance Controller notifies Legal, HR (if internal employee), and IT Security | Finance Controller | Same day |
| 5 | IT Security preserves all relevant system logs, email records, and access logs | IT Security | Same day |
| 6 | Internal Audit conducts preliminary investigation; reviews payment history for similar patterns | Internal Audit | Day 1–5 |
| 7 | If external vendor fraud confirmed: suspend vendor; notify legal counsel; consider police report | Finance Controller / Legal | Day 5+ |
| 8 | If internal fraud confirmed: follow HR disciplinary and legal process; notify external authorities if required | Finance Controller / HR / Legal | Day 5+ |
| 9 | Do not release any payment until fraud investigation is complete | Finance Controller | During investigation |
| 10 | Document all findings; conduct full controls review to identify gaps | Internal Audit | Post-investigation |

> **Critical:** Never confront a suspected internal fraudster or alert a suspected fraudulent vendor before escalating to Finance Controller, Internal Audit, and Legal. Premature disclosure may allow evidence to be destroyed.

---

### 7.10 Recurring / Periodic Invoice Misidentified as Duplicate

#### 7.10.1 Description
A legitimate recurring invoice (e.g., monthly rent, subscription, retainer fee) is incorrectly flagged as a duplicate because it shares the same vendor, similar amounts, and a similar reference as the previous month's invoice.

#### 7.10.2 Common Causes
- Vendor uses the same invoice number format with only a period reference changing
- ERP duplicate detection window too wide, capturing prior period invoices
- Blanket PO with recurring invoicing not properly configured in the system
- AP Clerk unfamiliar with the recurring invoice pattern

#### 7.10.3 Resolution Steps

| Step | Action | Responsible | Timeframe |
|---|---|---|---|
| 1 | Review system duplicate alert; check whether the invoices relate to different billing periods | AP Clerk | Day 1 |
| 2 | Confirm the vendor contract or blanket PO permits recurring invoicing at this frequency and amount | AP Clerk | Day 1 |
| 3 | Verify the new invoice covers a different period than the previously paid invoice | AP Clerk | Day 1 |
| 4 | If confirmed as a legitimate new period invoice: clear the duplicate flag; approve and process | AP Clerk | Day 1–2 |
| 5 | Tag the vendor and invoice type in ERP as "recurring" to reduce future false-positive alerts | AP Clerk / IT Admin | Day 2–3 |
| 6 | If the vendor's invoice numbering makes period identification unclear: request the vendor to include the billing period explicitly in invoice number or description | AP Clerk | Day 2–3 |
| 7 | Review ERP duplicate detection window configuration for recurring vendor categories | IT / ERP Admin | Quarterly |

---

## 8. Pre-Payment Duplicate Verification Checklist

Every invoice must pass the following checklist before payment is authorized. AP Clerks must complete this checklist and attach it (digitally) to the invoice record in ERP.

### 8.1 System Checks (Automated)

- [ ] ERP duplicate detection run — no hard block alerts outstanding
- [ ] No warning alerts unresolved from same-amount / same-vendor check
- [ ] Invoice number does not match any existing open or paid invoice for this vendor
- [ ] PO line item has not been fully invoiced already (cumulative invoiced quantity ≤ GR quantity)

### 8.2 Manual Checks (AP Clerk)

- [ ] Searched ERP by vendor + invoice number — no existing entry found
- [ ] Searched ERP by vendor + amount within last 90 days — no unresolved near-duplicate found
- [ ] Confirmed invoice references a valid, open PO with remaining uninvoiced balance
- [ ] Confirmed a Goods Receipt exists for the invoiced quantity and goods
- [ ] Verified vendor details (name, ID) match the PO vendor — no mismatch
- [ ] Verified vendor bank account has not changed since last payment (or change is verified per vendor master change process)
- [ ] Invoice submission channel is the vendor's designated channel
- [ ] For recurring invoices: confirmed billing period is different from the last paid invoice

### 8.3 Sign-Off

| Role | Signature / ERP Approval | Date |
|---|---|---|
| AP Clerk | | |
| AP Manager (if exception) | | |

---

## 9. Escalation Matrix

| Scenario | Level 1 — AP Clerk | Level 2 — AP Manager | Level 3 — Finance Controller |
|---|---|---|---|
| Exact duplicate identified | Reject duplicate; notify vendor | Review if dispute arises | N/A |
| Near duplicate — vendor confirms legitimate | Approve with documentation | Required sign-off | N/A |
| Near duplicate — unresolved after 3 days | Escalate | Investigate and resolve | If unresolved after 5 days |
| Same invoice number, different amount | Hold; contact vendor | Approve corrected invoice | If fraud suspected |
| Multi-channel duplicate | Reject duplicate; notify vendor | If vendor escalates | N/A |
| Vendor resubmission — payment tracing required | Initiate trace | Manage bank trace | If payment sent to wrong account |
| System import duplicate | Cancel duplicate; notify IT | If systemic recurring issue | N/A |
| Post-payment duplicate discovered | Report immediately | Manage recovery | Approve write-off if unrecoverable |
| Suspected fraud | Do NOT act; escalate | Escalate to Finance Controller + Audit | Lead investigation; engage Legal |

### 9.1 Escalation Timeframes

| Escalation Level | Acknowledgement | Resolution Target |
|---|---|---|
| AP Clerk → AP Manager | 1 business day | 3 business days |
| AP Manager → Finance Controller | 1 business day | 5 business days |
| Fraud escalation (any level) | Same day | Ongoing investigation |

---

## 10. Recovery Procedures for Duplicate Payments Already Made

### 10.1 Recovery Workflow

```
DUPLICATE PAYMENT CONFIRMED
           |
           v
    Calculate overpayment
    amount + tax impact
           |
           v
    Contact vendor within
    2 business days
           |
    ┌──────┴──────┐
    |             |
    v             v
Vendor         Vendor
agrees         disputes
    |             |
    v             v
Choose         Escalate to
recovery       AP Manager /
method         Procurement
    |
    ├── Credit Note → Apply to next invoice
    ├── Cash Refund → Post to GL on receipt
    └── Offset → Deduct from next payment
```

### 10.2 Recovery Method Options

| Method | When to Use | Steps |
|---|---|---|
| **Credit Note** | Vendor has upcoming invoices | Request credit note; apply in ERP against next invoice; ensure credit note matches overpayment exactly |
| **Cash Refund** | No upcoming invoices expected; large amount | Provide organization bank details to vendor; post refund receipt in ERP; reconcile GL |
| **Payment Offset** | Ongoing vendor relationship; small amounts | Deduct from next payment run; document offset in ERP; notify vendor in advance |
| **Write-Off** | Amount immaterial; vendor uncontactable | Finance Controller approval required; post to bad debt / AP write-off GL |

### 10.3 Aging and Escalation of Recovery

| Days Since Discovery | Action |
|---|---|
| Day 1–2 | Contact vendor; agree recovery method |
| Day 10 | Follow-up if no response; formal written demand |
| Day 20 | Final demand letter; Finance Controller engaged |
| Day 30 | Legal / commercial recovery options assessed |
| Day 60+ | Write-off assessed if recovery deemed uneconomic (Finance Controller approval) |

---

## 11. Preventive Controls

### 11.1 System Controls

| Control | Description | Owner |
|---|---|---|
| **ERP Duplicate Invoice Block** | Hard block on exact duplicates (vendor + invoice number + amount) | IT / ERP Admin |
| **Fuzzy Match Warning** | Soft alert for near-duplicates based on amount and vendor within 90-day window | IT / ERP Admin |
| **Mandatory PO Reference** | Invoices cannot be posted without a valid PO reference | IT / ERP Admin |
| **Cumulative Invoice Quantity Check** | System prevents invoicing beyond GR quantity | IT / ERP Admin |
| **Segregation of Duties** | Invoice entry and payment approval must be performed by different users | IT / ERP Admin |
| **Vendor Bank Change Workflow** | Bank detail changes require dual approval and callback verification | IT / AP Manager |
| **Invoice Submission Portal** | Single designated portal reduces multi-channel duplicates | IT / Procurement |

### 11.2 Process Controls

| Control | Description | Frequency |
|---|---|---|
| **Vendor Statement Reconciliation** | Compare vendor ledger to vendor statement to surface unrecognized payments | Monthly (high-value); Quarterly (all) |
| **AP Aging Review** | Review invoices on hold to ensure no legitimate invoices are stalled | Weekly |
| **Duplicate Payment Audit** | Internal Audit tests a sample of payments for duplicates | Annually (minimum) |
| **No-PO Invoice Report** | Identify invoices processed without PO references — a common duplicate risk factor | Monthly |
| **Vendor Exception Scorecard** | Track vendors with repeated duplicate submissions for Procurement action | Monthly |
| **New Vendor Verification** | All new vendors verified before first payment; bank details confirmed via callback | Per onboarding |

### 11.3 Training Controls

| Control | Description | Frequency |
|---|---|---|
| **AP Staff Training** | All AP staff trained on duplicate detection procedures and fraud awareness | On onboarding + annually |
| **Fraud Awareness Training** | BEC fraud, social engineering, and vendor impersonation awareness | Annually |
| **SOP Refresher** | Review and acknowledge this SOP | Annually or on update |

---

## 12. Documentation and Record Keeping

### 12.1 Minimum Documentation per Exception

Every duplicate invoice exception must be logged in the ERP exception tracking system with:

- [ ] Vendor name and ID
- [ ] Original invoice number, date, and amount
- [ ] Duplicate invoice number, date, and amount
- [ ] Submission channels for each instance
- [ ] Date exception identified and by whom
- [ ] Duplicate type (exact, near, post-payment, fraud suspected, etc.)
- [ ] Actions taken at each step with dates and names
- [ ] Final outcome (rejected, paid, recovered, written off, fraud escalated)
- [ ] Supporting attachments (both invoice copies, vendor correspondence, bank records)

### 12.2 Retention Policy

| Document | Retention Period |
|---|---|
| Invoice records and exception logs | 7 years |
| Vendor correspondence | 7 years |
| Payment and bank records | 7 years |
| Fraud investigation records | 10 years (or as required by legal counsel) |
| Audit reports | 7 years |

### 12.3 Reporting Schedule

| Report | Frequency | Audience |
|---|---|---|
| Duplicate Invoice Exception Log | Weekly | AP Manager |
| Duplicate Payment Summary (volume + value) | Monthly | Finance Controller |
| Recovery Status Report | Monthly | Finance Controller |
| Vendor Duplicate Scorecard | Monthly | Procurement / AP Manager |
| Fraud Incident Report | As required | Finance Controller / CFO / Legal |
| Annual Duplicate Payment Audit Results | Annually | CFO / Board Audit Committee |

---

## 13. Key Performance Indicators

| KPI | Target | Measurement Period |
|---|---|---|
| Duplicate Invoice Rate (% of total invoices) | < 0.5% | Monthly |
| Duplicate Payment Rate (% of total payments) | < 0.1% | Monthly |
| Duplicate Detection Rate (caught before payment) | > 99% | Monthly |
| Average Resolution Time — Duplicate Exception | ≤ 3 business days | Monthly |
| Post-Payment Recovery Rate | > 95% within 60 days | Quarterly |
| Vendor Statement Reconciliation Coverage | 100% of vendors > $50K/month | Monthly |
| False Positive Rate (legitimate invoices incorrectly flagged) | < 2% of flagged invoices | Monthly |
| Fraud Escalations Resolved Within SLA | 100% same-day escalation | Per occurrence |

---

## 14. Related Documents and References

| Document | Reference |
|---|---|
| Three-Way Match Exception Handling SOP | AP-SOP-001 |
| Accounts Payable Policy | AP-POL-001 |
| Vendor Master Management SOP | AP-SOP-003 |
| Vendor Onboarding and Change Management SOP | PROC-SOP-003 |
| Fraud and BEC Incident Response Procedure | SEC-INC-001 |
| Financial Signing Authority Matrix | FIN-AUTH-001 |
| Internal Audit — AP Duplicate Payment Test Plan | IA-TEST-004 |
| Employee Expense Reimbursement SOP | HR-EXP-002 |

---

## 15. Revision History

| Version | Date | Author | Changes |
|---|---|---|---|
| 1.0 | 2026-08-06 | Accounts Payable Department | Initial release |

---

*This document is subject to periodic review. The AP Manager is responsible for ensuring this SOP remains current and reflects any changes to systems, regulations, or organizational policy. All staff must be notified of updates within 5 business days of approval.*

*For questions or suggested amendments, contact the AP Manager or Finance Controller.*

---

**End of Document — AP-SOP-002 v1.0**
