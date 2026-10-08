import { createAnimator } from '../core/createAnimator.js';
import { shouldReduceMotion } from '../core/motion.js';
import { driftBlobs, enterInSequence, pulseLogo } from '../core/effects.js';

/** Mostra de uma vez os elementos que entrariam animados (só quando o movimento é reduzido). */
export function showAll(elements) {
  elements.forEach((element) => {
    element.style.opacity = '1';
  });
}

/**
 * Tela de marketplaces: manchas de luz no fundo, pulso do logo e a entrada do topo
 * (título e texto com [data-enter]). Os cards têm a própria entrada (cards.js),
 * porque só aparecem quando os dados chegam da API.
 */
export function runMarketplacesAnimations(root) {
  const animator = createAnimator(root);
  const items = animator.queryAll('[data-enter]');

  if (shouldReduceMotion()) {
    showAll(items);
    return animator.dispose;
  }

  enterInSequence(animator, items);
  driftBlobs(animator, { x: 30, y: 22, yStep: 10, scale: 1.12, duration: 12000, durationStep: 2600 });
  pulseLogo(animator);

  return animator.dispose;
}
