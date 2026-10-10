import { createAnimator } from '../core/createAnimator.js';
import { shouldReduceMotion } from '../core/motion.js';
import { driftBlobs, pulseLogo } from '../core/effects.js';
import { observeEntrances } from '../core/entrances.js';
import { observeLoops } from '../core/loops.js';
import { setupNavigation } from '../landing/navigation.js';

/**
 * Casca da área logada (AppShell): as luzes do fundo flutuam, o logo pulsa, o
 * navbar ganha vidro ao rolar, cada bloco [data-enter] entra em sequência,
 * inclusive os que aparecem depois (dados que chegam, abas que trocam), e o brilho
 * [data-shimmer] e [data-spin] rodam em laço (core/loops.js).
 * Devolve a função de limpeza.
 */
export function runShellAnimations(root) {
  const animator = createAnimator(root);
  setupNavigation(animator, { hideOnScroll: false });

  if (shouldReduceMotion()) {
    observeEntrances(animator, root, { instant: true });
    return animator.dispose;
  }

  driftBlobs(animator, { x: 34, y: 26, yStep: 12, scale: 1.14, duration: 14000, durationStep: 3000 });
  pulseLogo(animator, { peakOpacity: 0.5, peakOffset: 0.05, endOffset: 0.4 });
  observeEntrances(animator, root);
  observeLoops(animator, root);
  return animator.dispose;
}

/**
 * Página sozinha com fundo cinematográfico (404 e telas cheias): mesmas luzes e
 * mesma entrada em sequência, sem navbar.
 */
export function runStandaloneAnimations(root) {
  const animator = createAnimator(root);
  if (shouldReduceMotion()) {
    observeEntrances(animator, root, { instant: true });
    return animator.dispose;
  }
  driftBlobs(animator, { x: 30, y: 24, yStep: 10, scale: 1.12, duration: 13000, durationStep: 2800 });
  pulseLogo(animator);
  observeEntrances(animator, root, { start: 120, step: 90 });
  return animator.dispose;
}
