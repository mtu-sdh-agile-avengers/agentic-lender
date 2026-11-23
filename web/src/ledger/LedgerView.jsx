// Blockchain record of a loan application (ALG4-108).
// <LedgerView> sits in every Loan File; <BlockchainExplorer> tells the story of a sample loan.
//
// Visual idea: like a land registry, every status change is sealed. Each block gets a seal
// generated from its own SHA-256 hash, so a different hash is a visibly different seal. The
// loan's token travels along the track of states; threads tie each seal to the one before it
// and snap when someone rewrites history.
import React, {useEffect, useMemo, useRef, useState} from 'react';
import {
  Blocks, CircleCheckBig, CircleX, Database, Pause, Play, RotateCcw, ShieldCheck, SkipBack,
  SkipForward,
} from 'lucide-react';
import {
  ZERO_HASH, buildLedger, documentOf, fingerprint, rewriteBlock,
  shortHash, verifyBlocks,
} from './ledger.js';
import {SAMPLE_APPLICATION, SAMPLE_STEPS} from './sample.js';
import {BlockchainStages} from './BlockchainStages.jsx';
import {stagesFromLedger} from './stages.js';
import './ledger.css';

const STEP_MS = 900;
const HEX = '0123456789abcdef';
const SEAL_COLORS = ['#1f6b45', '#2a9cb8', '#8cc265', '#c98a1b', '#173b2a'];
const reducedMotion = () => typeof window !== 'undefined' && window.matchMedia?.('(prefers-reduced-motion: reduce)').matches;
const euro = (value) => new Intl.NumberFormat('en-IE', {style: 'currency', currency: 'EUR', maximumFractionDigits: 0}).format(value);
const when = (iso) => new Date(iso).toLocaleString('en-IE', {day: 'numeric', month: 'short', hour: '2-digit', minute: '2-digit'});

// ---------------------------------------------------------------------------
// Seal: a circular mark drawn from a hash. Same hash, same seal; any change, a new seal.
// ---------------------------------------------------------------------------
function arc(r1, r2, a0, a1) {
  const p = (r, a) => `${(r * Math.cos(a)).toFixed(2)} ${(r * Math.sin(a)).toFixed(2)}`;
  return `M${p(r2, a0)} A${r2} ${r2} 0 0 1 ${p(r2, a1)} L${p(r1, a1)} A${r1} ${r1} 0 0 0 ${p(r1, a0)} Z`;
}

export function Seal({hash, size = 64, label, tone = 'ok', stamp = false, delay = 0}) {
  const hex = (hash || '').replace(/^0x/, '').padEnd(64, '0');
  const nib = (i) => parseInt(hex[i % 64], 16);
  const ticks = Array.from({length: 36}, (_, i) => {
    const a = (i / 36) * Math.PI * 2 - Math.PI / 2;
    const len = 2.5 + (nib(i) % 4) * 1.6;
    return <line key={i} x1={(30 - len) * Math.cos(a)} y1={(30 - len) * Math.sin(a)} x2={30 * Math.cos(a)} y2={30 * Math.sin(a)}/>;
  });
  const arcs = Array.from({length: 8}, (_, i) => {
    const a0 = (i / 8) * Math.PI * 2 - Math.PI / 2 + 0.04;
    const a1 = ((i + 1) / 8) * Math.PI * 2 - Math.PI / 2 - 0.04;
    const color = SEAL_COLORS[(nib(36 + i * 2) * 16 + nib(37 + i * 2)) % SEAL_COLORS.length];
    return <path key={i} d={arc(15.5, 21.5, a0, a1)} fill={color} opacity={0.55 + (nib(52 + i) % 4) * 0.15}/>;
  });
  return <svg className={`lg-seal ${tone} ${stamp ? 'stamp' : ''}`} style={{width: size, height: size, animationDelay: `${delay}ms`}}
    viewBox="-32 -32 64 64" role="img" aria-label={`Seal of ${shortHash(hash)}`}>
    <circle r="31" className="lg-seal-bg"/>
    <g className="lg-seal-ticks">{ticks}</g>
    <circle r="23.5" className="lg-seal-ring"/>
    {arcs}
    <circle r="13" className="lg-seal-core"/>
    {label !== undefined && <text className="lg-seal-label" textAnchor="middle" dominantBaseline="central">{label}</text>}
    {tone === 'bad' && <path className="lg-seal-crack" d="M-24 -10 L-6 -3 L-11 6 L8 2 L4 12 L25 18"/>}
  </svg>;
}

// ---------------------------------------------------------------------------
// Hash text that computes in front of you: random hex settling left to right
// ---------------------------------------------------------------------------
function useScramble(value, duration = 600) {
  const [shown, setShown] = useState(value);
  useEffect(() => {
    if (!value || reducedMotion()) { setShown(value); return undefined; }
    let frame;
    const start = performance.now();
    const tick = (now) => {
      const progress = Math.min(1, (now - start) / duration);
      const settled = Math.floor(progress * value.length);
      setShown(value.split('').map((ch, i) => (i < settled || i < 2 || !HEX.includes(ch) ? ch : HEX[(Math.random() * 16) | 0])).join(''));
      if (progress < 1) frame = requestAnimationFrame(tick);
    };
    frame = requestAnimationFrame(tick);
    return () => cancelAnimationFrame(frame);
  }, [value, duration]);
  return shown;
}

function HashText({value}) {
  const shown = useScramble(value === ZERO_HASH ? '0x0000…0000' : shortHash(value));
  return <code className="lg-hashtext" title={value}>{shown}</code>;
}

// ---------------------------------------------------------------------------
// Sealed blocks, tied together
// ---------------------------------------------------------------------------
function BlockCard({block, verdict, rewritten, stampDelay}) {
  const broken = verdict && !verdict.linkOk;
  const tone = verdict && !verdict.contentOk ? 'bad' : rewritten ? 'warn' : broken ? 'bad' : 'ok';
  return <article className={`lg-block ${tone}`} aria-label={`Block ${block.index + 1}: ${block.state}`}>
    <Seal hash={block.hash} label={block.index + 1} tone={tone} stamp={stampDelay !== null || rewritten} delay={stampDelay || 0} key={block.hash}/>
    <span className="lg-block-no">Block {block.index + 1}</span>
    <h4>{block.state}</h4>
    <p className="lg-block-meta">{when(block.timestamp)}, by {block.actor.toLowerCase() === 'system' ? 'the system' : `the ${block.actor.toLowerCase()}`}</p>
    <dl className="lg-block-fields">
      <div><dt>Record</dt><dd><HashText value={block.documentHash}/></dd></div>
      {block.decisionHash && <div><dt>Decision</dt><dd><HashText value={block.decisionHash}/></dd></div>}
      <div className={broken ? 'bad' : ''}><dt>Previous</dt><dd><HashText value={block.prevHash}/></dd></div>
      <div className="own"><dt>This block</dt><dd><HashText value={block.hash}/></dd></div>
    </dl>
    {rewritten && <p className="lg-block-note warn">Rewritten and re-sealed</p>}
    {broken && <p className="lg-block-note bad">Expects block {block.index}'s old seal</p>}
  </article>;
}

function Chain({blocks, verdicts, revealed, rewrittenIndex, animateFrom}) {
  const scroller = useRef(null);
  useEffect(() => {
    const el = scroller.current;
    if (el && revealed > 0) el.scrollTo({left: el.scrollWidth, behavior: reducedMotion() ? 'auto' : 'smooth'});
  }, [revealed, blocks.length]);

  if (!blocks.length) return <p className="lg-empty">No blocks yet. The first one is sealed when the application is submitted.</p>;
  return <div className="lg-chain" ref={scroller} tabIndex={0} aria-label="Blocks, oldest first">
    <div className="lg-genesis" aria-hidden="true">start<code>0x0000…</code></div>
    {blocks.slice(0, revealed).map((block, index) => {
      const verdict = verdicts?.[index];
      const animate = index >= animateFrom;
      return <React.Fragment key={block.index}>
        <span className={`lg-thread ${verdict && !verdict.linkOk ? 'broken' : ''} ${animate ? 'draw' : ''}`}
          style={{animationDelay: `${animate ? (index - animateFrom) * 140 : 0}ms`}} aria-hidden="true"/>
        <BlockCard block={block} verdict={verdict} rewritten={index === rewrittenIndex}
          stampDelay={animate ? (index - animateFrom) * 140 + 120 : null}/>
      </React.Fragment>;
    })}
    {revealed < blocks.length && <div className="lg-next-block" aria-hidden="true">sealing…</div>}
  </div>;
}

// ---------------------------------------------------------------------------
// From record to seal: what the chain stores, and why an edit shows
// ---------------------------------------------------------------------------
function HexDiff({value, reference}) {
  const hex = value.replace(/^0x/, '');
  const ref = reference.replace(/^0x/, '');
  const changed = [...hex].filter((ch, i) => ch !== ref[i]).length;
  return <div className="lg-hex">
    <code aria-label={`SHA-256 ${value}`}>{[0, 16, 32, 48].map((start) => <span key={start}>
      {[...hex.slice(start, start + 16)].map((ch, i) => <i key={i} className={ch !== ref[start + i] ? 'changed' : ''}>{ch}</i>)}
    </span>)}</code>
    {changed > 0 && <p><strong>{changed} of 64</strong> characters are different. A tiny edit changes the whole fingerprint.</p>}
  </div>;
}

function RecordToSeal({application, edits, documentHash, anchoredHash}) {
  const p = application.propertySpec || {};
  const value = (key) => edits?.[key] ?? application[key];
  const changedKey = (key) => edits?.[key] !== undefined && edits[key] !== application[key];
  const rows = [
    ['Borrower', application.borrowerFullName || 'Borrower', true],
    ['Annual income', euro(value('annualGrossIncome')), true, 'annualGrossIncome'],
    ['Loan amount', euro(value('loanAmount')), true, 'loanAmount'],
    ['Deposit', euro(application.deposit), true],
    ['Property', [p.propertyType, p.county].filter(Boolean).join(', ')],
    ['Asking price', euro(p.askingPrice)],
  ];
  const matches = documentHash === anchoredHash;

  return <div className="lg-bench">
    <section className="lg-record">
      <h3><Database size={16}/>The record, in Firestore</h3>
      <p>Everything the decision was based on. It contains personal data, so it never goes on the chain.</p>
      <dl>{rows.map(([label, shown, personal, key]) => <div key={label} className={key && changedKey(key) ? 'edited' : ''}>
        <dt>{label}{personal && <span className="lg-personal">personal</span>}</dt><dd>{shown}</dd>
      </div>)}</dl>
    </section>

    <div className="lg-sha" aria-hidden="true"><span>SHA-256</span></div>

    <section className="lg-seals">
      <h3><Blocks size={16}/>What the chain keeps</h3>
      <p>Only the record's fingerprint, sealed when the application was submitted.</p>
      <div className="lg-seal-pair">
        <figure>
          <Seal hash={anchoredHash} size={96}/>
          <figcaption>Sealed on the chain<code>{shortHash(anchoredHash)}</code></figcaption>
        </figure>
        <span className={`lg-equals ${matches ? 'ok' : 'bad'}`} aria-hidden="true">{matches ? '=' : '≠'}</span>
        <figure>
          <Seal hash={documentHash} size={96} tone={matches ? 'ok' : 'bad'} stamp key={documentHash}/>
          <figcaption>The record right now<code>{shortHash(documentHash)}</code></figcaption>
        </figure>
      </div>
      <HexDiff value={documentHash} reference={anchoredHash}/>
    </section>
  </div>;
}

// ---------------------------------------------------------------------------
// Try to change it
// ---------------------------------------------------------------------------
function TamperPanel({application, blocks, mode, setMode, edits, setEdits, rewrite, setRewrite, onReset, dirty}) {
  const amount = edits.loanAmount ?? application.loanAmount;
  return <div className="lg-tamper">
    <div className="lg-tamper-head">
      <h3>Try to change it</h3>
      <div className="lg-tabs" role="tablist" aria-label="What to change">
        <button role="tab" aria-selected={mode === 'record'} onClick={() => setMode('record')}>Edit the record</button>
        <button role="tab" aria-selected={mode === 'history'} onClick={() => setMode('history')} disabled={blocks.length < 2}>Rewrite a block</button>
      </div>
      <button className="lg-undo" onClick={onReset} disabled={!dirty}><RotateCcw size={15}/>Undo changes</button>
    </div>
    {mode === 'record' ? <div className="lg-tamper-body">
      <p>Change a copy of the record, as if someone edited the database directly. Nothing is saved.</p>
      <div className="lg-inputs">
        <label>Loan amount (€)<input type="number" step="1000" value={amount}
          onChange={(e) => setEdits({...edits, loanAmount: Number(e.target.value)})}/></label>
        <label>Annual income (€)<input type="number" step="1000" value={edits.annualGrossIncome ?? application.annualGrossIncome}
          onChange={(e) => setEdits({...edits, annualGrossIncome: Number(e.target.value)})}/></label>
        <button className="secondary" onClick={() => setEdits({...edits, loanAmount: amount + 1})}>Add €1 to the loan</button>
      </div>
    </div> : <div className="lg-tamper-body">
      <p>Change when a step happened and re-seal that block, the way a forger would.</p>
      <div className="lg-inputs">
        <label>Block<select value={rewrite.index} onChange={(e) => setRewrite({...rewrite, index: Number(e.target.value)})}>
          {blocks.slice(0, -1).map((block) => <option key={block.index} value={block.index}>Block {block.index + 1}: {block.state}</option>)}
        </select></label>
        <label>New date and time<input type="datetime-local" value={rewrite.time} onChange={(e) => setRewrite({...rewrite, time: e.target.value})}/></label>
        <button className="secondary" onClick={() => setRewrite({...rewrite, time: '2026-01-01T08:00'})}>Back-date it to 1 January</button>
      </div>
    </div>}
  </div>;
}

// ---------------------------------------------------------------------------
// The record of one application
// ---------------------------------------------------------------------------
export function LedgerView({application, history: historyProp, title = 'Blockchain record', controls = true, onRetry, sceneHeight = 440}) {
  const history = historyProp ?? application.statusHistory ?? [];
  const [ledger, setLedger] = useState(null);
  const [error, setError] = useState('');
  const [revealed, setRevealed] = useState(history.length);
  const [animateFrom, setAnimateFrom] = useState(0);
  const [mode, setMode] = useState('record');
  const [edits, setEdits] = useState({});
  const [rewrite, setRewrite] = useState({index: 0, time: ''});
  const [view, setView] = useState({blocks: [], verdicts: [], documentHash: ''});
  const [replaying, setReplaying] = useState(false);
  const timer = useRef(null);
  const previousLength = useRef(history.length);
  const historyKey = JSON.stringify(history);

  useEffect(() => {
    let cancelled = false;
    buildLedger(application, history)
      .then((built) => { if (!cancelled) { setLedger(built); setError(''); } })
      .catch(() => { if (!cancelled) setError('This browser cannot compute SHA-256 here. Open the site over HTTPS or on localhost.'); });
    return () => { cancelled = true; };
  }, [application, historyKey]);

  // a new step (explorer) seals only the new block; the rest stay put
  useEffect(() => {
    if (history.length === previousLength.current) return;
    setAnimateFrom(history.length > previousLength.current ? previousLength.current : history.length);
    previousLength.current = history.length;
    setRevealed(history.length);
  }, [history.length]);
  useEffect(() => () => clearInterval(timer.current), []);

  useEffect(() => {
    if (!ledger) return undefined;
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
    setAnimateFrom(0);
    if (reducedMotion()) { setRevealed(history.length); return; }
    setRevealed(0);
    setReplaying(true);
    let shown = 0;
    timer.current = setInterval(() => {
      shown += 1;
      setAnimateFrom(shown - 1);
      setRevealed(shown);
      if (shown >= history.length) { clearInterval(timer.current); setReplaying(false); }
    }, STEP_MS);
  }
  function reset() { setEdits({}); setRewrite({index: 0, time: ''}); }

  if (error) return <section className="card lg-card"><p className="lg-empty" role="alert">{error}</p></section>;
  if (!ledger) return <section className="card lg-card"><p className="lg-empty" role="status">Sealing the record…</p></section>;

  const rewrittenIndex = mode === 'history' && rewrite.time ? rewrite.index : -1;
  const chainOk = view.verdicts.every((v) => v.contentOk && v.linkOk);
  const recordOk = view.documentHash === ledger.documentHash;
  const allGood = chainOk && recordOk;
  const shownBlocks = view.blocks.slice(0, revealed);
  const dirty = Object.keys(edits).length > 0 || Boolean(rewrite.time);
  const stages = stagesFromLedger({
    history: history.slice(0, revealed),
    application,
    verdicts: view.verdicts.slice(0, revealed),
    blocks: view.blocks,
  });

  return <section className="card lg-card">
    <header className="lg-head">
      <div>
        <h2>{title}</h2>
        <p className="lg-sub">Every status change is sealed into a block that also carries the seal of the block before it, so nobody can quietly change the history.</p>
        <p className="lg-honest">The chain is simulated in your browser until the bank's contracts are deployed; the SHA-256 hashes are real.</p>
      </div>
      {controls && <button className="primary" onClick={replay} disabled={replaying}><Play size={16}/>{replaying ? 'Replaying…' : 'Replay history'}</button>}
    </header>

    <BlockchainStages stages={stages} height={sceneHeight} onRetry={dirty ? reset : onRetry}/>
    <Chain blocks={view.blocks} verdicts={view.verdicts} revealed={revealed} rewrittenIndex={rewrittenIndex} animateFrom={animateFrom}/>

    {replaying ? <div className="lg-verdict busy" role="status" aria-live="polite">
      <Blocks size={20}/><p><strong>Sealing block {Math.min(revealed + 1, history.length)} of {history.length}…</strong></p>
    </div> : <div className={`lg-verdict ${allGood ? 'ok' : 'bad'}`} role="status" aria-live="polite">
      {allGood ? <ShieldCheck size={20}/> : <CircleX size={20}/>}
      <p>
        {allGood && <><strong>Intact.</strong> {shownBlocks.length} block{shownBlocks.length === 1 ? '' : 's'}, every link holds and the record matches its seal.</>}
        {!recordOk && <><strong>The record was changed after it was sealed.</strong> Its fingerprint no longer matches the one on the chain.</>}
        {!chainOk && <><strong>Block {rewrittenIndex + 1} was rewritten.</strong> Block {rewrittenIndex + 2} still carries its old seal, so the chain breaks there. Hiding that means re-sealing every later block on every copy of the chain.</>}
      </p>
    </div>}

    <RecordToSeal application={application} edits={mode === 'record' ? edits : null} documentHash={view.documentHash} anchoredHash={ledger.documentHash}/>
    {controls && view.blocks.length > 0 && <TamperPanel application={application} blocks={ledger.blocks} mode={mode}
      setMode={(m) => { reset(); setMode(m); }} edits={edits} setEdits={setEdits} rewrite={rewrite} setRewrite={setRewrite} onReset={reset} dirty={dirty}/>}

    <p className="lg-foot">Next: the loan token contract (ALG4-96) will hold the state, and the audit registry (ALG4-97) the fingerprints.</p>
  </section>;
}

// ---------------------------------------------------------------------------
// Explorer: the story of one loan
// ---------------------------------------------------------------------------
const AUTOPLAY_MS = 3400;

// the same sample, declined by the underwriter after the AI assessment
const DECLINED_HISTORY = [
  ...SAMPLE_APPLICATION.statusHistory.slice(0, 2),
  {status: 'Closed', changedById: SAMPLE_APPLICATION.bankOfficerId, changedAt: SAMPLE_APPLICATION.statusHistory[2].changedAt},
];
const DECLINED_APPLICATION = {
  ...SAMPLE_APPLICATION,
  status: 'Closed',
  decision: {...SAMPLE_APPLICATION.decision, outcome: 'Declined', reason: 'Stressed repayments too close to the 40% limit.', conditions: []},
};

export function BlockchainExplorer({Hero}) {
  const [step, setStep] = useState(0);
  const [playing, setPlaying] = useState(false);
  const [declined, setDeclined] = useState(false);
  const last = SAMPLE_STEPS.length - 1;
  const history = useMemo(() => (declined ? DECLINED_HISTORY : SAMPLE_APPLICATION.statusHistory.slice(0, step + 1)), [step, declined]);
  const application = declined ? DECLINED_APPLICATION : SAMPLE_APPLICATION;

  useEffect(() => {
    if (!playing) return undefined;
    if (step >= last) { setPlaying(false); return undefined; }
    const id = setTimeout(() => setStep((s) => s + 1), reducedMotion() ? 900 : AUTOPLAY_MS);
    return () => clearTimeout(id);
  }, [playing, step, last]);

  const go = (target) => { setPlaying(false); setDeclined(false); setStep(Math.max(0, Math.min(last, target))); };

  return <>
    {Hero && <Hero eyebrow="Blockchain" title="How a loan becomes a tamper-proof record" subtitle="Follow one application from the first click to the payout, and see what the chain keeps at every step." compact/>}
    <div className="lg-explorer">
      <aside className="card lg-story">
        <div className="lg-story-controls">
          <button className="secondary" onClick={() => go(step - 1)} disabled={step === 0} aria-label="Previous step"><SkipBack size={16}/></button>
          {playing
            ? <button className="primary" onClick={() => setPlaying(false)}><Pause size={16}/>Pause</button>
            : <button className="primary" onClick={() => { if (step >= last) setStep(0); setPlaying(true); }}><Play size={16}/>{step >= last ? 'Play again' : 'Play the story'}</button>}
          <button className="secondary" onClick={() => go(step + 1)} disabled={step === last} aria-label="Next step"><SkipForward size={16}/></button>
        </div>
        <ol className="lg-steps">
          {SAMPLE_STEPS.map((s, i) => <li key={s.state} className={i === step ? 'active' : i < step ? 'done' : ''}>
            <button onClick={() => go(i)} aria-current={i === step ? 'step' : undefined}>
              <span className="lg-step-no">{i < step ? <CircleCheckBig size={15}/> : i + 1}</span>
              <span className="lg-step-title">{s.title}</span>
            </button>
            {i === step && <div className="lg-step-body">
              {playing && <span key={step} className="lg-step-progress" style={{animationDuration: `${AUTOPLAY_MS}ms`}}/>}
              <h3><Database size={15}/>In the app</h3><p>{s.app}</p>
              <h3><Blocks size={15}/>On the chain</h3><p>{s.chain}</p>
            </div>}
          </li>)}
        </ol>
        <button className="secondary lg-what-if" onClick={() => { setPlaying(false); setDeclined((d) => !d); }} aria-pressed={declined}>
          {declined ? 'Back to the approved loan' : 'What if the underwriter declines?'}
        </button>
        <p className="lg-story-foot">{declined
          ? 'The chain breaks at the decision. Retry brings the approved story back.'
          : step === last ? 'Now try to change it: the controls are under the chain.' : 'A made-up application, for demonstration.'}</p>
      </aside>
      <LedgerView application={application} history={history} title="Sample loan" controls={(step === last || declined) && !playing}
        onRetry={declined ? () => setDeclined(false) : undefined} sceneHeight={480}/>
    </div>
  </>;
}
