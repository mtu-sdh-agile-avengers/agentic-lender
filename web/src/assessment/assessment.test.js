import test from 'node:test';
import assert from 'node:assert/strict';
import {
  canClaim, canRelease, canRunAssessment, isRunning, decisionTone, tallyVotes, agentLabel, providerLabel,
  affordabilityRows, collateralRows, riskRows, riskFactors, breachedLimits,
} from './assessment.js';

const BROKER = 'broker-uid';
const OFFICER = 'officer-uid';
const unclaimed = {status: 'Applied', brokerId: null, bankOfficerId: null};
const claimed = {status: 'Applied', brokerId: BROKER, bankOfficerId: null};

test('only a broker can claim an open, unclaimed application', () => {
  assert.equal(canClaim(unclaimed, 'mortgage_broker'), true);
  assert.equal(canClaim(unclaimed, 'underwriting_bank_officer'), false);
  assert.equal(canClaim(claimed, 'mortgage_broker'), false);
  assert.equal(canClaim({...unclaimed, status: 'Closed'}, 'mortgage_broker'), false);
});

test('the claiming broker can release it until an underwriter is assigned', () => {
  assert.equal(canRelease(claimed, BROKER), true);
  assert.equal(canRelease(claimed, 'another-broker'), false);
  assert.equal(canRelease({...claimed, bankOfficerId: OFFICER}, BROKER), false);
  assert.equal(canRelease({...claimed, status: 'Underwriter Approved'}, BROKER), false);
});

test('only the assigned broker or underwriter can run the AI committee, while the application is open', () => {
  const assigned = {...claimed, bankOfficerId: OFFICER};
  assert.equal(canRunAssessment(assigned, BROKER), true);
  assert.equal(canRunAssessment(assigned, OFFICER), true);
  assert.equal(canRunAssessment({...assigned, status: 'AI Deliberated'}, OFFICER), true);
  assert.equal(canRunAssessment(unclaimed, BROKER), false);
  assert.equal(canRunAssessment({...assigned, status: 'Closed'}, BROKER), false);
  assert.equal(canRunAssessment(assigned, undefined), false);
});

test('a run counts as in progress only while queued or running', () => {
  assert.equal(isRunning({status: 'queued'}), true);
  assert.equal(isRunning({status: 'running'}), true);
  assert.equal(isRunning({status: 'done'}), false);
  assert.equal(isRunning({status: 'failed'}), false);
  assert.equal(isRunning(null), false);
});

test('decisions map to pill colours and votes are tallied, unanswered as Unavailable', () => {
  assert.equal(decisionTone('Approve'), 'low');
  assert.equal(decisionTone('Conditionally Approve'), 'medium');
  assert.equal(decisionTone('Decline'), 'high');
  assert.equal(decisionTone('Unavailable'), 'neutral');
  assert.deepEqual(
    tallyVotes([{decision: 'Approve'}, {decision: 'Approve'}, {decision: null}, {decision: 'Decline'}]),
    {Approve: 2, Unavailable: 1, Decline: 1},
  );
});

test('agent names read as words, with known agents given friendly labels', () => {
  assert.equal(agentLabel('auto_decline'), 'Automatic decline');
  assert.equal(agentLabel('valuation'), 'Valuation agent');
  assert.equal(agentLabel('credit_history'), 'Credit history');
  assert.equal(agentLabel(undefined), 'Unknown');
  assert.equal(providerLabel('groq'), 'Groq');
  assert.equal(providerLabel('Ollama'), 'Ollama (local)');
  assert.equal(providerLabel('mistral_large'), 'Mistral large');
});

test('figures are formatted, and missing figures are left out', () => {
  assert.deepEqual(
    affordabilityRows({monthly_repayment: 1513, dti_percent: 31.2, lti_multiple: 3.69}).map(([label]) => label),
    ['Monthly repayment', 'Debt-to-income', 'Loan-to-income'],
  );
  assert.deepEqual(affordabilityRows({dti_percent: 0}), [['Debt-to-income', '0%']]);
  const collateral = Object.fromEntries(collateralRows({estimate: 400000, asking_price: 420000, gap_percent: 5, overvalued: false, ltv_percent: 84, ltv_basis: 'model estimate'}));
  assert.equal(collateral['Price vs valuation'], '+5%');
  assert.equal(collateral['Overvalued'], 'No');
  assert.equal(collateral['LTV'], '84% (on model estimate)');
  assert.deepEqual(riskRows({tier: 'Medium', score: 42, approval_chance_percent: 61}),
    [['Risk tier', 'Medium'], ['Risk score', '42 / 100'], ['Approval chance', '61%']]);
  assert.deepEqual(affordabilityRows(null), []);
  assert.deepEqual(collateralRows(undefined), []);
});

test('risk factors and broken limits are listed once', () => {
  assert.deepEqual(riskFactors({factors: [
    {factor: 'dti', label: 'Debt-to-income', value: 31.2, unit: '%', points: 12, max_points: 25},
    {factor: 'lti', label: 'Loan-to-income', value: 3.7, unit: 'x', points: 10, max_points: 25},
    {factor: 'income_headroom', label: 'Income left after repayments', value: 3449, unit: 'EUR/month', points: 0, max_points: 10},
  ]}), [
    {label: 'Debt-to-income', value: '31.2%', points: '12 / 25'},
    {label: 'Loan-to-income', value: '3.7 x', points: '10 / 25'},
    {label: 'Income left after repayments', value: '3,449 EUR/month', points: '0 / 10'},
  ]);
  assert.deepEqual(breachedLimits({
    affordability: {breaches: ['LTI above 4x']},
    collateral: {breaches: ['LTV above 90%']},
    risk: {hard_breaches: ['LTI above 4x']},
  }), ['LTI above 4x', 'LTV above 90%']);
  assert.deepEqual(breachedLimits({}), []);
});
