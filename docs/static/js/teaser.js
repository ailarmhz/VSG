// Teaser: the visual-state graph of one stream, write by write, from the stored write log (static/teaser/data.json).
(function () {
  const root = document.getElementById('teaser');
  if (!root) return;
  const $ = (id) => document.getElementById(id);
  const NS = 'http://www.w3.org/2000/svg';
  const C = {new: '#2E9E5B', merged: '#3F78D0', idle: '#B9B9B5', ev: '#2E8B4F', dis: '#C0392B', ink: '#17181C'};
  const POS = {screwdriver_0: [0.50, 0.70], wrench_0: [0.85, 0.55], motorcycle_1: [0.85, 0.22],
               workbench_0: [0.50, 0.10], blue_gloves_0: [0.15, 0.22], person_0: [0.15, 0.55]};
  const CAP = {screwdriver_0: 'above', wrench_0: 'above', person_0: 'above', motorcycle_1: 'below',
               workbench_0: 'below', blue_gloves_0: 'below'};
  const VW = 520, VH = 400, R = 33;
  const xy = (n) => [40 + POS[n][0] * (VW - 80), 330 - (POS[n][1] - 0.10) / 0.60 * 262];
  const STEP_MS = 1100, END_MS = 6500;
  const mmss = (t) => Math.floor(t / 60) + ':' + String(Math.floor(t % 60)).padStart(2, '0');
  const ease = (u) => { u = Math.min(1, Math.max(0, u)); return u * u * (3 - 2 * u); };

  let D, k = 0, u = 1, playing = false, last = 0, ended = false;
  const svg = $('tgraph');

  function el(tag, attrs, parent) {
    const e = document.createElementNS(NS, tag);
    for (const a in attrs) e.setAttribute(a, attrs[a]);
    (parent || svg).appendChild(e);
    return e;
  }

  function note(st) {
    if (st.t === 20) return 'The screwdriver is mentioned again. Its relations match the stored node, so the mention is merged: ×2.';
    if (st.t === 170) return 'Caption at 2:50: “… uses wrench to tighten bolt …”';
    if (st.t === 330) return 'Caption at 5:30: “… uses screwdriver on motorcycle …”, written 79 s before the question.';
    if (st.t === 10) return 'First write: triplets create the first nodes; one caption starts the event log.';
    return `Write at ${mmss(st.t)}: ${st.ntrip} triplets, ${st.ndesc} descriptions, 1 caption.`;
  }

  function drawGraph(st, prev, u) {
    svg.innerHTML = '';
    const defs = el('defs', {});
    ['b', 'g'].forEach((id) => {
      const m = el('marker', {id: 'ah' + id, viewBox: '0 0 10 10', refX: 9, refY: 5, markerWidth: 6, markerHeight: 6, orient: 'auto'}, defs);
      el('path', {d: 'M0,0 L10,5 L0,10 z', fill: id === 'b' ? C.merged : '#C4C4BF'}, m);
    });
    const shown = Object.keys(st.nodes);
    shown.forEach((n) => {
      const cp = el('clipPath', {id: 'cp' + n}, defs);
      const [x, y] = xy(n);
      el('circle', {cx: x, cy: y, r: R - 2}, cp);
    });
    // edges: stored ones grey, the ones written now blue
    const edges = st.edges.slice().sort((a, b) => a.live - b.live);
    edges.forEach((e) => {
      const [x1, y1] = xy(e.s), [x2, y2] = xy(e.o);
      const L = Math.hypot(x2 - x1, y2 - y1), ux = (x2 - x1) / L, uy = (y2 - y1) / L;
      const isNew = !prev || !prev.edges.some((p) => (p.s === e.s && p.o === e.o) || (p.s === e.o && p.o === e.s));
      const f = isNew ? ease(u / 0.7) : 1;
      const sx = x1 + ux * (R + 4), sy = y1 + uy * (R + 4);
      const ex = sx + (x2 - ux * (R + 6) - sx) * f, ey = sy + (y2 - uy * (R + 6) - sy) * f;
      el('line', {x1: sx, y1: sy, x2: ex, y2: ey, stroke: e.live ? C.merged : '#C9C9C4',
                  'stroke-width': e.live ? 2.6 : 1.4, 'marker-end': f > 0.95 ? `url(#ah${e.live ? 'b' : 'g'})` : ''});
    });
    // labels of up to two live edges that involve the tools
    const lab = edges.filter((e) => e.live).sort((a, b) => score(b) - score(a)).slice(0, 2);
    function score(e) { return (e.s === 'screwdriver_0' || e.o === 'screwdriver_0') * 2 + (e.s === 'wrench_0' || e.o === 'wrench_0'); }
    lab.forEach((e, i) => {
      const [x1, y1] = xy(e.s), [x2, y2] = xy(e.o);
      const t = i ? 0.38 : 0.55, x = x1 + (x2 - x1) * t, y = y1 + (y2 - y1) * t;
      const g = el('g', {opacity: ease((u - 0.5) / 0.3)});
      const tx = el('text', {x, y: y + 4, 'text-anchor': 'middle', 'font-size': 13, fill: C.merged}, g);
      tx.textContent = e.p;
      const w = e.p.length * 6.6 + 10;
      const bg = el('rect', {x: x - w / 2, y: y - 10, width: w, height: 19, rx: 4, fill: '#fff'});
      g.insertBefore(bg, tx);
    });
    // nodes
    shown.forEach((n) => {
      const nd = st.nodes[n], [x, y] = xy(n);
      const appear = !prev || !prev.nodes[n];
      const s = appear ? ease(u / 0.5) : 1;
      const g = el('g', {transform: `translate(${x},${y}) scale(${Math.max(0.01, s)}) translate(${-x},${-y})`});
      if (nd.img) el('image', {href: 'static/teaser/c_' + nd.img, x: x - R, y: y - R, width: 2 * R, height: 2 * R,
                               'clip-path': `url(#cp${n})`, preserveAspectRatio: 'xMidYMid slice'}, g);
      else el('circle', {cx: x, cy: y, r: R - 2, fill: '#ECECEA'}, g);
      const col = C[nd.s];
      el('circle', {cx: x, cy: y, r: R, fill: 'none', stroke: col, 'stroke-width': nd.s === 'idle' ? 3 : 5.5}, g);
      if (nd.s !== 'idle' && u < 1) {
        el('circle', {cx: x, cy: y, r: R + 4 + 14 * ease(u), fill: 'none', stroke: col, 'stroke-width': 3,
                      opacity: 0.6 * (1 - ease(u))}, g);
      }
      const above = CAP[n] === 'above';
      const t = el('text', {x, y: above ? y - R - 9 : y + R + 19, 'text-anchor': 'middle', 'font-size': 14.5,
                            'font-weight': 700, fill: C.ink}, g);
      t.textContent = `${D.names[n]} ×${nd.c}`;
      if (nd.s === 'merged' && u < 1) {
        const b = el('g', {opacity: 1 - ease((u - 0.55) / 0.45)});
        el('rect', {x: x + R + 3, y: y - 9 - 12 * ease(u), width: 26, height: 18, rx: 5, fill: C.merged}, b);
        const p = el('text', {x: x + R + 16, y: y + 4 - 12 * ease(u), 'text-anchor': 'middle', 'font-size': 12,
                              'font-weight': 700, fill: '#fff'}, b);
        p.textContent = '+1';
      }
    });
  }

  function drawLog(k) {
    const box = $('tlog');
    box.innerHTML = '';
    const lines = D.steps.slice(0, k + 1).map((s) => s).filter((s, i) => i >= k - 3 || s.t === 170 || s.t === 330);
    const keep = lines.slice(-5).slice(-5);
    keep.forEach((s) => {
      const d = document.createElement('div');
      d.className = 'ln' + (s.t === 330 ? ' ev' : s.t === 170 ? ' dis' : '') + (s === D.steps[k] ? ' now' : '');
      d.innerHTML = `<code>${mmss(s.t)}</code>${s.cap}`;
      box.appendChild(d);
    });
  }

  function drawBars(t) {
    const full = Math.min(t, D.T) * 195;
    $('bfull').style.width = (100 * Math.min(full, 80000) / 80000) + '%';
    $('vfull').textContent = '≈' + (full / 1000).toFixed(1) + 'K';
    $('bvsg').style.width = (100 * 3510 / 80000) + '%';
  }

  function drawTimeline(t) {
    $('tknob').style.left = (100 * t / D.T) + '%';
    $('tfill').style.width = (100 * t / D.T) + '%';
  }

  function render() {
    const st = D.steps[k], prev = k ? D.steps[k - 1] : null;
    if (ended) {
      drawGraph(st, null, 1);
      $('tframe').src = `static/teaser/f${String(Math.floor(D.T)).padStart(3, '0')}.jpg`;
      $('ttime').textContent = mmss(D.T);
      $('twrite').hidden = true;
      $('tq').hidden = false;
      $('tnote').innerHTML = 'Question at 6:49. VSG reads 40 event lines, 2 crops and the last 8 frames within 3,510 tokens; the 5:30 line supports the answer.';
      drawLog(D.steps.length - 1);
      [...$('tlog').children].forEach((d) => { if (!d.classList.contains('ev')) d.classList.add('dim'); });
      drawBars(D.T);
      drawTimeline(D.T);
      $('tstats').textContent = `${st.m} mentions → ${st.n} nodes`;
      return;
    }
    $('tq').hidden = true;
    $('twrite').hidden = u >= 1 && !playing;
    drawGraph(st, prev, u);
    $('tframe').src = `static/teaser/f${String(st.t).padStart(3, '0')}.jpg`;
    $('ttime').textContent = mmss(st.t);
    $('tstats').textContent = `${st.m} mentions → ${st.n} nodes  ·  6 shown`;
    $('tnote').textContent = note(st);
    drawLog(k);
    drawBars(st.t);
    drawTimeline(st.t);
  }

  function tick(now) {
    if (!playing) return;
    const dt = now - last;
    last = now;
    const dur = ended ? END_MS : (D.steps[k].t === 20 || D.steps[k].t === 170 || D.steps[k].t === 330) ? 3 * STEP_MS : STEP_MS;
    u += dt / Math.min(dur, STEP_MS);
    if (u >= dur / STEP_MS) {
      if (ended) { ended = false; k = 0; u = 0; }
      else if (k < D.steps.length - 1) { k++; u = 0; }
      else { ended = true; u = 0; }
    }
    render();
    requestAnimationFrame(tick);
  }

  function setPlaying(p) {
    playing = p;
    $('tplay').setAttribute('aria-label', p ? 'Pause' : 'Play');
    $('tplay').innerHTML = p ? '<i class="fa-solid fa-pause"></i>' : '<i class="fa-solid fa-play"></i>';
    if (p) { last = performance.now(); requestAnimationFrame(tick); }
  }

  function seek(clientX) {
    const r = $('tbar').getBoundingClientRect();
    const t = Math.max(0, Math.min(1, (clientX - r.left) / r.width)) * D.T;
    ended = t > D.steps[D.steps.length - 1].t + 4;
    k = 0;
    D.steps.forEach((s, i) => { if (s.t <= t) k = i; });
    u = 1;
    render();
  }

  fetch('static/teaser/data.json').then((r) => r.json()).then((data) => {
    D = data;
    D.steps.forEach((s) => { const im = new Image(); im.src = `static/teaser/f${String(s.t).padStart(3, '0')}.jpg`; });
    const bar = $('tticks');
    D.steps.forEach((s) => {
      const d = document.createElement('i');
      d.style.left = (100 * s.t / D.T) + '%';
      if (s.t === 170) d.className = 'dis';
      if (s.t === 330) d.className = 'ev';
      bar.appendChild(d);
    });
    $('tplay').addEventListener('click', () => setPlaying(!playing));
    let drag = false;
    $('tbar').addEventListener('pointerdown', (e) => { drag = true; setPlaying(false); seek(e.clientX); });
    window.addEventListener('pointermove', (e) => { if (drag) seek(e.clientX); });
    window.addEventListener('pointerup', () => { drag = false; });
    $('tbar').addEventListener('keydown', (e) => {
      if (e.key !== 'ArrowRight' && e.key !== 'ArrowLeft') return;
      setPlaying(false);
      ended = false;
      k = Math.max(0, Math.min(D.steps.length - 1, k + (e.key === 'ArrowRight' ? 1 : -1)));
      u = 1;
      render();
      e.preventDefault();
    });
    k = 0; u = 1;
    render();
    const reduce = window.matchMedia('(prefers-reduced-motion: reduce)').matches;
    if (!reduce && 'IntersectionObserver' in window) {
      const io = new IntersectionObserver((es) => {
        if (es[0].isIntersecting) { u = 0; setPlaying(true); io.disconnect(); }
      }, {threshold: 0.4});
      io.observe(root);
    }
  });
})();
