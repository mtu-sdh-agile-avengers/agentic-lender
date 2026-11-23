# Data model design

This document describes **data model** used, i.e.: **which** data is saved on the database by Agentic Lender, **how** it is structured, and **why** it designed in such way.

> [!TIP]
> This file is used as a reference for all API contracts (generated `openapi.yaml`). You can get familiar with Pydantic
> schemas (`./schemas`), models (`/models`) and routes (`./router`) inside of the API source code if you want more details.

<details>
<summary>Table of contents (click to show)</summary>

- [Data model design](#data-model-design)
  - [Initial reasoning and conventions](#initial-reasoning-and-conventions)
    - [Ground rules](#ground-rules)
    - [How to read the field tables](#how-to-read-the-field-tables)
  - [Structure of collections](#structure-of-collections)
  - [Each collection in details](#each-collection-in-details)
    - [users](#users)
    - [loan_applications](#loan_applications)
      - [property_spec](#property_spec)
      - [documents](#documents)
      - [assessments](#assessments)
        - [collateral_valuation](#collateral_valuation)
        - [agent_steps](#agent_steps)
    - [support_tickets](#support_tickets)
    - [reviews](#reviews)
    - [conversations](#conversations)
      - [messages](#messages)
    - [stress_tests](#stress_tests)
    - [payments](#payments)
</details>

## Initial reasoning and conventions

BaaS (Backend as a Service), i.e. Firebase platform, is used for the backend of this project. It offers NoSQL (aggregate-oriented) database management, authentication and authorization, and usage analytics features, which make the development process considerably easier.

In the context of the data model (that is, database design) Firebase provides Cloud Firestore and/or Realtime database, both of them are NoSQL document-oriented database (consisting of collections and documents), which are highly scalable and schemaless.

Consequently, what has been said above means that an aggregate data model needs to be developed.

### Ground rules

There are following rules, which are strictly adhered:

- **read / write access**: Only the AL-Core subsystem has write access (through Firebase Admin SDK) to the database; all others (web and mobile clients, AI engine) have read-only access (through Firebase Client SDK), described by Firestore security rules (`.\api\src\firebase\firestore.rules`). However, it is assumed that they will use the AL-Core API for both reading and writing, rather than accessing the database directly.

- **data sources**:
  - **Firebase Auth** -> end-users credentials, custom claims (i.e., role).
  - **Etherum blockchain** -> minted loan notes and audit hashes; Firestore keeps pointers to them (transaction hash, token ID).
  - **Stripe / PayPal sandbox** -> payment state; Firestore mirrors it from webhooks.
  - **Cloud Firestore** -> all other data relevant to the users.  

- **naming**: Collections and fields are named with plural in snake_case.

- **documents IDs**: For `users` Firebase Auth uid is used, Firestore auto ID for every other collection.

### How to read the field tables

Each collection described with a separate row for each field containing following columns:
field, type, req, source, description.

**field**: Firestore document field name (must be snake_case).

**type**: type of the field value used in Pydantic schemas and Firestore.

| type                          | meaning                                | in Pydantic           | in Firestore                     |
|-------------------------------|----------------------------------------|-----------------------|----------------------------------|
| str, int, float, bool         | primitive values                       | built-in types        | string, integer, double, boolean |
| datetime                      | UTC timestamp (i.e., since epoch)      | datetime              | timestamp                        |
| T[]                           | list of elements with same type        | list[T]               | array                            |
| dict                          | associative array (i.e., hash table)   | nested Pydantic model | map                              |
| PascalCase name               | enumeration                            | Enum or StrEnum       | integer/float or string          |

**req**: if the value is present or None / null.

| req | meaning                                         |
|-----|-------------------------------------------------|
| x   | required: always present, never null            |
| ?   | nullable: always present, null until known      |
| -   | optional: the field may be absent               |

**source**: who produces the value (AL-Core always performs the write).

| source | meaning                                                           |
|--------|-------------------------------------------------------------------|
| auth   | taken from the claims of verified Firebase ID token               |
| client | entered by the end user (through AL-Mobile or AL-Web)             |
| core   | generated by REST API (i.e, AL-Core)                              |
| ai     | produced by multi-agent comittet and ML model (i.e. AL-AI Engine) |
| bchain | taken from a blockchain transaction receipt                       |
| psp    | taken from the Stripe / PayPal webhook                            |

## Structure of collections

```text
users/{uid}

loan_applications/{loan_application_id}
|
|- property_spec (dictionary, not subcollection)
|
|- documents/{document_id}
|
|- assessments/{assessment_id}
    |
    |- affordability (dictionary, not subcollection)
    |
    |- collateral_valuation (dictionary, not subcollection)
    |
    |- agent_steps/{agent_step_id}

support_tickets/{support_ticket_id}

reviews/{review_id}

conversations/{conversation_id}
|
|- messages/{message_id}

stress_tests/{stress_test_id}
|
|- results (array of dictionaries, not subcollection)

payments/{payment_id}
```

<div align="center"><b>ERD (Entity Relationship Diagram)</b> will appear as follows (or use an <a src="https://mermaid.ai/app/projects/d17be33c-5719-4bbe-b184-f3eb946b4b2c/diagrams/67640134-c32d-4d2e-b47e-b1f394bf0619/share/invite/eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJkb2N1bWVudElEIjoiNjc2NDAxMzQtYzMyZC00ZDJlLWI0N2UtYjFmMzk0YmYwNjE5IiwiYWNjZXNzIjoiVmlldyIsInB1cnBvc2UiOiJzaGFyZS1pbnZpdGUiLCJpYXQiOjE3OTQ4NzkwMDIsImV4cCI6MTc5NzQ3MTAwMn0.FzJIRAU04pJ32xlyg5U0lDVKryaB5uvnySOrsaaTTd4?entryPoint=share-modal">online version</a>):</div>

<span></span>


```mermaid
classDiagram
  class users {
    <<collection>>
    uid: str 
    role: Role
  }

  class loan_applications {
    <<collection>>
    loan_application_id: str
    borrower_id: str
    broker_id: str | None
    bank_officer_id: str | None
    assessment_id: str | None
  }
  
  class property_spec {
    <<dict>>
  }
  
  class status_history {
      <<arrayOfDict>>
  }
  
  class underwriting_decision {
      <<dict>>
  }

  class documents {
    <<subcollection>>
    document_id: str
  }

  class assessments {
    <<subcollection>>
    assessment_id: str
  }
  class affordability {
      <<dict>>
  }
  class collateral_valuation {
      <<dict>>
  }
  class ai_decision {
      <<dict>>
  }
  class agent_steps {
    <<subcollection>>
    agent_step_id: str
  }

  class support_tickets {
    <<collection>>
    support_ticket_id: str
    user_id: str
    loan_application_id: str | None
  }

  class reviews {
    <<collection>>
    review_id: str
    user_id: str
  }
  
  class conversations {
    <<collection>>
    conversation_id: str
    loan_application_id: str
    participant_ids: str[]
  }

  class messages {
    <<subcollection>>
    message_id: str
    sender_id: str
  }
  
  class stress_tests {
    <<collection>>
    stress_test_id: str
    user_id: str
    loan_application_ids: str[] | None
  }
  
  class results {
    <<dict>>
    loan_application_id: str
  }
  
  class payments {
    <<collection>>
    payment_id: str
    user_id: str
    loan_application_id: str
  }

  loan_applications "0..*" --> "1..1" users : borrower_id
  loan_applications "0..*" --> "0..1" users : broker_id
  loan_applications "0..*" --> "0..1" users : bank_officer_id
  loan_applications "1..1" *-- "1..1" property_spec : property_spec
  loan_applications "1..1" *-- "1..1" status_history : status_history
  loan_applications "1..1" *-- "0..1" underwriting_decision : decision
  loan_applications "1..1" *-- "0..*" documents
  loan_applications "1..1" *-- "0..*" assessments
  loan_applications "0..1" --> "0..1" assessments : assessment_id (latest)

  assessments "1..1" *-- "0..1" affordability : affordability
  assessments "1..1" *-- "0..1" collateral_valuation : collateral
  assessments "1..1" *-- "0..1" ai_decision : decision
  assessments "1..1" *-- "0..*" agent_steps

  support_tickets "0..*" --> "1..1" users : user_id
  support_tickets "0..*" --> "0..1" loan_applications : loan_application_id

  reviews "0..*" --> "1..1" users : user_id

  conversations "1..1" *-- "0..*" messages
  conversations "0..*" --> "1..1" loan_applications : loan_application_id
  conversations "0..*" --> "2..2" users : participant_ids
  messages "0..*" --> "1..1" users : sender_id

  stress_tests "0..*" --> "1..1" users : user_id
  stress_tests "0..*" --> "0..*" loan_applications : loan_application_ids
  stress_tests "1..1" *-- "0..*" results : results
  results "0..*" --> "1..1" loan_applications : loan_application_id

  payments "0..*" --> "1..1" users : user_id
  payments "0..*" --> "1..1" loan_applications : loan_application_id
```

## Each collection in details

### users

One profile per Firebase Auth account (made using Firebase Client SDK); created by `POST /api/v1/users/me` request after
first sign-in.

| field          | type           | req   | source    | description                                                                                      |
|----------------|----------------|-------|-----------|--------------------------------------------------------------------------------------------------|
| uid            | str            | x     | auth      | user uid; must be a string between 1-128 characters long inclusive                               |
| email          | str            | x     | auth      | The user's primary email; must be a valid email address                                          |
| phone          | str            | ?     | client    | The user's primary phone number; must be a valid E.164 spec compliant phone number               |
| full_name      | str            | ?     | auth      | The user's full name                                                                             |
| role           | Role           | x     | core      | The user's role (i.e., retail_borrower, mortgage_broker, underwriting_bank_officer)              |
| created_at     | datetime       | x     | core      | Account creation time stamp                                                                      |
| updated_at     | datetime       | x     | core      | Account details modification time stamp                                                          |

```mermaid
classDiagram
  class users {
    <<collection>>
    uid: str 
    email: str
    phone: str | None
    full_name: str | None
    role: Role
    created_at: datetime
    updated_at: datetime
  }
```

> [!IMPORTANT]
> `email_verified`, `photo_url` and other user-related fields are not persisted in the Firestore database; instead, the user record is stored in Firebase Auth.

### loan_applications

One document per loan application. Created by user with role `retail-borrower` role `POST /api/v1/loan-applications` through mobile client. Changed only by AL-Core: a mortgage broker claims it, AI committee attaches an assessment, a bank underwriting officer makes the
final decision.

| field                  | type                        | req | source  | description                                                                                                      |
|------------------------|-----------------------------|-----|---------|------------------------------------------------------------------------------------------------------------------|
| loan_application_id    | str                         | x   | core    | Loan application uid; document name, not a field                                                                 |
| borrower_id            | str                         | x   | auth    | Borrowers uid; ID of person who submitted application                                                            |
| borrower_full_name     | str                         | ?   | core    | Borrowers full legal name; copy of `users.full_name` at submission, so extra read is not required                |
| broker_id              | str                         | ?   | core    | Brokers uid; ID of person who claimed application; null if unclaimed                                             |
| bank_officer_id        | str                         | ?   | core    | Underwriting officer Firebase Auth uid; ID of person who made a decision on application; null unil decision made |
| annual_gross_income    | float                       | x   | client  | Household annual gross income; in euro                                                                           |
| annual_debt_repayments | float                       | x   | client  | Existing annual debt repayments; in euro                                                                         |
| deposit                | float                       | x   | client  | Borrower's own funds; should always be lower than `property_spec.asking_price`; in euro                          |
| loan_amount            | float                       | x   | core    | Amount of the loan requested from the bank; `asking_price - deposite`; in euro                                   |
| term_years             | int                         | x   | client  | Requestet mortgage term in years (5-40)                                                                          |
| first_time_buyer       | bool                        | x   | client  | First time buyers have different lending limits from Central Bank                                                |
| ltv                    | float                       | x   | core    | Loan-To-Value; `loan_amount / asking_price` in euro                                                              |
| ltv_group              | LtvGroup                    | x   | core    | `up_to_60`, `60_to_80`, `80_to_90`, `over_90`; derived from ltv for filtering                                    |
| property_spec          | dict                        | x   | client  | The property being bought (see [property_spec](#property_spec))                                                  |
| status                 | LoanApplicationStatus       | x   | core    | Current application status: `applied`, `AI deliberated`, `underwriter approved`, `funded`, `closed`              |
| status_history         | dict[]                      | x   | core    | Application status history; updated on change                                                                    |
| assessment_id          | str                         | ?   | core    | ID of the latest related document in assesments (see [assessments](#assessments))                                |
| risk_tier              | RiskTier                    | ?   | ai      |  `low`, `medium`, `high`; derived from the latest assessment for filtering; null until assessed                  |
| decision               | dict                        | ?   | client  | Underwriting officer final decision; null until made                                                             |
| created_at             | datetime                    | x   | core    | Application creation time stamp                                                                                  |
| updated_at             | datetime                    | x   | core    | Application details modification time stamp                                                                      |

```mermaid
classDiagram
  class loan_applications {
    <<collection>>
    loan_application_id: str
    borrower_id: str
    borrower_full_name: str
    broker_id: str | None
    bank_officer_id: str | None
    annual_gross_income: float
    annual_debt_repayments: float
    deposit: float
    loan_amount: float
    term_years: int
    first_time_buyer: bool
    ltv: float
    ltv_group: LtvGroup
    property_spec: dict
    status: LoanApplicationStatus
    status_history: dict[LoanApplicationStatusChange]
    assessment_id: str | None
    risk_tier: RiskTier | None
    decision: dict | None
    created_at: datetime
    updated_at: datetime
  }
```

#### property_spec

Specification of the property, which retail borrower want to buy. Nested map, not a subcollection.

| field         | type         | req | source  | description                                                                                                  |
|---------------|--------------|-----|---------|--------------------------------------------------------------------------------------------------------------|
| county        | County       | x   | client  | One of the 26 Respublic of Ireland counties                                                                  |
| address       | str          | ?   | client  | Street address, up to 200 characters                                                                         |
| floor_area_m2 | float        | x   | client  | Floor area; 20-600 m^2                                                                                       |
| bedrooms      | int          | x   | client  | Number of bedrooms; 1-10                                                                                     |
| bathrooms     | int          | x   | client  | Number of bathrooms; 0-10                                                                                    |
| property_type | PropertyType | x   | client  | `Detached`, `Semi-D`, `Terrace`, `End of Terrace`, `Apartment`, `Bungalow`, `Townhouse`, `Duplex`, `Studio`  |
| ber           | BerRating    | x   | client  | 15 Irish Building Energy Rating grades, best to worst (`A1`, `A2`, ..., `G`)                                 |
| latitude      | float        | ?   | client  | Latitude (51.4-55.5); given together with `longitude`; if null, AI engine uses the county centroids          |
| longitude     | float        | ?   | client  | Longitude (-10.6 - -5.8); given together with `latitude`                                                     |
| asking_price  | float        | x   | client  | Seller's asking price; in euro                                                                               |

```mermaid
classDiagram
  class property_spec {
    <<dict>>
    county: County
    address: str | None
    floor_area_m2: float
    bedrooms: int
    bathrooms: int
    property_type: PropertyType
    ber: BerRating
    latitude: float | None
    longitude: float | None
    asking_price: float
  }
```

#### documents

...

#### assessments

One document per AI committee assessment run. Subcollection of the `loan_application`. Created by AL-Core when AI Engine starts
the committee (`POST /v1/deliberations` of AL-AI Engine) and filled in when the result arrives.

```mermaid
classDiagram
  class assessments {
    <<subcollection>>
    assessment_id: str
    job_id: str
    status: AssessmentStatus
    rate_percent: float
    affordability: dict | None
    collateral: dict | None
    decision: dict | None
    error: str | None
    created_at: datetime
    finished_at: datetime | None
  }

  class affordability {
    <<dict>>
    monthly_repayment: int
    stressed_repayment: int
    annual_debt_service: int
    dti_percent: float
    lti_multiple: float
    disposable_annual: int
    breaches: str[]
    limits: dict
  }

  class collateral {
    <<dict>>
    estimate: int
    asking_price: int
    gap_percent: float
    overvalued: bool
    ltv_percent: float
    ltv_basis: LtvBasis
    breaches: str[]
    limits: dict
  }

  class decision {
    <<dict>>
    decision: AiDecision
    reason: str | None
    conditions: str[]
    key_risks: str[]
    automatic: bool
    votes: dict[]
  }

  class agent_steps {
    <<subcollection>>
    agent_step_id: str
  }

  assessments "1..1" *-- "0..1" affordability
  assessments "1..1" *-- "0..1" collateral
  assessments "1..1" *-- "0..1" decision
  assessments "1..1" *-- "0..*" agent_steps
```

| field         | type             | req | source | description                                                                                          |
|---------------|------------------|-----|--------|------------------------------------------------------------------------------------------------------|
| assessment_id | str              | x   | core   | Assesment uid; document name, not a field                                                            |
| job_id        | str              | x   | ai     | AL-AI Engine job ID; used to `GET /v1/deliberations/{job_id}` for the result                         |
| status        | AssessmentStatus | x   | ai     | `queued`, `running`, `done`, `failed`; derived from the job                                          |
| rate_percent  | float            | x   | core   | Interest rate sent to the committee; DTI and repayments are calculated with it                       |
| affordability | dict             | ?   | ai     | Affordability calculations; null until done                                                          |
| collateral    | dict             | ?   | ai     | Collatelar assessment; null until done and when the committee declined automatically on a hard limit |
| decision      | dict             | ?   | ai     | Committee's decision; null until done                                                                |
| error         | str              | ?   | ai     | Reason why the run failed; null unless `status` is `failed`                                          |
| created_at    | datetime         | x   | core   | Assessment creation time stamp                                                                       |
| finished_at   | datetime         | ?   | ai     | Assessment finished (done or failed) time stamp; null until then                                     |

##### affordability

Assessment of the borrower’s ability to make payments.

| field               | type  | req | source | description                                                                             |
|---------------------|-------|-----|--------|-----------------------------------------------------------------------------------------|
| monthly_repayment   | float | x   | ai     | Montly repayment of `loan_amount` over `term_years` at `rate_percent` (anuity); in euro |
| stressed_repayment  | float | x   | ai     | `monthly_repayment` but with the `rate_percent` 2% points higher (stress test); in euro |
| annual_debt_service | float | x   | ai     | `stressed_repayment` for a year + `annual_debt_repayments`; in euro                     |
| dti_percent         | float | x   | ai     | Stressed Debt-To-Income; `annual_debt_service / annual_gross_income`; in %              |
| lti_multiple        | float | x   | ai     | Loan-To-Income; `loan_amount / annual_gross_income`                                     |
| disposable_annual   | float | x   | ai     | Income left after all debt repayments, per year; in euro                                |
| breaches            | str[] | x   | ai     | List of exceeded limits (LTI, DTI); empty if none                                       |
| limits              | dict  | x   | ai     | List of limits used; `lti`, `dti_percent`, `stress_bps`                                 |

##### collateral_valuation

Assessment of a property value to understand how valuable the collateral itself is. With a mortgage, the purchased home remains as collateral for the bank; 
that is, if the borrower stops making payments, the bank can repossess the home and sell it, so it’s important to understand how valuable the property itself is.

> [!NOTE]
> There is no reason to store `collateral_valuation` as a separate **collection** inside Firestore, because there is no requirements to
> see the history of valuations, therefore AL-Core can just pass the request response for it through AL-AI Engine `POST v1/valuations`.
 
| field         | type     | req | source | description                                                                                      |
|---------------|----------|-----|--------|--------------------------------------------------------------------------------------------------|
| estimate      | float    | x   | ai     | Estimated property value; in euro                                                                |
| asking_price  | float    | x   | ai     | Seller's asking price; in euro                                                                   |
| gap_percent   | float    | x   | ai     | By what percentage does the asking_price differ (`+` above or `-` below) from the estimate; in % |
| overvalued    | bool     | x   | ai     | `True` if `asking_price` > 10% above `estimate` (`gap_percent = 10%`), false otherwise           |
| ltv_percent   | float    | x   | ai     | Loan-To-Value divided by `ltv_basis` value; in %                                                 |
| ltv_basis     | LtvBasis | x   | ai     | `asking_price` or `estimate` (lower value is selected)                                           |
| model_version | str      | x   | ai     | Version of the valuation model used                                                              |


##### decision

Decision details of the AI committee, including votes of each model.

| field      | type       | req | source | description                                                                         |
|------------|------------|-----|--------|-------------------------------------------------------------------------------------|
| decision   | AiDecision | x   | ai     | `Approve`, `Conditionally Approve`, `Decline`                                       |
| reason     | str        | x   | ai     | Reason of the decision made by AI committee                                         |
| conditions | str[]      | x   | ai     | List of things which are required or needs to be changed by borrower; empty if none |
| key_risks  | str[]      | x   | ai     | List of the main risks found; empty if none                                         |
| automatic  | bool       | x   | ai     | `True` only if declined automatically (exceed hard coded limits)                    |
| votes      | Vote[]     | x   | ai     | Decision of each separate agent, majority wins; empty if `automatic` is `True`      |

> [!WARNING]
> AL-AI Engine is not yet providing risk_tier for the loan application, but it will be included in the future.

###### votes

Vote details of the agent.

| field    | type       | req | source | description                                             |
|----------|------------|-----|--------|---------------------------------------------------------|
| provider | str        | x   | ai     | Specific model which voted (`qroq`, `gemini`, `ollama`) |
| decision | AiDecision | ?   | ai     | `Approve`, `Conditionally Approve`, `Decline`           |
| reason   | str        | ?   | ai     | Reason of the decision made by the model                |


#### agent_steps

Step details of the agent.

| field         | type      | req | source | description                                          |
|---------------|-----------|-----|--------|------------------------------------------------------|
| agent_step_id | str       | x   | core   | Agent step uid; document name, not a field           |
| step_number   | int       | x   | core   | Order of the step; starts from 1                     |
| agent         | AgentName | x   | ai     | `affordability`, `valuation`, `market`, `strategist` |
| summary       | str       | x   | ai     | Agent's conclusions done on the step                 |


### support_tickets

Support requests submitted by a retail borrower in AL-Mobile client. Created by `POST /api/v1/support-tickets`; not 
edited (read-only) afterward.

```mermaid
classDiagram
  class support_tickets {
    <<dict>>
    support_ticket_id: str
    user_id: str
    category: SupportCategory
    description: str
    loan_application_id: str
    status: SupportTicketStatus
    created_at: datetime
    resolved_at: datetime
  }
```

| field               | type                  | req | source | description                                                            |
|---------------------|-----------------------|-----|--------|------------------------------------------------------------------------|
| support_ticket_id   | str                   | x   | core   | Support ticket uid; document name, not a field                         |
| user_id             | str                   | x   | auth   | Borrower's uid who submitted review                                    |
| category            | SupportTicketCategory | x   | client | `account`, `loan_application`, `payment`, `technical`, `other`         |
| description         | str                   | x   | client | Description of the issue, up to 1000 characters                        |
| loan_application_id | str                   | ?   | client | Related loan application; null if `category` is not `loan_application` |
| status              | SupportTicketStatus   | x   | core   | `open` on submisssion, `resolved` when closed                          |
| created_at          | datetime              | x   | core   | Support ticket creation time stamp                                     |
| resolved_at         | datetime              | ?   | core   | Support ticket resolvation time stamp                                  |

### reviews

Rating and feedback about the service, left by a retail borrower in AL-Mobile client. Created by
`POST /api/v1/reviews`; not edited (read-only) afterward.

```mermaid
classDiagram
  class reviews {
    <<dict>>
    review_id: str
    user_id: str
    rating: int
    comment: str
    created_at: datetime
  }
```

| field      | type     | req | source | description                                      |
|------------|----------|-----|--------|--------------------------------------------------|
| review_id  | str      | x   | core   | Review uid; document name, not a field           |
| user_id    | str      | x   | auth   | Review author (borrower's) uid                   |
| rating     | int      | x   | client | Rating from 1 (worst) to 5 (best)                |
| comment    | str      | ?   | client | Review text, up to 256 characters; null if empty |
| created_at | datetime | x   | ai     | Review creation time stamp                       |

### conversations

One conversation between retail borrower and mortgage broker and/or underwriting bank officer per loan application. Created by AL-Core
with the first message (`POST /api/v1/conversations`).

```mermaid
classDiagram
  class conversations {
    <<dict>>
    conversation_id: str
    loan_application_id: str
    participant_ids: int
    last_message_text: str
    last_message_at: datetime
    created_at: datetime
  }
  
  class messages {
    <<dict>>
    message_id: str
    sender_id: str
    sender_role: int
    content: str
    created_at: datetime
    modified_at: datetime
  }
  
  conversations "1..1" *-- "0..*" messages
```

| field               | type     | req | source | description                                                       |
|---------------------|----------|-----|--------|-------------------------------------------------------------------|
| conversation_id     | str      | x   | core   | Converstation uid; document name, not a field                     |
| loan_application_id | str      | x   | auth   | Related applcation uid                                            |
| participant_ids     | str[]    | x   | client | List of the participants uids; at least two participants required |
| last_message_text   | str      | x   | client | Copy of the latest message; first 100 characters                  |
| last_message_at     | datetime | x   | ai     | Copy of the latest message creation time stamp                    |
| created_at          | datetime | x   | ai     | Converstation creation time stamp                                 |

#### messages

A messages of a conversation, they number is not limited; subcollection.

| field       | type     | req | source | description                                                          |
|-------------|----------|-----|--------|----------------------------------------------------------------------|
| message_id  | str      | x   | core   | Message uid; document name, not a field                              |
| sender_id   | str      | x   | auth   | Sender author uid                                                    |
| sender_role | Role     | x   | auth   | Sender's role (`retail_borrower`, `mortgage_broker`, `bank_officer`) |                
| content     | str      | x   | client | Message text, up to 500 characters                                   |
| created_at  | datetime | x   | core   | Message creation (sending) time stamp                                |
| modified_at | datetime | x   | core   | Message last modification time stamp                                 |

### stress_tests

```mermaid
classDiagram
  class stress_tests {
    <<collection>>
    stress_test_id: str
    user_id: str
    statuses: str
    loan_applcation_ids: str[] | None
    rate_shock_bps: float
    price_change_percent: float
    base_rate_percent: float
    dti_limit_percent: float
    results: dict[]
    created_at: datetime
  }
```

Stress test run by a underwriting bank officer or mortgage broker: how chosen loan applications behave if the central bank raises
the interest rate (+100 to +300 bps) and/or property prices fall. Created by AL-Core through `POST api/v1/stress-test`.

| field                | type            | req | source | description                                                                                                                               |
|----------------------|-----------------|-----|--------|-------------------------------------------------------------------------------------------------------------------------------------------|
| stress_test_id       | str             | x   | core   | Stress test uid; document name, not a field                                                                                               |
| user_id              | str             | x   | auth   | uid of the person who requireing the stress-test                                                                                          |
| statuses             | str             | x   | client | Selects all the loan applications which have the same status; any except `closed`by default; ignored if `loan_applcation_ids` is provided |                
| loan_applcation_ids  | str[]           | ?   | client | List of concrete ids to make stress-test; null by default                                                                                 |                
| rate_shock_bps       | float           | x   | client | Bank interest shock bps (100 to 300 bps or 0)                                                                                             |
| price_change_percent | float           | x   | client | Change of property price based on `rate_shock_bps`                                                                                        |
| base_rate_percent    | float           | x   | core   | Original rate before "shock"                                                                                                              |
| dti_limit_percent    | float           | x   | ai     | Debt-To-Income hard limit                                                                                                                 |
| results              | dict[]          | x   | core   | Result details per loan application                                                                                                       |
| created_at           | datetime        | x   | core   | Payment creation time stamp                                                                                                               |

> [!WARNING]
> If `statues` are used then "portfolio-wide" stress test is ran, but there is one simplification, We assume that a single bank underwriting officer represents the bank and that, for him, 
the "portfolio" consists of all the loan applications with which he is related to.

#### results

| field                | type               | req | source | description                                                                                     |
|----------------------|--------------------|-----|--------|-------------------------------------------------------------------------------------------------|
| loan_applcation_id   | str                | x   | core   | Related loan application uid                                                                    |
| borrower_full_name   | str                | ?   | core   | Borrower's full legal name; derived from `loan_application`                                     |
| borrower_id          | str                | x   | core   | Borrower's uid; derived from `loan_application`                                                 |
| loan_amount          | str                | x   | core   | Loan amount; in euro                                                                            |                
| property_value       | str                | x   | core   | Initial property value; in euro                                                                 |                
| base_repayment       | str[]              | x   | core   | Initial monthly repayment at `base_rate_percent`; in euro                                       |                
| stressed_repayment   | PaymentFeeType     | x   | core   | Monthly repayment after the rate shock; in euro                                                 |
| dti_limit_percent    | float              | x   | core   | Debt-To-Income before the rate shock; in %                                                      |
| base_dti_percent     | float              | x   | core   | Debt-To-Income before the rate shock; in %                                                      |
| stressed_dti_percent | str                | x   | core   | Debt-To-Income after the rate shock; in %                                                       |
| base_ltv_percent     | PaymentProvider    | x   | core   | Loan-To-Value before the rate shock; in %                                                       |
| stressed_ltv_percent | PaymentProvider    | x   | core   | Loan-To-Value after the rate shock; in %                                                        |
| affordable           | PaymentProvider    | x   | core   | `True` if `stressed_dti_percent` is not > `dti_limit_percent`                                   |
| negative_equity      | StressTestResult[] | x   | core   | `stressed_ltv_percent` is above 100% (requested loan costs more than the value of the property) |

### payments

Fees paid by retail borrower for the loan application, shown as payment history. Created by AL-Core
when the borrower starts a payment (`POST /api/v1/payments/{loan_application_id}`); the payment state is updated only from the Stripe / Paypal webhook.

> [!IMPORTANT]
> Card details never reach AL-Core or Firestore.

```mermaid
classDiagram
  class payments {
    <<collection>>
    payment_id: str
    user_id: str
    fee_type: str
    amount: float
    currency: str
    provider: PaymentProvider
    payment_provider_id: PaymentProvider
    status: PaymentStatus
    receipt_url: str | None
    failure_reason: str | None
    created_at: datetime
    paid_at: datetime | None
  }
```

| field               | type            | req | source | description                                                              |
|---------------------|-----------------|-----|--------|--------------------------------------------------------------------------|
| payment_id          | str             | x   | core   | Payment uid; document name, not a field                                  |
| user_id             | str             | x   | auth   | uid of the person who making the payment (`retail_borrower` is expected) |
| loan_application_id | str             | x   | client | Loan application the fee is paiid for                                    |                
| fee_type            | PaymentFeeType  | x   | client | (fast-track) `appraisal_processing` or `application_verification`        |
| amount              | float           | x   | core   | Set by AL-Core for each `fee_type` separatly; in euro                    |
| currency            | str             | x   | core   | Always euro                                                              |
| provider            | PaymentProvider | x   | client | `stripe` or `paypal`                                                     |
| payment_provider_id | str             | x   | psp    | Payment uid from the provider; used to mach webhooks to this payment     |
| status              | PaymentStatus   | x   | psp    | `pending`, `succeded`, `failed`, `refunded`                              |
| receipt_url         | str             | ?   | psp    | Link to the provider's receipt; evidence of payment; null until paid     |
| failure_reason      | str             | ?   | psp    | Reason of failure; null until `failed`                                   |
| created_at          | datetime        | x   | core   | Payment creation time stamp                                              |
| paid_at             | datetime        | ?   | psp    | Payment success time stamp; only if it `succeded`                        |
