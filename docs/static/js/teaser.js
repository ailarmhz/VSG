// Teaser: the visual-state graph of one stream, write by write, from the stored write log (static/teaser/data.json).
// Ordinary writes play quickly; at the key writes the animation slows down, zooms in and highlights what changes.
(function () {
  const root = document.getElementById('teaser');
  if (!root) return;
  const $ = (id) => document.getElementById(id);
  const NS = 'http://www.w3.org/2000/svg';
  const C = {new: '#2E9E5B', merged: '#3F78D0', idle: '#B9B9B5', ok: '#2E8B4F', bad: '#C0392B', ink: '#17181C', gold: '#E8A800'};
  const POS = {screwdriver_0: [0.50, 0.70], wrench_0: [0.85, 0.55], motorcycle_1: [0.85, 0.22],
               workbench_0: [0.50, 0.10], blue_gloves_0: [0.15, 0.22], person_0: [0.15, 0.55]};
  const CAP = {screwdriver_0: 'above', wrench_0: 'above', person_0: 'above', motorcycle_1: 'below',
               workbench_0: 'below', blue_gloves_0: 'below'};
  const VW = 520, VH = 400, R = 33;
  const xy = (n) => [40 + POS[n][0] * (VW - 80), 330 - (POS[n][1] - 0.10) / 0.60 * 262];
  const FAST = 0.75;                          // seconds per ordinary write
  const mmss = (t) => Math.floor(t / 60) + ':' + String(Math.floor(t % 60)).padStart(2, '0');
  const ease = (u) => { u = Math.min(1, Math.max(0, u)); return u * u * (3 - 2 * u); };
  const lerp = (a, b, u) => a + (b - a) * u;
  const ekey = (a, b) => [a, b].sort().join('|');

  let D, seq = [], si = 0, u = 0, playing = false, last = 0;
  const svg = $('tgraph');

  // ---------------------------------------------------------------- scenes at the key writes
  const SCENES = {
    10: [
      {dur: 2.4, title: 'Writing', line: 'Every 10 s a frozen writer reads the last clip of 5 frames. No question is known.',
       fx: (u) => ({frameHl: 1, build: 0})},
      {dur: 4.2, title: 'Writing', line: 'It writes triplets. Each object becomes a node, each relation an edge.',
       fx: (u) => ({build: u})},
      {dur: 2.6, title: 'Writing', line: 'It also writes one caption, which starts the event log.',
       fx: (u) => ({logHl: 10})},
    ],
    20: [
      {dur: 2.6, title: 'Relational matching', line: '0:20: the screwdriver is mentioned again. Same object, or a new one?',
       fx: (u) => ({base: -1, zoom: ['screwdriver_0', u], ghost: {a: ease(u / 0.5), slide: 0}, dimExcept: ['screwdriver_0', 'person_0', 'workbench_0']})},
      {dur: 3.0, title: 'Relational matching', line: 'Its relations match the stored node: held by the person, on the workbench.',
       fx: (u) => ({base: -1, zoom: ['screwdriver_0', 1], ghost: {a: 1, slide: 0, edges: ease(u / 0.6)},
                     greenEdges: [['person_0', 'screwdriver_0'], ['screwdriver_0', 'workbench_0']], dimExcept: ['screwdriver_0', 'person_0', 'workbench_0']})},
      {dur: 3.0, title: 'Relational matching', line: 'Similarity above θ = 0.55, so the mention updates the stored node: screwdriver ×2.',
       fx: (u) => (u < 0.4 ? {base: -1, zoom: ['screwdriver_0', 1], ghost: {a: 1 - ease(u / 0.4) * 0.6, slide: ease(u / 0.4)}, dimExcept: ['screwdriver_0']}
                           : {zoom: ['screwdriver_0', 1 - ease((u - 0.75) / 0.25)], hl: ['screwdriver_0'], pulse: (u - 0.4) / 0.6})},
    ],
    170: [
      {dur: 3.2, title: 'Event log', line: '2:50 caption: “… uses wrench to tighten bolt …”', fx: (u) => ({logHl: 170})},
      {dur: 2.6, title: 'Event log', line: 'The wrench is used often in this video; its node has been seen ×13.',
       fx: (u) => ({zoom: ['wrench_0', u], hl: ['wrench_0'], dimExcept: ['wrench_0', 'person_0']})},
    ],
    250: [
      {dur: 2.6, title: 'Grounding', line: 'OWLv2 localizes the described screwdriver in the current frame.', fx: (u) => ({box: u})},
      {dur: 2.4, title: 'Grounding', line: 'Its crop is stored with the screwdriver node.',
       fx: (u) => ({box: 1, fly: u, zoom: ['screwdriver_0', u], hl: ['screwdriver_0'], dimExcept: ['screwdriver_0']})},
      {dur: 5.0, title: 'State history', line: 'Descriptions are appended, not overwritten: the node keeps a history of its state.',
       fx: (u) => ({zoom: ['screwdriver_0', 1 - ease((u - 0.85) / 0.15)], card: u, dimExcept: ['screwdriver_0']})},
    ],
    330: [
      {dur: 3.2, title: 'The key moment', line: '5:30 caption: “… uses screwdriver on motorcycle …”', fx: (u) => ({logHl: 330})},
      {dur: 3.0, title: 'The key moment', line: 'Reading every frame so far would cost ≈64K tokens. VSG reads at most 3.5K.',
       fx: (u) => ({meterHl: 1, logHl: 330})},
      {dur: 3.0, title: 'The key moment', line: 'It is written 79 s before a question that has not been asked yet.',
       fx: (u) => ({logHl: 330, gap: u})},
    ],
  };
  const END = [
    {dur: 3.0, title: 'Question at 6:49', line: '“What tool did I use to tighten the screw?” A recent-frame window no longer reaches 5:30.', fx: (u) => ({end: 1, window: 1})},
    {dur: 3.2, title: 'Question at 6:49', line: 'VSG reads its memory within 3,510 tokens; the event log includes the 5:30 line.', fx: (u) => ({end: 1, logHl: 330, dimLog: 1, gap: 1})},
    {dur: 4.0, title: 'Answer', line: 'VSG answers A. screwdriver, correct.', fx: (u) => ({end: 1, answer: 1, logHl: 330, dimLog: 1, gap: 1})},
  ];

  function buildSeq() {
    seq = [];
    D.steps.forEach((st, k) => {
      if (SCENES[st.t]) SCENES[st.t].forEach((b, j) => seq.push({k, beat: b, j}));
      else seq.push({k, beat: null});
    });
    END.forEach((b, j) => seq.push({k: D.steps.length - 1, beat: b, j, end: true}));
  }

  // ---------------------------------------------------------------- drawing
  function el(tag, attrs, parent) {
    const e = document.createElementNS(NS, tag);
    for (const a in attrs) e.setAttribute(a, attrs[a]);
    (parent || svg).appendChild(e);
    return e;
  }

  function setZoom(fx) {
    let vb = [0, 0, VW, VH];
    if (fx.zoom) {
      const [x, y] = xy(fx.zoom[0]), z = ease(fx.zoom[1]), w = VW / 1.7, h = VH / 1.7;
      const cx = Math.min(Math.max(x, w / 2), VW - w / 2), cy = Math.min(Math.max(y + 20, h / 2), VH - h / 2);
      vb = [lerp(0, cx - w / 2, z), lerp(0, cy - h / 2, z), lerp(VW, w, z), lerp(VH, h, z)];
    }
    svg.setAttribute('viewBox', vb.map((v) => v.toFixed(1)).join(' '));
  }

  function drawGraph(st, prev, u, fx, still) {
    svg.innerHTML = '';
    setZoom(fx);
    const defs = el('defs', {});
    [['b', C.merged], ['g', '#C4C4BF'], ['k', C.ok]].forEach(([id, col]) => {
      const m = el('marker', {id: 'ah' + id, viewBox: '0 0 10 10', refX: 9, refY: 5, markerWidth: 6, markerHeight: 6, orient: 'auto'}, defs);
      el('path', {d: 'M0,0 L10,5 L0,10 z', fill: col}, m);
    });
    let shown = Object.keys(st.nodes);
    let edges = st.edges.slice();
    if (fx.build !== undefined) {                       // first write: one relation (and its nodes) at a time
      const total = edges.length, pos = fx.build * total;
      const n = Math.min(total, Math.floor(pos));
      edges = edges.slice(0, Math.min(total, n + 1)).map((e, i) => Object.assign({}, e, {grow: i < n ? 1 : pos - n}));
      if (fx.build === 0) edges = [];
      const nodesIn = new Set();
      edges.forEach((e) => { nodesIn.add(e.s); nodesIn.add(e.o); });
      shown = shown.filter((x) => nodesIn.has(x));
    }
    const dim = fx.dimExcept ? new Set(fx.dimExcept) : null;
    shown.forEach((n) => {
      const cp = el('clipPath', {id: 'cp' + n}, defs);
      const [x, y] = xy(n);
      el('circle', {cx: x, cy: y, r: R - 2}, cp);
    });
    const green = new Set((fx.greenEdges || []).map(([a, b]) => ekey(a, b)));
    edges.sort((a, b) => a.live - b.live).forEach((e) => {
      const [x1, y1] = xy(e.s), [x2, y2] = xy(e.o);
      const L = Math.hypot(x2 - x1, y2 - y1), ux = (x2 - x1) / L, uy = (y2 - y1) / L;
      const isNew = prev && !prev.edges.some((p) => ekey(p.s, p.o) === ekey(e.s, e.o));
      const f = e.grow !== undefined ? ease(e.grow / 0.8) : (isNew ? ease(u / 0.7) : 1);
      const sx = x1 + ux * (R + 4), sy = y1 + uy * (R + 4);
      const ex = sx + (x2 - ux * (R + 6) - sx) * f, ey = sy + (y2 - uy * (R + 6) - sy) * f;
      const g = green.has(ekey(e.s, e.o)), live = e.live && !fx.end;
      const faded = dim && !(dim.has(e.s) && dim.has(e.o));
      el('line', {x1: sx, y1: sy, x2: ex, y2: ey, stroke: g ? C.ok : live ? C.merged : '#C9C9C4', 'stroke-width': g ? 3.6 : live ? 2.6 : 1.4,
                  opacity: faded ? 0.15 : 1, 'marker-end': f > 0.95 ? `url(#ah${g ? 'k' : live ? 'b' : 'g'})` : ''});
    });
    let lab = edges.filter((e) => (e.grow !== undefined ? e.grow > 0.6 : green.has(ekey(e.s, e.o))));
    if (!lab.length && !fx.end && !dim) {
      const score = (e) => (e.s === 'screwdriver_0' || e.o === 'screwdriver_0') * 2 + (e.s === 'wrench_0' || e.o === 'wrench_0');
      lab = edges.filter((e) => e.live).sort((a, b) => score(b) - score(a)).slice(0, 2);
    }
    lab.forEach((e, i) => {
      const [x1, y1] = xy(e.s), [x2, y2] = xy(e.o);
      const t = 0.5 + (i % 2 ? -0.12 : 0.05), x = x1 + (x2 - x1) * t, y = y1 + (y2 - y1) * t;
      const gr = green.has(ekey(e.s, e.o));
      const g = el('g', {});
      const w = e.p.length * 6.8 + 12;
      el('rect', {x: x - w / 2, y: y - 10, width: w, height: 19, rx: 4, fill: '#fff'}, g);
      const tx = el('text', {x, y: y + 4, 'text-anchor': 'middle', 'font-size': 13, 'font-weight': gr ? 700 : 400, fill: gr ? C.ok : C.merged}, g);
      tx.textContent = e.p;
    });
    const ph = performance.now() / 1000;
    shown.forEach((n) => {
      const nd = st.nodes[n], [x, y] = xy(n);
      const mine = edges.filter((e) => e.s === n || e.o === n);
      const grow = fx.build !== undefined && mine.length ? Math.max(...mine.map((e) => e.grow)) : 1;
      const isNew = prev && !prev.nodes[n] && fx.build === undefined;
      const s = fx.build !== undefined ? ease(grow / 0.4) : isNew && !still ? ease(u / 0.5) : 1;
      const g = el('g', {transform: `translate(${x},${y}) scale(${Math.max(0.01, s)}) translate(${-x},${-y})`, opacity: dim && !dim.has(n) ? 0.2 : 1});
      if (nd.img) el('image', {href: 'static/teaser/c_' + nd.img, x: x - R, y: y - R, width: 2 * R, height: 2 * R,
                               'clip-path': `url(#cp${n})`, preserveAspectRatio: 'xMidYMid slice'}, g);
      else el('circle', {cx: x, cy: y, r: R - 2, fill: '#ECECEA'}, g);
      const state = fx.end ? 'idle' : nd.s;
      el('circle', {cx: x, cy: y, r: R, fill: 'none', stroke: C[state], 'stroke-width': state === 'idle' ? 3 : 5.5}, g);
      if (state !== 'idle' && !fx.hl && !fx.dimExcept && u < 1 && !still) {
        el('circle', {cx: x, cy: y, r: R + 4 + 14 * ease(u), fill: 'none', stroke: C[state], 'stroke-width': 3, opacity: 0.6 * (1 - ease(u))}, g);
      }
      const t = el('text', {x, y: CAP[n] === 'above' ? y - R - 9 : y + R + 19, 'text-anchor': 'middle', 'font-size': 14.5, 'font-weight': 700, fill: C.ink}, g);
      t.textContent = `${D.names[n]} ×${nd.c}`;
      if (fx.hl && fx.hl.includes(n)) {
        el('circle', {cx: x, cy: y, r: R + 8 + 2.5 * Math.sin(ph * 6), fill: 'none', stroke: C.gold, 'stroke-width': 4.5}, g);
      }
      const pu = fx.pulse !== undefined ? (fx.hl && !fx.hl.includes(n) ? -1 : fx.pulse) : (state === 'merged' && !still && !fx.dimExcept ? u : -1);
      if (pu >= 0 && pu < 1 && state === 'merged') {
        const b = el('g', {opacity: 1 - ease((pu - 0.55) / 0.45)});
        el('rect', {x: x + R + 3, y: y - 9 - 12 * ease(pu), width: 26, height: 18, rx: 5, fill: C.merged}, b);
        const p = el('text', {x: x + R + 16, y: y + 4 - 12 * ease(pu), 'text-anchor': 'middle', 'font-size': 12, 'font-weight': 700, fill: '#fff'}, b);
        p.textContent = '+1';
      }
    });
    if (fx.ghost) {                                     // a new mention, compared with the stored node (0:20)
      const [nx, ny] = xy('screwdriver_0'), gx0 = nx + 105, gy0 = ny + 10;
      const gx = lerp(gx0, nx, fx.ghost.slide), gy = lerp(gy0, ny, fx.ghost.slide);
      const g = el('g', {opacity: fx.ghost.a});
      if (fx.ghost.edges) {
        ['person_0', 'workbench_0'].forEach((tgt) => {
          const [tx, ty] = xy(tgt), L = Math.hypot(tx - gx, ty - gy), f = fx.ghost.edges;
          el('line', {x1: gx + (tx - gx) / L * (R + 3), y1: gy + (ty - gy) / L * (R + 3),
                      x2: gx + (tx - gx) * f - (tx - gx) / L * (R + 3) * f, y2: gy + (ty - gy) * f - (ty - gy) / L * (R + 3) * f,
                      stroke: C.ok, 'stroke-width': 3, 'stroke-dasharray': '6 5'}, g);
        });
      }
      el('circle', {cx: gx, cy: gy, r: R, fill: '#FFF8E0', stroke: C.gold, 'stroke-width': 4, 'stroke-dasharray': '7 5'}, g);
      const t1 = el('text', {x: gx, y: gy - 2, 'text-anchor': 'middle', 'font-size': 12, 'font-weight': 700, fill: C.ink}, g);
      t1.textContent = 'new';
      const t2 = el('text', {x: gx, y: gy + 13, 'text-anchor': 'middle', 'font-size': 12, fill: C.ink}, g);
      t2.textContent = 'mention';
    }
  }

  function drawLog(k, fx) {
    const box = $('tlog');
    box.innerHTML = '';
    let lines = D.steps.slice(0, k + 1).filter((s, i) => i >= k - 3 || s.t === 170 || s.t === 330).slice(-5);
    if (fx.build !== undefined) lines = [];
    lines.forEach((s) => {
      const d = document.createElement('div');
      d.className = 'ln' + (s.t === 330 ? ' ev' : s.t === 170 ? ' dis' : '') + (s === D.steps[k] && !fx.end ? ' now' : '')
        + (fx.logHl === s.t ? ' hl' : '') + (fx.dimLog && s.t !== 330 ? ' dim' : '');
      d.innerHTML = `<code>${mmss(s.t)}</code>${s.cap}`;
      box.appendChild(d);
    });
  }

  function drawOverlays(fx) {
    const b = $('tbox');
    if (fx.box !== undefined && D.ground) {
      const [x0, y0, x1, y1] = D.ground.box, g = ease(fx.box), cx = (x0 + x1) / 2, cy = (y0 + y1) / 2;
      const w = (x1 - x0) * (0.4 + 0.6 * g), h = (y1 - y0) * (0.4 + 0.6 * g);
      Object.assign(b.style, {left: (cx - w / 2) * 100 + '%', top: (cy - h / 2) * 100 + '%', width: w * 100 + '%', height: h * 100 + '%', opacity: g});
      b.hidden = false;
      $('tboxlab').textContent = `OWLv2: screwdriver ${D.ground.score}`;
      $('tboxlab').style.opacity = g >= 1 ? 1 : 0;
    } else b.hidden = true;
    const f = $('tfly');
    if (fx.fly !== undefined && fx.fly < 1) {
      const fr = $('tframe').getBoundingClientRect(), rr = root.getBoundingClientRect();
      const [x0, y0, x1, y1] = D.ground.box;
      const sx = fr.left + fr.width * (x0 + x1) / 2 - rr.left, sy = fr.top + fr.height * (y0 + y1) / 2 - rr.top;
      const pt = svg.createSVGPoint(), [nx, ny] = xy('screwdriver_0');
      pt.x = nx; pt.y = ny;
      const sp = pt.matrixTransform(svg.getScreenCTM());
      const e = ease(fx.fly / 0.8);
      Object.assign(f.style, {left: lerp(sx, sp.x - rr.left, e) - 32 + 'px', top: lerp(sy, sp.y - rr.top, e) - 32 + 'px',
                              opacity: fx.fly > 0.85 ? (1 - fx.fly) / 0.15 : 1});
      if (!f.src.endsWith(D.ground.img)) f.src = 'static/teaser/c_' + D.ground.img;
      f.hidden = false;
    } else f.hidden = true;
    const card = $('tcard');
    if (fx.card !== undefined) {
      card.hidden = false;
      card.style.opacity = ease(fx.card / 0.08) * (1 - ease((fx.card - 0.88) / 0.12));
      const n = Math.min(D.hist.length, 1 + Math.floor(fx.card / 0.22));
      card.innerHTML = '<b>screwdriver · descriptions appended</b>' + D.hist.slice(0, n).map((h) =>
        `<div class="hrow">${h.img ? `<img src="static/teaser/c_${h.img}" alt="">` : '<span class="nocrop">no crop</span>'}` +
        `<code>${mmss(h.t)}</code><span>“${h.text}”</span></div>`).join('');
    } else card.hidden = true;
    const gp = $('tgap');
    if (fx.gap !== undefined) {
      const g = ease(fx.gap);
      gp.hidden = false;
      gp.style.left = (100 * 330 / D.T) + '%';
      gp.style.width = (100 * (D.T - 330) / D.T) * g + '%';
      gp.querySelector('span').style.opacity = g >= 1 ? 1 : 0;
    } else gp.hidden = true;
    $('twin').hidden = !fx.window;
    $('tframewrap').classList.toggle('hl', !!fx.frameHl);
    $('tmeters').classList.toggle('hl', !!fx.meterHl);
  }

  function render() {
    const sg = seq[si], st = D.steps[sg.k], fx = sg.beat ? sg.beat.fx(u) : {};
    const base = fx.base === -1 ? D.steps[sg.k - 1] : st;
    const prev = fx.base === -1 ? null : (sg.k ? D.steps[sg.k - 1] : null);
    drawGraph(base, prev, sg.beat ? 1 : u, fx, !playing);
    const t = sg.end ? D.T : st.t;
    $('tframe').src = `static/teaser/f${String(Math.floor(t)).padStart(3, '0')}.jpg`;
    $('ttime').textContent = mmss(t);
    $('twrite').hidden = !!sg.end;
    $('tq').hidden = !sg.end;
    $('tqa').hidden = !fx.answer;
    $('tstats').textContent = `${base.m} mentions → ${base.n} nodes · 6 shown`;
    $('ttitle').textContent = sg.beat ? sg.beat.title : `Write at ${mmss(st.t)}`;
    $('tline').textContent = sg.beat ? sg.beat.line : `${st.ntrip} triplets, ${st.ndesc} descriptions and one caption.`;
    root.classList.toggle('focus', !!sg.beat);
    drawLog(sg.k, fx);
    const full = Math.min(t, D.T) * 195;
    $('bfull').style.width = (100 * Math.min(full, 80000) / 80000) + '%';
    $('vfull').textContent = '≈' + (full / 1000).toFixed(1) + 'K';
    $('bvsg').style.width = (100 * 3510 / 80000) + '%';
    $('tknob').style.left = (100 * t / D.T) + '%';
    $('tfill').style.width = (100 * t / D.T) + '%';
    drawOverlays(fx);
  }

  function tick(now) {
    if (!playing) return;
    const dt = Math.min(0.1, (now - last) / 1000);
    last = now;
    u += dt / (seq[si].beat ? seq[si].beat.dur : FAST);
    if (u >= 1) { si = si < seq.length - 1 ? si + 1 : 0; u = 0; }
    render();
    requestAnimationFrame(tick);
  }

  function setPlaying(p) {
    playing = p;
    $('tplay').setAttribute('aria-label', p ? 'Pause' : 'Play');
    $('tplay').innerHTML = p ? '<i class="fa-solid fa-pause"></i>' : '<i class="fa-solid fa-play"></i>';
    if (p) { last = performance.now(); requestAnimationFrame(tick); } else render();
  }

  function seek(clientX) {
    const r = $('tbar').getBoundingClientRect(), t = Math.max(0, Math.min(1, (clientX - r.left) / r.width)) * D.T;
    let best = 0;
    seq.forEach((s, i) => { const ts = s.end ? D.T : D.steps[s.k].t; if (ts <= t + 1e-6 && (!s.beat || s.j === 0)) best = i; });
    if (t > D.steps[D.steps.length - 1].t + 4) best = seq.length - 1;
    si = best; u = seq[si].beat ? 0.6 : 1;
    render();
  }

  fetch('static/teaser/data.json').then((r) => r.json()).then((data) => {
    D = data;
    buildSeq();
    D.steps.forEach((s) => { const im = new Image(); im.src = `static/teaser/f${String(s.t).padStart(3, '0')}.jpg`; });
    const bar = $('tticks');
    D.steps.forEach((s) => {
      const d = document.createElement('i');
      d.style.left = (100 * s.t / D.T) + '%';
      if (s.t === 170) d.className = 'dis';
      if (s.t === 330) d.className = 'ev';
      bar.appendChild(d);
    });
    $('twin').style.left = (100 * (D.T - 18) / D.T) + '%';
    $('twin').style.width = (100 * 18 / D.T) + '%';
    $('tplay').addEventListener('click', () => setPlaying(!playing));
    let drag = false;
    $('tbar').addEventListener('pointerdown', (e) => { drag = true; setPlaying(false); seek(e.clientX); });
    window.addEventListener('pointermove', (e) => { if (drag) seek(e.clientX); });
    window.addEventListener('pointerup', () => { drag = false; });
    $('tbar').addEventListener('keydown', (e) => {
      if (e.key !== 'ArrowRight' && e.key !== 'ArrowLeft') return;
      setPlaying(false);
      si = Math.max(0, Math.min(seq.length - 1, si + (e.key === 'ArrowRight' ? 1 : -1)));
      u = seq[si].beat ? 0.6 : 1;
      render();
      e.preventDefault();
    });
    si = 0; u = 0;
    render();
    root.go = (i, v) => { setPlaying(false); si = i; u = v; render(); };
    const reduce = window.matchMedia('(prefers-reduced-motion: reduce)').matches;
    if (!reduce && 'IntersectionObserver' in window) {
      const io = new IntersectionObserver((es) => { if (es[0].isIntersecting) { setPlaying(true); io.disconnect(); } }, {threshold: 0.35});
      io.observe(root);
    }
  });
})();
