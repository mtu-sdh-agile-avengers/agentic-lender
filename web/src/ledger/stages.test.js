// node --test "src/ledger/*.test.js"
import assert from 'node:assert/strict';
import {test} from 'node:test';
import {buildLedger, rewriteBlock, verifyBlocks} from './ledger.js';
import {SAMPLE_APPLICATION} from './sample.js';
import {stagesFromLedger} from './stages.js';

const H = SAMPLE_APPLICATION.statusHistory;
const statuses = (stages) => stages.map((s) => s.status);

test('a loan in progress: done stages, the next one in progress, the rest waiting', () => {
  const stages = stagesFromLedger({history: H.slice(0, 2), application: SAMPLE_APPLICATION});
  assert.deepEqual(statuses(stages), ['success', 'success', 'processing', 'pending']);
});

test('a funded loan: every stage done', () => {
  assert.deepEqual(statuses(stagesFromLedger({history: H, application: SAMPLE_APPLICATION})), ['success', 'success', 'success', 'success']);
});

test('a declined loan stops at the underwriter decision', () => {
  const history = [...H.slice(0, 2), {status: 'Closed', changedById: SAMPLE_APPLICATION.bankOfficerId, changedAt: H[2].changedAt}];
  const application = {...SAMPLE_APPLICATION, decision: {...SAMPLE_APPLICATION.decision, outcome: 'Declined'}};
  const stages = stagesFromLedger({history, application});
  assert.deepEqual(statuses(stages), ['success', 'success', 'failed', 'pending']);
  assert.match(stages[2].reason, /Declined/);
});

test('a withdrawn application stops at the next stage', () => {
  const history = [H[0], {status: 'Closed', changedById: SAMPLE_APPLICATION.borrowerId, changedAt: H[1].changedAt}];
  const stages = stagesFromLedger({history, application: {...SAMPLE_APPLICATION, decision: null}});
  assert.deepEqual(statuses(stages), ['success', 'failed', 'pending', 'pending']);
  assert.match(stages[1].reason, /Withdrawn/);
});

test('a rewritten block fails the stage whose link broke', async () => {
  const {blocks} = await buildLedger(SAMPLE_APPLICATION);
  const tampered = await rewriteBlock(blocks, 0, {timestamp: '2026-01-01T00:00:00.000Z'});
  const stages = stagesFromLedger({history: H, application: SAMPLE_APPLICATION, verdicts: await verifyBlocks(tampered), blocks: tampered});
  assert.deepEqual(statuses(stages), ['success', 'failed', 'pending', 'pending']);
  assert.match(stages[1].reason, /Chain broken/);
});
