/* Melodie A11Y — Matrix text background (runs once, persists across SPA) */
(function () {
  if (document.getElementById('matrix-bg')) return; // already running

  const canvas = document.createElement('canvas');
  canvas.id = 'matrix-bg';
  canvas.style.cssText = 'position:fixed;inset:0;z-index:0;pointer-events:none;';
  document.body.prepend(canvas);

  const ctx = canvas.getContext('2d');
  const CHARS = 'abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789<>{}[]()=+/\\|;:,.#@!?';
  const CW = 8, CH = 16, FONT = 12;
  let cols, rows, grid;

  const rnd = () => CHARS[Math.random() * CHARS.length | 0];

  function resize() {
    canvas.width  = innerWidth;
    canvas.height = innerHeight;
    cols = Math.ceil(innerWidth  / CW);
    rows = Math.ceil(innerHeight / CH);
    grid = Array.from({ length: cols * rows }, rnd);
  }
  window.addEventListener('resize', resize);
  resize();

  const blobs = Array.from({ length: 11 }, () => ({
    x: Math.random(), y: Math.random(),
    r:  0.20 + Math.random() * 0.22,
    vx: (Math.random() - 0.5) * 0.0004,
    vy: (Math.random() - 0.5) * 0.0004,
    phase: Math.random() * Math.PI * 2,
  }));

  function draw(t) {
    ctx.fillStyle = '#06050d';
    ctx.fillRect(0, 0, canvas.width, canvas.height);
    ctx.font = `${FONT}px 'SF Mono','Fira Mono','Consolas',monospace`;
    ctx.textBaseline = 'top';

    for (const b of blobs) {
      b.x += b.vx; b.y += b.vy;
      if (b.x < 0 || b.x > 1) b.vx *= -1;
      if (b.y < 0 || b.y > 1) b.vy *= -1;
    }

    for (let i = 0; i < grid.length * 0.008; i++) {
      grid[Math.random() * grid.length | 0] = rnd();
    }

    const aspect = canvas.width / canvas.height;
    for (let y = 0; y < rows; y++) {
      for (let x = 0; x < cols; x++) {
        const nx = x / cols, ny = y / rows;
        let v = 0;
        for (const b of blobs) {
          const dx = (nx - b.x) * aspect, dy = ny - b.y;
          const pulse = 0.75 + 0.25 * Math.sin(t / 1500 + b.phase);
          v += Math.max(0, 1 - Math.hypot(dx, dy) / (b.r * pulse));
        }
        v *= 0.72 + 0.28 * Math.sin(x * 12.9898 + y * 78.233 + t / 900);
        if (v < 0.04) continue;
        const alpha = Math.min(v, 1) * 0.32;
        ctx.fillStyle = `rgba(168,85,247,${alpha.toFixed(3)})`;
        ctx.fillText(grid[y * cols + x], x * CW, y * CH);
      }
    }
    requestAnimationFrame(draw);
  }
  requestAnimationFrame(draw);
})();
