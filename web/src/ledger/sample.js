// A made-up application for the Blockchain explorer page: the same shape AL-Core returns for
// GET /api/v1/loan-applications/{id}, so the explorer and the Loan File share one component.

const at = (iso) => new Date(iso).toISOString();

export const SAMPLE_APPLICATION = {
  loanApplicationId: 'demo-7f3c2a91',
  borrowerId: 'uid-borrower-demo',
  borrowerFullName: 'Bríd Borrower (demo)',
  brokerId: 'uid-broker-demo',
  bankOfficerId: 'uid-officer-demo',
  annualGrossIncome: 85000,
  annualDebtRepayments: 4000,
  deposit: 50000,
  loanAmount: 300000,
  termYears: 30,
  firstTimeBuyer: true,
  ltv: 0.8571,
  ltvGroup: 'from_80_to_90',
  propertySpec: {
    county: 'Cork',
    address: '12 Demo Terrace, Douglas',
    floorAreaM2: 110,
    bedrooms: 3,
    bathrooms: 2,
    propertyType: 'Semi-D',
    ber: 'B2',
    latitude: null,
    longitude: null,
    askingPrice: 350000,
  },
  status: 'Funded',
  statusHistory: [
    {status: 'Applied', changedById: 'uid-borrower-demo', changedAt: at('2026-11-02T09:14:00Z')},
    {status: 'AI Deliberated', changedById: 'system', changedAt: at('2026-11-02T09:16:41Z')},
    {status: 'Underwriter Approved', changedById: 'uid-officer-demo', changedAt: at('2026-11-05T14:30:12Z')},
    {status: 'Funded', changedById: 'system', changedAt: at('2026-11-19T11:02:55Z')},
  ],
  assessmentId: 'assessment-demo-1',
  riskTier: 'Medium',
  decision: {
    outcome: 'Approved',
    reason: 'Within LTI and stressed DTI limits; LTV 85.7% on the asking price.',
    conditions: ['Proof of deposit source', 'Final valuation report'],
    decidedBy: 'uid-officer-demo',
    decidedAt: at('2026-11-05T14:30:12Z'),
  },
  createdAt: at('2026-11-02T09:14:00Z'),
  updatedAt: at('2026-11-19T11:02:55Z'),
};

// What happens at each step of the explorer, in the app and on chain.
export const SAMPLE_STEPS = [
  {
    state: 'Applied',
    title: 'The borrower applies',
    app: 'Bríd submits her application in AL Mobile. AL-Core keeps the full record in Firestore: her name, income, deposit and the property.',
    chain: 'A loan token is created in state Applied, and the audit registry stores the SHA-256 fingerprint of the application. The chain holds no name and no amounts.',
  },
  {
    state: 'AI Deliberated',
    title: 'The AI committee assesses it',
    app: 'The AI engine checks affordability, values the property, reads current ECB rates and votes: Medium risk, 80% approval chance.',
    chain: 'The token moves to AI Deliberated. The new block carries the hash of the block before it: that hash is the chain.',
  },
  {
    state: 'Underwriter Approved',
    title: 'The underwriter decides',
    app: 'The underwriter approves with two conditions. The decision is saved with the application.',
    chain: 'The decision\'s fingerprint is anchored in this block. Anyone can later prove the decision was not edited after the fact.',
  },
  {
    state: 'Funded',
    title: 'The bank pays out',
    app: 'The money is released and the mortgage starts.',
    chain: 'The token reaches Funded. Bank, broker and auditor now share one record that no single party can rewrite.',
  },
];
