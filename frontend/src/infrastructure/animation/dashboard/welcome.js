import { createAnimator } from '../core/createAnimator.js';
import { EASE_SPRING, shouldReduceMotion } from '../core/motion.js';
import { ripple } from '../core/effects.js';
import { createParticleField } from '../core/particleField.js';

/**
 * Boas vindas depois do cadastro: o banner entra com mola, o selo de check pula
 * girando e duas explosões de partículas saem dele. Devolve a limpeza.
 */
export function playWelcome(root) {
  const animator = createAnimator(root);
  if (shouldReduceMotion()) return animator.dispose;

  const badge = animator.part('badge');
  const canvas = animator.part('particles');
  const field = canvas ? createParticleField(animator, canvas) : null;

  animator.animate(
    root,
    [
      { opacity: 0, transform: 'translateY(-16px) scale(.94)' },
      { opacity: 1, transform: 'translateY(0) scale(1)' }
    ],
    { duration: 700, easing: EASE_SPRING }
  );
  animator.animate(
    badge,
    [
      { transform: 'scale(0) rotate(-40deg)' },
      { transform: 'scale(1.22) rotate(10deg)', offset: 0.6 },
      { transform: 'scale(1) rotate(0)' }
    ],
    { duration: 760, delay: 220, easing: 'ease-out', fill: 'backwards' }
  );
  ripple(animator, animator.part('wave'), { from: 0.6, to: 2.4, opacity: 0.7, duration: 1100, iterations: 1 });

  const explode = () => {
    if (!badge || !field) return;
    const rootBox = root.getBoundingClientRect();
    const box = badge.getBoundingClientRect();
    field.burst(box.left - rootBox.left + box.width / 2, box.top - rootBox.top + box.height / 2, { count: 36, power: 0.6 });
  };
  animator.after(420, explode);
  animator.after(1500, explode);

  return animator.dispose;
}
