/**
 * Chama `callback(scrollY)` no máximo uma vez por quadro enquanto a página rola.
 * O listener é removido sozinho quando o animador é descartado.
 */
export function onScrollFrame(animator, callback) {
  let ticking = false;

  const update = () => {
    ticking = false;
    if (animator.alive) callback(window.scrollY);
  };

  const onScroll = () => {
    if (ticking) return;
    ticking = true;
    requestAnimationFrame(update);
  };

  window.addEventListener('scroll', onScroll, { passive: true });
  animator.onDispose(() => window.removeEventListener('scroll', onScroll));
  callback(window.scrollY);
}
