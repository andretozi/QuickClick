/**
 * Runtime de animacao da landing "Quick Click".
 *
 * Port 1:1 do `class Component extends DCLogic` que vive em
 * html/Quick Click.dc.html (mantido em _legacy/ como referencia).
 * Todos os timings, curvas cubic-bezier, delays e ordem de disparo
 * sao identicos ao original.
 *
 * Framework-agnostic: recebe `rootEl` e devolve uma funcao `cleanup`.
 * O hook React (src/hooks/useLandingAnimations.js) e' uma casca fina
 * que chama este setup no `useEffect` e cancela no unmount.
 */

export function runLandingAnimations(rootEl, options = {}) {
  const motion = options.motion ?? 'Cinematográfica';
  const loopScenes = options.loopScenes ?? true;
  const parallax = options.parallax ?? true;
  const showTexture = options.showTexture ?? true;
  // A landing e' cinematografica por escolha do produto.
  // Passe respectReducedMotion={true} p/ honrar prefers-reduced-motion.
  const respectReducedMotion = options.respectReducedMotion ?? false;

  const amp = motion === 'Sutil' ? 0.4 : motion === 'Equilibrada' ? 0.7 : 1;
  const blurOn = motion !== 'Sutil';

  const timers = [];
  const anims = [];
  const q = (s, c) => (c || rootEl).querySelector(s);
  const qa = (s, c) => Array.from((c || rootEl).querySelectorAll(s));
  const after = (ms, fn) => {
    const t = setTimeout(fn, ms);
    timers.push(t);
    return t;
  };
  const A = (el, kf, animOpts) => {
    if (!el) return null;
    const a = el.animate(kf, animOpts);
    anims.push(a);
    return a;
  };
  // Sentinel para os loopers checarem se o setup ainda esta ativo.
  const state = { alive: true };

  qa('[data-tex]').forEach((el) => {
    if (!showTexture) el.style.backgroundImage = 'none';
  });

  const reduced =
    respectReducedMotion &&
    typeof window !== 'undefined' &&
    window.matchMedia &&
    matchMedia('(prefers-reduced-motion: reduce)').matches;

  if (reduced) {
    qa('[data-reveal]').forEach((el) => {
      el.style.opacity = '1';
      el.style.transform = 'none';
      el.style.filter = 'none';
    });
    qa('[data-hero-word]').forEach((el) => {
      el.style.opacity = '1';
      el.style.transform = 'none';
    });
    qa('[data-ck]').forEach((p) => {
      p.style.strokeDashoffset = '0';
    });
    ['[data-c-check]', '[data-c-done]', '[data-ia-tag]', '[data-v-toast]', '[data-v-amount]'].forEach(
      (s) => qa(s).forEach((e) => (e.style.opacity = '1'))
    );
    qa('[data-f-listing]').forEach((e) => {
      e.style.opacity = '1';
      e.style.transform = 'none';
    });
    qa('[data-c-fill]').forEach((e) => (e.style.width = '100%'));
    qa('[data-ia-bar],[data-v-bar]').forEach(
      (b) => (b.style.height = b.getAttribute('data-h') || '60%')
    );
    return () => {
      state.alive = false;
      timers.forEach(clearTimeout);
      anims.forEach((a) => {
        try {
          a.cancel();
        } catch {}
      });
    };
  }

  // --- ambient ---
  qa('[data-blob]').forEach((el, i) =>
    A(
      el,
      [
        { transform: 'translate(0,0) scale(1)' },
        {
          transform: `translate(${i % 2 ? -26 : 26}px,${-20 - i * 10}px) scale(1.1)`
        },
        { transform: 'translate(0,0) scale(1)' }
      ],
      { duration: 11000 + i * 2500, iterations: Infinity, easing: 'ease-in-out' }
    )
  );

  A(
    q('[data-badge-dot]'),
    [
      { boxShadow: '0 0 0 0 rgba(255,106,61,.5)' },
      { boxShadow: '0 0 0 9px rgba(255,106,61,0)' }
    ],
    { duration: 1900, iterations: Infinity, easing: 'ease-out' }
  );

  A(
    q('[data-arrow]'),
    [
      { transform: 'translateY(0)', opacity: 0.55 },
      { transform: 'translateY(7px)', opacity: 1 },
      { transform: 'translateY(0)', opacity: 0.55 }
    ],
    { duration: 1500, iterations: Infinity, easing: 'ease-in-out' }
  );

  qa('[data-logo-pulse]').forEach((el) =>
    A(
      el,
      [
        { transform: 'scale(.7)', opacity: 0, offset: 0 },
        { transform: 'scale(.7)', opacity: 0.55, offset: 0.04 },
        { transform: 'scale(1.55)', opacity: 0, offset: 0.38 },
        { transform: 'scale(1.55)', opacity: 0, offset: 1 }
      ],
      { duration: 5200, iterations: Infinity, easing: 'ease-out' }
    )
  );

  // --- scrollFx (nav auto-hide + parallax) ---
  const nav = q('[data-nav]');
  const pxEls = qa('[data-parallax]');
  if (nav) {
    nav.style.transition =
      'transform .45s cubic-bezier(.16,1,.3,1),background .35s,box-shadow .35s,border-color .35s';
  }
  let lastY = window.scrollY;
  let acc = 0;
  let hidden = false;
  let ticking = false;
  const apply = () => {
    const y = window.scrollY;
    if (nav) {
      const s = y > 24;
      nav.style.background = 'transparent';
      nav.style.backdropFilter = nav.style.webkitBackdropFilter = s
        ? 'blur(9px) saturate(1.12)'
        : 'none';
      nav.style.boxShadow = 'none';
      nav.style.borderBottomColor = 'transparent';
      const dy = y - lastY;
      if (dy > 0 && acc < 0) acc = 0;
      else if (dy < 0 && acc > 0) acc = 0;
      acc += dy;
      if (y < 90) {
        hidden = false;
        acc = 0;
      } else if (acc > 10) {
        hidden = true;
        acc = 0;
      } else if (acc < -10) {
        hidden = false;
        acc = 0;
      }
      nav.style.transform = hidden ? 'translateY(-108%)' : 'translateY(0)';
    }
    if (parallax) {
      pxEls.forEach((el) => {
        const sp = (parseFloat(el.getAttribute('data-parallax')) || 0.15) * amp;
        el.style.transform = `translate3d(0,${y * sp}px,0)`;
      });
    }
    lastY = y;
    ticking = false;
  };
  const onScroll = () => {
    if (!ticking) {
      ticking = true;
      requestAnimationFrame(apply);
    }
  };
  window.addEventListener('scroll', onScroll, { passive: true });
  apply();

  // --- reveals ---
  const bl = blurOn ? 6 : 0;
  const revealEls = qa('[data-reveal]');
  const initialTransform = new WeakMap();
  revealEls.forEach((el) => {
    const d = el.getAttribute('data-reveal') || 'up';
    const tx = (d === 'left' ? -1 : d === 'right' ? 1 : 0) * 46 * amp;
    const ty = (d === 'down' ? -1 : d === 'up' ? 1 : 0) * 46 * amp;
    const t = `translate(${tx}px,${ty}px)`;
    initialTransform.set(el, t);
    el.style.opacity = '0';
    el.style.transform = t;
    el.style.filter = bl ? `blur(${bl}px)` : 'none';
    el.style.willChange = 'transform,opacity';
  });
  const revealIO = new IntersectionObserver(
    (entries) => {
      entries.forEach((e) => {
        if (!e.isIntersecting) return;
        const el = e.target;
        const delay = parseInt(el.getAttribute('data-delay') || '0', 10);
        A(
          el,
          [
            {
              opacity: 0,
              transform: initialTransform.get(el),
              filter: bl ? `blur(${bl}px)` : 'none'
            },
            { opacity: 1, transform: 'translate(0,0)', filter: 'blur(0)' }
          ],
          { duration: 900, delay, easing: 'cubic-bezier(.16,1,.3,1)', fill: 'forwards' }
        );
        revealIO.unobserve(el);
      });
    },
    { threshold: 0.16, rootMargin: '0px 0px -6% 0px' }
  );
  revealEls.forEach((el) => revealIO.observe(el));

  // --- hero ---
  const w1 = q('[data-hero-word="1"]');
  const w2 = q('[data-hero-word="2"]');
  const cur = q('[data-cursor]');
  const rip = q('[data-ripple]');
  const heroBl = blurOn ? 10 : 0;

  const press = () => {
    const el = q('h1');
    if (!el) return;
    A(
      el,
      [
        { transform: 'translateY(0) scale(1)' },
        { transform: 'translateY(8px) scale(.952)', offset: 0.3 },
        { transform: 'translateY(-2px) scale(1.008)', offset: 0.62 },
        { transform: 'translateY(0) scale(1)' }
      ],
      { duration: 520, easing: 'cubic-bezier(.34,1.56,.64,1)' }
    );
    qa('[data-hero-word]').forEach((w) =>
      A(
        w,
        [
          { filter: 'brightness(1)' },
          { filter: 'brightness(.86)', offset: 0.3 },
          { filter: 'brightness(1)' }
        ],
        { duration: 520, easing: 'ease-out' }
      )
    );
  };

  [w1, w2].forEach((w) => {
    if (w) {
      w.style.transform = 'translateY(115%)';
      w.style.opacity = '0';
    }
  });
  A(
    w1,
    [
      { transform: 'translateY(115%)', opacity: 0, filter: `blur(${heroBl}px)` },
      { transform: 'translateY(0)', opacity: 1, filter: 'blur(0)' }
    ],
    { duration: 900, delay: 150, easing: 'cubic-bezier(.16,1,.3,1)', fill: 'forwards' }
  );
  if (cur) {
    cur.style.opacity = '0';
    after(650, () =>
      A(
        cur,
        [
          { opacity: 0, transform: 'translate(-34px,22px) scale(.6)' },
          { opacity: 1, transform: 'translate(0,0) scale(1)' }
        ],
        { duration: 420, easing: 'cubic-bezier(.16,1,.3,1)', fill: 'forwards' }
      )
    );
    after(1120, () => {
      A(
        cur,
        [
          { transform: 'translate(0,0) scale(1)' },
          { transform: 'translate(0,4px) scale(.8)' },
          { transform: 'translate(0,0) scale(1)' }
        ],
        { duration: 340, easing: 'ease-out' }
      );
      if (rip) {
        rip.style.opacity = '1';
        A(
          rip,
          [
            { transform: 'scale(0)', opacity: 0.55 },
            { transform: 'scale(1.4)', opacity: 0 }
          ],
          { duration: 760, easing: 'ease-out', fill: 'forwards' }
        );
      }
      press();
    });
  }
  A(
    w2,
    [
      { transform: 'translateY(115%)', opacity: 0, filter: `blur(${heroBl}px)` },
      { transform: 'translateY(0)', opacity: 1, filter: 'blur(0)' }
    ],
    { duration: 950, delay: 1150, easing: 'cubic-bezier(.16,1,.3,1)', fill: 'forwards' }
  );
  after(2150, () => {
    if (cur) {
      A(cur, [{ opacity: 1 }, { opacity: 0 }], { duration: 500, fill: 'forwards' });
    }
  });
  if (loopScenes && cur) {
    const loopClick = () => {
      if (!state.alive) return;
      A(
        cur,
        [
          { opacity: 0, transform: 'translate(-26px,18px) scale(.62)' },
          { opacity: 1, transform: 'translate(0,0) scale(1)' }
        ],
        { duration: 420, easing: 'cubic-bezier(.16,1,.3,1)', fill: 'forwards' }
      );
      after(470, () => {
        A(
          cur,
          [
            { transform: 'translate(0,0) scale(1)' },
            { transform: 'translate(0,4px) scale(.8)' },
            { transform: 'translate(0,0) scale(1)' }
          ],
          { duration: 340, easing: 'ease-out' }
        );
        if (rip) {
          rip.style.opacity = '1';
          A(
            rip,
            [
              { transform: 'scale(0)', opacity: 0.55 },
              { transform: 'scale(1.5)', opacity: 0 }
            ],
            { duration: 820, easing: 'ease-out', fill: 'forwards' }
          );
        }
        press();
      });
      after(1280, () =>
        A(cur, [{ opacity: 1 }, { opacity: 0 }], { duration: 520, fill: 'forwards' })
      );
      after(6500, loopClick);
    };
    after(6500, loopClick);
  }

  // --- scenes ---
  const scenes = {
    cadastro(el) {
      const fills = qa('[data-c-fill]', el);
      const checks = qa('[data-c-check]', el);
      const btn = q('[data-c-btn]', el);
      const done = q('[data-c-done]', el);
      const card = q('[data-c-card]', el);
      fills.forEach((f, i) => {
        after(300 + i * 650, () => {
          A(
            f,
            [{ width: '0%' }, { width: '100%' }],
            { duration: 520, easing: 'cubic-bezier(.16,1,.3,1)', fill: 'forwards' }
          );
          after(360, () => {
            const c = checks[i];
            if (!c) return;
            c.style.opacity = '1';
            A(
              c,
              [
                { transform: 'scale(0) rotate(-30deg)' },
                { transform: 'scale(1.25) rotate(0)' },
                { transform: 'scale(1) rotate(0)' }
              ],
              { duration: 440, easing: 'cubic-bezier(.34,1.56,.64,1)', fill: 'forwards' }
            );
          });
        });
      });
      after(300 + fills.length * 650 + 280, () => {
        A(
          btn,
          [
            { transform: 'scale(1)' },
            { transform: 'scale(.95)' },
            { transform: 'scale(1.04)' },
            { transform: 'scale(1)' }
          ],
          { duration: 540, easing: 'ease-out' }
        );
        if (done) {
          done.style.opacity = '1';
          A(
            done,
            [
              { transform: 'translateY(8px) scale(.9)', opacity: 0 },
              { transform: 'translateY(0) scale(1)', opacity: 1 }
            ],
            { duration: 500, easing: 'cubic-bezier(.34,1.56,.64,1)', fill: 'forwards' }
          );
        }
      });
      after(1500, () =>
        A(
          card,
          [
            { transform: 'translateY(0)' },
            { transform: 'translateY(-6px)' },
            { transform: 'translateY(0)' }
          ],
          { duration: 6000, iterations: Infinity, easing: 'ease-in-out' }
        )
      );
    },
    foto(el) {
      const flash = q('[data-f-flash]', el);
      const listing = q('[data-f-listing]', el);
      const br = qa('[data-f-bracket]', el);
      const shutter = q('[data-f-shutter]', el);
      const prod = q('[data-f-prod]', el);
      const cycle = () => {
        if (!state.alive) return;
        if (listing) {
          listing.style.opacity = '0';
          listing.style.transform = 'translateX(30px) scale(.9)';
        }
        br.forEach((b, i) =>
          A(
            b,
            [
              { transform: 'scale(1.3)', opacity: 0.25 },
              { transform: 'scale(1)', opacity: 1 }
            ],
            {
              duration: 500,
              delay: i * 60,
              easing: 'cubic-bezier(.16,1,.3,1)',
              fill: 'forwards'
            }
          )
        );
        A(
          prod,
          [{ transform: 'scale(.94)' }, { transform: 'scale(1)' }],
          { duration: 620, easing: 'ease-out' }
        );
        after(720, () =>
          A(
            shutter,
            [
              { transform: 'scale(1)' },
              { transform: 'scale(.82)' },
              { transform: 'scale(1)' }
            ],
            { duration: 300, easing: 'ease-out' }
          )
        );
        after(770, () => {
          if (flash) {
            A(
              flash,
              [{ opacity: 0 }, { opacity: 0.92 }, { opacity: 0 }],
              { duration: 440, easing: 'ease-out' }
            );
          }
        });
        after(910, () => {
          if (listing) {
            listing.style.opacity = '1';
            A(
              listing,
              [
                { transform: 'translateX(30px) scale(.9)', opacity: 0 },
                { transform: 'translateX(0) scale(1)', opacity: 1 }
              ],
              { duration: 620, easing: 'cubic-bezier(.16,1,.3,1)', fill: 'forwards' }
            );
          }
        });
        if (loopScenes) after(4300, cycle);
      };
      cycle();
    },
    ia(el) {
      const radar = q('[data-ia-radar]', el);
      const scan = q('[data-ia-scan]', el);
      const pills = qa('[data-ia-pill]', el);
      const rec = q('[data-ia-rec]', el);
      const tag = q('[data-ia-tag]', el);
      const bars = qa('[data-ia-bar]', el);
      const core = q('[data-ia-core]', el);
      const IT = loopScenes ? Infinity : 1;
      A(
        radar,
        [{ transform: 'rotate(0)' }, { transform: 'rotate(360deg)' }],
        { duration: 4200, iterations: Infinity, easing: 'linear' }
      );
      A(
        core,
        [
          { transform: 'scale(1)', opacity: 0.92 },
          { transform: 'scale(1.08)', opacity: 1 },
          { transform: 'scale(1)', opacity: 0.92 }
        ],
        { duration: 2600, iterations: Infinity, easing: 'ease-in-out' }
      );
      if (scan) {
        A(
          scan,
          [
            { transform: 'translateY(-4px)', opacity: 0, offset: 0 },
            { opacity: 0.9, offset: 0.12 },
            { transform: 'translateY(118px)', opacity: 0.9, offset: 0.82 },
            { transform: 'translateY(128px)', opacity: 0, offset: 1 }
          ],
          { duration: 3200, iterations: IT, easing: 'ease-in-out', fill: 'forwards' }
        );
      }
      pills.forEach((p, i) =>
        A(
          p,
          [
            { boxShadow: '0 0 0 0 rgba(242,169,59,0)', offset: 0 },
            { boxShadow: '0 0 14px 0 rgba(242,169,59,.4)', offset: 0.15 },
            { boxShadow: '0 0 0 0 rgba(242,169,59,0)', offset: 0.4 },
            { boxShadow: '0 0 0 0 rgba(242,169,59,0)', offset: 1 }
          ],
          {
            duration: 3200,
            iterations: IT,
            delay: i * 260,
            easing: 'ease-in-out'
          }
        )
      );
      after(1000, () =>
        A(
          rec,
          [
            { boxShadow: '0 0 0 0 rgba(255,106,61,0)' },
            { boxShadow: '0 0 26px 2px rgba(255,106,61,.5)' },
            { boxShadow: '0 0 0 0 rgba(255,106,61,0)' }
          ],
          { duration: 2600, iterations: Infinity, easing: 'ease-in-out' }
        )
      );
      if (tag) {
        after(1200, () => {
          tag.style.opacity = '1';
          A(
            tag,
            [
              { transform: 'scale(0) rotate(-10deg)', opacity: 0 },
              { transform: 'scale(1) rotate(0)', opacity: 1 }
            ],
            { duration: 520, easing: 'cubic-bezier(.34,1.56,.64,1)', fill: 'forwards' }
          );
        });
      }
      bars.forEach((b, i) => {
        const h = b.getAttribute('data-h') || '60%';
        after(400 + i * 110, () =>
          A(
            b,
            [{ height: '0%' }, { height: h }],
            { duration: 720, easing: 'cubic-bezier(.16,1,.3,1)', fill: 'forwards' }
          )
        );
      });
    },
    venda(el) {
      const toast = q('[data-v-toast]', el);
      const ring = q('[data-v-ring]', el);
      const bars = qa('[data-v-bar]', el);
      const amount = q('[data-v-amount]', el);
      const badge = q('[data-v-badge]', el);
      bars.forEach((b, i) => {
        const h = b.getAttribute('data-h') || '60%';
        after(250 + i * 130, () =>
          A(
            b,
            [{ height: '0%' }, { height: h }],
            { duration: 780, easing: 'cubic-bezier(.16,1,.3,1)', fill: 'forwards' }
          )
        );
      });
      after(950, () => {
        if (toast) {
          toast.style.opacity = '1';
          A(
            toast,
            [
              { transform: 'translateY(26px) scale(.85)', opacity: 0 },
              { transform: 'translateY(-6px) scale(1.03)', opacity: 1, offset: 0.7 },
              { transform: 'translateY(0) scale(1)', opacity: 1 }
            ],
            { duration: 720, easing: 'cubic-bezier(.34,1.56,.64,1)', fill: 'forwards' }
          );
        }
        if (ring) {
          ring.style.opacity = '1';
          A(
            ring,
            [
              { transform: 'scale(.5)', opacity: 0.6 },
              { transform: 'scale(1.5)', opacity: 0 }
            ],
            { duration: 1000, easing: 'ease-out', fill: 'forwards' }
          );
        }
        if (amount) {
          A(
            amount,
            [
              { transform: 'translateY(10px)', opacity: 0 },
              { transform: 'translateY(0)', opacity: 1 }
            ],
            { duration: 560, delay: 200, easing: 'cubic-bezier(.16,1,.3,1)', fill: 'forwards' }
          );
        }
      });
      after(2100, () => {
        if (ring) {
          A(
            ring,
            [
              { transform: 'scale(.5)', opacity: 0.45 },
              { transform: 'scale(1.5)', opacity: 0 }
            ],
            { duration: 2400, iterations: Infinity, easing: 'ease-out' }
          );
        }
      });
      after(1200, () =>
        A(
          badge,
          [
            { transform: 'translateY(0)' },
            { transform: 'translateY(-5px)' },
            { transform: 'translateY(0)' }
          ],
          { duration: 5000, iterations: Infinity, easing: 'ease-in-out' }
        )
      );
    },
    compare(el) {
      const cks = qa('[data-ck]', el);
      A(
        el,
        [{ transform: 'scale(.97)' }, { transform: 'scale(1)' }],
        { duration: 700, easing: 'cubic-bezier(.16,1,.3,1)', fill: 'forwards' }
      );
      cks.forEach((p, i) =>
        after(200 + i * 220, () => {
          p.style.strokeDashoffset = '0';
          A(
            p,
            [{ strokeDashoffset: 1 }, { strokeDashoffset: 0 }],
            { duration: 480, easing: 'cubic-bezier(.65,0,.35,1)', fill: 'forwards' }
          );
        })
      );
    },
    price(el) {
      const shine = q('[data-price-shine]', el);
      after(150, () => {
        if (shine) {
          A(
            shine,
            [
              { transform: 'translateX(-160%) skewX(-16deg)' },
              { transform: 'translateX(460%) skewX(-16deg)' }
            ],
            { duration: 1300, easing: 'cubic-bezier(.4,0,.2,1)', fill: 'forwards' }
          );
        }
      });
      after(4000, () => {
        if (shine) {
          A(
            shine,
            [
              { transform: 'translateX(-160%) skewX(-16deg)' },
              { transform: 'translateX(460%) skewX(-16deg)' }
            ],
            { duration: 1300, iterations: Infinity, easing: 'ease-in-out', delay: 3000 }
          );
        }
      });
    }
  };

  const sceneIO = new IntersectionObserver(
    (entries) => {
      entries.forEach((e) => {
        if (!e.isIntersecting) return;
        const k = e.target.getAttribute('data-scene');
        const fn = scenes[k];
        if (fn) fn(e.target);
        sceneIO.unobserve(e.target);
      });
    },
    { threshold: 0.3 }
  );

  qa('[data-scene]').forEach((el) => sceneIO.observe(el));

  return () => {
    state.alive = false;
    timers.forEach(clearTimeout);
    anims.forEach((a) => {
      try {
        a.cancel();
      } catch {}
    });
    revealIO.disconnect();
    sceneIO.disconnect();
    window.removeEventListener('scroll', onScroll);
  };
}
