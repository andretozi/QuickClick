import { EASE_OUT_EXPO, EASE_SPRING } from '../../core/motion.js';
import { floatY, growBars, ripple } from '../../core/effects.js';

/** Passo 4: o faturamento sobe e chega a notificação "Vendido!". */
export function animateSale(animator, scene) {
  const toast = animator.part('toast', scene);
  const ring = animator.part('ring', scene);
  const amount = animator.part('amount', scene);

  growBars(animator, animator.parts('bar', scene), { start: 250, step: 130, duration: 780 });

  animator.after(950, () => {
    animator.animate(
      toast,
      [
        { transform: 'translateY(26px) scale(.85)', opacity: 0 },
        { transform: 'translateY(-6px) scale(1.03)', opacity: 1, offset: 0.7 },
        { transform: 'translateY(0) scale(1)', opacity: 1 }
      ],
      { duration: 720, easing: EASE_SPRING, fill: 'forwards' }
    );
    ripple(animator, ring, { from: 0.5, to: 1.5, opacity: 0.6, duration: 1000, iterations: 1 });
    animator.animate(
      amount,
      [
        { transform: 'translateY(10px)', opacity: 0 },
        { transform: 'translateY(0)', opacity: 1 }
      ],
      { duration: 560, delay: 200, easing: EASE_OUT_EXPO, fill: 'forwards' }
    );
  });

  animator.after(1200, () => floatY(animator, animator.part('store', scene), { distance: 5, duration: 5000 }));
  animator.after(2100, () => ripple(animator, ring, { from: 0.5, to: 1.5, opacity: 0.45, duration: 2400 }));
}
