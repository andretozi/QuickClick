import { MARKETPLACE_SHOWCASE_SCENE_MS, SHOWCASE_PARTICLES } from '../../core/config.js';
import { createSpring, quadraticPoint, between } from '../../core/physics.js';
import { frameLoop, watchVisibility } from '../../core/frameLoop.js';
import { createParticleField } from '../../core/particleField.js';

/**
 * Vitrine de marketplaces (seção #marketplaces da landing), em tela cheia.
 *
 * Cada marketplace é uma cena com o fundo da marca. A cada MARKETPLACE_SHOWCASE_SCENE_MS
 * (core/config.js), na ordem:
 *   1. troca de cena: a atual sai pela direita e a próxima entra pela esquerda, numa mola
 *      que desacelera até parar; o fundo anda mais devagar que a cena e o logo mais rápido
 *      (parallax);
 *   2. o cursor da marca entra numa curva e para sobre o logo;
 *   3. clique com física: o cursor afunda e volta, o logo amassa e volta, sai um anel de onda
 *      e uma explosão de partículas (gravidade, resistência do ar e giro);
 *   4. molas puxam as partículas e elas formam a palavra da cena ("Já integrado" ou "Em breve");
 *   5. a palavra fica cerca de 1 s, se desfaz, o cursor sai e vem a próxima.
 * O laço é infinito. Fora da tela ou com a aba oculta, tudo pausa (o relógio da cena junto).
 */

const SCENE_MS = MARKETPLACE_SHOWCASE_SCENE_MS;

/** Em que ponto da cena cada passo acontece (fração do tempo da cena). */
const CUES = [
  { at: 0.2, run: 'cursorIn' },
  { at: 0.34, run: 'click' },
  { at: 0.44, run: 'formWord' },
  { at: 0.78, run: 'dissolve' }
];

const SLIDE_SPRING = { stiffness: 38, damping: 10.5 }; // um leve passo além antes de assentar
const BACKDROP_PARALLAX = 0.42; // o fundo anda 58% do caminho da cena
const LOGO_PARALLAX = 0.28; // o logo anda 128%
const CURRENT_CLASS = 'showcase__slide--current';
const CREAM_TITLE_CLASS = 'showcase__header--cream';
const MOBILE = '(max-width: 720px)';

export function animateMarketplaces(animator, scene) {
  const slides = animator.parts('slide', scene);
  const cursor = animator.part('cursor', scene);
  const ring = animator.part('ring', scene);
  const header = animator.part('header', scene);
  const canvas = animator.part('particles', scene);
  if (slides.length < 2 || !cursor || !canvas) return;

  const field = createParticleField(animator, canvas);
  const slideParts = slides.map((slide) => ({
    slide,
    far: animator.part('depth-far', slide),
    logo: animator.part('logo', slide),
    mark: animator.part('logo', slide)?.firstElementChild
  }));

  let width = scene.clientWidth;
  let height = scene.clientHeight;
  let current = 0;
  let previous = null;
  let sceneTime = 0;
  const fired = new Set();
  const progress = createSpring({ ...SLIDE_SPRING, position: 1 });

  const isMobile = () => window.matchMedia(MOBILE).matches;

  // ---------- Medidas ----------
  const logoBox = () => {
    const logo = slideParts[current].logo;
    return { width: logo?.offsetWidth ?? width * 0.5, height: logo?.offsetHeight ?? height * 0.3 };
  };

  const logoCenter = () => ({ x: width / 2, y: height * 0.5 });

  /** Onde a ponta do cursor clica: um pouco à direita e abaixo do meio do logo. */
  const clickPoint = () => {
    const center = logoCenter();
    const box = logoBox();
    return { x: center.x + box.width * 0.1, y: center.y + box.height * 0.12 };
  };

  // ---------- Troca de cenas ----------
  function placeSlide(index, offset) {
    const parts = slideParts[index];
    parts.slide.style.transform = `translate3d(${offset.toFixed(1)}px,0,0)`;
    if (parts.far) parts.far.style.transform = `translate3d(${(-offset * BACKDROP_PARALLAX).toFixed(1)}px,0,0)`;
    if (parts.logo) parts.logo.style.transform = `translate3d(${(offset * LOGO_PARALLAX).toFixed(1)}px,0,0)`;
  }

  function render() {
    const p = progress.position;
    placeSlide(current, (p - 1) * width);
    if (previous !== null) {
      placeSlide(previous, p * width);
      if (progress.isResting(0.002)) {
        slides[previous].classList.remove(CURRENT_CLASS);
        placeSlide(previous, 0);
        previous = null;
      }
    }
  }

  function setTitleTone() {
    header?.classList.toggle(CREAM_TITLE_CLASS, slides[current].dataset.titleTone === 'cream');
  }

  /** A próxima cena entra pela esquerda, a atual sai pela direita. */
  function advance() {
    if (previous !== null) slides[previous].classList.remove(CURRENT_CLASS);
    previous = current;
    current = (current + 1) % slides.length;
    slides[current].classList.add(CURRENT_CLASS);
    progress.jump(0);
    progress.setTarget(1);
    setTitleTone();
  }

  // ---------- Cursor ----------
  const hotspot = () => ({ x: cursor.offsetWidth * (4 / 24), y: cursor.offsetHeight * (3 / 24) });

  const cursorTransform = (point, { scale = 1, rotate = 0 } = {}) => {
    const hot = hotspot();
    return `translate(${(point.x - hot.x).toFixed(1)}px, ${(point.y - hot.y).toFixed(1)}px) rotate(${rotate.toFixed(1)}deg) scale(${scale.toFixed(3)})`;
  };

  /** Voo numa curva de Bézier, amostrado em keyframes. */
  function flyCursor(from, control, to, { duration, easing, fadeIn = false, fadeOut = false, scaleFrom = 1, scaleTo = 1 }) {
    const steps = 16;
    const frames = Array.from({ length: steps + 1 }, (_, i) => {
      const t = i / steps;
      const point = quadraticPoint(from, control, to, t);
      return {
        offset: t,
        transform: cursorTransform(point, { scale: scaleFrom + (scaleTo - scaleFrom) * t, rotate: (fadeIn ? 1 - t : t) * -18 }),
        opacity: fadeIn ? Math.min(1, t * 2.4) : fadeOut ? Math.min(1, (1 - t) * 2.2) : 1
      };
    });
    animator.animate(cursor, frames, { duration, easing, fill: 'forwards' });
  }

  function cursorIn() {
    const target = clickPoint();
    const from = { x: width * 0.92, y: height * 1.05 };
    const control = { x: width * 0.98, y: target.y - height * 0.2 };
    flyCursor(from, control, target, {
      duration: SCENE_MS * 0.12,
      easing: 'cubic-bezier(.22,.9,.32,1)',
      fadeIn: true,
      scaleFrom: 0.7
    });
  }

  function click() {
    const point = clickPoint();

    // o cursor afunda e volta com mola
    animator.animate(
      cursor,
      [
        { transform: cursorTransform(point), offset: 0 },
        { transform: cursorTransform({ x: point.x, y: point.y + 8 }, { scale: 0.78 }), offset: 0.26 },
        { transform: cursorTransform(point, { scale: 1.08 }), offset: 0.6 },
        { transform: cursorTransform(point, { scale: 0.98 }), offset: 0.82 },
        { transform: cursorTransform(point), offset: 1 }
      ],
      { duration: 560, easing: 'ease-out', fill: 'forwards' }
    );

    // o logo amassa e volta
    const mark = slideParts[current].mark;
    if (mark) {
      animator.animate(
        mark,
        [
          { transform: 'scale(1, 1)' },
          { transform: 'scale(1.07, 0.88)', offset: 0.22 },
          { transform: 'scale(0.96, 1.05)', offset: 0.5 },
          { transform: 'scale(1.015, 0.99)', offset: 0.76 },
          { transform: 'scale(1, 1)' }
        ],
        { duration: 760, easing: 'ease-out' }
      );
    }

    // anel de onda grande
    if (ring) {
      ring.style.left = `${point.x}px`;
      ring.style.top = `${point.y}px`;
      animator.animate(
        ring,
        [
          { opacity: 1, transform: 'scale(.2)' },
          { opacity: 0, transform: 'scale(2.6)' }
        ],
        { duration: 1000, easing: 'cubic-bezier(.2,.7,.3,1)' }
      );
    }

    // explosão
    const mobile = isMobile();
    field.burst(point.x, point.y, {
      count: Math.round(between(0.9, 1.1) * (mobile ? SHOWCASE_PARTICLES.mobile : SHOWCASE_PARTICLES.desktop)),
      power: mobile ? 0.7 : 1
    });
  }

  function formWord() {
    const center = logoCenter();
    const box = logoBox();
    const size = isMobile() ? width * 0.12 : Math.min(width * 0.07, 108);
    field.formWord(slides[current].dataset.word ?? '', {
      x: width / 2,
      y: Math.min(height - size * 0.8, center.y + box.height / 2 + size * 0.75),
      size,
      maxWidth: width * 0.86
    });
  }

  function dissolve() {
    field.scatter();
    const point = clickPoint();
    flyCursor(point, { x: point.x + width * 0.12, y: point.y + height * 0.05 }, { x: width * 1.05, y: -height * 0.1 }, {
      duration: SCENE_MS * 0.1,
      easing: 'cubic-bezier(.5,0,.75,.4)',
      fadeOut: true,
      scaleTo: 0.82
    });
  }

  const ACTIONS = { cursorIn, click, formWord, dissolve };

  /** Avança o relógio da cena e dispara cada passo uma vez. */
  function tick(dt) {
    sceneTime += dt;
    if (sceneTime >= SCENE_MS) {
      sceneTime -= SCENE_MS;
      fired.clear();
      advance();
    }
    CUES.forEach((cue) => {
      if (!fired.has(cue.run) && sceneTime >= cue.at * SCENE_MS) {
        fired.add(cue.run);
        ACTIONS[cue.run]();
      }
    });
  }

  // ---------- Fundo vivo: manchas e faixas em movimento lento ----------
  scene.querySelectorAll('[data-part="drift"]').forEach((orb, i) => {
    const dx = 4 + (i % 3) * 2;
    animator.animate(
      orb,
      [
        { transform: 'translate(0, 0) scale(1)' },
        { transform: `translate(${dx}%, ${-dx}%) scale(1.12)` },
        { transform: `translate(${-dx}%, ${dx / 2}%) scale(.94)` },
        { transform: 'translate(0, 0) scale(1)' }
      ],
      { duration: 14000 + (i % 3) * 3000, iterations: Infinity, easing: 'ease-in-out' }
    );
  });
  scene.querySelectorAll('[data-part="streak"]').forEach((streak, i) => {
    animator.animate(
      streak,
      [
        { transform: 'translateX(-60vw) rotate(18deg)' },
        { transform: 'translateX(60vw) rotate(18deg)' }
      ],
      { duration: 9000 + i * 2600, delay: i * -3800, iterations: Infinity, easing: 'cubic-bezier(.45,0,.55,1)' }
    );
  });
  scene.querySelectorAll('[data-part="spot"]').forEach((spot) => {
    animator.animate(
      spot,
      [
        { opacity: 0.92, transform: 'translate(-50%, -48%) scale(1)' },
        { opacity: 1, transform: 'translate(-50%, -48%) scale(1.06)' },
        { opacity: 0.92, transform: 'translate(-50%, -48%) scale(1)' }
      ],
      { duration: 7000, iterations: Infinity, easing: 'ease-in-out' }
    );
  });

  // ---------- Começo: a primeira cena (Mercado Livre) já está na tela ----------
  slides.forEach((slide, i) => slide.classList.toggle(CURRENT_CLASS, i === 0));
  setTitleTone();
  render();

  const loop = frameLoop(animator, (dt) => {
    tick(dt);
    progress.step(dt);
    render();
  });

  // Pausa fora da tela e com a aba oculta (o relógio da cena para junto)
  let paused = [];
  watchVisibility(animator, scene, (visible) => {
    if (visible) {
      loop.resume();
      field.resume();
      paused.forEach((animation) => animation.play());
      paused = [];
    } else {
      loop.pause();
      field.pause();
      paused = scene.getAnimations({ subtree: true }).filter((animation) => animation.playState === 'running');
      paused.forEach((animation) => animation.pause());
    }
  });

  const resize = new ResizeObserver(() => {
    width = scene.clientWidth;
    height = scene.clientHeight;
    render();
  });
  resize.observe(scene);
  animator.onDispose(() => resize.disconnect());
}
