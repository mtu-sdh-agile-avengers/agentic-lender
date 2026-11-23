// Blockchain ledger of a loan application (ALG4-108).
//
// Until the smart contracts exist (ALG4-96 loan token, ALG4-97 audit registry) the chain is
// built here, in the browser, from the application's real data in AL-Core. The hashing is the
// real thing (SHA-256 over a canonical JSON form), so the fingerprints, links and tamper checks
// behave exactly as they would on Ethereum; only the "chain" is simulated.
//
// What goes on chain: no names, no amounts, no user IDs. Only the application ID, the state,
// the time, the actor's role, and SHA-256 fingerprints of the off-chain record (Firestore).

export const STATES = ['Applied', 'AI Deliberated', 'Underwriter Approved', 'Funded', 'Closed'];
export const MAIN_PATH = ['Applied', 'AI Deliberated', 'Underwriter Approved', 'Funded'];

// The same rules as AL-Core (LoanApplicationModel._ALLOWED_TRANSITIONS).
export const TRANSITIONS = {
  Applied: ['AI Deliberated', 'Closed'],
  'AI Deliberated': ['Underwriter Approved', 'Closed'],
  'Underwriter Approved': ['Funded', 'Closed'],
  Funded: ['Closed'],
  Closed: [],
};

// Who moves the application along each edge.
export const TRANSITION_ACTORS = {
  'Applied>AI Deliberated': 'AI committee',
  'AI Deliberated>Underwriter Approved': 'Underwriter',
  'Underwriter Approved>Funded': 'Bank',
  'Applied>Closed': 'Borrower withdraws',
  'AI Deliberated>Closed': 'Declined or withdrawn',
  'Underwriter Approved>Closed': 'Withdrawn',
  'Funded>Closed': 'Repaid',
};

export const ZERO_HASH = `0x${'0'.repeat(64)}`;

/** JSON with keys sorted at every level and no spaces: the same object always gives the
 *  same bytes, so the same fingerprint. */
export function canonicalJson(value) {
  if (Array.isArray(value)) return `[${value.map(canonicalJson).join(',')}]`;
  if (value && typeof value === 'object') {
    return `{${Object.keys(value)
      .filter((key) => value[key] !== undefined)
      .sort()
      .map((key) => `${JSON.stringify(key)}:${canonicalJson(value[key])}`)
      .join(',')}}`;
  }
  return JSON.stringify(value ?? null);
}

export async function sha256Hex(text) {
  const bytes = new TextEncoder().encode(text);
  const digest = await globalThis.crypto.subtle.digest('SHA-256', bytes);
  return `0x${[...new Uint8Array(digest)].map((b) => b.toString(16).padStart(2, '0')).join('')}`;
}

export const fingerprint = (value) => sha256Hex(canonicalJson(value));

export function shortHash(hash = '') {
  return hash.length > 14 ? `${hash.slice(0, 8)}…${hash.slice(-4)}` : hash;
}

/** The part of the application the audit registry fingerprints: the terms the decision was
 *  made on. Stays in Firestore; only its SHA-256 goes on chain. */
export function documentOf(application) {
  return {
    loanApplicationId: application.loanApplicationId,
    borrowerId: application.borrowerId,
    annualGrossIncome: application.annualGrossIncome,
    annualDebtRepayments: application.annualDebtRepayments,
    deposit: application.deposit,
    loanAmount: application.loanAmount,
    termYears: application.termYears,
    firstTimeBuyer: application.firstTimeBuyer,
    propertySpec: application.propertySpec,
  };
}

/** A role, never a user ID: who did it is in Firestore, the chain only says what kind of actor. */
export function actorRole(application, uid) {
  if (uid === 'system') return 'System';
  if (uid === application.borrowerId) return 'Borrower';
  if (uid && uid === application.brokerId) return 'Broker';
  if (uid && uid === application.bankOfficerId) return 'Underwriter';
  return 'Team member';
}

/** The on-chain records, one per status change, each linked to the one before by its hash.
 *  `history` defaults to the application's own status history. */
export async function buildLedger(application, history = application.statusHistory || []) {
  const documentHash = await fingerprint(documentOf(application));
  const decisionHash = application.decision ? await fingerprint(application.decision) : null;

  const blocks = [];
  let prevHash = ZERO_HASH;
  for (const [index, change] of history.entries()) {
    const record = {
      index,
      applicationId: application.loanApplicationId,
      state: change.status,
      timestamp: change.changedAt,
      actor: actorRole(application, change.changedById),
      documentHash,
      prevHash,
    };
    // the decision is anchored in the block that records it
    if (decisionHash && ['Underwriter Approved', 'Closed'].includes(change.status)) {
      record.decisionHash = decisionHash;
    }
    const hash = await fingerprint(record);
    blocks.push({...record, hash});
    prevHash = hash;
  }
  return {documentHash, decisionHash, blocks};
}

/** Re-checks a chain: each block's hash against its content, and each link against the block
 *  before. Returns one verdict per block; the first problem breaks everything after it. */
export async function verifyBlocks(blocks) {
  const verdicts = [];
  let expectedPrev = ZERO_HASH;
  for (const block of blocks) {
    const {hash, ...record} = block;
    const recomputed = await fingerprint(record);
    const contentOk = recomputed === hash;
    const linkOk = record.prevHash === expectedPrev;
    verdicts.push({index: record.index, contentOk, linkOk, recomputed});
    expectedPrev = hash;
  }
  return verdicts;
}

/** Where the application can go next, and which states it can no longer reach. */
export function stateMap(history) {
  const visited = history.map((change) => change.status);
  const current = visited[visited.length - 1] || null;
  const next = current ? TRANSITIONS[current] || [] : ['Applied'];
  return {visited, current, next};
}

/** What an attacker would do to change history: edit one block and recompute its hash so the
 *  block itself looks fine. The next block still points at the old hash, so the chain breaks
 *  there; hiding that means rewriting every later block too, and the newest hash would then
 *  differ from the copy everyone else holds. */
export async function rewriteBlock(blocks, index, changes) {
  const copy = blocks.map((block) => ({...block}));
  const {hash: _oldHash, ...record} = {...copy[index], ...changes};
  copy[index] = {...record, hash: await fingerprint(record)};
  return copy;
}
