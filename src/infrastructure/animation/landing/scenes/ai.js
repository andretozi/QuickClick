import { EASE_SPRING } from '../../core/motion.js';
import { growBars } from '../../core/effects.js';

/** Passo 3: radar girando, varredura nos canais e o canal recomendado em destaque. */
export function animateAi(animator, scene, { loop }) {
  const iterations = loop ? Infinity : 1;
  const channels = animator.parts('channel', scene);
  const recommended = channels.find((channel) => channel.hasAttribute('data-recommended'));

  animator.animate(animator.part('sweep', scene), [{ transform: 'rotate(0)' }, { transform: 'rotate(360deg)' }], {
    duration: 4200,
    iterations: Infinity,
    easing: 'linear'
  });

  animator.animate(
    animator.part('core', scene),
    [
      { transform: 'scale(1)', opacity: 0.92 },
      { transform: 'scale(1.08)', opacity: 1 },
      { transform: 'scale(1)', opacity: 0.92 }
    ],
    { duration: 2600, iterations: Infinity, easing: 'ease-in-out' }
  );

  animator.animate(
    animator.part('scan', scene),
    [
      { transform: 'translateY(-4px)', opacity: 0, offset: 0 },
      { opacity: 0.9, offset: 0.12 },
      { transform: 'translateY(118px)', opacity: 0.9, offset: 0.82 },
      { transform: 'translateY(128px)', opacity: 0, offset: 1 }
    ],
    { duration: 3200, iterations, easing: 'ease-in-out', fill: 'forwards' }
  );

  channels.forEach((channel, i) =>
    animator.animate(
      channel,
      [
        { boxShadow: '0 0 0 0 rgba(242,169,59,0)', offset: 0 },
        { boxShadow: '0 0 14px 0 rgba(242,169,59,.4)', offset: 0.15 },
        { boxShadow: '0 0 0 0 rgba(242,169,59,0)', offset: 0.4 },
        { boxShadow: '0 0 0 0 rgba(242,169,59,0)', offset: 1 }
      ],
      { duration: 3200, iterations, delay: i * 260, easing: 'ease-in-out' }
    )
  );

  animator.after(1000, () =>
    animator.animate(
      recommended,
      [
        { boxShadow: '0 0 0 0 rgba(255,106,61,0)' },
        { boxShadow: '0 0 26px 2px rgba(255,106,61,.5)' },
        { boxShadow: '0 0 0 0 rgba(255,106,61,0)' }
      ],
      { duration: 2600, iterations: Infinity, easing: 'ease-in-out' }
    )
  );

  animator.after(1200, () => {
    const tag = animator.part('tag', scene);
    if (!tag) return;
    tag.style.opacity = '1';
    animator.animate(
      tag,
      [
        { transform: 'scale(0) rotate(-10deg)', opacity: 0 },
        { transform: 'scale(1) rotate(0)', opacity: 1 }
      ],
      { duration: 520, easing: EASE_SPRING, fill: 'forwards' }
    );
  });

  growBars(animator, animator.parts('bar', scene), { start: 400, step: 110, duration: 720 });
}
