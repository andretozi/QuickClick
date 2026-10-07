import { EASE_OUT_EXPO } from '../../core/motion.js';

const CYCLE_MS = 4300;
const LISTING_HIDDEN = 'translateX(30px) scale(.9)';

/** Passo 2: a câmera foca, dispara o flash e o anúncio aparece ao lado. Repete. */
export function animatePhoto(animator, scene, { loop }) {
  const brackets = animator.parts('bracket', scene);
  const product = animator.part('product', scene);
  const shutter = animator.part('shutter', scene);
  const flash = animator.part('flash', scene);
  const listing = animator.part('listing', scene);
  let listingAnimation = null;

  const cycle = () => {
    // Esconde o anúncio da volta anterior antes de "tirar" a próxima foto
    listingAnimation?.cancel();

    brackets.forEach((bracket, i) =>
      animator.animate(
        bracket,
        [
          { transform: 'scale(1.3)', opacity: 0.25 },
          { transform: 'scale(1)', opacity: 1 }
        ],
        { duration: 500, delay: i * 60, easing: EASE_OUT_EXPO, fill: 'forwards' }
      )
    );

    animator.animate(product, [{ transform: 'scale(.94)' }, { transform: 'scale(1)' }], {
      duration: 620,
      easing: 'ease-out'
    });

    animator.after(720, () =>
      animator.animate(shutter, [{ transform: 'scale(1)' }, { transform: 'scale(.82)' }, { transform: 'scale(1)' }], {
        duration: 300,
        easing: 'ease-out'
      })
    );

    animator.after(770, () =>
      animator.animate(flash, [{ opacity: 0 }, { opacity: 0.92 }, { opacity: 0 }], {
        duration: 440,
        easing: 'ease-out'
      })
    );

    animator.after(910, () => {
      listingAnimation = animator.animate(
        listing,
        [
          { transform: LISTING_HIDDEN, opacity: 0 },
          { transform: 'translateX(0) scale(1)', opacity: 1 }
        ],
        { duration: 620, easing: EASE_OUT_EXPO, fill: 'forwards' }
      );
    });

    if (loop) animator.after(CYCLE_MS, cycle);
  };

  cycle();
}
