/* Melodie A11Y — SPA router: swaps .page content without full reload */
(function () {
  // Pages that use this router (keep audio alive)
  const SPA_PATHS = ['/analise', '/correcao', '/fix', '/scan', '/relatorios', '/docs', '/log', '/dashboard', '/teste'];

  // Push initial state so popstate works on first back
  // keep the query string and hash (e.g. /correcao?report=...) that the page itself may still read
  history.replaceState({ spa: location.pathname }, document.title, location.pathname + location.search + location.hash);

  function loadScript(src) {
    return new Promise(resolve => {
      const s = document.createElement('script');
      s.src = src;
      s.onload = resolve;
      s.onerror = () => { console.warn('[SPA] failed to load', src); resolve(); };
      document.head.appendChild(s);
    });
  }

  async function navigate(href) {
    const url = new URL(href, location.origin);
    const path = url.pathname;

    if (!SPA_PATHS.includes(path)) {
      location.href = href;
      return;
    }

    try {
      const html = await fetch(href).then(r => r.text());
      const doc = new DOMParser().parseFromString(html, 'text/html');
      const curPage = document.querySelector('.page');
      const newPage = doc.querySelector('.page');

      if (!curPage || !newPage) { location.href = href; return; }

      // Inject new page's styles (remove previously SPA-injected ones first)
      document.querySelectorAll('style[data-spa]').forEach(el => el.remove());
      doc.querySelectorAll('style').forEach(style => {
        const clone = document.createElement('style');
        clone.setAttribute('data-spa', 'true');
        clone.textContent = style.textContent;
        document.head.appendChild(clone);
      });

      curPage.replaceWith(newPage);
      newPage.style.background = 'transparent';
      document.title = doc.title;
      history.pushState({ spa: path }, doc.title, href);
      window.scrollTo(0, 0);

      // Sync active nav link
      document.querySelectorAll('.nav-link').forEach(el => {
        const elPath = new URL(el.getAttribute('href') || '', location.origin).pathname;
        el.classList.toggle('active', elPath === path);
      });

      // External libraries (e.g. Chart.js on /dashboard) must be loaded before the inline scripts that use them.
      const loaded = new Set([...document.querySelectorAll('script[src]')].map(s => s.getAttribute('src')));
      for (const el of doc.querySelectorAll('script[src]')) {
        const src = el.getAttribute('src');
        if (!loaded.has(src)) await loadScript(src);
      }

      // Execute inline scripts from the fetched page so app pages initialize.
      // Wrapped in IIFE + try-catch so errors in page scripts (e.g. Chart.js not
      // yet loaded) don't bubble up and trigger a full-page fallback reload.
      doc.querySelectorAll('script:not([src])').forEach(old => {
        const s = document.createElement('script');
        s.textContent = `(function(){try{\n${old.textContent}\n}catch(e){console.warn('[SPA]',e);}})();`;
        document.head.appendChild(s);
        document.head.removeChild(s);
      });

      // Remove landing footer margin so app pages fill to the bottom
      const footer = document.querySelector('footer');
      if (footer) footer.style.marginTop = '0';

      // Emit event for other modules to react
      window.dispatchEvent(new CustomEvent('spa:navigate', { detail: { path } }));

    } catch (_) {
      location.href = href;
    }
  }

  // Intercept clicks on internal links
  document.addEventListener('click', e => {
    const a = e.target.closest('a[href]');
    if (!a) return;
    if (a.target === '_blank' || e.ctrlKey || e.metaKey || e.shiftKey) return;
    const href = a.getAttribute('href');
    if (!href || !href.startsWith('/')) return;
    e.preventDefault();
    navigate(href);
  });

  // Handle browser back/forward
  window.addEventListener('popstate', e => {
    if (e.state && e.state.spa) navigate(location.href);
  });

  // ── TextScramble nav effect ─────────────────────────────────────────────────
  // Defined here so it initialises on every first page load, regardless of
  // which template the user lands on (not just landing.html).
  window.TextScramble = class {
    constructor(el) {
      this.el = el;
      this.original = el.textContent;
      this.chars = [...new Set(this.original.replace(/ /g, ''))].join('');
      this.timer = null;
    }
    scramble() {
      const original = this.original;
      const chars = this.chars;
      let iteration = -2.5;
      clearInterval(this.timer);
      this.timer = setInterval(() => {
        this.el.textContent = Array.from(original).map((ch, i) => {
          if (ch === ' ') return ' ';
          if (i < Math.floor(iteration)) return ch;
          return chars[Math.floor(Math.random() * chars.length)];
        }).join('');
        iteration += 0.42;
        if (iteration >= original.length) {
          clearInterval(this.timer);
          this.el.textContent = original;
        }
      }, 30);
    }
    restore() {
      clearInterval(this.timer);
      this.el.textContent = this.original;
    }
  }

  function initScramble() {
    document.querySelectorAll('.nav-link').forEach(el => {
      if (el.dataset.scrambleInit) return; // skip if already attached
      el.dataset.scrambleInit = '1';
      const ts = new window.TextScramble(el);
      el.addEventListener('mouseenter', () => ts.scramble());
      el.addEventListener('mouseleave',  () => ts.restore());
    });
  }

  // Init on first load and re-check on each SPA navigation (nav links don't
  // change, but the guard prevents double-attaching).
  if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', initScramble);
  } else {
    initScramble();
  }
  window.addEventListener('spa:navigate', initScramble);

})();
