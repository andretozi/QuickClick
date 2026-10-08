import { EASE_DRAW, EASE_OUT_EXPO } from './motion.js';

/**
 * Efeitos reutilizados pela landing e pelo login.
 * Cada função recebe o animador e parâmetros; nenhuma conhece a página.
 */

/** Manchas de luz ([data-blob]) flutuando devagar no fundo. */
export function driftBlobs(
  animator,
  { x = 26, y = 20, yStep = 10, scale = 1.1, duration = 11000, durationStep = 2500 } = {}
) {
  animator.queryAll('[data-blob]').forEach((blob, i) =>
    animator.animate(
      blob,
      [
        { transform: 'translate(0,0) scale(1)' },
        { transform: `translate(${i % 2 ? -x : x}px,${-y - i * yStep}px) scale(${scale})` },
        { transform: 'translate(0,0) scale(1)' }
      ],
      { duration: duration + i * durationStep, iterations: Infinity, easing: 'ease-in-out' }
    )
  );
}

/** Anel que pulsa em volta do logo ([data-logo-pulse]). */
export function pulseLogo(animator, { peakOpacity = 0.55, peakOffset = 0.04, endOffset = 0.38 } = {}) {
  animator.queryAll('[data-logo-pulse]').forEach((ring) =>
    animator.animate(
      ring,
      [
        { transform: 'scale(.7)', opacity: 0, offset: 0 },
        { transform: 'scale(.7)', opacity: peakOpacity, offset: peakOffset },
        { transform: 'scale(1.55)', opacity: 0, offset: endOffset },
        { transform: 'scale(1.55)', opacity: 0, offset: 1 }
      ],
      { duration: 5200, iterations: Infinity, easing: 'ease-out' }
    )
  );
}

/** Sobe e desce suavemente, em loop (cards e notificações flutuando). */
export function floatY(animator, element, { distance = 6, duration = 6000 } = {}) {
  return animator.animate(
    element,
    [
      { transform: 'translateY(0)' },
      { transform: `translateY(-${distance}px)` },
      { transform: 'translateY(0)' }
    ],
    { duration, iterations: Infinity, easing: 'ease-in-out' }
  );
}

/** Onda que se expande e some (anéis de confirmação, clique do cursor). */
export function ripple(
  animator,
  element,
  { from = 0.7, to = 1.5, opacity = 0.55, duration = 2600, iterations = Infinity } = {}
) {
  return animator.animate(
    element,
    [
      { transform: `scale(${from})`, opacity },
      { transform: `scale(${to})`, opacity: 0 }
    ],
    { duration, iterations, easing: 'ease-out', fill: iterations === Infinity ? 'none' : 'forwards' }
  );
}

/**
 * Barras de gráfico crescendo uma depois da outra.
 * A altura final vem da variável CSS --bar-height de cada barra.
 */
export function growBars(animator, bars, { start = 0, step = 120, duration = 750 } = {}) {
  bars.forEach((bar, i) => {
    const height = bar.style.getPropertyValue('--bar-height') || '60%';
    animator.after(start + i * step, () =>
      animator.animate(bar, [{ height: '0%' }, { height }], {
        duration,
        easing: EASE_OUT_EXPO,
        fill: 'forwards'
      })
    );
  });
}

/**
 * Check que se desenha. O path usa pathLength="1" e o CSS começa com
 * stroke-dasharray: 1 (o traço vai de "escondido" a "inteiro").
 */
export function drawCheck(animator, path, { duration = 480 } = {}) {
  if (!path) return null;
  path.style.strokeDashoffset = '0';
  return animator.animate(path, [{ strokeDashoffset: 1 }, { strokeDashoffset: 0 }], {
    duration,
    easing: EASE_DRAW,
    fill: 'forwards'
  });
}

/**
 * Entrada em sequência: cada elemento sobe, perde o desfoque e aparece um pouco
 * depois do anterior. `settle` devolve o elemento ao CSS no fim (o :hover volta a funcionar).
 */
export function enterInSequence(
  animator,
  elements,
  { start = 130, step = 90, distance = 22, blur = 7, duration = 780, settle = false } = {}
) {
  elements.forEach((element, i) => {
    const animation = animator.animate(
      element,
      [
        { opacity: 0, transform: `translateY(${distance}px)`, filter: `blur(${blur}px)` },
        { opacity: 1, transform: 'translateY(0)', filter: 'blur(0)' }
      ],
      { duration, delay: start + i * step, easing: EASE_OUT_EXPO, fill: 'forwards' }
    );
    if (settle && animation) {
      animation.addEventListener('finish', () => {
        element.style.opacity = '1';
        animation.cancel();
      });
    }
  });
}

/** Feedback de clique: o elemento "afunda" e volta. */
export function press(element, { scale = 0.955, duration = 300 } = {}) {
  if (!element) return;
  element.animate(
    [{ transform: 'scale(1)' }, { transform: `scale(${scale})` }, { transform: 'scale(1)' }],
    { duration, easing: 'ease-out' }
  );
}
