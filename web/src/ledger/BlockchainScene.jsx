// The 3D scene of <BlockchainStages> (ALG4-108). Loaded on demand: three.js is big.
//
// Glass tiles stand in a diagonal row on a reflective floor (theme: forest or mist); glowing beams with ring
// connectors tie them together and carry energy from one stage to the next. A failed stage
// breaks the beam in front of it: it glitches, snaps in the middle with sparks, the block
// shakes and cracks, and everything after it goes dark. When the stage recovers, it all
// reassembles.
import React, {useEffect, useMemo, useRef, useState} from 'react';
import * as THREE from 'three';
import {Canvas, useFrame, useThree} from '@react-three/fiber';
import {Environment, Html, Lightformer, Line, MeshReflectorMaterial, RoundedBox} from '@react-three/drei';
import {Bloom, ChromaticAberration, EffectComposer, Vignette} from '@react-three/postprocessing';
import {RotateCcw} from 'lucide-react';
import {STATUS_LABELS} from './stages.js';

// ---------------------------------------------------------------------------
// Look
// ---------------------------------------------------------------------------
// Two looks: "forest" (deep brand green, glowing) and "mist" (the site's light green surfaces).
const THEMES = {
  // deep brand green (#234b35 family) instead of black, so the glow still reads
  forest: {
    bg: '#12301f', floor: '#143724', mirror: 0.5, mix: 10, metal: 0.45, ambient: 0.4, glass: '#e8fbf1',
    glow: 1, bloom: 0.75, vignette: 0.45, key: '#3cc8f2', additive: true, tint: 1, attDist: 1.4, roughness: 0.12,
    success: '#3cf2a0', processing: '#3cc8f2', pending: '#6f9a84', failed: '#ff4d6a', dead: '#2f4d3d', spark: '#ffb27a',
  },
  // the site's own light surfaces and colours (aero.css: --forest, --sage, --danger, --accent)
  mist: {
    bg: '#e6f3ec', floor: '#dcede3', mirror: 0, mix: 0, metal: 0.05, ambient: 1.15, glass: '#ffffff',
    glow: 0.95, bloom: 0.25, vignette: 0.12, key: '#9fdcc8', additive: false, tint: 0.16, attDist: 6, roughness: 0.32,
    success: '#258444', processing: '#239fc0', pending: '#93ad9f', failed: '#cc4962', dead: '#c3d3ca', spark: '#ed8750',
  },
};

function makePalette(name) {
  const theme = THEMES[name] ? name : 'forest';
  const raw = THEMES[theme];
  const color = (hex) => new THREE.Color(hex);
  return {
    ...raw, name: theme,
    success: color(raw.success), processing: color(raw.processing), pending: color(raw.pending),
    failed: color(raw.failed), dead: color(raw.dead), spark: color(raw.spark),
  };
}

// Our own clock. react-three-fiber resets its clock to 0 whenever rendering pauses and resumes
// (the scene pauses while it is off screen), which would put every stored time in the "future".
const now = () => performance.now() / 1000;
const MAX_DELTA = 0.05;
const WHITE = new THREE.Color('#ffffff');
const TILE = 1.5;
const DEPTH = 0.34;
const RADIUS = 0.16;
const SPACING = 2.85;
const V_SPACING = 2.7;
const ROW_TURN = 0.42; // the row recedes to the right
const FLOOR_Y = -TILE / 2 - 0.55;

// timings (seconds)
const APPEAR_STAGGER = 0.15;
const APPEAR_TIME = 0.75;
const FLICKER = 0.6; // the beam glitches before it snaps
const SNAP_TIME = 1.1; // halves fly apart and fade
const HEAL_TIME = 0.7;

// ---------------------------------------------------------------------------
// Helpers
// ---------------------------------------------------------------------------
const clamp01 = (x) => Math.max(0, Math.min(1, x));
const easeOutCubic = (t) => 1 - (1 - t) ** 3;
const easeOutBack = (t) => { const c = 1.6; return 1 + (c + 1) * (t - 1) ** 3 + c * (t - 1) ** 2; };
const UP = new THREE.Vector3(0, 1, 0);
const Z = new THREE.Vector3(0, 0, 1);

function roundedRect(size, r, steps = 6) {
  const h = size / 2;
  const pts = [];
  const corners = [[h - r, h - r, 0], [-h + r, h - r, Math.PI / 2], [-h + r, -h + r, Math.PI], [h - r, -h + r, Math.PI * 1.5]];
  for (const [cx, cy, a0] of corners) {
    for (let s = 0; s <= steps; s++) {
      const a = a0 + (s / steps) * (Math.PI / 2);
      pts.push([cx + r * Math.cos(a), cy + r * Math.sin(a), 0]);
    }
  }
  pts.push(pts[0]);
  return pts;
}

const circle = (r, n = 40, cx = 0, cy = 0) => Array.from({length: n + 1}, (_, i) => {
  const a = (i / n) * Math.PI * 2;
  return [cx + r * Math.cos(a), cy + r * Math.sin(a), 0];
});

/** Engraved icons, as polylines in the tile's plane (about 0.6 units across). */
const ICONS = {
  document: [
    [[-0.18, 0.25, 0], [0.08, 0.25, 0], [0.18, 0.15, 0], [0.18, -0.25, 0], [-0.18, -0.25, 0], [-0.18, 0.25, 0]],
    [[0.08, 0.25, 0], [0.08, 0.15, 0], [0.18, 0.15, 0]],
    [[-0.1, 0.06, 0], [0.1, 0.06, 0]], [[-0.1, -0.04, 0], [0.1, -0.04, 0]], [[-0.1, -0.14, 0], [0.04, -0.14, 0]],
  ],
  chip: [
    [[-0.17, -0.17, 0], [0.17, -0.17, 0], [0.17, 0.17, 0], [-0.17, 0.17, 0], [-0.17, -0.17, 0]],
    [[-0.08, -0.08, 0], [0.08, -0.08, 0], [0.08, 0.08, 0], [-0.08, 0.08, 0], [-0.08, -0.08, 0]],
    ...[-0.1, 0, 0.1].flatMap((o) => [
      [[o, 0.17, 0], [o, 0.25, 0]], [[o, -0.17, 0], [o, -0.25, 0]],
      [[0.17, o, 0], [0.25, o, 0]], [[-0.17, o, 0], [-0.25, o, 0]],
    ]),
  ],
  shield: [
    [[0, 0.27, 0], [0.21, 0.19, 0], [0.19, -0.04, 0], [0, -0.27, 0], [-0.19, -0.04, 0], [-0.21, 0.19, 0], [0, 0.27, 0]],
    [[-0.09, 0.0, 0], [-0.02, -0.08, 0], [0.11, 0.08, 0]],
  ],
  coin: [circle(0.25), circle(0.18), [[0.08, 0.1, 0], [-0.02, 0.1, 0], [-0.08, 0.04, 0], [-0.08, -0.04, 0], [-0.02, -0.1, 0], [0.08, -0.1, 0]], [[-0.13, 0.02, 0], [0.04, 0.02, 0]], [[-0.13, -0.03, 0], [0.04, -0.03, 0]]],
  hex: [circle(0.25, 6), circle(0.15, 6)],
};

/** Circuit traces running from the icon to the edges, brightest first in from the centre. */
const TRACES = Array.from({length: 10}, (_, k) => {
  const a = (k / 10) * Math.PI * 2 + 0.3;
  const r0 = 0.33;
  const r1 = 0.47 + (k % 3) * 0.04;
  const x0 = r0 * Math.cos(a), y0 = r0 * Math.sin(a);
  const x1 = r1 * Math.cos(a), y1 = r1 * Math.sin(a);
  const horizontal = Math.abs(Math.cos(a)) > Math.abs(Math.sin(a));
  const edge = 0.64;
  const end = horizontal ? [Math.sign(x1) * edge, y1, 0] : [x1, Math.sign(y1) * edge, 0];
  return [[x0, y0, 0], [x1, y1, 0], end];
}).sort((a, b) => Math.hypot(...a[0]) - Math.hypot(...b[0]));

const CRACKS = [
  [[0.12, 0.08, 0], [0.3, 0.22, 0], [0.38, 0.45, 0], [0.55, 0.62, 0]],
  [[0.12, 0.08, 0], [0.02, 0.3, 0], [-0.12, 0.42, 0], [-0.2, 0.66, 0]],
  [[0.12, 0.08, 0], [-0.15, 0.02, 0], [-0.4, -0.08, 0], [-0.68, -0.05, 0]],
  [[0.12, 0.08, 0], [0.2, -0.2, 0], [0.12, -0.45, 0], [0.22, -0.68, 0]],
  [[0.12, 0.08, 0], [0.42, -0.04, 0], [0.68, -0.18, 0]],
];

function layout(n, vertical) {
  return Array.from({length: n}, (_, i) => (vertical
    ? new THREE.Vector3(i % 2 ? 0.28 : -0.28, -(i - (n - 1) / 2) * V_SPACING, 0)
    : new THREE.Vector3((i - (n - 1) / 2) * SPACING, 0, 0)));
}

// pseudo-random but stable per index
const rand = (i) => { const x = Math.sin(i * 127.1 + 311.7) * 43758.5453; return x - Math.floor(x); };

// ---------------------------------------------------------------------------
// Shared timeline: when each stage changed status, and what it was before
// ---------------------------------------------------------------------------
function useTimeline(stages, active) {
  const tl = useRef(null);
  if (!tl.current || tl.current.items.length !== stages.length) {
    tl.current = {appearAt: null, items: stages.map((s) => ({status: s.status, prev: s.status, at: null}))};
  }
  useEffect(() => {
    const t = now();
    stages.forEach((stage, i) => {
      const item = tl.current.items[i];
      if (item.status !== stage.status) tl.current.items[i] = {status: stage.status, prev: item.status, at: t};
    });
  }, [stages]);
  useEffect(() => {
    if (active && tl.current.appearAt === null) {
      const start = now() + 0.1;
      tl.current.appearAt = start;
      // a stage that is already failed breaks during the intro, once the blocks are up
      const after = start + stages.length * APPEAR_STAGGER + APPEAR_TIME + 0.2;
      tl.current.items.forEach((item) => { if (item.at === null) item.at = item.status === 'failed' ? after : -100; });
    }
  }, [active, stages.length]);
  return tl;
}

function failure(tl) {
  const index = tl.items.findIndex((item) => item.status === 'failed');
  return index < 0 ? {index: -1, at: 0} : {index, at: tl.items[index].at ?? 0};
}

// ---------------------------------------------------------------------------
// A glass block
// ---------------------------------------------------------------------------
function GlowLine({points, lineRef, width = 1.5}) {
  return <Line ref={lineRef} points={points} lineWidth={width} transparent toneMapped={false} color="#ffffff"/>;
}

function Block({i, n, stage, position, prevDir, nextDir, tl, pal, reduced, vertical, hovered, selected, setHovered, onSelect, onRetry}) {
  const group = useRef();
  const tilt = useRef();
  const glass = useRef();
  const outlineFront = useRef();
  const outlineBack = useRef();
  const iconRefs = useRef([]);
  const traceRefs = useRef([]);
  const crackRefs = useRef([]);
  const rings = useRef([]);
  const pointer = useRef({x: 0, y: 0});
  const lift = useRef(0);
  const color = useMemo(() => new THREE.Color(), []);
  const glow = useMemo(() => new THREE.Color(), []);
  const frame = useMemo(() => roundedRect(TILE - 0.05, RADIUS - 0.02), []);
  const icon = ICONS[stage.icon] || ICONS.hex;

  const ringPlacements = useMemo(() => [prevDir && prevDir.clone().negate(), nextDir].filter(Boolean).map((dir) => ({
    position: dir.clone().multiplyScalar(TILE / 2 + 0.03),
    quaternion: new THREE.Quaternion().setFromUnitVectors(Z, dir),
  })), [prevDir, nextDir]);

  useFrame((_, rawDelta) => {
    const t = now();
    const delta = Math.min(rawDelta, MAX_DELTA);
    const state = tl.current;
    const item = state.items[i];
    const since = item.at === null ? 0 : Math.max(0, t - item.at);
    const fail = failure(state);
    const dead = fail.index >= 0 && i > fail.index;
    const deadT = dead ? (reduced ? 1 : clamp01((t - (fail.at + FLICKER + 0.5 + (i - fail.index) * 0.2)) / 0.5)) : 0;

    // appear: rise with a little overshoot, one after another
    const appearT = state.appearAt === null ? 0 : reduced ? 1 : clamp01((t - state.appearAt - i * APPEAR_STAGGER) / APPEAR_TIME);
    const rise = reduced ? appearT : easeOutBack(appearT);

    // colour and glow by status
    let intensity = 1.6 * pal.glow;
    if (item.status === 'success') {
      color.copy(pal.success);
      if (item.prev !== 'success' && since < 0.9 && !reduced) intensity += 1.1 * (1 - since / 0.9); // short flash
    } else if (item.status === 'processing') {
      color.copy(pal.processing);
      intensity += reduced ? 0.2 : 0.3 * (0.5 + 0.5 * Math.sin(t * 2));
    } else if (item.status === 'failed') {
      color.copy(pal.failed);
      intensity += reduced ? 0.4 : (since > FLICKER ? 0.45 * (0.5 + 0.5 * Math.sin(t * 3.5)) : 0);
    } else {
      color.copy(pal.pending);
      intensity = 0.9 * pal.glow;
    }
    if (!reduced) intensity *= 0.97 + 0.03 * Math.sin(t * 1.2 + i); // breathing, barely
    if (deadT > 0) { color.lerp(pal.dead, deadT); intensity *= 1 - 0.75 * deadT; }
    if (hovered) intensity *= 1.3;
    if (!pal.additive) intensity = Math.max(intensity, 1); // on a light scene, dim means paler, not darker

    // position: levitate, hover lift, failure shake and settle, success bounce
    let y = (1 - rise) * -1.9;
    let x = 0;
    let rotZ = 0;
    let scale = 1;
    if (!reduced) y += Math.sin(t * 1.1 + i * 1.7) * 0.05;
    lift.current = THREE.MathUtils.damp(lift.current, hovered ? 0.2 : 0, 8, delta);
    y += lift.current;
    if (item.status === 'failed') {
      const shakeT = since - FLICKER;
      if (!reduced && shakeT > 0 && shakeT < 0.7) x += (rand(Math.floor(t * 60)) - 0.5) * 0.16 * (1 - shakeT / 0.7);
      const settle = reduced ? 1 : easeOutCubic(clamp01((since - FLICKER - 0.3) / 0.6));
      y -= 0.14 * settle;
      rotZ = 0.1 * settle;
    } else if (item.prev === 'failed' && since < HEAL_TIME) {
      const back = 1 - easeOutCubic(clamp01(since / HEAL_TIME));
      y -= 0.14 * back;
      rotZ = 0.1 * back;
    }
    if (item.status === 'success' && item.prev !== 'success' && since < 0.6 && !reduced) {
      scale = 1 + 0.025 * Math.sin(Math.PI * (since / 0.6));
    }
    group.current.position.set(position.x + x, position.y + y, position.z);
    group.current.scale.setScalar(scale);
    const targetX = hovered && !reduced ? -pointer.current.y * 0.35 : 0;
    const targetY = hovered && !reduced ? pointer.current.x * 0.35 : 0;
    tilt.current.rotation.x = THREE.MathUtils.damp(tilt.current.rotation.x, targetX, 8, delta);
    tilt.current.rotation.y = THREE.MathUtils.damp(tilt.current.rotation.y, targetY, 8, delta);
    tilt.current.rotation.z = rotZ;

    // materials
    const opacity = appearT;
    glow.copy(color).multiplyScalar(intensity);
    glass.current.opacity = 0.18 + 0.82 * opacity;
    glass.current.attenuationColor.copy(color).lerp(WHITE, 1 - pal.tint);
    glass.current.emissive.copy(color);
    glass.current.emissiveIntensity = (item.status === 'pending' || deadT > 0.5 ? 0.02 : 0.08) * pal.tint;
    for (const ref of [outlineFront, outlineBack]) {
      const m = ref.current?.material;
      if (m) { m.color.copy(glow); m.opacity = opacity * (ref === outlineBack ? 0.5 : 1); }
    }
    iconRefs.current.forEach((line) => { if (line) { line.material.color.copy(glow); line.material.opacity = opacity; } });

    // circuit traces light up from the centre while processing
    const total = TRACES.length;
    traceRefs.current.forEach((line, k) => {
      if (!line) return;
      let level;
      if (item.status === 'processing') level = reduced ? 0.8 : clamp01((since * 0.9 + (t % 2.4 > 1.6 ? 0 : 0) - k / total) * 3);
      else if (item.status === 'success') level = 0.85;
      else if (item.status === 'failed') level = reduced ? 0.5 : 0.25 + 0.6 * rand(Math.floor(t * 14) + k);
      else level = 0.12;
      if (item.status === 'processing' && !reduced && since > 1.2) level = 0.65 + 0.2 * Math.sin(t * 1.8 - k * 0.5);
      line.material.color.copy(color).multiplyScalar(0.6 + intensity * 0.5 * level);
      line.material.opacity = opacity * level * (1 - deadT * 0.8);
    });

    // cracks spread across the glass after the snap, and close up on recovery
    let crack = 0;
    if (item.status === 'failed') crack = reduced ? 1 : clamp01((since - FLICKER - 0.1) / 0.35);
    else if (item.prev === 'failed') crack = 1 - clamp01(since / HEAL_TIME);
    crackRefs.current.forEach((line, k) => {
      if (!line) return;
      const reach = clamp01(crack * 1.4 - k * 0.08);
      line.material.opacity = reach;
      line.material.color.copy(pal.failed).multiplyScalar(2.2 * pal.glow);
    });

    // connectors spin while the stage is being worked on
    rings.current.forEach((ring) => {
      if (!ring) return;
      ring.material.color.copy(glow);
      ring.material.opacity = opacity;
      if (!reduced && item.status === 'processing') ring.rotation.z += delta * 2.4;
    });
  });

  const onMove = (e) => {
    const local = e.object.worldToLocal(e.point.clone());
    pointer.current = {x: local.x / (TILE / 2), y: local.y / (TILE / 2)};
  };

  return <group ref={group} position={position}>
    <group ref={tilt}>
      <RoundedBox args={[TILE, TILE, DEPTH]} radius={RADIUS} smoothness={4}
        onPointerOver={(e) => { e.stopPropagation(); setHovered(i); document.body.style.cursor = 'pointer'; }}
        onPointerOut={() => { setHovered(null); document.body.style.cursor = ''; }}
        onPointerMove={onMove}
        onClick={(e) => { e.stopPropagation(); onSelect(i); }}>
        <meshPhysicalMaterial ref={glass} transparent transmission={1} thickness={0.9} roughness={pal.roughness} ior={1.45}
          iridescence={0.6} iridescenceIOR={1.25} clearcoat={1} clearcoatRoughness={0.1} color={pal.glass}
          attenuationDistance={pal.attDist} envMapIntensity={1.2} emissiveIntensity={0.08}/>
      </RoundedBox>
      <group position={[0, 0, DEPTH / 2 + 0.004]}>
        <GlowLine points={frame} lineRef={outlineFront} width={1.8}/>
        {icon.map((pts, k) => <GlowLine key={k} points={pts} width={1.8} lineRef={(el) => { iconRefs.current[k] = el; }}/>)}
        {TRACES.map((pts, k) => <GlowLine key={k} points={pts} width={1} lineRef={(el) => { traceRefs.current[k] = el; }}/>)}
        {CRACKS.map((pts, k) => <GlowLine key={k} points={pts} width={1.4} lineRef={(el) => { crackRefs.current[k] = el; }}/>)}
      </group>
      <group position={[0, 0, -DEPTH / 2 - 0.004]}><GlowLine points={frame} lineRef={outlineBack} width={1.2}/></group>
      {ringPlacements.map((ring, k) => <mesh key={k} position={ring.position} quaternion={ring.quaternion} ref={(el) => { rings.current[k] = el; }}>
        <torusGeometry args={[0.13, 0.022, 10, 36, Math.PI * 1.7]}/>
        <meshBasicMaterial transparent toneMapped={false}/>
      </mesh>)}
    </group>

    {/* label under the block: also the keyboard way in */}
    <Html position={[0, -TILE / 2 - 0.58, 0]} center zIndexRange={[30, 10]}>
      <button type="button" data-bs-label={i} className={`bs-label ${stage.status} ${selected ? 'selected' : ''}`}
        onClick={() => onSelect(i)}
        onFocus={() => setHovered(i)} onBlur={() => setHovered(null)}
        onKeyDown={(e) => {
          const step = e.key === 'ArrowRight' || e.key === 'ArrowDown' ? 1 : e.key === 'ArrowLeft' || e.key === 'ArrowUp' ? -1 : 0;
          if (!step) return;
          e.preventDefault();
          e.currentTarget.closest('.bs-root')?.querySelector(`[data-bs-label="${(i + step + n) % n}"]`)?.focus();
        }}>
        <strong>{stage.title}</strong>
        <span>{STATUS_LABELS[stage.status]}</span>
      </button>
    </Html>

    {hovered && !selected && stage.status !== 'failed' && <Html position={[0, TILE / 2 + 0.32, 0]} center zIndexRange={[40, 30]}>
      <div className="bs-tooltip" role="tooltip">{stage.description}</div>
    </Html>}

    {stage.status === 'failed' && <Html position={vertical ? [0, -TILE / 2 - 1.35, 0.3] : [0, TILE / 2 + 0.85, 0]} center zIndexRange={[45, 35]}>
      <div className="bs-error" role="alert">
        <p>{stage.reason || 'This stage did not go through.'}</p>
        {onRetry && <button type="button" className="bs-retry" onClick={onRetry}><RotateCcw size={14}/>Retry</button>}
      </div>
    </Html>}
  </group>;
}

// ---------------------------------------------------------------------------
// A beam between two blocks: two halves that meet in the middle (until they snap)
// ---------------------------------------------------------------------------
const SPARKS = 40;

function Beam({k, from, to, tl, pal, reduced}) {
  const halves = [useRef(), useRef()];
  const cores = [useRef(), useRef()];
  const glows = [useRef(), useRef()];
  const particles = useRef();
  const pulse = useRef();
  const sparks = useRef();
  const dummy = useMemo(() => new THREE.Object3D(), []);
  const col = useMemo(() => new THREE.Color(), []);

  const geo = useMemo(() => {
    const dir = to.clone().sub(from).normalize();
    const start = from.clone().add(dir.clone().multiplyScalar(TILE / 2 + 0.06));
    const end = to.clone().sub(dir.clone().multiplyScalar(TILE / 2 + 0.06));
    const length = start.distanceTo(end);
    const perp = new THREE.Vector3().crossVectors(dir, Z).normalize();
    if (perp.lengthSq() < 0.01) perp.set(1, 0, 0);
    const quat = new THREE.Quaternion().setFromUnitVectors(UP, dir);
    const mid = start.clone().add(end).multiplyScalar(0.5);
    const velocities = Array.from({length: SPARKS}, (_, s) => new THREE.Vector3(
      (rand(s * 3 + k) - 0.5) * 3.2, rand(s * 3 + 1 + k) * 2.6 + 0.4, (rand(s * 3 + 2 + k) - 0.5) * 3.2));
    return {dir, start, end, length, perp, quat, mid, velocities};
  }, [from, to, k]);

  useFrame((_, rawDelta) => {
    const t = now();
    const delta = Math.min(rawDelta, MAX_DELTA);
    const state = tl.current;
    const a = state.items[k];
    const b = state.items[k + 1];
    const fail = failure(state);
    const n = state.items.length;

    // grow in after the blocks have risen
    const growStart = state.appearAt === null ? Infinity : state.appearAt + n * APPEAR_STAGGER + 0.2 + k * 0.12;
    const grow = reduced ? (state.appearAt === null ? 0 : 1) : easeOutCubic(clamp01((t - growStart) / 0.45));

    // what this link is doing
    const breaking = fail.index === k + 1;
    const deadLink = fail.index >= 0 && k + 1 > fail.index;
    const healing = !breaking && b.prev === 'failed' && b.at !== null && t - b.at < HEAL_TIME;
    const sinceFail = t - fail.at;
    const live = a.status === 'success' && !breaking && !deadLink;

    // colour: carries the colour of the stage it leaves, red while breaking, dark when dead
    col.copy(live ? (b.status === 'processing' ? pal.processing : pal.success) : pal.pending);
    let opacity = live ? 1 : 0.35;
    let intensity = (live ? 2.4 : 0.9) * pal.glow;
    let split = 0;
    if (breaking) {
      const flick = clamp01(sinceFail / FLICKER);
      col.lerp(pal.failed, reduced ? 1 : flick);
      intensity = 2.6 * pal.glow;
      if (!reduced && sinceFail < FLICKER) opacity = 0.25 + 0.75 * rand(Math.floor(t * 40) + k); // glitch
      split = reduced ? 0.35 : easeOutCubic(clamp01((sinceFail - FLICKER) / SNAP_TIME));
      if (!reduced) opacity *= 1 - 0.75 * split;
      else opacity = 0.7;
    } else if (deadLink) {
      const fade = reduced ? 1 : clamp01((t - (fail.at + FLICKER + 0.5 + (k + 1 - fail.index) * 0.2)) / 0.4);
      col.lerp(pal.dead, fade);
      opacity *= 1 - 0.85 * fade;
      intensity *= 1 - 0.7 * fade;
    } else if (healing) {
      split = 1 - easeOutCubic(clamp01((t - b.at) / HEAL_TIME));
    }
    if (!reduced && live) intensity *= 0.95 + 0.05 * Math.sin(t * 1.5 + k);
    if (!pal.additive) intensity = Math.max(intensity, 1);

    // the two halves: meet in the middle, or fly apart around the break
    const half = geo.length / 2;
    for (let h = 0; h < 2; h++) {
      const g = halves[h].current;
      const covered = h === 0 ? Math.min(grow, 0.5) : Math.max(grow - 0.5, 0);
      const len = Math.max(covered * geo.length, 0.0001);
      const startAt = h === 0 ? 0 : half;
      const sign = h === 0 ? -1 : 1;
      g.position.copy(geo.start).addScaledVector(geo.dir, startAt + len / 2)
        .addScaledVector(geo.dir, sign * split * 0.7)
        .addScaledVector(UP, split * 0.25 * (h === 0 ? 1 : -0.6));
      g.quaternion.copy(geo.quat);
      g.rotateOnWorldAxis(geo.perp, sign * split * 0.9);
      g.scale.set(1, len, 1);
      g.visible = covered > 0.001;
      cores[h].current.color.copy(col).multiplyScalar(intensity);
      cores[h].current.opacity = opacity;
      glows[h].current.color.copy(col).multiplyScalar(intensity * 0.6);
      glows[h].current.opacity = opacity * 0.22;
    }

    // energy particles running along a live beam
    const count = 5;
    for (let p = 0; p < count; p++) {
      const u = (t * 0.42 + p / count) % 1;
      const on = live && !reduced && grow >= 1;
      dummy.position.copy(geo.start).addScaledVector(geo.dir, u * geo.length);
      dummy.scale.setScalar(on ? 0.9 + 0.4 * Math.sin(u * Math.PI) : 0.0001);
      dummy.updateMatrix();
      particles.current.setMatrixAt(p, dummy.matrix);
    }
    particles.current.instanceMatrix.needsUpdate = true;
    particles.current.material.color.copy(col).multiplyScalar(3.2 * pal.glow);

    // success: a bright impulse runs to the next block and wakes it up
    const pulseT = a.status === 'success' && a.prev !== 'success' && a.at !== null ? (t - a.at - 0.15) / 0.7 : -1;
    if (pulseT > 0 && pulseT < 1 && !reduced) {
      pulse.current.visible = true;
      pulse.current.position.copy(geo.start).addScaledVector(geo.dir, pulseT * geo.length);
      pulse.current.scale.setScalar(1 + 0.6 * Math.sin(pulseT * Math.PI));
      pulse.current.material.color.copy(pal.success).multiplyScalar(3 * pal.glow);
    } else pulse.current.visible = false;

    // sparks fly from the break
    const sparkT = breaking && !reduced ? sinceFail - FLICKER : -1;
    for (let s = 0; s < SPARKS; s++) {
      if (sparkT > 0 && sparkT < 1) {
        const v = geo.velocities[s];
        dummy.position.copy(geo.mid).addScaledVector(v, sparkT * 0.55);
        dummy.position.y -= 2.2 * sparkT * sparkT;
        dummy.scale.setScalar((1 - sparkT) * (0.6 + rand(s) * 0.8));
      } else dummy.scale.setScalar(0.0001);
      dummy.position.x += 0;
      dummy.updateMatrix();
      sparks.current.setMatrixAt(s, dummy.matrix);
    }
    sparks.current.instanceMatrix.needsUpdate = true;
    sparks.current.material.color.copy(pal.spark).lerp(pal.failed, clamp01(sparkT)).multiplyScalar(4 * pal.glow);
  });

  return <group>
    {[0, 1].map((h) => <group key={h} ref={halves[h]}>
      <mesh><cylinderGeometry args={[0.028, 0.028, 1, 10, 1, true]}/><meshBasicMaterial ref={cores[h]} transparent toneMapped={false}/></mesh>
      <mesh><cylinderGeometry args={[0.085, 0.085, 1, 14, 1, true]}/><meshBasicMaterial ref={glows[h]} transparent depthWrite={false} blending={pal.additive ? THREE.AdditiveBlending : THREE.NormalBlending} toneMapped={false}/></mesh>
    </group>)}
    <instancedMesh ref={particles} args={[null, null, 5]}>
      <sphereGeometry args={[0.04, 10, 10]}/>
      <meshBasicMaterial toneMapped={false}/>
    </instancedMesh>
    <mesh ref={pulse} visible={false}><sphereGeometry args={[0.06, 14, 14]}/><meshBasicMaterial toneMapped={false}/></mesh>
    <instancedMesh ref={sparks} args={[null, null, SPARKS]}>
      <sphereGeometry args={[0.022, 6, 6]}/>
      <meshBasicMaterial toneMapped={false}/>
    </instancedMesh>
  </group>;
}

// ---------------------------------------------------------------------------
// Floor with soft pools of light under the blocks
// ---------------------------------------------------------------------------
function usePoolTexture() {
  return useMemo(() => {
    const canvas = document.createElement('canvas');
    canvas.width = canvas.height = 128;
    const ctx = canvas.getContext('2d');
    const g = ctx.createRadialGradient(64, 64, 0, 64, 64, 64);
    g.addColorStop(0, 'rgba(255,255,255,1)');
    g.addColorStop(0.4, 'rgba(255,255,255,.35)');
    g.addColorStop(1, 'rgba(255,255,255,0)');
    ctx.fillStyle = g;
    ctx.fillRect(0, 0, 128, 128);
    const texture = new THREE.CanvasTexture(canvas);
    texture.colorSpace = THREE.SRGBColorSpace;
    return texture;
  }, []);
}

function Floor({positions, tl, pal, reduced}) {
  const texture = usePoolTexture();
  const pools = useRef([]);
  useFrame(() => {
    const t = now();
    const fail = failure(tl.current);
    pools.current.forEach((pool, i) => {
      if (!pool) return;
      const item = tl.current.items[i];
      const dead = fail.index >= 0 && i > fail.index;
      const c = dead ? pal.dead : pal[item.status] || pal.pending;
      pool.material.color.copy(c);
      const appear = tl.current.appearAt === null ? 0 : clamp01((t - tl.current.appearAt - i * APPEAR_STAGGER) / APPEAR_TIME);
      pool.material.opacity = appear * (dead ? 0.15 : item.status === 'pending' ? 0.25 : 0.55) * (reduced ? 1 : 0.96 + 0.04 * Math.sin(t * 1.2 + i));
    });
  });
  return <group>
    <mesh rotation-x={-Math.PI / 2} position={[0, FLOOR_Y, 0]}>
      <planeGeometry args={[60, 60]}/>
      {pal.mirror > 0
        ? <MeshReflectorMaterial blur={[300, 80]} resolution={512} mixBlur={1} mixStrength={pal.mix} roughness={0.85}
          depthScale={1.1} minDepthThreshold={0.4} maxDepthThreshold={1.4} color={pal.floor} metalness={pal.metal} mirror={pal.mirror}/>
        : <meshStandardMaterial color={pal.floor} roughness={1} metalness={0}/>}
    </mesh>
    {positions.map((p, i) => <mesh key={i} ref={(el) => { pools.current[i] = el; }} rotation-x={-Math.PI / 2} position={[p.x, FLOOR_Y + 0.01, p.z]}>
      <planeGeometry args={[3.2, 3.2]}/>
      <meshBasicMaterial map={texture} transparent depthWrite={false} blending={pal.additive ? THREE.AdditiveBlending : THREE.NormalBlending} toneMapped={false}/>
    </mesh>)}
  </group>;
}

// ---------------------------------------------------------------------------
// Camera: dolly in on appear, follow the pointer a little, focus a selected block
// ---------------------------------------------------------------------------
function CameraRig({positions, vertical, selected, tl, reduced, rowTurn}) {
  const {camera, size} = useThree();
  const target = useMemo(() => new THREE.Vector3(), []);
  const desired = useMemo(() => new THREE.Vector3(), []);
  const look = useMemo(() => new THREE.Vector3(), []);
  const world = useMemo(() => new THREE.Vector3(), []);

  const base = useMemo(() => {
    const n = positions.length;
    const aspect = size.width / Math.max(size.height, 1);
    const fov = THREE.MathUtils.degToRad(camera.fov);
    if (vertical) {
      const h = (n - 1) * V_SPACING + TILE + 1.4;
      const dist = (h / 2) / Math.tan(fov / 2) + 0.6;
      return {pos: new THREE.Vector3(0.5, 0.5, dist), look: new THREE.Vector3(0, -0.1, 0)};
    }
    // fit the row's width (the near end is closer, so add half the row's depth) and the height
    const w = ((n - 1) * SPACING + TILE) * Math.cos(rowTurn) + 1.2;
    const depth = (n - 1) * SPACING * Math.sin(Math.abs(rowTurn));
    const byWidth = (w * 0.62) / (Math.tan(fov / 2) * aspect) + depth * 0.5;
    const byHeight = ((TILE + 2.2) * 0.6) / Math.tan(fov / 2);
    const dist = Math.max(byWidth, byHeight);
    return {pos: new THREE.Vector3(0.6, dist * 0.3, dist), look: new THREE.Vector3(0.35, -0.3, 0)};
  }, [positions.length, size.width, size.height, vertical, camera.fov, rowTurn]);

  useEffect(() => {
    camera.position.copy(base.pos).multiplyScalar(reduced ? 1 : 1.35);
    look.copy(base.look);
    camera.lookAt(look);
  }, [base, camera, look, reduced]);

  useFrame(({pointer}, rawDelta) => {
    const t = now();
    const delta = Math.min(rawDelta, MAX_DELTA);
    const appearAt = tl.current.appearAt;
    const dolly = appearAt === null || reduced ? 1 : easeOutCubic(clamp01((t - appearAt - 0.3) / 1.8));
    if (selected !== null && positions[selected]) {
      world.copy(positions[selected]);
      if (!vertical) world.applyAxisAngle(UP, rowTurn);
      // leave room for the details panel on the right (below it on phones)
      target.copy(world).add(vertical ? new THREE.Vector3(0, -0.6, 0) : new THREE.Vector3(0.85, 0, 0));
      desired.copy(target).add(new THREE.Vector3(0.4, 0.45, vertical ? 5.2 : 4.4));
    } else {
      target.copy(base.look);
      desired.copy(base.pos).multiplyScalar(1 + 0.35 * (1 - dolly));
      if (!reduced) { desired.x += pointer.x * 0.5; desired.y += pointer.y * 0.3; }
    }
    const speed = reduced ? 20 : 3.2;
    camera.position.x = THREE.MathUtils.damp(camera.position.x, desired.x, speed, delta);
    camera.position.y = THREE.MathUtils.damp(camera.position.y, desired.y, speed, delta);
    camera.position.z = THREE.MathUtils.damp(camera.position.z, desired.z, speed, delta);
    look.x = THREE.MathUtils.damp(look.x, target.x, speed, delta);
    look.y = THREE.MathUtils.damp(look.y, target.y, speed, delta);
    look.z = THREE.MathUtils.damp(look.z, target.z, speed, delta);
    camera.lookAt(look);
  });
  return null;
}

// ---------------------------------------------------------------------------
// Post: bloom on the glow, a vignette, and a short chromatic glitch when the chain breaks
// ---------------------------------------------------------------------------
function Effects({tl, pal, reduced, multisampling}) {
  const aberration = useRef();
  const offset = useMemo(() => new THREE.Vector2(0, 0), []);
  useFrame(() => {
    const t = now();
    const fail = failure(tl.current);
    let amount = 0;
    if (!reduced && fail.index >= 0) {
      const s = t - fail.at - FLICKER;
      if (s > -0.3 && s < 0.6) amount = 0.004 * (1 - Math.abs(s - 0.05) / 0.6) * (0.6 + 0.4 * rand(Math.floor(t * 30)));
    }
    offset.set(Math.max(amount, 0), Math.max(amount, 0) * 0.6);
    if (aberration.current) aberration.current.offset = offset;
  });
  return <EffectComposer multisampling={multisampling} enableNormalPass={false}>
    <Bloom mipmapBlur intensity={pal.bloom} luminanceThreshold={0.9} luminanceSmoothing={0.2}/>
    <ChromaticAberration ref={aberration} offset={offset} radialModulation={false} modulationOffset={0}/>
    <Vignette offset={0.25} darkness={pal.vignette}/>
  </EffectComposer>;
}

// ---------------------------------------------------------------------------
// Scene
// ---------------------------------------------------------------------------
function Scene({stages, active, reducedMotion, vertical, selected, onSelect, onRetry, theme}) {
  const [hovered, setHovered] = useState(null);
  const pal = useMemo(() => makePalette(theme), [theme]);
  const tl = useTimeline(stages, active);
  const positions = useMemo(() => layout(stages.length, vertical), [stages.length, vertical]);
  const rowTurn = vertical ? 0 : ROW_TURN;
  const dirs = useMemo(() => positions.map((p, i) => (i < positions.length - 1 ? positions[i + 1].clone().sub(p).normalize() : null)), [positions]);

  return <>
    <color attach="background" args={[pal.bg]}/>
    <fog attach="fog" args={[pal.bg, 10, 30]}/>
    <ambientLight intensity={pal.ambient}/>
    <directionalLight position={[-4, 6, 5]} intensity={0.6} color="#cfeee0"/>
    <pointLight position={[0, 3, 4]} intensity={8} distance={14} color={pal.key}/>
    <Environment resolution={256} frames={1}>
      <Lightformer form="rect" intensity={2.2} position={[0, 5, -8]} scale={[14, 3, 1]} color="#bfe9ff"/>
      <Lightformer form="rect" intensity={1.4} position={[-7, 2, 2]} rotation-y={Math.PI / 2} scale={[8, 2, 1]} color="#3cf2a0"/>
      <Lightformer form="rect" intensity={1.2} position={[7, 1, 3]} rotation-y={-Math.PI / 2} scale={[8, 2, 1]} color="#3cc8f2"/>
      <Lightformer form="circle" intensity={3} position={[0, 7, 2]} scale={3} color="#ffffff"/>
    </Environment>

    <group rotation-y={rowTurn}>
      {stages.map((stage, i) => <Block key={stage.id} i={i} n={stages.length} stage={stage} position={positions[i]}
        prevDir={i > 0 ? dirs[i - 1] : null} nextDir={dirs[i]} tl={tl} pal={pal} reduced={reducedMotion} vertical={vertical}
        hovered={hovered === i} selected={selected === i} setHovered={setHovered} onSelect={onSelect} onRetry={onRetry}/>)}
      {positions.slice(0, -1).map((p, k) => <Beam key={`${k}-${positions.length}`} k={k} from={p} to={positions[k + 1]} tl={tl} pal={pal} reduced={reducedMotion}/>)}
      {!vertical && <Floor positions={positions} tl={tl} pal={pal} reduced={reducedMotion}/>}
    </group>

    <CameraRig positions={positions} vertical={vertical} selected={selected} tl={tl} reduced={reducedMotion} rowTurn={rowTurn}/>
    <Effects tl={tl} pal={pal} reduced={reducedMotion} multisampling={vertical ? 0 : 4}/>
  </>;
}

export default function BlockchainScene(props) {
  const {active, onSelect, selected} = props;
  return <div className="bs-canvas">
    <Canvas dpr={[1, 2]} frameloop={active ? 'always' : 'never'} camera={{fov: 35, position: [0, 3, 12], near: 0.1, far: 80}}
      gl={{antialias: false, powerPreference: 'high-performance'}}
      onPointerMissed={() => { if (selected !== null) onSelect(selected); }}>
      <Scene {...props}/>
    </Canvas>
  </div>;
}
