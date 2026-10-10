/**
 * Laço de quadros (requestAnimationFrame) ligado a um animador.
 *
 * `onFrame(dtMs, nowMs)` roda a cada quadro com o tempo real desde o quadro anterior
 * (limitado, para uma aba que volta do segundo plano não dar um salto).
 * Devolve { pause, resume, stop }. O dispose do animador para o laço sozinho.
 */
export function frameLoop(animator, onFrame) {
  let frame = null;
  let last = null;
  let running = false;

  const tick = (now) => {
    if (!running || !animator.alive) return;
    const dt = last === null ? 16 : Math.min(now - last, 50);
    last = now;
    onFrame(dt, now);
    frame = requestAnimationFrame(tick);
  };

  const resume = () => {
    if (running || !animator.alive) return;
    running = true;
    last = null;
    frame = requestAnimationFrame(tick);
  };

  const pause = () => {
    running = false;
    if (frame !== null) cancelAnimationFrame(frame);
    frame = null;
  };

  animator.onDispose(pause);
  resume();
  return { pause, resume, stop: pause };
}

/**
 * Chama `onChange(visible)` quando o elemento entra ou sai da tela, ou quando a aba
 * fica oculta ou volta. Usado para pausar animações contínuas que ninguém está vendo.
 */
export function watchVisibility(animator, element, onChange, { threshold = 0.05 } = {}) {
  let onScreen = false;
  let lastVisible = null;

  const update = () => {
    const visible = onScreen && document.visibilityState === 'visible';
    if (visible === lastVisible) return;
    lastVisible = visible;
    onChange(visible);
  };

  const observer = new IntersectionObserver(
    ([entry]) => {
      onScreen = entry.isIntersecting;
      update();
    },
    { threshold }
  );
  observer.observe(element);
  document.addEventListener('visibilitychange', update);

  animator.onDispose(() => {
    observer.disconnect();
    document.removeEventListener('visibilitychange', update);
  });
}
