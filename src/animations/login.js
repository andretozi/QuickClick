/**
 * Runtime de animacao do login "Quick Click".
 *
 * Port 1:1 do `class Component extends DCLogic` que vive em
 * html/Login.dc.html (mantido em _legacy/ como referencia).
 *
 * Framework-agnostic: recebe `rootEl` e devolve `cleanup`.
 */

export function runLoginAnimations(rootEl, options = {}) {
  const ambientOn = options.ambient ?? true;
  const respectReducedMotion = options.respectReducedMotion ?? false;

  const timers = [];
  const anims = [];
  const q = (s, c) => (c || rootEl).querySelector(s);
  const qa = (s, c) => Array.from((c || rootEl).querySelectorAll(s));
  const A = (el, kf, animOpts) => {
    if (!el) return null;
    const a = el.animate(kf, animOpts);
    anims.push(a);
    return a;
  };

  const reduced =
    respectReducedMotion &&
    typeof window !== 'undefined' &&
    window.matchMedia &&
    matchMedia('(prefers-reduced-motion: reduce)').matches;

  if (reduced) {
    qa('[data-in]').forEach((el) => {
      el.style.opacity = '1';
      el.style.transform = 'none';
      el.style.filter = 'none';
    });
    return () => {
      timers.forEach(clearTimeout);
      anims.forEach((a) => {
        try {
          a.cancel();
        } catch {}
      });
    };
  }

  const els = qa('[data-in]').sort((a, b) => +a.dataset.in - +b.dataset.in);
  els.forEach((el, i) => {
    el.style.opacity = '0';
    el.style.transform = 'translateY(22px)';
    el.style.filter = 'blur(7px)';
    A(
      el,
      [
        { opacity: 0, transform: 'translateY(22px)', filter: 'blur(7px)' },
        { opacity: 1, transform: 'translateY(0)', filter: 'blur(0)' }
      ],
      {
        duration: 780,
        delay: 130 + i * 90,
        easing: 'cubic-bezier(.16,1,.3,1)',
        fill: 'forwards'
      }
    );
  });

  if (ambientOn) {
    qa('[data-blob]').forEach((el, i) =>
      A(
        el,
        [
          { transform: 'translate(0,0) scale(1)' },
          {
            transform: `translate(${i % 2 ? -24 : 24}px,${-18 - i * 8}px) scale(1.12)`
          },
          { transform: 'translate(0,0) scale(1)' }
        ],
        { duration: 12000 + i * 2600, iterations: Infinity, easing: 'ease-in-out' }
      )
    );
  }

  qa('[data-logo-pulse]').forEach((el) =>
    A(
      el,
      [
        { transform: 'scale(.7)', opacity: 0, offset: 0 },
        { transform: 'scale(.7)', opacity: 0.5, offset: 0.05 },
        { transform: 'scale(1.55)', opacity: 0, offset: 0.4 },
        { transform: 'scale(1.55)', opacity: 0, offset: 1 }
      ],
      { duration: 5200, iterations: Infinity, easing: 'ease-out' }
    )
  );

  const proof = q('[data-proof]');
  if (proof && ambientOn) {
    A(
      proof,
      [
        { transform: 'translateY(0)' },
        { transform: 'translateY(-9px)' },
        { transform: 'translateY(0)' }
      ],
      { duration: 4200, iterations: Infinity, easing: 'ease-in-out' }
    );
  }

  const ring = q('[data-proof-ring]');
  if (ring) {
    A(
      ring,
      [
        { transform: 'scale(.7)', opacity: 0.55 },
        { transform: 'scale(1.5)', opacity: 0 }
      ],
      { duration: 2600, iterations: Infinity, easing: 'ease-out' }
    );
  }

  return () => {
    timers.forEach(clearTimeout);
    anims.forEach((a) => {
      try {
        a.cancel();
      } catch {}
    });
  };
}

export function pressAnimation(el) {
  if (!el) return;
  el.animate(
    [
      { transform: 'scale(1)' },
      { transform: 'scale(.955)' },
      { transform: 'scale(1)' }
    ],
    { duration: 300, easing: 'ease-out' }
  );
}
