import { EASE_OUT_EXPO, EASE_SPRING } from '../core/motion.js';
import { ripple } from '../core/effects.js';

const LOOP_EVERY_MS = 6500;

/**
 * Abertura do hero: "Clicou…" sobe, um cursor clica no título, "vendeu." aparece.
 * Depois o clique se repete de tempos em tempos.
 */
export function playHero(animator, { blur, loop }) {
  const hero = animator.query('[data-hero]');
  if (!hero) return;

  const title = animator.part('title', hero);
  const words = animator.parts('word', hero);
  const cursor = animator.part('cursor', hero);
  const rippleElement = animator.part('ripple', hero);
  const blurFilter = `blur(${blur ? 10 : 0}px)`;

  playAmbient(animator, hero);

  const showWord = (word, delay, duration) =>
    animator.animate(
      word,
      [
        { transform: 'translateY(115%)', opacity: 0, filter: blurFilter },
        { transform: 'translateY(0)', opacity: 1, filter: 'blur(0)' }
      ],
      { duration, delay, easing: EASE_OUT_EXPO, fill: 'forwards' }
    );

  const showCursor = (from) =>
    animator.animate(
      cursor,
      [
        { opacity: 0, transform: from },
        { opacity: 1, transform: 'translate(0,0) scale(1)' }
      ],
      { duration: 420, easing: EASE_OUT_EXPO, fill: 'forwards' }
    );

  const hideCursor = (duration) =>
    animator.animate(cursor, [{ opacity: 1 }, { opacity: 0 }], { duration, fill: 'forwards' });

  /** O título "afunda" como um botão sendo apertado. */
  const pressTitle = () => {
    animator.animate(
      title,
      [
        { transform: 'translateY(0) scale(1)' },
        { transform: 'translateY(8px) scale(.952)', offset: 0.3 },
        { transform: 'translateY(-2px) scale(1.008)', offset: 0.62 },
        { transform: 'translateY(0) scale(1)' }
      ],
      { duration: 520, easing: EASE_SPRING }
    );
    words.forEach((word) =>
      animator.animate(
        word,
        [{ filter: 'brightness(1)' }, { filter: 'brightness(.86)', offset: 0.3 }, { filter: 'brightness(1)' }],
        { duration: 520, easing: 'ease-out' }
      )
    );
  };

  const click = ({ rippleScale, rippleDuration }) => {
    animator.animate(
      cursor,
      [
        { transform: 'translate(0,0) scale(1)' },
        { transform: 'translate(0,4px) scale(.8)' },
        { transform: 'translate(0,0) scale(1)' }
      ],
      { duration: 340, easing: 'ease-out' }
    );
    ripple(animator, rippleElement, { from: 0, to: rippleScale, opacity: 0.55, duration: rippleDuration, iterations: 1 });
    pressTitle();
  };

  // Primeira vez
  showWord(words[0], 150, 900);
  animator.after(650, () => showCursor('translate(-34px,22px) scale(.6)'));
  animator.after(1120, () => click({ rippleScale: 1.4, rippleDuration: 760 }));
  showWord(words[1], 1150, 950);
  animator.after(2150, () => hideCursor(500));

  if (!loop) return;

  // Repetição
  const repeatClick = () => {
    showCursor('translate(-26px,18px) scale(.62)');
    animator.after(470, () => click({ rippleScale: 1.5, rippleDuration: 820 }));
    animator.after(1280, () => hideCursor(520));
    animator.after(LOOP_EVERY_MS, repeatClick);
  };
  animator.after(LOOP_EVERY_MS, repeatClick);
}

/** Pequenos movimentos contínuos: ponto do selo pulsando e seta de rolagem. */
function playAmbient(animator, hero) {
  animator.animate(
    animator.part('badge-dot', hero),
    [{ boxShadow: '0 0 0 0 rgba(255,106,61,.5)' }, { boxShadow: '0 0 0 9px rgba(255,106,61,0)' }],
    { duration: 1900, iterations: Infinity, easing: 'ease-out' }
  );

  animator.animate(
    animator.part('scroll-arrow', hero),
    [
      { transform: 'translateY(0)', opacity: 0.55 },
      { transform: 'translateY(7px)', opacity: 1 },
      { transform: 'translateY(0)', opacity: 0.55 }
    ],
    { duration: 1500, iterations: Infinity, easing: 'ease-in-out' }
  );
}
