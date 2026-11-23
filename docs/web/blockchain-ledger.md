# Blockchain ledger (AL-Web)

**Jira:** ALG4-108 (custom feature) · **Author:** Pavlo · **Status:** implemented

Shows how a loan application's data is stored on a blockchain and how it moves between
states, so brokers, underwriters and auditors can see why the record cannot be quietly changed.

![Ledger in the Loan File](../imgs/blockchain-ledger-loan-file.png)

## Where to find it

- **Loan File:** every application has a *Blockchain ledger* section, built from its real
  status history in AL-Core. **Replay** rebuilds the chain block by block.
- **Blockchain** (sidebar): a step-by-step explorer that walks a sample application through
  Applied → AI Deliberated → Underwriter Approved → Funded, explaining what happens in the app
  and on the chain at each step. Good for demos and presentations.

## What it shows

1. **State machine:** the same transitions AL-Core enforces (`LoanApplicationModel`): done,
   current and possible next states, and the exit to Closed from any open state.
2. **Chain of blocks:** one block per status change with the state, time, the actor's *role*,
   the fingerprint of the application record (and of the decision, in the block that records
   it), the previous block's hash and its own hash. The coloured bars come from the first bytes
   of each hash, so different hashes look different at a glance.
3. **Off-chain vs on-chain:** the full record (names, income, amounts) stays in Firestore;
   only SHA-256 fingerprints, the application ID, state and time go on chain. No personal data
   on chain, which is how a bank would stay GDPR-compliant.
4. **Tamper test:**
   - *Change the record:* edit the loan amount or income; the record's fingerprint no longer
     matches the one on chain.
   - *Rewrite history:* change when a block happened and recompute its hash like a forger
     would; the next block still points at the old hash, so the link breaks.

![Tamper test: the chain breaks after a rewritten block](../imgs/blockchain-ledger-tamper.png)

## How it works

- `web/src/ledger/ledger.js`: canonical JSON (sorted keys) → SHA-256 with the browser's Web
  Crypto API; blocks, links and verification. Covered by `npm test` (Node's built-in test
  runner, also run in CI).
- `web/src/ledger/LedgerView.jsx`: `LedgerView` (Loan File) and `BlockchainExplorer` (page).
- `web/src/ledger/sample.js`: the made-up application for the explorer.

The hashing is real; the chain itself is **simulated in the browser** until the contracts
exist. When ALG4-96 (loan token: the state) and ALG4-97 (audit registry: the fingerprints) are
deployed, the blocks can show real transaction hashes and the Verify step can compare against
the contract instead of the locally built chain. The record fingerprint is already computed
the way ALG4-124 describes (canonical serialisation, then SHA-256).

Web Crypto needs a secure context: it works on `https://` (Azure) and on `localhost`.
