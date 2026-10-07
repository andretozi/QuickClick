import { createAnimator } from '../core/createAnimator.js';
import { getMotionSettings, shouldReduceMotion } from '../core/motion.js';
import { driftBlobs, pulseLogo } from '../core/effects.js';
import { setupNavigation } from './navigation.js';
import { setupParallax } from './parallax.js';
import { setupReveals } from './reveal.js';
import { playHero } from './hero.js';
import { setupScenes } from './scenes/index.js';
import { showFinalState } from './finalState.js';

/**
 * Liga todas as animações da landing e devolve a função de limpeza.
 * Cada parte da coreografia mora no seu próprio módulo:
 *   navigation → menu que some/volta    parallax → luzes do topo
 *   reveal     → entrada ao rolar        hero     → "Clicou… vendeu." + cursor
 *   scenes/    → uma coreografia por cena ([data-scene])
 *
 * @param {HTMLElement} root raiz da página
 */
export function runLandingAnimations(root) {
  const animator = createAnimator(root);
  const motion = getMotionSettings();

  setupNavigation(animator);

  if (shouldReduceMotion()) {
    showFinalState(animator);
    return animator.dispose;
  }

  driftBlobs(animator);
  pulseLogo(animator);
  if (motion.parallax) setupParallax(animator, motion);
  setupReveals(animator, motion);
  playHero(animator, motion);
  setupScenes(animator, motion);

  return animator.dispose;
}
