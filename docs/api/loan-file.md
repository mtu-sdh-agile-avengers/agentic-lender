# Loan file (AL-Core)

**Jira:** ALG4-91 (story), ALG4-255 (endpoint) · **Author:** Pavlo · **Status:** implemented

The loan file page shows the full dossier of one application in one request.

```http
GET /api/v1/loan-applications/{loanApplicationId}
Authorization: Bearer <Firebase ID token>
```

**200 OK**: every field of the loan application (as before: financials, `propertySpec`, `status`, `statusHistory`,
`decision`, ...) plus:

| field              | description                                                                                         |
|--------------------|-----------------------------------------------------------------------------------------------------|
| `borrower`         | `uid`, `fullName`, `email`, `phone` from the borrower's profile (name from the application if there is no profile) |
| `documents`        | attached files, oldest upload first: `documentId`, `name`, `category`, `contentType`, `sizeBytes`, `uploadedById`, `uploadedAt` |
| `latestAssessment` | summary of the latest AI committee run, `null` if it was never asked: `assessmentId`, `status`, `decision`, `reason`, `automatic`, `riskTier`, `riskScore`, `approvalChancePercent`, `dtiPercent`, `ltiMultiple`, `ltvPercent`, `valuationEstimate`, `overvalued`, `error`, `createdAt`, `finishedAt` |

The full reasoning (votes, steps, all figures) stays at `GET .../assessments/latest`.

| status | when                                                                                                       |
|--------|------------------------------------------------------------------------------------------------------------|
| 403    | the application is not one of the caller's: a broker sees referred clients (and unclaimed applications, so they can be claimed), a bank officer their portfolio (assigned applications), a borrower their own |
| 404    | the application does not exist                                                                             |

Code: `LoanApplicationService.get_file` and `LoanFileResponse` in `api/src/loan_applications/`; tests in
`api/tests/loan_files/`.
