import { EASE_OUT_EXPO } from '../../core/motion.js';

const DRAW_EASING = 'cubic-bezier(.65,0,.35,1)';

/** Comparativo: o cartão da Quick Click "assenta" e os checks se desenham um a um. */
export function animateComparison(animator, card) {
  animator.animate(card, [{ transform: 'scale(.97)' }, { transform: 'scale(1)' }], {
    duration: 700,
    easing: EASE_OUT_EXPO,
    fill: 'forwards'
  });

  animator.parts('check', card).forEach((path, i) =>
    animator.after(200 + i * 220, () => {
      path.style.strokeDashoffset = '0';
      animator.animate(path, [{ strokeDashoffset: 1 }, { strokeDashoffset: 0 }], {
        duration: 480,
        easing: DRAW_EASING,
        fill: 'forwards'
      });
    })
  );
}
