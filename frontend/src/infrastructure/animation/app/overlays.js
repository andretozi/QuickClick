import { createAnimator } from '../core/createAnimator.js';
import { EASE_OUT_EXPO, EASE_SPRING, shouldReduceMotion } from '../core/motion.js';
import { observeLoops } from '../core/loops.js';

/**
 * Entradas e saídas das camadas que ficam por cima da página: modal, menu do
 * usuário e avisos (toasts). Cada função recebe o elemento raiz da camada,
 * acha as partes por [data-part] e devolve a limpeza.
 */

const run = (root, play) => {
  const animator = createAnimator(root);
  if (!shouldReduceMotion()) play(animator);
  return animator.dispose;
};

/**
 * Modal abrindo: o fundo escurece e o painel sobe com mola. Como o modal mora fora da
 * casca (portal no body), os laços de dentro dele ([data-spin], [data-shimmer]) ligam aqui.
 */
export function playModalEnter(root) {
  return run(root, (animator) => {
    observeLoops(animator, root);
    animator.animate(animator.part('backdrop'), [{ opacity: 0 }, { opacity: 1 }], {
      duration: 300,
      easing: 'ease-out'
    });
    animator.animate(
      animator.part('panel'),
      [
        { opacity: 0, transform: 'translateY(26px) scale(.94)' },
        { opacity: 1, transform: 'translateY(0) scale(1)' }
      ],
      { duration: 560, easing: EASE_SPRING }
    );
  });
}

/** Modal fechando: o painel desce um pouco e tudo some. */
export function playModalExit(root) {
  return run(root, (animator) => {
    animator.animate(animator.part('backdrop'), [{ opacity: 1 }, { opacity: 0 }], {
      duration: 220,
      easing: 'ease-in',
      fill: 'forwards'
    });
    animator.animate(
      animator.part('panel'),
      [
        { opacity: 1, transform: 'translateY(0) scale(1)' },
        { opacity: 0, transform: 'translateY(14px) scale(.97)' }
      ],
      { duration: 220, easing: 'ease-in', fill: 'forwards' }
    );
  });
}

/** Menu do usuário abrindo do canto do avatar, com mola. */
export function playMenuEnter(menu) {
  return run(menu, (animator) => {
    animator.animate(
      menu,
      [
        { opacity: 0, transform: 'translateY(-10px) scale(.9)' },
        { opacity: 1, transform: 'translateY(0) scale(1)' }
      ],
      { duration: 520, easing: EASE_SPRING }
    );
    animator.parts('item', menu).forEach((item, i) =>
      animator.animate(
        item,
        [
          { opacity: 0, transform: 'translateX(-8px)' },
          { opacity: 1, transform: 'translateX(0)' }
        ],
        { duration: 380, delay: 60 + i * 35, easing: EASE_OUT_EXPO, fill: 'backwards' }
      )
    );
  });
}

export function playMenuExit(menu) {
  return run(menu, (animator) => {
    animator.animate(
      menu,
      [
        { opacity: 1, transform: 'translateY(0) scale(1)' },
        { opacity: 0, transform: 'translateY(-6px) scale(.96)' }
      ],
      { duration: 160, easing: 'ease-in', fill: 'forwards' }
    );
  });
}

/** Aviso chegando de baixo com mola. */
export function playToastEnter(toast) {
  return run(toast, (animator) => {
    animator.animate(
      toast,
      [
        { opacity: 0, transform: 'translateY(22px) scale(.92)' },
        { opacity: 1, transform: 'translateY(0) scale(1)' }
      ],
      { duration: 560, easing: EASE_SPRING }
    );
    animator.animate(
      animator.part('icon', toast),
      [
        { transform: 'scale(.4) rotate(-20deg)' },
        { transform: 'scale(1.15) rotate(6deg)', offset: 0.6 },
        { transform: 'scale(1) rotate(0)' }
      ],
      { duration: 620, delay: 80, easing: 'ease-out', fill: 'backwards' }
    );
  });
}

export function playToastExit(toast) {
  return run(toast, (animator) => {
    animator.animate(
      toast,
      [
        { opacity: 1, transform: 'translateY(0) scale(1)' },
        { opacity: 0, transform: 'translateY(10px) scale(.96)' }
      ],
      { duration: 240, easing: 'ease-in', fill: 'forwards' }
    );
  });
}
