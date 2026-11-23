// Blockchain ledger views (ALG4-108): a loan application as a chain of hash-linked blocks.
// <LedgerView> sits in every Loan File; <BlockchainExplorer> is a page that walks a sample
// application through its life, step by step, for demos.
import React, {useEffect, useMemo, useRef, useState} from 'react';
import {
  ArrowRight, Blocks, CircleCheckBig, CircleX, CornerDownRight, Database, Fingerprint, Link2, Pause, Play,
  RotateCcw, ShieldCheck, SkipBack, SkipForward, Unlink,
} from 'lucide-react';
import {
  MAIN_PATH, TRANSITION_ACTORS, ZERO_HASH, buildLedger, documentOf, fingerprint, rewriteBlock,
  shortHash, stateMap, verifyBlocks,
} from './ledger.js';
import {SAMPLE_APPLICATION, SAMPLE_STEPS} from './sample.js';
import './ledger.css';

const STEP_MS = 700;
const reducedMotion = () => typeof window !== 'undefined' && window.matchMedia?.('(prefers-reduced-motion: reduce)').matches;
const euro = (value) => new Intl.NumberFormat('en-IE', {style: 'currency', currency: 'EUR', maximumFractionDigits: 0}).format(value);
const when = (iso) => new Date(iso).toLocaleString('en-IE', {day: 'numeric', month: 'short', hour: '2-digit', minute: '2-digit'});

/** Four coloured bars from the first bytes of a hash: two different hashes look different at a glance. */
function HashSwatch({hash}) {
  const hex = (hash || '').replace(/^0x/, '').padEnd(24, '0');
  return <span className="lg-swatch" aria-hidden="true">
    {[0, 6, 12, 18].map((i) => <i key={i} style={{background: `#${hex.slice(i, i + 6)}`}}/>)}
  </span>;
}

function Hash({label, value, tone}) {
  return <div className={`lg-hash ${tone || ''}`}>
    <span>{label}</span>
    <code title={value}>{value === ZERO_HASH ? '0x0000…0000' : shortHash(value)}</code>
  </div>;
}

// ---------------------------------------------------------------------------
// State machine: the same transitions AL-Core enforces
// ---------------------------------------------------------------------------
export function StateMachine({history}) {
  const {visited, current, next} = stateMap(history);
  const closed = visited.includes('Closed');
  const classFor = (state) => {
    if (state === current) return 'current';
    if (visited.includes(state)) return 'done';
    if (next.includes(state)) return 'next';
    return closed ? 'skipped' : 'todo';
  };
  return <div className="lg-machine" role="img" aria-label={`Application state: ${current || 'not submitted'}. Next possible: ${next.join(', ') || 'none'}.`}>
    <ol className="lg-path">
      {MAIN_PATH.map((state, index) => <React.Fragment key={state}>
        {index > 0 && <li className={`lg-edge ${visited.includes(state) ? 'done' : ''}`} aria-hidden="true">
          <span>{TRANSITION_ACTORS[`${MAIN_PATH[index - 1]}>${state}`]}</span><ArrowRight size={16}/>
        </li>}
        <li className={`lg-state ${classFor(state)}`}>
          <i>{visited.includes(state) && state !== current ? <CircleCheckBig size={16}/> : index + 1}</i>
          <strong>{state}</strong>
          <small>{state === current ? 'now' : next.includes(state) ? 'can go next' : visited.includes(state) ? 'done' : ''}</small>
        </li>
      </React.Fragment>)}
    </ol>
    <div className={`lg-exit ${classFor('Closed')}`}>
      <CornerDownRight className="lg-exit-arrow" size={22} aria-hidden="true"/>
      <div className="lg-state-closed"><strong>Closed</strong><small>from any open state: withdrawn, declined or repaid</small></div>
    </div>
  </div>;
}

// ---------------------------------------------------------------------------
// The chain of blocks
// ---------------------------------------------------------------------------
function BlockCard({block, verdict, revealed, rewritten}) {
  const broken = verdict && !verdict.linkOk;
  const invalid = verdict && !verdict.contentOk;
  return <article className={`lg-block ${revealed ? 'in' : 'out'} ${rewritten ? 'rewritten' : ''} ${broken || invalid ? 'bad' : ''}`} aria-label={`Block ${block.index}: ${block.state}`}>
    <header>
      <span className="lg-index">#{block.index}</span>
      <strong>{block.state}</strong>
      <HashSwatch hash={block.hash}/>
    </header>
    <dl>
      <div><dt>time</dt><dd>{when(block.timestamp)}</dd></div>
      <div><dt>actor</dt><dd>{block.actor}</dd></div>
    </dl>
    <Hash label="record" value={block.documentHash}/>
    {block.decisionHash && <Hash label="decision" value={block.decisionHash}/>}
    <Hash label="prev" value={block.prevHash} tone={broken ? 'bad' : ''}/>
    <Hash label="hash" value={block.hash} tone={rewritten ? 'warn' : 'own'}/>
    {rewritten && <p className="lg-note warn">Rewritten: content and hash changed</p>}
    {broken && <p className="lg-note bad">prev no longer matches block #{block.index - 1}</p>}
    {invalid && <p className="lg-note bad">hash does not match the content</p>}
  </article>;
}

function Chain({blocks, verdicts, revealed, rewrittenIndex}) {
  const scroller = useRef(null);
  useEffect(() => {
    const el = scroller.current;
    if (el && revealed > 0) el.scrollTo({left: el.scrollWidth, behavior: reducedMotion() ? 'auto' : 'smooth'});
  }, [revealed, blocks.length]);
  if (!blocks.length) return <p className="lg-empty">No blocks yet: the first one is written when the application is submitted.</p>;
  return <div className="lg-chain" ref={scroller} tabIndex={0} aria-label="Blocks, oldest first">
    <div className="lg-genesis" aria-hidden="true"><span>0x0000…</span><small>start</small></div>
    {blocks.map((block, index) => {
      const verdict = verdicts?.[index];
      const linkBroken = verdict && !verdict.linkOk;
      return <React.Fragment key={block.index}>
        <span className={`lg-link ${index < revealed ? 'in' : 'out'} ${linkBroken ? 'bad' : ''}`} aria-hidden="true">
          {linkBroken ? <Unlink size={18}/> : <Link2 size={18}/>}
        </span>
        <BlockCard block={block} verdict={verdict} revealed={index < revealed} rewritten={index === rewrittenIndex}/>
      </React.Fragment>;
    })}
  </div>;
}

// ---------------------------------------------------------------------------
// Off-chain vs on-chain
// ---------------------------------------------------------------------------
function ChainSplit({application, documentHash, anchoredHash, edits}) {
  const p = application.propertySpec || {};
  const rows = [
    ['Borrower', application.borrowerFullName || 'Borrower', true],
    ['Annual income', euro(edits?.annualGrossIncome ?? application.annualGrossIncome), true],
    ['Loan amount', euro(edits?.loanAmount ?? application.loanAmount), true],
    ['Deposit', euro(application.deposit), true],
    ['Property', [p.propertyType, p.county].filter(Boolean).join(', '), false],
    ['Asking price', euro(p.askingPrice), false],
  ];
  const matches = documentHash === anchoredHash;
  return <div className="lg-split">
    <section className="lg-offchain">
      <h3><Database size={17}/>Off-chain · Firestore</h3>
      <p>The full record, readable only through AL-Core.</p>
      <dl>{rows.map(([label, value, personal]) => <div key={label}><dt>{label}</dt><dd>{value}{personal && <span className="lg-tag">personal</span>}</dd></div>)}</dl>
    </section>
    <div className="lg-funnel" aria-hidden="true"><Fingerprint size={22}/><span>SHA-256</span><ArrowRight size={18}/></div>
    <section className="lg-onchain">
      <h3><Blocks size={17}/>On-chain · audit registry</h3>
      <p>Only fingerprints: no names, no amounts, no user IDs.</p>
      <pre>{`{
  "applicationId": "${application.loanApplicationId}",
  "documentHash": "${shortHash(anchoredHash)}",
  "timestamp": "${application.createdAt?.slice(0, 19) || ''}Z"
}`}</pre>
      <div className={`lg-match ${matches ? 'ok' : 'bad'}`} role="status">
        {matches ? <ShieldCheck size={18}/> : <CircleX size={18}/>}
        <span>{matches
          ? 'The Firestore record matches its on-chain fingerprint.'
          : `The record was changed: its fingerprint is now ${shortHash(documentHash)}, the chain says ${shortHash(anchoredHash)}.`}</span>
      </div>
    </section>
  </div>;
}

// ---------------------------------------------------------------------------
// Tamper test
// ---------------------------------------------------------------------------
function TamperPanel({application, blocks, mode, setMode, edits, setEdits, rewrite, setRewrite, onReset}) {
  return <div className="lg-tamper">
    <div className="lg-tabs" role="tablist" aria-label="Tamper test">
      <button role="tab" aria-selected={mode === 'record'} onClick={() => setMode('record')}>Change the record</button>
      <button role="tab" aria-selected={mode === 'history'} onClick={() => setMode('history')} disabled={blocks.length < 2}>Rewrite history</button>
      <button className="lg-reset" onClick={onReset}><RotateCcw size={15}/>Reset</button>
    </div>
    {mode === 'record' ? <div className="lg-tamper-body">
      <p>Edit a copy of the Firestore record as if someone changed it in the database. Nothing is saved.</p>
      <div className="lg-fields">
        <label>Loan amount (€)<input type="number" step="1000" value={edits.loanAmount ?? application.loanAmount}
          onChange={(e) => setEdits({...edits, loanAmount: Number(e.target.value)})}/></label>
        <label>Annual income (€)<input type="number" step="1000" value={edits.annualGrossIncome ?? application.annualGrossIncome}
          onChange={(e) => setEdits({...edits, annualGrossIncome: Number(e.target.value)})}/></label>
      </div>
    </div> : <div className="lg-tamper-body">
      <p>Pick a block and change when it happened, then recompute its hash, like a forger would.</p>
      <div className="lg-fields">
        <label>Block<select value={rewrite.index} onChange={(e) => setRewrite({...rewrite, index: Number(e.target.value)})}>
          {blocks.slice(0, -1).map((block) => <option key={block.index} value={block.index}>#{block.index} · {block.state}</option>)}
        </select></label>
        <label>New time<input type="datetime-local" value={rewrite.time} onChange={(e) => setRewrite({...rewrite, time: e.target.value})}/></label>
      </div>
    </div>}
  </div>;
}

// ---------------------------------------------------------------------------
// The ledger of one application
// ---------------------------------------------------------------------------
export function LedgerView({application, history: historyProp, title = 'Blockchain ledger', controls = true}) {
  const history = historyProp ?? application.statusHistory ?? [];
  const [ledger, setLedger] = useState(null);
  const [error, setError] = useState('');
  const [revealed, setRevealed] = useState(history.length);
  const [mode, setMode] = useState('record');
  const [edits, setEdits] = useState({});
  const [rewrite, setRewrite] = useState({index: 0, time: ''});
  const [view, setView] = useState({blocks: [], verdicts: [], documentHash: ''});
  const timer = useRef(null);
  const historyKey = JSON.stringify(history);

  // the chain as written: what every node of the network holds
  useEffect(() => {
    let cancelled = false;
    buildLedger(application, history)
      .then((built) => { if (!cancelled) { setLedger(built); setError(''); } })
      .catch(() => { if (!cancelled) setError('Your browser cannot compute SHA-256 here (it needs HTTPS or localhost).'); });
    return () => { cancelled = true; };
  }, [application, historyKey]);

  // grow with the history (explorer steps), without replaying everything
  useEffect(() => { setRevealed(history.length); }, [history.length]);
  useEffect(() => () => clearInterval(timer.current), []);

  // what you see: the anchored chain, after the tamper test
  useEffect(() => {
    if (!ledger) return;
    let cancelled = false;
    (async () => {
      let blocks = ledger.blocks;
      if (mode === 'history' && rewrite.time && blocks[rewrite.index]) {
        blocks = await rewriteBlock(blocks, rewrite.index, {timestamp: new Date(rewrite.time).toISOString()});
      }
      const documentHash = await fingerprint(documentOf({...application, ...(mode === 'record' ? edits : {})}));
      const verdicts = await verifyBlocks(blocks);
      if (!cancelled) setView({blocks, verdicts, documentHash});
    })();
    return () => { cancelled = true; };
  }, [ledger, mode, edits, rewrite, application]);

  function replay() {
    clearInterval(timer.current);
    if (reducedMotion()) { setRevealed(history.length); return; }
    setRevealed(0);
    let shown = 0;
    timer.current = setInterval(() => {
      shown += 1;
      setRevealed(shown);
      if (shown >= history.length) clearInterval(timer.current);
    }, STEP_MS);
  }
  function reset() { setEdits({}); setRewrite({index: 0, time: ''}); }

  if (error) return <section className="card lg-card"><p className="lg-empty" role="alert">{error}</p></section>;
  if (!ledger) return <section className="card lg-card"><p className="lg-empty" role="status">Hashing the application…</p></section>;

  const rewrittenIndex = mode === 'history' && rewrite.time ? rewrite.index : -1;
  const chainOk = view.verdicts.every((v) => v.contentOk && v.linkOk);
  const recordOk = view.documentHash === ledger.documentHash;
  const head = view.blocks[view.blocks.length - 1];
  const anchoredHead = ledger.blocks[ledger.blocks.length - 1];
  const headMoved = head && anchoredHead && head.hash !== anchoredHead.hash;
  const shownHistory = history.slice(0, revealed);

  return <section className="card lg-card">
    <header className="lg-head">
      <div>
        <h2><span className="icon-chip"><Blocks size={18}/></span>{title}</h2>
        <p className="lg-sub">Every status change becomes a block that carries the hash of the block before it.
          <span className="lg-badge">Simulated in your browser · real SHA-256</span></p>
      </div>
      {controls && <button className="secondary" onClick={replay}><Play size={16}/>Replay</button>}
    </header>

    <StateMachine history={shownHistory}/>
    <Chain blocks={view.blocks} verdicts={view.verdicts} revealed={revealed} rewrittenIndex={rewrittenIndex}/>

    <div className={`lg-verdict ${chainOk && recordOk && !headMoved ? 'ok' : 'bad'}`} role="status" aria-live="polite">
      {chainOk && recordOk && !headMoved ? <ShieldCheck size={20}/> : <CircleX size={20}/>}
      <div>
        {chainOk && recordOk && !headMoved && <><strong>Chain intact.</strong> {view.blocks.length} block{view.blocks.length === 1 ? '' : 's'}, every link checks out, and the record matches its fingerprint.</>}
        {!recordOk && <><strong>Record tampered.</strong> The Firestore data no longer produces the fingerprint stored on chain, so the change is detected.</>}
        {!chainOk && <><strong>Chain broken.</strong> Block #{rewrittenIndex} was rewritten, so block #{rewrittenIndex + 1} points at a hash that no longer exists.</>}
        {chainOk && headMoved && <><strong>History rewritten.</strong> The last block's hash differs from the copy everyone else holds.</>}
      </div>
    </div>

    <ChainSplit application={application} documentHash={view.documentHash} anchoredHash={ledger.documentHash} edits={mode === 'record' ? edits : null}/>
    {controls && view.blocks.length > 0 && <TamperPanel application={application} blocks={ledger.blocks} mode={mode} setMode={(m) => { reset(); setMode(m); }}
      edits={edits} setEdits={setEdits} rewrite={rewrite} setRewrite={setRewrite} onReset={reset}/>}

    <p className="lg-foot">Contracts to come: loan token (ALG4-96) holds the state, audit registry (ALG4-97) holds the fingerprints. Until they are deployed, these blocks exist only in this page.</p>
  </section>;
}

// ---------------------------------------------------------------------------
// Explorer page
// ---------------------------------------------------------------------------
export function BlockchainExplorer({Hero}) {
  const [step, setStep] = useState(0);
  const [playing, setPlaying] = useState(false);
  const last = SAMPLE_STEPS.length - 1;
  const history = useMemo(() => SAMPLE_APPLICATION.statusHistory.slice(0, step + 1), [step]);
  const current = SAMPLE_STEPS[step];

  useEffect(() => {
    if (!playing) return undefined;
    if (step >= last) { setPlaying(false); return undefined; }
    const id = setTimeout(() => setStep((s) => s + 1), reducedMotion() ? 600 : 2200);
    return () => clearTimeout(id);
  }, [playing, step, last]);

  function play() { if (step >= last) setStep(0); setPlaying(true); }

  return <>
    {Hero && <Hero eyebrow="Custom feature · blockchain" title="How a loan becomes a tamper-proof record" subtitle="Follow a sample application through its states and watch each one land on the chain." compact/>}
    <section className="card lg-steps">
      <div className="lg-step-controls">
        <button className="secondary" onClick={() => { setPlaying(false); setStep((s) => Math.max(0, s - 1)); }} disabled={step === 0} aria-label="Previous step"><SkipBack size={16}/></button>
        {playing
          ? <button className="primary" onClick={() => setPlaying(false)}><Pause size={16}/>Pause</button>
          : <button className="primary" onClick={play}><Play size={16}/>{step >= last ? 'Play again' : 'Play'}</button>}
        <button className="secondary" onClick={() => { setPlaying(false); setStep((s) => Math.min(last, s + 1)); }} disabled={step === last} aria-label="Next step"><SkipForward size={16}/></button>
        <ol className="lg-dots" aria-label="Steps">{SAMPLE_STEPS.map((s, i) => <li key={s.state}>
          <button className={i === step ? 'active' : i < step ? 'done' : ''} onClick={() => { setPlaying(false); setStep(i); }} aria-label={`Step ${i + 1}: ${s.title}`} aria-current={i === step ? 'step' : undefined}/>
        </li>)}</ol>
      </div>
      <div className="lg-story" aria-live="polite">
        <span className="eyebrow">Step {step + 1} of {SAMPLE_STEPS.length} · {current.state}</span>
        <h2>{current.title}</h2>
        <div className="lg-story-cols">
          <div><h3><Database size={16}/>In the app</h3><p>{current.app}</p></div>
          <div><h3><Blocks size={16}/>On the chain</h3><p>{current.chain}</p></div>
        </div>
      </div>
    </section>
    <LedgerView application={SAMPLE_APPLICATION} history={history} title="Sample loan · demo data" controls={step === last && !playing}/>
  </>;
}
