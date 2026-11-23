// Rules and formatting for the AI committee flow (claim -> run assessment -> audit).
// Plain functions with no React or network code, so they can be tested with `node --test`.

export const OPEN_STATUSES = ['Applied', 'AI Deliberated'];
const BROKER_ROLE = 'mortgage_broker';

export const isOpen = application => OPEN_STATUSES.includes(application?.status);

// AL-Core lets any broker claim an open application nobody has claimed yet.
export function canClaim(application, role) {
  return role === BROKER_ROLE && !application?.brokerId && isOpen(application);
}

// The claiming broker may return it to the pool, but not once an underwriter is assigned.
export function canRelease(application, uid) {
  return Boolean(uid) && application?.brokerId === uid && !application?.bankOfficerId && isOpen(application);
}

// Only the assigned broker or underwriter may start the AI committee, while the application is open.
export function canRunAssessment(application, uid) {
  return Boolean(uid) && (application?.brokerId === uid || application?.bankOfficerId === uid) && isOpen(application);
}

export const isRunning = assessment => assessment?.status === 'queued' || assessment?.status === 'running';

// Pill colour for an AI decision ("low" is green, "medium" amber, "high" red).
export function decisionTone(decision) {
  switch (decision) {
    case 'Approve': return 'low';
    case 'Conditionally Approve': return 'medium';
    case 'Decline': return 'high';
    default: return 'neutral';
  }
}

// Votes per decision, e.g. {Approve: 2, Decline: 1}; a model that gave no answer counts as "Unavailable".
export function tallyVotes(votes = []) {
  const tally = {};
  for (const vote of votes) {
    const decision = vote.decision || 'Unavailable';
    tally[decision] = (tally[decision] || 0) + 1;
  }
  return tally;
}

const AGENT_LABELS = {
  auto_decline: 'Automatic decline',
  affordability: 'Affordability agent',
  valuation: 'Valuation agent',
  market: 'Market agent',
  risk: 'Risk agent',
  strategist: 'Strategist',
};
export function agentLabel(agent) {
  if (AGENT_LABELS[agent]) return AGENT_LABELS[agent];
  const words = String(agent || 'unknown').replace(/[_-]+/g, ' ').trim();
  return words.charAt(0).toUpperCase() + words.slice(1);
}

// The committee's language models, e.g. "groq" -> "Groq", "ollama" -> "Ollama (local)".
const PROVIDER_LABELS = {groq: 'Groq', gemini: 'Gemini', ollama: 'Ollama (local)'};
export function providerLabel(provider) {
  const key = String(provider || '').toLowerCase();
  return PROVIDER_LABELS[key] || agentLabel(provider);
}

const euro = value => new Intl.NumberFormat('en-IE', {style: 'currency', currency: 'EUR', maximumFractionDigits: 0}).format(value);
const known = value => value !== undefined && value !== null;
const signed = value => `${value > 0 ? '+' : ''}${value}%`;
// [label, value] pairs for a figure that is present; missing figures are left out.
const rows = pairs => pairs.filter(([, value, present]) => present).map(([label, value]) => [label, value()]);

// The AI engine's figures keep its own snake_case keys (AL-Core passes them through unchanged).
export function affordabilityRows(a) {
  if (!a) return [];
  return rows([
    ['Monthly repayment', () => euro(a.monthly_repayment), known(a.monthly_repayment)],
    ['Stressed repayment', () => euro(a.stressed_repayment), known(a.stressed_repayment)],
    ['Debt-to-income', () => `${a.dti_percent}%`, known(a.dti_percent)],
    ['Loan-to-income', () => `${a.lti_multiple}×`, known(a.lti_multiple)],
    ['Disposable income (yearly)', () => euro(a.disposable_annual), known(a.disposable_annual)],
  ]);
}

export function collateralRows(c) {
  if (!c) return [];
  return rows([
    ['Model valuation', () => euro(c.estimate), known(c.estimate)],
    ['Asking price', () => euro(c.asking_price), known(c.asking_price)],
    ['Price vs valuation', () => signed(c.gap_percent), known(c.gap_percent)],
    ['Overvalued', () => (c.overvalued ? 'Yes' : 'No'), known(c.overvalued)],
    ['LTV', () => `${c.ltv_percent}%${c.ltv_basis ? ` (on ${c.ltv_basis})` : ''}`, known(c.ltv_percent)],
  ]);
}

export function riskRows(r) {
  if (!r) return [];
  return rows([
    ['Risk tier', () => r.tier, known(r.tier)],
    ['Risk score', () => `${r.score} / 100`, known(r.score)],
    ['Approval chance', () => `${r.approval_chance_percent}%`, known(r.approval_chance_percent)],
  ]);
}

// One line per risk factor, e.g. {label: 'Debt-to-income', value: '31.2%', points: '12 / 25'}.
const number = value => (typeof value === 'number' ? value.toLocaleString('en-IE', {maximumFractionDigits: 2}) : value);
export function riskFactors(r) {
  return (r?.factors || []).map(f => ({
    label: f.label || agentLabel(f.factor),
    value: f.unit === '%' ? `${number(f.value)}%` : `${number(f.value)}${f.unit ? ` ${f.unit}` : ''}`,
    points: `${number(f.points)} / ${number(f.max_points)}`,
  }));
}

// Every lending limit the run found broken, without duplicates.
export function breachedLimits(assessment) {
  const all = [
    ...(assessment?.affordability?.breaches || []),
    ...(assessment?.collateral?.breaches || []),
    ...(assessment?.risk?.hard_breaches || []),
  ];
  return [...new Set(all)];
}
