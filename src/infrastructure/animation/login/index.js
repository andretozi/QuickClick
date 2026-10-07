import { createAnimator } from '../core/createAnimator.js';
import { EASE_OUT_EXPO, shouldReduceMotion } from '../core/motion.js';
import { driftBlobs, floatY, pulseLogo, ripple } from '../core/effects.js';

/**
 * Animações do login: entrada em sequência dos blocos [data-enter="ordem"]
 * e o ambiente vivo do painel da marca. Devolve a função de limpeza.
 */
export function runLoginAnimations(root) {
  const animator = createAnimator(root);
  const items = animator
    .queryAll('[data-enter]')
    .sort((a, b) => Number(a.dataset.enter) - Number(b.dataset.enter));

  if (shouldReduceMotion()) {
    items.forEach((element) => {
      element.style.opacity = '1';
    });
    return animator.dispose;
  }

  items.forEach((element, i) =>
    animator.animate(
      element,
      [
        { opacity: 0, transform: 'translateY(22px)', filter: 'blur(7px)' },
        { opacity: 1, transform: 'translateY(0)', filter: 'blur(0)' }
      ],
      { duration: 780, delay: 130 + i * 90, easing: EASE_OUT_EXPO, fill: 'forwards' }
    )
  );

  driftBlobs(animator, { x: 24, y: 18, yStep: 8, scale: 1.12, duration: 12000, durationStep: 2600 });
  pulseLogo(animator, { peakOpacity: 0.5, peakOffset: 0.05, endOffset: 0.4 });
  floatY(animator, animator.part('proof'), { distance: 9, duration: 4200 });
  ripple(animator, animator.part('proof-ring'), { from: 0.7, to: 1.5, opacity: 0.55, duration: 2600 });

  return animator.dispose;
}
