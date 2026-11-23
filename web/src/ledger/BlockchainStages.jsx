// <BlockchainStages stages onStageClick onRetry height /> (ALG4-108)
// An interactive 3D chain of glass blocks, one per stage of a loan. The 3D scene (three.js,
// react-three-fiber) is loaded only when this section is about to be seen; until then, and on
// devices without WebGL, a 2D version in CSS shows the same stages, colours and statuses.
import React, {Suspense, lazy, useCallback, useEffect, useMemo, useRef, useState} from 'react';
import {RotateCcw, X} from 'lucide-react';
import {STATUS_LABELS} from './stages.js';
import './stages.css';

const BlockchainScene = lazy(() => import('./BlockchainScene.jsx'));

function hasWebGL() {
  try {
    const canvas = document.createElement('canvas');
    return Boolean(canvas.getContext('webgl2') || canvas.getContext('webgl'));
  } catch {
    return false;
  }
}

function useMedia(query) {
  const [matches, setMatches] = useState(() => typeof window !== 'undefined' && window.matchMedia?.(query).matches);
  useEffect(() => {
    const media = window.matchMedia?.(query);
    if (!media) return undefined;
    const update = () => setMatches(media.matches);
    update();
    media.addEventListener('change', update);
    return () => media.removeEventListener('change', update);
  }, [query]);
  return matches;
}

/** True while the element is on screen (rendering stops otherwise); `seen` stays true after the first time. */
function useInView(ref) {
  const [state, setState] = useState({inView: false, seen: false});
  useEffect(() => {
    const el = ref.current;
    if (!el || typeof IntersectionObserver === 'undefined') { setState({inView: true, seen: true}); return undefined; }
    const observer = new IntersectionObserver(([entry]) => {
      setState((s) => ({inView: entry.isIntersecting, seen: s.seen || entry.isIntersecting}));
    }, {rootMargin: '120px 0px'});
    observer.observe(el);
    return () => observer.disconnect();
  }, [ref]);
  return state;
}

/** The 2D version: same stages and colours, for no WebGL, while the 3D code loads, and for print. */
export function FlatStages({stages, vertical, selected, onSelect, onRetry}) {
  const failed = stages.findIndex((s) => s.status === 'failed');
  return <ol className={`bs-flat ${vertical ? 'vertical' : ''} ${failed >= 0 ? 'has-error' : ''}`}>
    {stages.map((stage, i) => {
      const dead = failed >= 0 && i > failed;
      const link = i === 0 ? null : failed >= 0 && i === failed ? 'broken' : dead ? 'dead' : stages[i - 1].status === 'success' ? 'live' : 'off';
      return <li key={stage.id} className={`bs-flat-item ${stage.status} ${dead ? 'dead' : ''}`}>
        {link && <span className={`bs-flat-link ${link}`} aria-hidden="true"><i/><i/></span>}
        <button className={`bs-flat-tile ${selected === i ? 'selected' : ''}`} onClick={() => onSelect(i)} aria-pressed={selected === i}>
          <span className="bs-flat-glyph" aria-hidden="true"/>
          <strong>{stage.title}</strong>
          <small>{STATUS_LABELS[stage.status]}</small>
        </button>
        {stage.status === 'failed' && <div className="bs-flat-error" role="alert">
          <p>{stage.reason}</p>
          {onRetry && <button className="bs-retry" onClick={onRetry}><RotateCcw size={14}/>Retry</button>}
        </div>}
      </li>;
    })}
  </ol>;
}

export function BlockchainStages({stages, onStageClick, onRetry, height = 440, label = 'Loan stages on the chain'}) {
  const wrapper = useRef(null);
  const {inView, seen} = useInView(wrapper);
  const reducedMotion = useMedia('(prefers-reduced-motion: reduce)');
  const vertical = useMedia('(max-width: 640px)');
  const [webgl] = useState(() => typeof document !== 'undefined' && hasWebGL());
  const [selected, setSelected] = useState(null);

  const select = useCallback((index) => {
    setSelected((current) => (current === index ? null : index));
    if (index !== null) onStageClick?.(stages[index], index);
  }, [onStageClick, stages]);

  useEffect(() => {
    if (selected === null) return undefined;
    const onKey = (e) => { if (e.key === 'Escape') setSelected(null); };
    window.addEventListener('keydown', onKey);
    return () => window.removeEventListener('keydown', onKey);
  }, [selected]);

  const sceneHeight = vertical ? Math.max(height, stages.length * 190 + 70) : height;
  const detail = selected !== null ? stages[selected] : null;
  const flat = useMemo(() => <FlatStages stages={stages} vertical={vertical} selected={selected} onSelect={select} onRetry={onRetry}/>, [stages, vertical, selected, select, onRetry]);

  return <section className="bs-root" ref={wrapper} aria-label={label}>
    {/* what a screen reader gets: the stages and their status, in order */}
    <ol className="bs-sr-only">
      {stages.map((stage, i) => <li key={stage.id}>Stage {i + 1} of {stages.length}, {stage.title}: {STATUS_LABELS[stage.status]}.{stage.reason ? ` ${stage.reason}` : ''}</li>)}
    </ol>

    <div className="bs-stage" style={{height: webgl ? sceneHeight : 'auto'}}>
      {webgl && seen
        ? <Suspense fallback={<div className="bs-loading">{flat}</div>}>
            <BlockchainScene stages={stages} active={inView} reducedMotion={reducedMotion} vertical={vertical}
              selected={selected} onSelect={select} onRetry={onRetry}/>
          </Suspense>
        : <div className="bs-loading">{flat}</div>}

      {detail && <aside className="bs-detail" role="dialog" aria-label={`${detail.title} details`}>
        <button className="bs-detail-close" onClick={() => setSelected(null)} aria-label="Close details"><X size={16}/></button>
        <span className={`bs-pill ${detail.status}`}>{STATUS_LABELS[detail.status]}</span>
        <h3>{detail.title}</h3>
        <p>{detail.description}</p>
        {detail.reason && <p className="bs-detail-reason">{detail.reason}</p>}
        {detail.meta?.length > 0 && <dl>{detail.meta.map(([k, v]) => <div key={k}><dt>{k}</dt><dd>{v}</dd></div>)}</dl>}
        <small>Click the block again or press Esc to go back.</small>
      </aside>}
    </div>
  </section>;
}
