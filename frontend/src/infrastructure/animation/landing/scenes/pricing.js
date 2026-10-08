const SWEEP_MS = 1300;
const PAUSE_MS = 3000;
const LOOP_START_MS = 4000;

const FROM = 'translateX(-160%) skewX(-16deg)';
const TO = 'translateX(460%) skewX(-16deg)';

/** Planos: uma faixa de brilho atravessa o cartão do Pro e repete com uma pausa entre as passadas. */
export function animatePricing(animator, card, { loop }) {
  const shine = animator.part('shine', card);

  animator.after(150, () =>
    animator.animate(shine, [{ transform: FROM }, { transform: TO }], {
      duration: SWEEP_MS,
      easing: 'cubic-bezier(.4,0,.2,1)',
      fill: 'forwards'
    })
  );

  if (!loop) return;

  const sweepEnd = SWEEP_MS / (SWEEP_MS + PAUSE_MS);
  animator.after(LOOP_START_MS, () =>
    animator.animate(
      shine,
      [
        { transform: FROM, offset: 0, easing: 'ease-in-out' },
        { transform: TO, offset: sweepEnd },
        { transform: TO, offset: 1 }
      ],
      { duration: SWEEP_MS + PAUSE_MS, iterations: Infinity }
    )
  );
}
