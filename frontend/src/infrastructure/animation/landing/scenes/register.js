import { EASE_OUT_EXPO, EASE_SPRING } from '../../core/motion.js';
import { floatY } from '../../core/effects.js';

const START_MS = 300;
const FIELD_INTERVAL_MS = 650;

/** Passo 1: os campos se preenchem um a um, ganham check e a loja é criada. */
export function animateRegister(animator, scene) {
  const fills = animator.parts('fill', scene);
  const checks = animator.parts('check', scene);

  fills.forEach((fill, i) =>
    animator.after(START_MS + i * FIELD_INTERVAL_MS, () => {
      animator.animate(fill, [{ width: '0%' }, { width: '100%' }], {
        duration: 520,
        easing: EASE_OUT_EXPO,
        fill: 'forwards'
      });
      animator.after(360, () => popCheck(animator, checks[i]));
    })
  );

  animator.after(START_MS + fills.length * FIELD_INTERVAL_MS + 280, () => {
    animator.animate(
      animator.part('button', scene),
      [{ transform: 'scale(1)' }, { transform: 'scale(.95)' }, { transform: 'scale(1.04)' }, { transform: 'scale(1)' }],
      { duration: 540, easing: 'ease-out' }
    );
    animator.animate(
      animator.part('done', scene),
      [
        { transform: 'translateY(8px) scale(.9)', opacity: 0 },
        { transform: 'translateY(0) scale(1)', opacity: 1 }
      ],
      { duration: 500, easing: EASE_SPRING, fill: 'forwards' }
    );
  });

  animator.after(1500, () => floatY(animator, animator.part('card', scene), { distance: 6, duration: 6000 }));
}

function popCheck(animator, check) {
  if (!check) return;
  check.style.opacity = '1';
  animator.animate(
    check,
    [
      { transform: 'scale(0) rotate(-30deg)' },
      { transform: 'scale(1.25) rotate(0)' },
      { transform: 'scale(1) rotate(0)' }
    ],
    { duration: 440, easing: EASE_SPRING, fill: 'forwards' }
  );
}
