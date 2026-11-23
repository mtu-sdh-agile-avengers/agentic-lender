// The stages of a loan application, as shown by <BlockchainStages> (ALG4-108).
// One stage per state on AL-Core's main path; their status comes from the status history,
// the decision, and the tamper test (a broken chain fails the stage whose block broke).

export const STAGE_DEFS = [
  {
    id: 'Applied',
    title: 'Application sealed',
    icon: 'document',
    description: 'The borrower submits the application. AL-Core stores the record, and the chain keeps its fingerprint.',
  },
  {
    id: 'AI Deliberated',
    title: 'AI assessment',
    icon: 'chip',
    description: 'The AI committee checks affordability, values the property, reads current ECB rates and votes.',
  },
  {
    id: 'Underwriter Approved',
    title: 'Underwriter decision',
    icon: 'shield',
    description: 'A bank underwriter reviews the assessment and approves or declines the loan.',
  },
  {
    id: 'Funded',
    title: 'Funded',
    icon: 'coin',
    description: 'The bank pays out and the mortgage starts. The chain now holds the full, shared history.',
  },
];

export const STATUS_LABELS = {
  pending: 'Waiting',
  processing: 'In progress',
  success: 'Done',
  failed: 'Stopped',
};

/**
 * @param {object} args
 * @param {{status: string, changedAt: string, changedById: string}[]} args.history  shown status history
 * @param {object} [args.application]  AL-Core application (decision, ids)
 * @param {{contentOk: boolean, linkOk: boolean}[]} [args.verdicts]  per-block verification
 * @param {{hash: string, actor: string, timestamp: string}[]} [args.blocks]  ledger blocks
 * @returns {{id, title, description, icon, status, reason?, meta: [string, string][]}[]}
 */
export function stagesFromLedger({history = [], application = {}, verdicts = [], blocks = []}) {
  const visited = history.map((change) => change.status);
  const closed = visited[visited.length - 1] === 'Closed';
  const reached = STAGE_DEFS.filter((stage) => visited.includes(stage.id)).length;

  // tamper test: the first block whose link or content fails stops the chain there
  const brokenBlock = verdicts.findIndex((v) => v && (!v.linkOk || !v.contentOk));
  const brokenStage = brokenBlock >= 0 ? STAGE_DEFS.findIndex((stage) => stage.id === history[brokenBlock]?.status) : -1;

  let failedAt = -1;
  let reason = '';
  if (brokenStage >= 0) {
    failedAt = brokenStage;
    reason = `Chain broken: block ${brokenBlock + 1} still expects the old seal of block ${brokenBlock}.`;
  } else if (closed && reached < STAGE_DEFS.length) {
    failedAt = reached;
    const declined = application.decision?.outcome === 'Declined';
    const byBorrower = history[history.length - 1]?.changedById === application.borrowerId;
    reason = declined ? 'Declined by the underwriter.' : byBorrower ? 'Withdrawn by the borrower.' : 'Closed before this step.';
  }

  return STAGE_DEFS.map((stage, index) => {
    const at = visited.indexOf(stage.id);
    const block = at >= 0 ? blocks[at] : null;
    let status = 'pending';
    if (failedAt >= 0 && index >= failedAt) status = index === failedAt ? 'failed' : 'pending';
    else if (at >= 0) status = 'success';
    else if (index === reached && !closed) status = 'processing';

    const meta = [];
    if (block) {
      meta.push(['Sealed', new Date(block.timestamp).toLocaleString('en-IE', {day: 'numeric', month: 'short', hour: '2-digit', minute: '2-digit'})]);
      meta.push(['By', block.actor]);
      meta.push(['Block hash', `${block.hash.slice(0, 10)}…${block.hash.slice(-4)}`]);
    }
    return {...stage, status, reason: status === 'failed' ? reason : undefined, meta};
  });
}
