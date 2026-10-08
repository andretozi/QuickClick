import { createAnimator } from '../core/createAnimator.js';
import { EASE_OUT_EXPO, EASE_SPRING, shouldReduceMotion } from '../core/motion.js';
import { pulseLogo } from '../core/effects.js';

/**
 * Diálogo de conexão abrindo: o fundo escurece e o cartão sobe com um leve pulo.
 * Roda antes da primeira pintura (useLayoutEffect), então o CSS não precisa esconder nada.
 */
export function runDialogEntrance(dialog) {
  const animator = createAnimator(dialog);
  if (shouldReduceMotion()) return animator.dispose;

  animator.animate(animator.part('backdrop'), [{ opacity: 0 }, { opacity: 1 }], {
    duration: 280,
    easing: 'ease-out'
  });
  animator.animate(
    animator.part('panel'),
    [
      { opacity: 0, transform: 'translateY(18px) scale(.95)' },
      { opacity: 1, transform: 'translateY(0) scale(1)' }
    ],
    { duration: 480, easing: EASE_SPRING }
  );
  return animator.dispose;
}

/**
 * Cada etapa do diálogo (confirmar, autorizando, erro) entra suave. No "Autorizando…",
 * os pontos andam do logo da Quick Click até o marketplace, sem parar.
 */
export function runDialogStep(step) {
  const animator = createAnimator(step);
  if (shouldReduceMotion()) return animator.dispose;

  animator.animate(
    step,
    [
      { opacity: 0, transform: 'translateY(8px)' },
      { opacity: 1, transform: 'translateY(0)' }
    ],
    { duration: 360, easing: EASE_OUT_EXPO }
  );

  animator.parts('dot', step).forEach((dot, i) =>
    animator.animate(
      dot,
      [
        { opacity: 0.25, transform: 'scale(.7)' },
        { opacity: 1, transform: 'scale(1.15)', offset: 0.35 },
        { opacity: 0.25, transform: 'scale(.7)' }
      ],
      { duration: 1100, delay: i * 160, iterations: Infinity, easing: 'ease-in-out' }
    )
  );
  pulseLogo(animator, { peakOpacity: 0.5, peakOffset: 0.05, endOffset: 0.4 });

  return animator.dispose;
}
