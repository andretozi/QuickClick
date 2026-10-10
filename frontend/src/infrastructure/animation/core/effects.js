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

/**
 * Clique com mola: o elemento amassa, passa um pouco do tamanho e assenta,
 * como uma mola amortecida. Use num elemento interno (não no que já se move pelo JS).
 */
export function springPress(animator, element, { depth = 0.9, overshoot = 1.045, duration = 620 } = {}) {
  return animator.animate(
    element,
    [
      { transform: 'scale(1)', easing: 'cubic-bezier(.3,.6,.5,1)' },
      { transform: `scale(${depth})`, offset: 0.2, easing: 'cubic-bezier(.3,0,.3,1)' },
      { transform: `scale(${overshoot})`, offset: 0.52, easing: 'ease-in-out' },
      { transform: 'scale(.988)', offset: 0.78, easing: 'ease-in-out' },
      { transform: 'scale(1)' }
    ],
    { duration }
  );
}

/**
 * Número que conta do zero até o valor ao aparecer.
 * format: 'number' (1.234) ou 'money' (o valor chega em centavos e vira R$).
 */
export function countUp(animator, element, { to, from = 0, duration = 1400, delay = 0, format = 'number' } = {}) {
  if (!element) return;
  const formatter =
    format === 'money'
      ? new Intl.NumberFormat('pt-BR', { style: 'currency', currency: 'BRL' })
      : new Intl.NumberFormat('pt-BR');
  const render = (value) => {
    element.textContent = formatter.format(format === 'money' ? value / 100 : Math.round(value));
  };
  const easeOut = (t) => 1 - Math.pow(1 - t, 4);

  render(from);
  let frame = null;
  animator.after(delay, () => {
    const startedAt = performance.now();
    const tick = (now) => {
      if (!animator.alive) return;
      const t = Math.min(1, (now - startedAt) / duration);
      render(from + (to - from) * easeOut(t));
      if (t < 1) frame = requestAnimationFrame(tick);
    };
    frame = requestAnimationFrame(tick);
  });
  animator.onDispose(() => {
    if (frame !== null) cancelAnimationFrame(frame);
    render(to);
  });
}

/**
 * Linha que se desenha (gráficos, trilho de progresso). O path usa pathLength="1";
 * a posição final fica gravada no elemento, então ela continua desenhada depois.
 */
export function drawPath(animator, path, { duration = 900, delay = 0, easing = EASE_DRAW } = {}) {
  if (!path) return null;
  path.style.strokeDasharray = '1';
  path.style.strokeDashoffset = '0';
  return animator.animate(path, [{ strokeDashoffset: 1 }, { strokeDashoffset: 0 }], {
    duration,
    delay,
    easing,
    fill: 'both'
  });
}
