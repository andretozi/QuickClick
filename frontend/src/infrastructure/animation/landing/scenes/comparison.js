import { EASE_OUT_EXPO } from '../../core/motion.js';
import { drawCheck } from '../../core/effects.js';

/** Comparativo: o cartão da Quick Click "assenta" e os checks se desenham um a um. */
export function animateComparison(animator, card) {
  animator.animate(card, [{ transform: 'scale(.97)' }, { transform: 'scale(1)' }], {
    duration: 700,
    easing: EASE_OUT_EXPO,
    fill: 'forwards'
  });

  animator.parts('check', card).forEach((path, i) => animator.after(200 + i * 220, () => drawCheck(animator, path)));
}
