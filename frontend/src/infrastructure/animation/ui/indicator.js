import { EASE_SPRING, shouldReduceMotion } from '../core/motion.js';

/**
 * Indicador que anda até a opção ativa (seletor segmentado, abas, navegação lateral).
 * Acha o indicador por [data-part="indicator"] e a opção ativa por [data-active].
 * A posição anterior fica guardada no próprio indicador, para a mola sair dela.
 * Devolve a limpeza (cancela a animação em andamento).
 */
export function placeIndicator(container, { animate = true } = {}) {
  const indicator = container.querySelector('[data-part="indicator"]');
  const active = container.querySelector('[data-active]');
  if (!indicator || !active) return undefined;

  const to = { x: active.offsetLeft, y: active.offsetTop, w: active.offsetWidth, h: active.offsetHeight };
  const from = indicator.dataset.ready
    ? {
        x: Number(indicator.dataset.x),
        y: Number(indicator.dataset.y),
        w: Number(indicator.dataset.w),
        h: Number(indicator.dataset.h)
      }
    : null;

  const frame = ({ x, y, w, h }) => ({ width: `${w}px`, height: `${h}px`, transform: `translate(${x}px, ${y}px)` });
  Object.assign(indicator.style, frame(to));
  Object.assign(indicator.dataset, { ready: '1', x: to.x, y: to.y, w: to.w, h: to.h });

  const moved = from && (from.x !== to.x || from.y !== to.y || from.w !== to.w || from.h !== to.h);
  if (!animate || !moved || shouldReduceMotion()) return undefined;

  const animation = indicator.animate([frame(from), frame(to)], { duration: 560, easing: EASE_SPRING });
  return () => animation.cancel();
}

/** Recoloca o indicador (sem animar) quando o tamanho do grupo muda. */
export function watchIndicator(container) {
  const observer = new ResizeObserver(() => placeIndicator(container, { animate: false }));
  observer.observe(container);
  return () => observer.disconnect();
}
