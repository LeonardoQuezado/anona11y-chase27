/* Melodie A11Y — "Esmaga-bugs", started from the big star of Melodie's orbit (landing page).
   Bugs are accessibility violations crawling to Melodie's phone; one reaching it ends the game,
   because one accessibility failure is enough to exclude a user. Five waves, the last with a boss.
   Mouse/touch: move the hand, click to smash, hold to charge a wider smash.
   Keyboard: arrows move, Space/Enter smash (hold to charge), P pauses, Esc stops. */
(function () {
  const hero = document.querySelector('.landing .hero');
  const mark = hero && hero.querySelector('.hero-mark');
  if (!mark) return;

  const reduceMotion = window.matchMedia('(prefers-reduced-motion: reduce)');
  const TOP_KEY = 'melodie-bugs-top', OLD_KEY = 'melodie-bugs-best';
  const TAU = Math.PI * 2;
  const clamp = (v, a, b) => Math.min(b, Math.max(a, v));
  const rand = (a, b) => a + Math.random() * (b - a);

  // ── content ───────────────────────────────────────────────────────────────
  const TYPES = {
    bug:      { name: 'Bug',             size: 1.0,  speed: 1.0,  points: 10 },
    small:    { name: 'Small Target',    size: 0.55, speed: 1.75, points: 20, zig: true },
    label:    { name: 'No Label',        size: 1.0,  speed: 1.05, points: 25, hidden: true },
    contrast: { name: 'Low Contrast',    size: 1.0,  speed: 1.1,  points: 20, camo: true, tint: ['#140a2e', 0.72] },
    regress:  { name: 'Regression',      size: 1.1,  speed: 0.9,  points: 15, split: true, tint: ['#f472b6', 0.38] },
    child:    { name: 'Regression',      size: 0.68, speed: 1.3,  points: 10, tint: ['#f472b6', 0.25] },
    boss:     { name: 'Build Failed',    size: 2.4,  speed: 0.34, points: 250, hp: 18, tint: ['#ff2e63', 0.42] },
  };
  // burst: chance that a spawn brings 2-3 bugs together
  const WAVES = [
    { count: 10, mix: { bug: 0.8, small: 0.2 },                                      gap: 1.1,  burst: 0,    intro: 'Common bugs. Smash them before they reach the phone.' },
    { count: 14, mix: { bug: 0.45, small: 0.4, label: 0.15 },                        gap: 0.95, burst: 0.2,  intro: 'Small Target: tiny and fast. They demand precision.' },
    { count: 17, mix: { bug: 0.25, small: 0.25, label: 0.35, contrast: 0.15 },       gap: 0.85, burst: 0.28, intro: 'No Label: almost invisible, they only show up near the reticle.' },
    { count: 20, mix: { bug: 0.15, small: 0.2, label: 0.2, contrast: 0.2, regress: 0.25 }, gap: 0.75, burst: 0.35, intro: 'Low Contrast blends in. Regression splits when smashed.' },
    { count: 16, mix: { small: 0.25, label: 0.25, contrast: 0.25, regress: 0.25 },   gap: 0.85, burst: 0.4, boss: true, intro: 'Build Failed: the boss. It takes several hits.' },
  ];
  const POWERS = {
    lint: { label: 'L', name: 'Lint Sweep',     color: '#38bdf8', secs: 7, say: 'Lint Sweep: hidden bugs revealed.' },
    atf:  { label: 'A', name: 'ATF Pulse',      color: '#34d399', secs: 5, say: 'ATF Pulse: bugs slowed down.' },
  };
  const CODE = [
    '@Composable', 'fun CheckoutScreen() {', '  Column(Modifier.padding(16.dp)) {',
    '    Icon(Icons.Filled.Lock, contentDescription = null)', '    TextField(value = email, onValueChange = { email = it })',
    '    IconButton(onClick = {}) { Icon(Icons.Filled.Send, null) }', '    Text("Pay", color = Color(0xFFBDBDBD))',
    '    Box(Modifier.size(24.dp).clickable { pay() })', '    Image(painter, contentDescription = null)', '  }', '}',
    '// TODO: accessibility', 'Modifier.semantics { }', 'Slider(value = v, onValueChange = { v = it })',
  ];
  const HIT = 0.068, HIT_CHARGED = 0.14, COOL = 0.42, COOL_CHARGED = 1.0, CHARGE_S = 0.5;
  // Melodie's claw: a power that fills up with kills; it falls on the reticle and crushes a wide area
  const CLAW_R = 0.27, CLAW_FALL = 0.32, CLAW_HOLD = 0.35, CLAW_RISE = 0.35, CLAW_BOSS_DMG = 5;

  // Melodie's shop, between waves. Credits come with every point; spending them never lowers the score.
  const UPGRADES = {
    laser: { name: 'Laser ATF', color: '#f472b6', icon: 'atf', prices: [300, 600, 1100],
      levels: ['Melodie defends the phone: shoots the nearest bug every 1.6 s.', '1.0 s reload and longer range.', '0.7 s reload and hits two targets per shot.'],
      blurb: 'A running test: the device defends itself.' },
    lint: { name: 'Custom Lint', color: '#38bdf8', icon: 'lint', prices: [250, 550, 950],
      levels: ['The reticle reveals hidden bugs in a 60% larger area.', 'No Label and Low Contrast never fully disappear.', 'An automatic sweep reveals everything every 10 s.'],
      blurb: 'Custom static analysis rules see what is hidden.' },
    aim: { name: 'Sharp Aim', color: '#f0abfc', icon: 'aim', prices: [180, 420, 780],
      levels: ['15% larger ring and 12% shorter reload.', '30% larger ring and 24% shorter reload.', '45% larger ring and 36% shorter reload.'],
      blurb: 'Wider and more frequent hits.' },
    claw: { name: 'Turbo Claw', color: '#e879f9', icon: 'claw', prices: [240, 540, 900],
      levels: ['The Claw charges 35% faster.', 'Charges 70% faster and covers a 15% larger area.', 'Charges 105% faster and covers a 30% larger area.'],
      blurb: "Melodie's power, more often and stronger." },
  };
  const LASER = [null, { every: 1.6, range: 0.42, shots: 1 }, { every: 1.0, range: 0.52, shots: 1 }, { every: 0.7, range: 0.58, shots: 2 }];

  // ── assets ────────────────────────────────────────────────────────────────
  const loadImg = src => { const i = new Image(); i.decoding = 'async'; i.src = src; return i; };
  let IMG = null;
  const tintCache = {};
  function sprite(kind) {
    const T = TYPES[kind];
    if (!T.tint) return IMG.bug;
    if (tintCache[kind]) return tintCache[kind];
    if (!IMG.bug.complete || !IMG.bug.naturalWidth) return IMG.bug;
    const c = document.createElement('canvas');
    c.width = IMG.bug.naturalWidth; c.height = IMG.bug.naturalHeight;
    const x = c.getContext('2d');
    x.drawImage(IMG.bug, 0, 0);
    x.globalCompositeOperation = 'source-atop'; x.globalAlpha = T.tint[1]; x.fillStyle = T.tint[0];
    x.fillRect(0, 0, c.width, c.height);
    return (tintCache[kind] = c);
  }

  // ── scores ────────────────────────────────────────────────────────────────
  function readTop() {
    try {
      const t = JSON.parse(localStorage.getItem(TOP_KEY) || '[]');
      if (Array.isArray(t) && t.length) return t;
      const old = +localStorage.getItem(OLD_KEY) || 0;
      return old ? [{ score: old, wave: 0, date: 0 }] : [];
    } catch (_) { return []; }
  }
  const writeTop = t => { try { localStorage.setItem(TOP_KEY, JSON.stringify(t)); } catch (_) {} };

  // ── Melodie reacts (the landing eye script listens) ───────────────────────
  const emit = detail => window.dispatchEvent(new CustomEvent('melodie:game', { detail }));

  let g = null;

  function start() {
    if (g) return;
    IMG = IMG || { bug: loadImg('/static/art/melodie-bug.webp?v=3'), hand: loadImg('/static/art/melodie-hand.webp?v=3'), logo: loadImg('/static/logo-icon.png') };
    const top = readTop();
    const root = document.createElement('div');
    root.className = 'bug-game';
    root.tabIndex = 0;
    root.setAttribute('role', 'application');
    root.setAttribute('aria-roledescription', 'game');
    root.setAttribute('aria-label', "Bug Smash. Accessibility bugs crawl toward Melodie's phone: if one gets there, the game is over. " +
      "Arrow keys or mouse move the reticle; Space, Enter or click smash; hold for a wider hit; Q or right click drop Melodie's Claw when it is ready; P pauses; Esc quits.");
    root.innerHTML = `
      <div class="bg-hud">
        <span class="bg-stat">Wave<b class="bg-wave">1/5</b></span>
        <span class="bg-stat">Score<b class="bg-score">0</b></span>
        <span class="bg-stat">Combo<b class="bg-combo">×1</b></span>
        <span class="bg-stat">Best<b class="bg-best">${top[0] ? top[0].score : 0}</b></span>
        <span class="bg-actions">
          <button type="button" class="bg-claw" disabled aria-label="Melodie's Claw: 0%"><span class="bg-claw-fill"></span><span class="bg-claw-txt">Claw</span></button>
          <button type="button" class="bg-pause">Pause</button><button type="button" class="bg-stop">Stop</button>
        </span>
      </div>
      <div class="bg-field">
        <canvas class="bg-canvas" aria-hidden="true"></canvas>
        <div class="bg-paused" hidden><p>Paused</p><button type="button" class="bg-resume">Resume</button></div>
        <div class="bg-shop" hidden role="dialog" aria-modal="true" aria-labelledby="bg-shop-title">
          <div class="bg-shop-head"><h2 id="bg-shop-title">Melodie's Shop</h2><p class="bg-credits"></p></div>
          <div class="bg-shop-grid"></div>
          <button type="button" class="bg-shop-go"></button>
        </div>
      </div>
      <div class="bg-end" hidden>
        <p class="bg-end-rank" aria-hidden="true"></p>
        <h2 class="bg-end-title"></h2>
        <p class="bg-end-score"></p>
        <dl class="bg-end-stats"></dl>
        <p class="bg-record" hidden>New record!</p>
        <ol class="bg-top" aria-label="High scores"></ol>
        <div class="bg-end-actions"><button type="button" class="bg-again">Play again</button><button type="button" class="bg-close">Back</button></div>
      </div>
      <p class="sr-only bg-live" aria-live="polite"></p>`;
    hero.append(root);
    hero.classList.add('is-gaming');
    requestAnimationFrame(() => root.classList.add('is-open'));
    const $ = s => root.querySelector(s);
    const canvas = $('.bg-canvas');

    g = {
      root, canvas, ctx: canvas.getContext('2d'), field: $('.bg-field'), live: $('.bg-live'),
      hud: { wave: $('.bg-wave'), score: $('.bg-score'), combo: $('.bg-combo') },
      font: getComputedStyle(root).fontFamily, W: 1, H: 1, dpr: 1, top,
      wave: -1, state: 'intro', stateT: 0, queue: [], nextSpawn: 0, bossTimer: 0,
      bugs: [], orbs: [], parts: [], pops: [], corpses: [],
      score: 0, combo: 0, maxCombo: 0, swings: 0, hitSwings: 0, killed: {},
      aim: { x: 0.5, y: 0.55 }, keys: new Set(), pressT: -1, cool: 0, queued: null, smashT: -9,
      claw: 0, clawFx: null, waves: [], clawBtn: $('.bg-claw'),
      credits: 0, up: { laser: 0, lint: 0, aim: 0, claw: 0 }, laserT: 0, beams: [], lintPulseT: 10, coolTotal: COOL,
      power: { lint: 0, atf: 0 }, freezeUntil: 0, shake: 0, cracked: false,
      over: false, paused: false, t: 0, last: 0, raf: 0, lastEmit: 0, lastWarn: -9, closeTimer: 0,
    };

    resize();
    g.ro = new ResizeObserver(resize); g.ro.observe(g.field);
    canvas.addEventListener('pointermove', onPointerMove);
    canvas.addEventListener('pointerdown', onPointerDown);
    canvas.addEventListener('pointerup', onPointerUp);
    canvas.addEventListener('pointercancel', () => { if (g) g.pressT = -1; });
    canvas.addEventListener('contextmenu', e => { e.preventDefault(); if (g && !g.over && !g.paused) { aimFrom(e); releaseClaw(); } });
    $('.bg-claw').addEventListener('click', () => { releaseClaw(); if (g) g.root.focus({ preventScroll: true }); });
    $('.bg-shop').addEventListener('click', e => { const bt = e.target.closest('.bg-buy'); if (bt && !bt.disabled) buy(bt.dataset.up); });
    $('.bg-shop-go').addEventListener('click', () => { if (g && g.state === 'shop') closeShop(); });
    root.addEventListener('keydown', onKeyDown);
    root.addEventListener('keyup', onKeyUp);
    $('.bg-pause').addEventListener('click', () => setPaused(true));
    $('.bg-resume').addEventListener('click', () => setPaused(false));
    $('.bg-stop').addEventListener('click', () => finish('quit'));
    $('.bg-close').addEventListener('click', close);
    $('.bg-again').addEventListener('click', () => { close(true); start(); });
    const keepOpen = () => { if (g && g.root === root && g.over) armClose(); };
    $('.bg-end').addEventListener('pointermove', keepOpen);
    $('.bg-end').addEventListener('focusin', keepOpen);
    document.addEventListener('visibilitychange', onHidden);
    root.focus({ preventScroll: true });
    emit({ kind: 'start' });
    nextWave();
    g.raf = requestAnimationFrame(tick);
  }

  function say(text) { if (g) { g.live.textContent = ''; g.live.textContent = text; } }

  function resize() {
    if (!g) return;
    const r = g.field.getBoundingClientRect(), dpr = Math.min(2, window.devicePixelRatio || 1);
    const k = g.W > 1 ? r.width / g.W : 1;
    g.bugs.concat(g.orbs, g.corpses).forEach(o => { o.x *= k; o.y *= k; });
    g.W = r.width; g.H = r.height; g.dpr = dpr;
    g.canvas.width = Math.round(r.width * dpr); g.canvas.height = Math.round(r.height * dpr);
  }

  const phone = () => ({ x: g.W / 2, y: g.H - g.W * 0.135, w: g.W * 0.12, h: g.W * 0.21 });
  const bugW = () => g.W * 0.12;

  // ── waves ─────────────────────────────────────────────────────────────────
  function nextWave() {
    g.wave++;
    if (g.wave >= WAVES.length) { finish('win'); return; }
    const W = WAVES[g.wave];
    const kinds = Object.keys(W.mix);
    g.queue = [];
    for (let i = 0; i < W.count; i++) {
      let r = Math.random(), k = kinds[0];
      for (const kk of kinds) { r -= W.mix[kk]; if (r <= 0) { k = kk; break; } }
      g.queue.push(k);
    }
    if (W.boss) g.queue.splice(2, 0, 'boss');
    g.state = 'intro'; g.stateT = reduceMotion.matches ? 1.6 : 2.4; g.waveT0 = g.t + g.stateT;
    g.hud.wave.textContent = `${g.wave + 1}/${WAVES.length}`;
    say(`Wave ${g.wave + 1} of ${WAVES.length}. ${W.intro}`);
  }

  function spawn(kind, x, y) {
    const T = TYPES[kind], w = bugW() * T.size;
    if (x === undefined) {
      const s = Math.random();
      if (s < 0.6) { x = rand(w, g.W - w); y = -w * 0.6; }
      else if (s < 0.8) { x = -w * 0.6; y = rand(0, g.H * 0.5); }
      else { x = g.W + w * 0.6; y = rand(0, g.H * 0.5); }
    }
    g.bugs.push({ kind, T, x, y, w, r: w * 0.36, hp: T.hp || 1, maxHp: T.hp || 1, phase: rand(0, TAU), dir: 1, tilt: 0, flash: 0, alpha: 1 });
  }

  // ── input ─────────────────────────────────────────────────────────────────
  function aimFrom(e) {
    const r = g.canvas.getBoundingClientRect();
    g.aim.x = clamp((e.clientX - r.left) / r.width, 0, 1);
    g.aim.y = clamp((e.clientY - r.top) / r.height, 0, 1);
  }
  function onPointerMove(e) { if (g && !g.over) aimFrom(e); }
  function onPointerDown(e) {
    if (!g || g.over || g.paused || e.button === 2) return;
    aimFrom(e); g.pressT = g.t;
    try { g.canvas.setPointerCapture(e.pointerId); } catch (_) {}
  }
  function onPointerUp(e) { if (!g || g.over || g.paused || g.pressT < 0) return; aimFrom(e); release(); }
  function release() {
    const charged = g.t - g.pressT >= CHARGE_S;
    g.pressT = -1;
    if (g.cool <= 0) smash(charged);
    else if (g.cool < 0.15) g.queued = charged;            // small input buffer
  }
  function onKeyDown(e) {
    if (!g) return;
    if (e.key === 'Escape') { e.preventDefault(); if (g.over) close(); else finish('quit'); return; }
    if (e.target.tagName === 'BUTTON') return;              // let buttons work normally
    if (g.over) return;
    if (g.state === 'shop') return;
    if (e.key === 'p' || e.key === 'P') { e.preventDefault(); setPaused(!g.paused); return; }
    if ((e.key === 'q' || e.key === 'Q') && !g.paused) { e.preventDefault(); releaseClaw(); return; }
    if (g.paused) return;
    if (e.key === ' ' || e.key === 'Enter') { e.preventDefault(); if (!e.repeat) g.pressT = g.t; return; }
    if (e.key.startsWith('Arrow')) { e.preventDefault(); g.keys.add(e.key); }
  }
  function onKeyUp(e) {
    if (!g) return;
    g.keys.delete(e.key);
    if ((e.key === ' ' || e.key === 'Enter') && g.pressT >= 0 && !g.over && !g.paused && e.target.tagName !== 'BUTTON') release();
  }
  function onHidden() { if (g && document.hidden && !g.over) setPaused(true); }
  function setPaused(on) {
    if (!g || g.over || g.paused === on || (on && g.state === 'shop')) return;
    g.paused = on; g.pressT = -1; g.keys.clear();
    g.root.querySelector('.bg-paused').hidden = !on;
    g.root.querySelector('.bg-pause').textContent = on ? 'Resume' : 'Pause';
    if (on) { g.root.querySelector('.bg-resume').focus({ preventScroll: true }); say('Game paused.'); }
    else { g.root.focus({ preventScroll: true }); g.last = 0; say('Game resumed.'); }
  }

  // ── smashing ──────────────────────────────────────────────────────────────
  function smash(charged) {
    const px = g.aim.x * g.W, py = g.aim.y * g.H, reach = hitR(charged);
    g.cool = g.coolTotal = coolOf(charged); g.smashT = g.t; g.swings++;
    g.waves.push({ x: px, y: py, r0: reach * 0.4, r1: reach * 1.6, life: 0.35, max: 0.35, c: charged ? '#fde68a' : '#f0abfc' });
    let hits = 0, gotOrb = false;
    g.orbs = g.orbs.filter(o => {
      if (Math.hypot(o.x - px, o.y - py) > reach + o.r) return true;
      const P = POWERS[o.kind]; g.power[o.kind] = P.secs; gotOrb = true;
      pop(o.x, o.y, P.name, P.color); burst(o.x, o.y, [P.color, '#ffffff'], 14); say(P.say);
      return false;
    });
    for (const b of g.bugs) {
      if (b.dead || Math.hypot(b.x - px, b.y - py) > reach + b.r) continue;
      hits++;
      b.hp -= charged ? 3 : 1; b.flash = 0.15;
      if (b.hp <= 0) kill(b);
      else { burst(b.x, b.y, ['#ff2e63', '#f0abfc'], 6); if (b.kind === 'boss') say(`Build Failed: ${b.hp} health left.`); }
    }
    g.bugs = g.bugs.filter(b => !b.dead);
    if (hits) {
      g.hitSwings++; g.combo += hits; g.maxCombo = Math.max(g.maxCombo, g.combo);
      if (!reduceMotion.matches) { g.freezeUntil = performance.now() + (charged ? 90 : 60); g.shake = 4 + 2 * Math.min(hits, 4); }
    } else if (!gotOrb) {
      g.combo = 0;
    }
    updateHud();
  }
  const mult = () => Math.min(5, 1 + Math.floor(g.combo / 5));
  const hitR = charged => (charged ? HIT_CHARGED : HIT) * g.W * (1 + 0.15 * g.up.aim);
  const coolOf = charged => (charged ? COOL_CHARGED : COOL) * (1 - 0.12 * g.up.aim);
  const clawR = () => CLAW_R * g.W * (1 + 0.15 * Math.max(0, g.up.claw - 1));

  function kill(b) {
    b.dead = true;
    const pts = b.T.points * mult();
    g.score += pts;
    g.killed[b.T.name] = (g.killed[b.T.name] || 0) + 1;
    if (!g.clawFx) addClaw((0.04 + 0.012 * (mult() - 1)) * (1 + 0.35 * g.up.claw));
    g.credits += pts;
    pop(b.x, b.y - b.w * 0.3, '+' + pts, '#f0abfc');
    burst(b.x, b.y, ['#f0abfc', '#c084fc', '#8b5cf6', '#6d28d9', '#e879f9'], b.kind === 'boss' ? 60 : 14);
    g.corpses.push({ kind: b.kind, x: b.x, y: b.y, w: b.w, dir: b.dir, life: 0.45 });
    if (b.T.split) { spawn('child', b.x - b.w * 0.3, b.y); spawn('child', b.x + b.w * 0.3, b.y); }
    if (b.kind === 'boss') say('Build Failed taken down!');
    if (!g.orbs.length && b.kind !== 'child' && Math.random() < 0.06)
      g.orbs.push({ kind: Math.random() < 0.5 ? 'lint' : 'atf', x: b.x, y: b.y, r: g.W * 0.03, life: 6 });
  }

  function addClaw(v) {
    const was = g.claw;
    g.claw = Math.min(1, g.claw + v);
    const b = g.clawBtn;
    b.style.setProperty('--fill', g.claw.toFixed(3));
    b.setAttribute('aria-label', g.claw >= 1 ? "Melodie's Claw ready" : `Melodie's Claw: ${Math.round(g.claw * 100)}%`);
    b.disabled = g.claw < 1;
    b.classList.toggle('is-ready', g.claw >= 1);
    if (was < 1 && g.claw >= 1) say("Melodie's Claw ready: Q key, right click or the Claw button.");
  }

  function releaseClaw() {
    if (!g || g.over || g.paused || g.claw < 1 || g.clawFx) return;
    g.clawFx = { x: g.aim.x * g.W, y: g.aim.y * g.H, t: 0, hit: false };
    g.claw = 0; addClaw(0);
    say("Melodie's Claw!");
  }

  function clawImpact(fx) {
    const R = clawR();
    let n = 0;
    for (const b of g.bugs) {
      if (b.dead || Math.hypot(b.x - fx.x, b.y - fx.y) > R + b.r) continue;
      n++; b.flash = 0.2;
      b.hp -= b.kind === 'boss' ? CLAW_BOSS_DMG : 99;
      if (b.hp <= 0) kill(b);
    }
    g.bugs = g.bugs.filter(b => !b.dead);
    g.orbs = g.orbs.filter(o => {
      if (Math.hypot(o.x - fx.x, o.y - fx.y) > R) return true;
      g.power[o.kind] = POWERS[o.kind].secs; say(POWERS[o.kind].say); return false;
    });
    if (n) { g.combo += n; g.maxCombo = Math.max(g.maxCombo, g.combo); }
    g.waves.push({ x: fx.x, y: fx.y, r0: R * 0.2, r1: R * 1.25, life: 0.55, max: 0.55, c: '#e879f9', w: 6 });
    g.waves.push({ x: fx.x, y: fx.y, r0: R * 0.1, r1: R * 0.9, life: 0.4, max: 0.4, c: '#fde68a', w: 3 });
    burst(fx.x, fx.y, ['#c084fc', '#e879f9', '#a855f7', '#f0abfc', '#7c3aed'], 46);
    if (!reduceMotion.matches) { g.shake = 14; g.freezeUntil = performance.now() + 110; }
    pop(fx.x, fx.y - R * 0.5, n ? `Claw ×${n}` : 'Claw', '#fde68a');
    updateHud();
  }

  // ATF laser: a turret on top of Melodie's phone shoots the closest bugs in range
  function laserTick(dt) {
    const L = LASER[g.up.laser];
    g.laserT -= dt;
    if (g.laserT > 0) return;
    const ph = phone(), ox = ph.x, oy = ph.y - ph.h * 0.55, range = L.range * g.W;
    const targets = g.bugs.filter(b => !b.dead && b.y > 0 && Math.hypot(b.x - ox, b.y - oy) <= range)
      .sort((a, b) => Math.hypot(a.x - ox, a.y - oy) - Math.hypot(b.x - ox, b.y - oy)).slice(0, L.shots);
    if (!targets.length) { g.laserT = 0.1; return; }
    g.laserT = L.every;
    for (const b of targets) {
      g.beams.push({ x0: ox, y0: oy - ph.w * 0.42, x1: b.x, y1: b.y, life: 0.18 });
      g.turretLook = { x: b.x, y: b.y, t: g.t };
      b.hp -= 1; b.flash = 0.15;
      burst(b.x, b.y, ['#f0abfc', '#e879f9', '#ffffff'], 6);
      if (b.hp <= 0) kill(b);
    }
    g.bugs = g.bugs.filter(b => !b.dead);
    updateHud();
  }

  // ── shop ──────────────────────────────────────────────────────────────────
  const ICONS = {
    atf: '<path d="M12 3v4M12 17v4M3 12h4M17 12h4" stroke="currentColor" stroke-width="2" stroke-linecap="round"/><circle cx="12" cy="12" r="4" fill="none" stroke="currentColor" stroke-width="2"/><circle cx="12" cy="12" r="1.5" fill="currentColor"/>',
    lint: '<circle cx="10.5" cy="10.5" r="6" fill="none" stroke="currentColor" stroke-width="2"/><path d="M15 15l5.5 5.5" stroke="currentColor" stroke-width="2.4" stroke-linecap="round"/><path d="M7.5 10.5h6M10.5 7.5v6" stroke="currentColor" stroke-width="1.6" stroke-linecap="round"/>',
    aim: '<circle cx="12" cy="12" r="8" fill="none" stroke="currentColor" stroke-width="2" stroke-dasharray="3 2.5"/><path d="M12 7.5Q12.6 11.4 16.5 12Q12.6 12.6 12 16.5Q11.4 12.6 7.5 12Q11.4 11.4 12 7.5Z" fill="currentColor"/>',
    claw: '<path d="M6 4c1 5 1 9 0 15M10 3c.8 6 .8 11 0 17M14 3c-.8 6-.8 11 0 17M18 4c-1 5-1 9 0 15" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round"/>',
  };

  function openShop() {
    g.state = 'shop'; g.pressT = -1; g.keys.clear();
    renderShop();
    const shop = g.root.querySelector('.bg-shop');
    shop.hidden = false;
    const first = shop.querySelector('.bg-buy:not(:disabled)') || shop.querySelector('.bg-shop-go');
    first.focus({ preventScroll: true });
    say(`Wave ${g.wave + 1} cleared. Melodie's Shop is open: ${g.credits} credits.`);
  }

  function renderShop() {
    const shop = g.root.querySelector('.bg-shop');
    shop.querySelector('.bg-credits').innerHTML = `Credits <b>${g.credits}</b>`;
    shop.querySelector('.bg-shop-go').textContent = `Continue to wave ${g.wave + 2} →`;
    shop.querySelector('.bg-shop-grid').innerHTML = Object.entries(UPGRADES).map(([key, U]) => {
      const lvl = g.up[key], maxed = lvl >= 3, price = maxed ? 0 : U.prices[lvl];
      const pips = [0, 1, 2].map(i => `<span class="bg-pip${i < lvl ? ' is-on' : ''}"></span>`).join('');
      const label = maxed ? `${U.name}: max level` : `Buy ${U.name} level ${lvl + 1} for ${price} credits. ${U.levels[lvl]}`;
      return `<div class="bg-up" style="--c:${U.color}">
        <div class="bg-up-top"><svg viewBox="0 0 24 24" aria-hidden="true">${ICONS[U.icon]}</svg><h3>${U.name}</h3><span class="bg-pips" role="img" aria-label="Level ${lvl} of 3">${pips}</span></div>
        <p class="bg-up-blurb">${U.blurb}</p>
        <p class="bg-up-next">${maxed ? 'Max level.' : `Level ${lvl + 1}: ${U.levels[lvl]}`}</p>
        <button type="button" class="bg-buy" data-up="${key}" ${maxed || price > g.credits ? 'disabled' : ''} aria-label="${label}">${maxed ? 'Max' : `${price} credits`}</button>
      </div>`;
    }).join('');
  }

  function buy(key) {
    const U = UPGRADES[key], lvl = g.up[key];
    if (lvl >= 3 || U.prices[lvl] > g.credits) return;
    g.credits -= U.prices[lvl]; g.up[key]++;
    renderShop();
    say(`${U.name} level ${g.up[key]}. ${g.credits} credits left.`);
    const again = g.root.querySelector(`.bg-buy[data-up="${key}"]:not(:disabled)`) || g.root.querySelector('.bg-buy:not(:disabled)') || g.root.querySelector('.bg-shop-go');
    again.focus({ preventScroll: true });
  }

  function closeShop() {
    g.root.querySelector('.bg-shop').hidden = true;
    g.root.focus({ preventScroll: true });
    g.laserT = 0.5; g.lintPulseT = 4; g.last = 0;
    nextWave();
  }

  function burst(x, y, colors, n) {
    if (reduceMotion.matches) n = Math.ceil(n / 3);
    for (let i = 0; i < n; i++) {
      const a = rand(0, TAU), v = rand(60, 220) * (g.W / 560);
      g.parts.push({ x, y, vx: Math.cos(a) * v, vy: Math.sin(a) * v - 40, life: rand(0.35, 0.7), max: 0.7, c: colors[i % colors.length], s: rand(3, 7) });
    }
  }
  function pop(x, y, text, color) { g.pops.push({ x, y, text, color, life: 0.8 }); }

  function updateHud() {
    g.hud.score.textContent = g.score;
    g.hud.combo.textContent = '×' + mult();
    if (g.combo && g.combo % 10 === 0) say(`${g.combo} combo! Multiplier ×${mult()}.`);
  }

  // ── loop ──────────────────────────────────────────────────────────────────
  function tick(now) {
    if (!g) return;
    g.raf = requestAnimationFrame(tick);
    const dt = Math.min(0.12, g.last ? (now - g.last) / 1000 : 0); g.last = now;
    if (!g.paused && !g.over && g.state !== 'shop' && now >= g.freezeUntil) update(dt);
    g.shake *= Math.exp(-dt / 0.08);
    render();
  }

  function update(dt) {
    g.t += dt;
    // aim with the keyboard
    if (g.keys.size) {
      const v = 0.8 * dt;
      if (g.keys.has('ArrowLeft')) g.aim.x -= v;
      if (g.keys.has('ArrowRight')) g.aim.x += v;
      if (g.keys.has('ArrowUp')) g.aim.y -= v;
      if (g.keys.has('ArrowDown')) g.aim.y += v;
      g.aim.x = clamp(g.aim.x, 0, 1); g.aim.y = clamp(g.aim.y, 0, 1);
    }
    if (g.cool > 0) { g.cool -= dt; if (g.cool <= 0 && g.queued !== null) { const q = g.queued; g.queued = null; smash(q); } }
    for (const k in g.power) g.power[k] = Math.max(0, g.power[k] - dt);
    if (g.clawFx) {
      const fx = g.clawFx; fx.t += dt;
      if (!fx.hit && fx.t >= CLAW_FALL) { fx.hit = true; clawImpact(fx); }
      if (fx.t >= CLAW_FALL + CLAW_HOLD + CLAW_RISE) g.clawFx = null;
    }
    g.waves.forEach(w => { w.life -= dt; }); g.waves = g.waves.filter(w => w.life > 0);
    g.beams.forEach(bm => { bm.life -= dt; }); g.beams = g.beams.filter(bm => bm.life > 0);
    if (g.state === 'play') {
      if (g.up.laser) laserTick(dt);
      if (g.up.lint >= 3) {
        g.lintPulseT -= dt;
        if (g.lintPulseT <= 0) {
          g.lintPulseT = 10; g.power.lint = Math.max(g.power.lint, 3);
          g.waves.push({ x: g.W / 2, y: g.H / 2, r0: 10, r1: g.W * 0.75, life: 0.7, max: 0.7, c: '#38bdf8', w: 3 });
        }
      }
    }

    if (g.state === 'intro') {
      g.stateT -= dt;
      if (g.stateT <= 0) { g.state = 'play'; g.nextSpawn = g.t + 0.2; }
    } else {
      const W = WAVES[g.wave];
      if (g.queue.length && g.t >= g.nextSpawn) {
        spawn(g.queue.shift());
        if (W.burst && Math.random() < W.burst) {           // a group arrives together
          for (let n = Math.random() < 0.4 ? 2 : 1; n > 0 && g.queue.length; n--) spawn(g.queue.shift());
        }
        g.nextSpawn = g.t + W.gap * rand(0.7, 1.3) * (1 - 0.3 * (g.queue.length < W.count / 2));
      }
      if (!g.queue.length && !g.bugs.length) {
        const bonus = 50 * (g.wave + 1);
        g.score += bonus; g.credits += bonus; updateHud();
        pop(g.W / 2, g.H * 0.42, `Wave clear +${bonus}`, '#fde68a');
        if (g.wave < WAVES.length - 1) { openShop(); return; }
        nextWave();
        if (g.over) return;
      }
    }

    // bugs
    const ph = phone(), slow = g.power.atf > 0 ? 0.45 : 1;
    // speed grows with the wave and keeps creeping up inside it
    const base = (0.095 + 0.016 * g.wave + 0.0012 * clamp(g.t - g.waveT0, 0, 60)) * g.W * slow;
    let minD = Infinity;
    for (const b of g.bugs) {
      const T = b.T;
      b.flash = Math.max(0, b.flash - dt);
      b.phase += dt * (T.zig ? 12 : 7);
      const wob = Math.sin(b.phase) * (T.zig ? 0.85 : 0.5);
      const dx = ph.x - b.x, dy = ph.y - b.y, d = Math.hypot(dx, dy) || 1;
      const ux = dx / d, uy = dy / d;
      b.x += (ux - uy * wob) * base * T.speed * dt;
      b.y += (uy + ux * wob) * base * T.speed * dt;
      b.dir = dx < 0 ? 1 : -1;
      b.tilt = wob * 0.12;
      minD = Math.min(minD, d - b.r);
      if (d < ph.w * 0.55 + b.r * 0.4) { g.cracked = true; finish('lose', b.T.name); return; }
      if (b.kind === 'boss') {
        g.bossTimer -= dt;
        if (g.bossTimer <= 0) { g.bossTimer = 2.4; spawn(Math.random() < 0.5 ? 'small' : 'label', b.x + rand(-b.w, b.w) * 0.3, b.y); }
      }
    }
    const danger = clamp(1 - (minD / g.W - 0.04) / 0.3, 0, 1);
    if (danger > 0.8 && g.t - g.lastWarn > 5) { g.lastWarn = g.t; say('Bug near the phone!'); }

    g.orbs.forEach(o => { o.life -= dt; }); g.orbs = g.orbs.filter(o => o.life > 0);
    g.corpses.forEach(c => { c.life -= dt; }); g.corpses = g.corpses.filter(c => c.life > 0);
    g.parts.forEach(p => { p.life -= dt; p.x += p.vx * dt; p.y += p.vy * dt; p.vy += 420 * dt; }); g.parts = g.parts.filter(p => p.life > 0);
    g.pops.forEach(p => { p.life -= dt; p.y -= 40 * dt; }); g.pops = g.pops.filter(p => p.life > 0);

    if (performance.now() - g.lastEmit > 100) {
      g.lastEmit = performance.now();
      const r = g.canvas.getBoundingClientRect();
      emit({ kind: 'state', x: r.left + g.aim.x * r.width, y: r.top + g.aim.y * r.height, danger, combo: g.combo });
    }
  }

  // ── drawing ───────────────────────────────────────────────────────────────
  function render() {
    const { ctx, W, H } = g;
    ctx.setTransform(g.dpr, 0, 0, g.dpr, 0, 0);
    ctx.clearRect(0, 0, W, H);
    if (g.shake > 0.3) ctx.translate(rand(-g.shake, g.shake), rand(-g.shake, g.shake));

    // scrolling code underneath, full of the same violations
    ctx.font = `${Math.max(9, W * 0.019)}px ${g.font}`;
    ctx.fillStyle = 'rgba(167,139,250,0.11)';
    const lh = W * 0.034, off = reduceMotion.matches ? 0 : (g.t * 10) % (lh * CODE.length);
    for (let i = -1, y = -off; y < H + lh; i++, y += lh) ctx.fillText(CODE[((i % CODE.length) + CODE.length) % CODE.length], W * 0.04, y + lh);

    drawPhone();
    if (g.up.laser) drawTurret();
    for (const bm of g.beams) {
      const k = bm.life / 0.18;
      ctx.save(); ctx.globalAlpha = k; ctx.lineCap = 'round';
      const grd = ctx.createLinearGradient(bm.x0, bm.y0, bm.x1, bm.y1);
      grd.addColorStop(0, '#a855f7'); grd.addColorStop(1, '#f472b6');
      ctx.strokeStyle = grd; ctx.lineWidth = 8; ctx.shadowColor = '#e879f9'; ctx.shadowBlur = 18;
      ctx.beginPath(); ctx.moveTo(bm.x0, bm.y0); ctx.lineTo(bm.x1, bm.y1); ctx.stroke();
      ctx.strokeStyle = '#fdf4ff'; ctx.lineWidth = 2.2; ctx.shadowBlur = 0;
      ctx.beginPath(); ctx.moveTo(bm.x0, bm.y0); ctx.lineTo(bm.x1, bm.y1); ctx.stroke();
      // a 4-point star sparkles where it lands
      ctx.fillStyle = '#fdf4ff'; ctx.shadowColor = '#f472b6'; ctx.shadowBlur = 12;
      starPath(ctx, bm.x1, bm.y1, g.W * 0.03 * (0.6 + 0.4 * k)); ctx.fill();
      ctx.restore();
    }

    for (const o of g.orbs) {
      const P = POWERS[o.kind], blink = o.life < 1.5 && !reduceMotion.matches ? 0.55 + 0.45 * Math.sin(g.t * TAU * 2) : 1;
      ctx.save(); ctx.globalAlpha = blink;
      ctx.shadowColor = P.color; ctx.shadowBlur = 18;
      ctx.fillStyle = '#0b0820'; ctx.strokeStyle = P.color; ctx.lineWidth = 3;
      ctx.beginPath(); ctx.arc(o.x, o.y, o.r, 0, TAU); ctx.fill(); ctx.stroke();
      ctx.shadowBlur = 0; ctx.fillStyle = P.color; ctx.font = `700 ${o.r * 1.1}px ${g.font}`; ctx.textAlign = 'center'; ctx.textBaseline = 'middle';
      ctx.fillText(P.label, o.x, o.y + 1); ctx.restore();
    }

    for (const c of g.corpses) {
      const img = sprite(c.kind), w = c.w, h = w * (img.height / img.width) * (img.naturalHeight ? 1 : 1);
      ctx.save(); ctx.globalAlpha = c.life / 0.45 * 0.8; ctx.translate(c.x, c.y + h * 0.3);
      ctx.scale(c.dir * 1.25, 0.25); ctx.drawImage(img, -w / 2, -h / 2, w, h); ctx.restore();
    }

    const hx = g.aim.x * W, hy = g.aim.y * H;
    for (const b of g.bugs) drawBug(b, hx, hy);

    for (const p of g.parts) { ctx.globalAlpha = clamp(p.life / p.max, 0, 1); ctx.fillStyle = p.c; ctx.fillRect(p.x - p.s / 2, p.y - p.s / 2, p.s, p.s); }
    ctx.globalAlpha = 1;
    ctx.textAlign = 'center'; ctx.textBaseline = 'middle';
    for (const p of g.pops) {
      ctx.globalAlpha = clamp(p.life / 0.8, 0, 1); ctx.fillStyle = p.color; ctx.font = `800 ${W * 0.03}px ${g.font}`;
      ctx.shadowColor = '#a855f7'; ctx.shadowBlur = 10; ctx.fillText(p.text, p.x, p.y);
    }
    ctx.globalAlpha = 1; ctx.shadowBlur = 0;

    for (const w of g.waves) {
      const k = 1 - w.life / w.max;
      ctx.globalAlpha = (1 - k) * 0.9; ctx.strokeStyle = w.c; ctx.lineWidth = (w.w || 2.5) * (1 - k * 0.6);
      ctx.beginPath(); ctx.arc(w.x, w.y, w.r0 + (w.r1 - w.r0) * (1 - Math.pow(1 - k, 3)), 0, TAU); ctx.stroke();
    }
    ctx.globalAlpha = 1;
    drawClaw();
    drawReticle(hx, hy);

    // active power-ups
    let py = H - W * 0.035;
    ctx.textAlign = 'left'; ctx.font = `700 ${W * 0.022}px ${g.font}`;
    for (const k in g.power) {
      if (g.power[k] <= 0) continue;
      ctx.fillStyle = POWERS[k].color; ctx.fillText(`${POWERS[k].name} ${Math.ceil(g.power[k])}s`, W * 0.03, py); py -= W * 0.035;
    }

    // wave banner
    if (g.state === 'intro' && !g.over) {
      const a = clamp(Math.min(g.stateT, 2.4 - g.stateT + 0.3) * 2.5, 0, 1);
      ctx.globalAlpha = a; ctx.textAlign = 'center';
      ctx.fillStyle = 'rgba(6,5,13,0.6)'; ctx.fillRect(0, H * 0.33, W, H * 0.2);
      ctx.fillStyle = '#f5f0ff'; ctx.font = `800 ${W * 0.06}px ${g.font}`; ctx.fillText(`Wave ${g.wave + 1} of ${WAVES.length}`, W / 2, H * 0.4);
      ctx.fillStyle = '#d8ccf5'; ctx.font = `${W * 0.024}px ${g.font}`; wrap(WAVES[g.wave].intro, W / 2, H * 0.47, W * 0.82, W * 0.032);
      ctx.globalAlpha = 1;
    }
  }

  function wrap(text, x, y, max, lh) {
    const words = text.split(' '); let line = '', yy = y;
    for (const w of words) {
      const t = line ? line + ' ' + w : w;
      if (g.ctx.measureText(t).width > max && line) { g.ctx.fillText(line, x, yy); line = w; yy += lh; } else line = t;
    }
    g.ctx.fillText(line, x, yy);
  }

  function drawPhone() {
    const { ctx } = g, p = phone(), x = p.x - p.w / 2, y = p.y - p.h / 2;
    ctx.save();
    ctx.shadowColor = g.cracked ? '#ff2e63' : '#c084fc'; ctx.shadowBlur = 22;
    ctx.fillStyle = '#0d0820'; ctx.strokeStyle = g.cracked ? '#ff2e63' : '#c084fc'; ctx.lineWidth = 3;
    roundRect(x, y, p.w, p.h, p.w * 0.18); ctx.fill(); ctx.stroke(); ctx.shadowBlur = 0;
    const sx = x + p.w * 0.1, sy = y + p.h * 0.1, sw = p.w * 0.8, sh = p.h * 0.78;
    const grd = ctx.createLinearGradient(0, sy, 0, sy + sh); grd.addColorStop(0, '#2e1065'); grd.addColorStop(1, '#7c3aed');
    ctx.fillStyle = grd; roundRect(sx, sy, sw, sh, p.w * 0.07); ctx.fill();
    if (IMG.logo.complete && IMG.logo.naturalWidth) ctx.drawImage(IMG.logo, p.x - sw * 0.35, sy + sh * 0.3, sw * 0.7, sw * 0.7);
    if (g.cracked) {
      ctx.strokeStyle = '#ffffff'; ctx.lineWidth = 1.6; ctx.beginPath();
      const cx = p.x + p.w * 0.08, cy = sy + sh * 0.35;
      [[-0.4, -0.3], [0.35, -0.42], [0.42, 0.25], [-0.3, 0.45], [0.05, 0.5]].forEach(([a, b]) => {
        ctx.moveTo(cx, cy); ctx.lineTo(cx + sw * a * 0.6, cy + sh * b * 0.3); ctx.lineTo(cx + sw * a, cy + sh * b * 0.6);
      });
      ctx.stroke();
    }
    ctx.restore();
  }
  // Melodie's turret: her crescent as the base, her ring with two little eyes that turn to the target,
  // and the 4-point star on top as the emitter, lighting up as the laser recharges
  function drawTurret() {
    const { ctx } = g, p = phone(), cx = p.x, cy = p.y - p.h * 0.5 - p.w * 0.2, R = p.w * 0.3;
    const L = LASER[g.up.laser], ready = 1 - clamp(g.laserT / L.every, 0, 1);
    const look = g.turretLook && g.t - g.turretLook.t < 0.6 ? g.turretLook : null;
    const ang = look ? Math.atan2(look.y - cy, look.x - cx) : -Math.PI / 2;
    ctx.save();
    // range hint
    ctx.globalAlpha = 0.12; ctx.strokeStyle = '#e879f9'; ctx.setLineDash([2, 6]); ctx.lineWidth = 1.5;
    ctx.beginPath(); ctx.arc(p.x, p.y - p.h * 0.55, L.range * g.W, Math.PI, 0); ctx.stroke(); ctx.setLineDash([]);
    ctx.globalAlpha = 1;
    // crescent base hugging the phone top
    ctx.fillStyle = '#6a14ec'; ctx.shadowColor = '#7c3aed'; ctx.shadowBlur = 10;
    ctx.beginPath(); ctx.arc(cx, cy + R * 0.2, R * 1.35, 0.15 * Math.PI, 0.85 * Math.PI);
    ctx.arc(cx, cy - R * 0.05, R * 1.15, 0.82 * Math.PI, 0.18 * Math.PI, true); ctx.closePath(); ctx.fill();
    // ring
    const ring = ctx.createLinearGradient(cx - R, cy - R, cx + R, cy + R);
    ring.addColorStop(0, '#f472b6'); ring.addColorStop(1, '#8b5cf6');
    ctx.fillStyle = '#0d0820'; ctx.strokeStyle = ring; ctx.lineWidth = R * 0.32; ctx.shadowColor = '#c084fc'; ctx.shadowBlur = 8 + 10 * ready;
    ctx.beginPath(); ctx.arc(cx, cy, R, 0, TAU); ctx.fill(); ctx.stroke(); ctx.shadowBlur = 0;
    // two eyes looking at the target
    const ex = Math.cos(ang) * R * 0.14, ey = Math.sin(ang) * R * 0.1;
    for (const sx of [-1, 1]) {
      const x = cx + sx * R * 0.36, y = cy + R * 0.05;
      ctx.fillStyle = '#f5d0fe';
      ctx.beginPath(); ctx.ellipse(x, y, R * 0.24, R * 0.14, -sx * 0.32, 0, TAU); ctx.fill();   // inner corner lower, like hers
      ctx.fillStyle = '#2e1065';
      ctx.beginPath(); ctx.arc(x + ex, y + ey, R * 0.1, 0, TAU); ctx.fill();
      ctx.strokeStyle = '#a855f7'; ctx.lineWidth = 1.6;      // the brow, slanted like hers
      ctx.lineWidth = 2.4; ctx.lineCap = 'round';
      ctx.beginPath(); ctx.moveTo(x + sx * R * 0.32, y - R * 0.3); ctx.lineTo(x - sx * R * 0.26, y - R * 0.08); ctx.stroke();
    }
    // star emitter on top
    const sr = R * (0.42 + 0.18 * ready);
    const sg = ctx.createLinearGradient(cx, cy - R * 1.4 - sr, cx, cy - R * 1.4 + sr);
    sg.addColorStop(0, ready >= 1 ? '#fdf4ff' : '#f9a8d4'); sg.addColorStop(1, '#c026d3');
    ctx.fillStyle = sg; ctx.shadowColor = '#f472b6'; ctx.shadowBlur = 6 + 14 * ready; ctx.globalAlpha = 0.55 + 0.45 * ready;
    starPath(ctx, cx, cy - R * 1.4, sr); ctx.fill();
    ctx.restore();
  }

  function roundRect(x, y, w, h, r) {
    const c = g.ctx; c.beginPath(); c.moveTo(x + r, y); c.arcTo(x + w, y, x + w, y + h, r); c.arcTo(x + w, y + h, x, y + h, r);
    c.arcTo(x, y + h, x, y, r); c.arcTo(x, y, x + w, y, r); c.closePath();
  }

  function drawBug(b, hx, hy) {
    const { ctx } = g, T = b.T, img = sprite(b.kind);
    const iw = img.naturalWidth || img.width, ih = img.naturalHeight || img.height;
    if (!iw) return;
    const w = b.w, h = w * ih / iw;
    let alpha = 1;
    if (T.hidden && g.power.lint <= 0) {
      const d = Math.hypot(b.x - hx, b.y - hy);
      const seen = hitR(false) * 1.15 * (g.up.lint >= 1 ? 1.6 : 1);
      alpha = d <= seen ? 0.85 : clamp(1 - d / (g.W * 0.24), g.up.lint >= 2 ? 0.3 : 0.05, 1);   // the reticle inspects what is inside it
    }
    if (T.camo && g.power.lint <= 0) alpha = (reduceMotion.matches ? 0.36 : 0.32 + 0.1 * Math.sin(g.t * TAU * 1.2)) + (g.up.lint >= 2 ? 0.18 : 0);
    ctx.save();
    ctx.translate(b.x, b.y);
    ctx.globalAlpha = alpha * 0.35; ctx.fillStyle = '#000';
    ctx.beginPath(); ctx.ellipse(0, h * 0.36, w * 0.36, h * 0.09, 0, 0, TAU); ctx.fill();
    ctx.globalAlpha = alpha;
    ctx.rotate(b.tilt);
    ctx.scale(b.dir, 1 + (reduceMotion.matches ? 0 : Math.sin(b.phase * 2) * 0.05));
    ctx.drawImage(img, -w / 2, -h / 2, w, h);
    if (b.flash > 0) { ctx.globalCompositeOperation = 'lighter'; ctx.globalAlpha = b.flash / 0.15; ctx.drawImage(img, -w / 2, -h / 2, w, h); }
    ctx.restore();
    if (T.hidden && g.power.lint > 0) { ctx.strokeStyle = '#38bdf8'; ctx.setLineDash([4, 4]); ctx.lineWidth = 1.5; ctx.beginPath(); ctx.arc(b.x, b.y, b.r * 1.15, 0, TAU); ctx.stroke(); ctx.setLineDash([]); }
    if (T.split) {   // two chevrons: it splits in two
      ctx.save(); ctx.globalAlpha = alpha; ctx.strokeStyle = '#f9a8d4'; ctx.lineWidth = 2.2; ctx.beginPath();
      const y = b.y - h * 0.55, s = w * 0.07;
      ctx.moveTo(b.x - s * 2.4, y - s); ctx.lineTo(b.x - s * 1.2, y); ctx.lineTo(b.x - s * 2.4, y + s);
      ctx.moveTo(b.x + s * 2.4, y - s); ctx.lineTo(b.x + s * 1.2, y); ctx.lineTo(b.x + s * 2.4, y + s);
      ctx.stroke(); ctx.restore();
    }
    if (b.maxHp > 1) {
      const bw = w * 0.7, bx = b.x - bw / 2, by = b.y - h * 0.62;
      ctx.fillStyle = 'rgba(0,0,0,0.6)'; ctx.fillRect(bx, by, bw, 6);
      ctx.fillStyle = '#ff2e63'; ctx.fillRect(bx, by, bw * b.hp / b.maxHp, 6);
      ctx.fillStyle = '#ffd1dc'; ctx.font = `700 ${g.W * 0.02}px ${g.font}`; ctx.textAlign = 'center'; ctx.fillText('BUILD FAILED', b.x, by - 9);
    }
  }

  // 4-point star like the ones in Melodie's orbit
  function starPath(ctx, x, y, r) {
    const k = 0.18;
    ctx.beginPath();
    ctx.moveTo(x, y - r);
    ctx.quadraticCurveTo(x + r * k, y - r * k, x + r, y);
    ctx.quadraticCurveTo(x + r * k, y + r * k, x, y + r);
    ctx.quadraticCurveTo(x - r * k, y + r * k, x - r, y);
    ctx.quadraticCurveTo(x - r * k, y - r * k, x, y - r);
    ctx.closePath();
  }

  // the player: Melodie's reticle (thin ring, dashed arc with beads, 4-point star in the centre)
  function drawReticle(x, y) {
    const { ctx, W } = g;
    const charge = g.pressT >= 0 ? clamp((g.t - g.pressT - 0.12) / (CHARGE_S - 0.12), 0, 1) : 0;
    const sinceSmash = g.t - g.smashT, squeeze = sinceSmash < 0.18 ? 1 - 0.35 * Math.sin(Math.PI * sinceSmash / 0.18) : 1;
    const base = hitR(false), r = (base + (hitR(true) - base) * charge) * squeeze;
    const ready = g.cool <= 0, gold = charge >= 1;
    const main = gold ? '#fde68a' : ready ? '#f0abfc' : '#a78bfa';
    const spin = reduceMotion.matches ? 0 : g.t * 0.9;
    ctx.save();
    ctx.shadowColor = gold ? '#fde68a' : '#c084fc'; ctx.shadowBlur = gold ? 16 : 10;
    // outer ring
    ctx.strokeStyle = main; ctx.globalAlpha = ready ? 0.95 : 0.55; ctx.lineWidth = 2;
    ctx.beginPath(); ctx.arc(x, y, r, 0, TAU); ctx.stroke();
    // cooldown: the dashed orbit arc completes itself
    const total = g.coolTotal;
    const fill = ready ? 1 : 1 - g.cool / total;
    ctx.globalAlpha = 0.95; ctx.lineWidth = 2.5; ctx.setLineDash([7, 6]); ctx.lineDashOffset = -spin * 20;
    ctx.beginPath(); ctx.arc(x, y, r + 8, -Math.PI / 2 + spin, -Math.PI / 2 + spin + TAU * 0.62 * fill); ctx.stroke();
    ctx.setLineDash([]);
    // beads riding the arc
    ctx.fillStyle = main;
    [0.0, 0.31, 0.62].forEach((f, i) => {
      if (f > 0.62 * fill + 0.001) return;
      const a = -Math.PI / 2 + spin + TAU * f;
      ctx.beginPath(); ctx.arc(x + Math.cos(a) * (r + 8), y + Math.sin(a) * (r + 8), i === 1 ? 3.6 : 2.8, 0, TAU); ctx.fill();
    });
    // ticks at the four cardinal points
    ctx.lineWidth = 2; ctx.strokeStyle = main;
    for (let k = 0; k < 4; k++) {
      const a = k * Math.PI / 2;
      ctx.beginPath(); ctx.moveTo(x + Math.cos(a) * (r - 6), y + Math.sin(a) * (r - 6)); ctx.lineTo(x + Math.cos(a) * (r - 1), y + Math.sin(a) * (r - 1)); ctx.stroke();
    }
    // centre star
    const sr = Math.max(7, W * 0.016) * (gold ? 1.3 : 1) * (sinceSmash < 0.18 ? 1.25 : 1);
    const grd = ctx.createLinearGradient(x, y - sr, x, y + sr);
    grd.addColorStop(0, gold ? '#fef3c7' : '#f9a8d4'); grd.addColorStop(1, gold ? '#f59e0b' : '#c026d3');
    ctx.fillStyle = grd; ctx.globalAlpha = 1;
    starPath(ctx, x, y, sr); ctx.fill();
    ctx.restore();
    // claw ready: a soft pulse around the reticle
    if (g.claw >= 1 && !g.clawFx) {
      const p = reduceMotion.matches ? 0.5 : 0.5 + 0.5 * Math.sin(g.t * TAU * 0.8);
      ctx.save(); ctx.strokeStyle = '#e879f9'; ctx.globalAlpha = 0.25 + 0.35 * p; ctx.lineWidth = 1.5;
      ctx.setLineDash([3, 5]); ctx.beginPath(); ctx.arc(x, y, clawR(), 0, TAU); ctx.stroke(); ctx.restore();
    }
  }

  // Melodie's claw falling from above onto the reticle, holding, then rising away
  function drawClaw() {
    const fx = g.clawFx, img = IMG.hand;
    if (!fx || !img.complete || !img.naturalWidth) return;
    const { ctx, W } = g, hw = W * 0.5, hh = hw * img.naturalHeight / img.naturalWidth;
    const tipX = 0.51, tipY = 0.9;                              // claw tips inside the sprite
    let k, alpha = 1;
    if (fx.t < CLAW_FALL) k = Math.pow(fx.t / CLAW_FALL, 2.2);              // accelerating fall
    else if (fx.t < CLAW_FALL + CLAW_HOLD) k = 1;
    else { const u = (fx.t - CLAW_FALL - CLAW_HOLD) / CLAW_RISE; k = 1 - u * u; alpha = 1 - u; }
    const startY = -hh * (1 - tipY) - 20, endY = fx.y;
    const y = startY + (endY - startY) * k;
    // shadow on the board grows as the claw comes down
    ctx.save();
    ctx.globalAlpha = 0.45 * k * alpha; ctx.fillStyle = '#000';
    ctx.beginPath(); ctx.ellipse(fx.x, fx.y + 6, clawR() * 0.55 * (0.4 + 0.6 * k), clawR() * 0.14, 0, 0, TAU); ctx.fill();
    ctx.globalAlpha = alpha;
    ctx.shadowColor = '#c084fc'; ctx.shadowBlur = 24;
    ctx.drawImage(img, fx.x - hw * tipX, y - hh * tipY, hw, hh);
    ctx.restore();
  }

  // ── end ───────────────────────────────────────────────────────────────────
  function finish(result, culprit) {
    if (!g || g.over) return;
    g.over = true; g.pressT = -1; g.keys.clear();
    const reached = Math.min(g.wave + 1, WAVES.length);
    const accuracy = g.swings ? g.hitSwings / g.swings : 0;
    const won = result === 'win';
    const rank = won ? (accuracy >= 0.75 && g.maxCombo >= 10 ? 'S' : 'A') : reached >= 4 ? 'B' : 'C';
    let top = g.top.slice(), record = false, mine = -1;
    if (g.score > 0) {
      record = !top.length || g.score > top[0].score;
      const entry = { score: g.score, wave: won ? WAVES.length : reached, date: Date.now(), won };
      top.push(entry); top.sort((a, b) => b.score - a.score); top = top.slice(0, 5); mine = top.indexOf(entry);
      writeTop(top);
    }
    const title = won ? 'Phone protected!' : result === 'quit' ? 'Game over' : `${culprit || 'A bug'} reached the phone!`;
    const $ = s => g.root.querySelector(s);
    $('.bg-end-rank').textContent = rank;
    $('.bg-end-rank').dataset.rank = rank;
    $('.bg-end-title').textContent = title;
    $('.bg-end-score').textContent = `${g.score} points · rank ${rank}`;
    const killed = Object.values(g.killed).reduce((a, b) => a + b, 0);
    $('.bg-end-stats').innerHTML =
      `<div><dt>Wave</dt><dd>${won ? WAVES.length : reached} of ${WAVES.length}</dd></div>` +
      `<div><dt>Accuracy</dt><dd>${Math.round(accuracy * 100)}%</dd></div>` +
      `<div><dt>Best combo</dt><dd>${g.maxCombo}</dd></div>` +
      `<div><dt>Smashed</dt><dd>${killed}</dd></div>`;
    $('.bg-record').hidden = !record;
    $('.bg-top').innerHTML = top.map((e, i) =>
      `<li${i === mine ? ' class="is-mine"' : ''}><span>${i + 1}.</span> ${e.score} pts${e.wave ? ` · wave ${e.wave}` : ''}${e.won ? ' ✓' : ''}</li>`).join('');
    const show = () => {
      if (!g) return;
      $('.bg-end').hidden = false;
      $('.bg-again').focus({ preventScroll: true });
      say(`${title} ${g.score} points, rank ${rank}, ${Math.round(accuracy * 100)} percent accuracy.${record ? ' New record!' : ''}`);

      armClose();
    };
    emit({ kind: 'end' });
    setTimeout(show, result === 'lose' ? 900 : 250);
  }

  // auto-close after the result; the timer belongs to this round only
  function armClose() {
    const me = g;
    clearTimeout(me.closeTimer);
    me.closeTimer = setTimeout(() => { if (g === me) close(); }, 15000);
  }

  function close(instant) {
    const cur = g; if (!cur) return;
    clearTimeout(cur.closeTimer);
    cancelAnimationFrame(cur.raf);
    cur.ro.disconnect();
    document.removeEventListener('visibilitychange', onHidden);
    if (!cur.over) emit({ kind: 'end' });
    g = null;
    if (instant === true) { cur.root.remove(); return; }
    cur.root.classList.remove('is-open');
    hero.classList.remove('is-gaming');
    setTimeout(() => cur.root.remove(), 420);
    const back = mark.querySelector('.bg-start');
    if (back && cur.root.contains(document.activeElement)) back.focus({ preventScroll: true });
  }

  // entry points: the big star (pointer) and a button that appears on keyboard focus
  mark.querySelectorAll('.mel-orbit .orb-star-1').forEach(st => st.addEventListener('click', e => { e.stopPropagation(); start(); }));
  const startBtn = mark.querySelector('.bg-start');
  if (startBtn) startBtn.addEventListener('click', start);

  // leaving the landing through the SPA router removes the hero
  window.addEventListener('spa:navigate', function onNav() {
    if (document.contains(mark)) return;
    if (g) { cancelAnimationFrame(g.raf); clearTimeout(g.closeTimer); g.ro.disconnect(); g = null; emit({ kind: 'end' }); }
    document.removeEventListener('visibilitychange', onHidden);
    window.removeEventListener('spa:navigate', onNav);
  });
})();
