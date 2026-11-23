# Lending decision audit pack (AL-Core)

**Jira:** ALG4-100 (story), ALG4-236 (contract and mocks), ALG4-237 (endpoint) · **Author:** Pavlo · **Status:** implemented

A bank underwriting officer downloads everything recorded about a **decided** loan application as one file, to share
or archive the decision: the application, the borrower, the status history, the lending decision, and how the AI
committee reached its verdict (decision, each model's vote, verified figures, reasoning steps). The pack is not
stored: it is built from Firestore on every download, so it always shows the current record.

## Contract

```http
GET /api/v1/loan-applications/{loanApplicationId}/audit-pack?format=pdf
Authorization: Bearer <Firebase ID token of an underwriting_bank_officer>
```

| query    | values         | default | description          |
|----------|----------------|---------|----------------------|
| `format` | `pdf`, `csv`   | `pdf`   | File format to return |

**200 OK**: the file as an attachment.

| header                | value                                                                          |
|-----------------------|--------------------------------------------------------------------------------|
| `Content-Type`        | `application/pdf` or `text/csv; charset=utf-8`                                 |
| `Content-Disposition` | `attachment; filename="audit-pack-{loanApplicationId}.pdf"` (or `.csv`)        |
| `X-Audit-Pack-SHA256` | fingerprint of the record in the pack (64 hex characters), see *Integrity*     |
| `Cache-Control`       | `no-store` (the pack contains personal data)                                   |

| status | when                                                                              |
|--------|-----------------------------------------------------------------------------------|
| 401    | no or invalid token                                                               |
| 403    | the caller is not a bank officer, or not the officer assigned to the application  |
| 404    | the application does not exist                                                    |
| 409    | no lending decision yet (the pack exists only for approved or declined applications) |
| 422    | unknown `format`                                                                  |

Web client (ALG4-239/240): request the file with `fetch` and the bearer token, then save `response.blob()` under the
name from `Content-Disposition`; a plain link cannot send the token.

## What the pack contains

Both formats contain the same sections, in this order:

1. **Summary**: application ID, status, lending decision, who decided and when, AI decision, risk tier, approval chance
2. **Borrower**: name, email, phone, borrower ID, first-time buyer, broker and bank officer IDs
3. **Financials**: income, debt repayments, deposit, loan amount, term, loan-to-value
4. **Property**: county, address, type, floor area, bedrooms, bathrooms, BER, asking price, coordinates
5. **Status history**: every status change with time and author
6. **Lending decision**: outcome, reason, conditions, decided by, decided at
7. **AI committee assessment**: run, interest rate used, decision, reason, conditions, key risks
8. **Verified figures**: repayments, stressed DTI, LTI, valuation estimate, asking price vs estimate, AI LTV, risk tier,
   risk score, approval chance
9. **Committee votes**: each model's vote and reason
10. **Reasoning steps**: the agents' steps in order
11. **Integrity**: the fingerprint and how it is computed

If the AI committee was never asked, sections 7-10 are replaced by one line saying so.

### CSV

One row per value, columns `section,field,value`; UTF-8 with a BOM, so Excel shows `€` and accents correctly. Numbers
are plain (`300000`, `85.71`) and the unit is in the field name (`Loan amount (EUR)`, `Loan-to-value (%)`); times are
ISO 8601 in UTC; lists are joined with `; `. A table row (status history, votes, steps) is one CSV row: the first
column is the field, the other columns are `name: value` pairs.

```csv
section,field,value
Financials,Loan amount (EUR),300000
Status history,1,"Status: Applied; Changed at: 2026-11-02T09:00:00Z; Changed by: demo-borrower"
Committee votes,groq,"Vote: Conditionally Approve; Reason: High LTV, affordable"
```

### PDF

A4, one section per block, values formatted for reading (`€300,000`, `85.7%`, `02 Nov 2026, 09:00 UTC`); the
fingerprint and page number are in the footer of every page.

## Integrity

`X-Audit-Pack-SHA256` (and the *Integrity* section) is the SHA-256 of the canonical JSON (sorted keys, no spaces) of
the loan application document, its latest assessment and the reasoning steps. Who downloaded the pack and when are
not part of it, so the same record always gives the same fingerprint and any change gives a different one: two packs
with the same fingerprint describe exactly the same data. When the audit registry contract (ALG4-97) is deployed, this
is the value to anchor on chain.

## Mocks

[`mocks/audit-pack-sample.pdf`](mocks/audit-pack-sample.pdf) and [`mocks/audit-pack-sample.csv`](mocks/audit-pack-sample.csv)
are packs of a made-up approved application, produced by the real renderers. Regenerate them after changing the pack:

```bash
cd api
uv run python -m src.scripts.generate_audit_pack_samples
```

## Code

`api/src/audit_packs/`: `service.py` (access rules, collecting the data), `models.py` (pack and fingerprint),
`content.py` (sections, format independent), `rendering.py` (CSV and PDF with ReportLab), `v1/router.py`.
Tests: `api/tests/audit_packs/`.
