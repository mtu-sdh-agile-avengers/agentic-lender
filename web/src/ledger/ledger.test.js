// node --test src/ledger   (Node 20+: Web Crypto is built in)
import assert from 'node:assert/strict';
import {test} from 'node:test';
import {
  ZERO_HASH, buildLedger, canonicalJson, documentOf, fingerprint, rewriteBlock, sha256Hex, stateMap, verifyBlocks,
} from './ledger.js';
import {SAMPLE_APPLICATION} from './sample.js';

test('canonical JSON does not depend on key order', () => {
  assert.equal(canonicalJson({b: 1, a: {d: [1, {y: 2, x: 1}], c: null}}), canonicalJson({a: {c: null, d: [1, {x: 1, y: 2}]}, b: 1}));
});

test('sha256 matches a known vector', async () => {
  assert.equal(await sha256Hex('abc'), '0xba7816bf8f01cfea414140de5dae2223b00361a396177a9cb410ff61f20015ad');
});

test('blocks are linked by hash, starting from zero', async () => {
  const {blocks} = await buildLedger(SAMPLE_APPLICATION);
  assert.equal(blocks.length, SAMPLE_APPLICATION.statusHistory.length);
  assert.equal(blocks[0].prevHash, ZERO_HASH);
  for (let i = 1; i < blocks.length; i++) assert.equal(blocks[i].prevHash, blocks[i - 1].hash);
  assert.ok((await verifyBlocks(blocks)).every((v) => v.contentOk && v.linkOk));
});

test('no personal data goes on chain', async () => {
  const {blocks} = await buildLedger(SAMPLE_APPLICATION);
  const onChain = JSON.stringify(blocks);
  for (const secret of [SAMPLE_APPLICATION.borrowerId, SAMPLE_APPLICATION.borrowerFullName, String(SAMPLE_APPLICATION.loanAmount)]) {
    assert.ok(!onChain.includes(secret), `${secret} leaked on chain`);
  }
});

test('rewriting a block breaks the link to the next one', async () => {
  const {blocks} = await buildLedger(SAMPLE_APPLICATION);
  const tampered = await rewriteBlock(blocks, 1, {timestamp: '2026-01-01T00:00:00Z'});
  const verdicts = await verifyBlocks(tampered);
  assert.ok(verdicts[0].contentOk && verdicts[0].linkOk);
  assert.ok(verdicts[1].contentOk && verdicts[1].linkOk); // the forger fixed its own hash...
  assert.equal(verdicts[2].linkOk, false); // ...but the next block still points at the old one
  assert.notEqual(tampered[1].hash, blocks[1].hash);
});

test('editing a block without fixing its hash is caught too', async () => {
  const {blocks} = await buildLedger(SAMPLE_APPLICATION);
  const edited = blocks.map((b) => ({...b}));
  edited[2].actor = 'Broker';
  assert.equal((await verifyBlocks(edited))[2].contentOk, false);
});

test('changing the off-chain record changes its fingerprint', async () => {
  const original = await fingerprint(documentOf(SAMPLE_APPLICATION));
  const edited = await fingerprint(documentOf({...SAMPLE_APPLICATION, loanAmount: SAMPLE_APPLICATION.loanAmount + 1}));
  assert.notEqual(original, edited);
});

test('state map follows AL-Core transitions', () => {
  assert.deepEqual(stateMap([{status: 'Applied'}]).next, ['AI Deliberated', 'Closed']);
  assert.deepEqual(stateMap([]).next, ['Applied']);
  assert.deepEqual(stateMap([{status: 'Applied'}, {status: 'Closed'}]).next, []);
});
