import { createAnimator } from '../core/createAnimator.js';
import { shouldReduceMotion } from '../core/motion.js';
import { driftBlobs, enterInSequence, pulseLogo } from '../core/effects.js';

/**
 * Animações do login: entrada em sequência dos blocos [data-enter="ordem"]
 * e o ambiente vivo do painel da marca (manchas de luz e pulso do logo).
 * Devolve a função de limpeza.
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

  enterInSequence(animator, items);
  driftBlobs(animator, { x: 24, y: 18, yStep: 8, scale: 1.12, duration: 12000, durationStep: 2600 });
  pulseLogo(animator, { peakOpacity: 0.5, peakOffset: 0.05, endOffset: 0.4 });

  return animator.dispose;
}
