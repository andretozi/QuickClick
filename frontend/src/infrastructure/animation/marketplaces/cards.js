import { createAnimator } from '../core/createAnimator.js';
import { EASE_SPRING, shouldReduceMotion } from '../core/motion.js';
import { drawCheck, enterInSequence, ripple } from '../core/effects.js';
import { showAll } from './index.js';

/** O painel do plano e os cards ([data-enter]) entram em sequência, um depois do outro. */
export function runCardsEntrance(container) {
  const animator = createAnimator(container);
  const items = animator.queryAll('[data-enter]');

  if (shouldReduceMotion()) {
    showAll(items);
    return animator.dispose;
  }

  enterInSequence(animator, items, { start: 80, step: 70, settle: true });
  return animator.dispose;
}

/** Card que acabou de conectar: o selo "Conectado" aparece, o check se desenha e uma onda sai do monograma. */
export function playConnected(card) {
  const animator = createAnimator(card);
  if (shouldReduceMotion()) return animator.dispose;

  animator.animate(
    animator.part('status'),
    [
      { transform: 'scale(.7)', opacity: 0 },
      { transform: 'scale(1)', opacity: 1 }
    ],
    { duration: 460, easing: EASE_SPRING }
  );
  animator.after(120, () => drawCheck(animator, animator.part('check'), { duration: 560 }));
  ripple(animator, animator.part('wave'), { from: 0.7, to: 1.9, opacity: 0.7, duration: 1100, iterations: 1 });
  animator.after(420, () =>
    ripple(animator, animator.part('wave'), { from: 0.7, to: 1.6, opacity: 0.45, duration: 1300, iterations: 1 })
  );

  return animator.dispose;
}
