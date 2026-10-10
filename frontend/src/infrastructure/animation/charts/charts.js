import { createAnimator } from '../core/createAnimator.js';
import { EASE_OUT_EXPO, EASE_SPRING, shouldReduceMotion } from '../core/motion.js';

/**
 * Entrada dos gráficos em SVG próprio (aba Insights). Os elementos são achados por data-*:
 *   [data-chart-draw]  linha que se desenha (stroke-dasharray);
 *   [data-chart-rise]  área ou forma que sobe do eixo (opacidade e escala vertical);
 *   [data-chart-grow]  barra que cresce a partir do começo (escala horizontal);
 *   [data-chart-arc]   fatia da rosca que gira até o lugar;
 *   [data-chart-pop]   ponto que aparece com mola.
 * O atraso de cada um vem de data-delay (ms). Devolve a limpeza.
 */
export function animateChart(root) {
  const animator = createAnimator(root);
  if (shouldReduceMotion()) return animator.dispose;
  const delayOf = (element, base = 0) => base + Number(element.dataset.delay ?? 0);

  animator.queryAll('[data-chart-draw]').forEach((path) => {
    const length = path.getTotalLength?.() ?? 0;
    if (!length) return;
    animator.animate(
      path,
      [
        { strokeDasharray: `${length}`, strokeDashoffset: length },
        { strokeDasharray: `${length}`, strokeDashoffset: 0 }
      ],
      { duration: 1400, delay: delayOf(path, 120), easing: 'cubic-bezier(.65,0,.35,1)', fill: 'backwards' }
    );
  });

  animator.queryAll('[data-chart-rise]').forEach((shape) => {
    animator.animate(
      shape,
      [
        { opacity: 0, transform: 'scaleY(0.2)' },
        { opacity: 1, transform: 'scaleY(1)' }
      ],
      { duration: 1100, delay: delayOf(shape, 260), easing: EASE_OUT_EXPO, fill: 'backwards' }
    );
  });

  animator.queryAll('[data-chart-grow]').forEach((bar) => {
    animator.animate(bar, [{ transform: 'scaleX(0)' }, { transform: 'scaleX(1)' }], {
      duration: 900,
      delay: delayOf(bar, 120),
      easing: EASE_SPRING,
      fill: 'backwards'
    });
  });

  animator.queryAll('[data-chart-arc]').forEach((arc) => {
    const length = Number(arc.dataset.length ?? 0);
    animator.animate(
      arc,
      [
        { strokeDasharray: `0 ${length + 1000}` },
        { strokeDasharray: arc.getAttribute('stroke-dasharray') }
      ],
      { duration: 1000, delay: delayOf(arc, 140), easing: EASE_OUT_EXPO, fill: 'backwards' }
    );
  });

  animator.queryAll('[data-chart-pop]').forEach((dot) => {
    animator.animate(dot, [{ transform: 'scale(0)' }, { transform: 'scale(1)' }], {
      duration: 620,
      delay: delayOf(dot, 500),
      easing: EASE_SPRING,
      fill: 'backwards'
    });
  });

  return animator.dispose;
}
