/**
 * Infraestrutura · Navegador
 * Único lugar que conversa com window.location e com a rolagem da janela.
 */

/** Hash atual da URL (ex.: "#/login", "#como" ou ""). */
export function getHash() {
  return window.location.hash;
}

/** Avisa sempre que o hash mudar. Devolve a função que cancela a inscrição. */
export function subscribeToHashChange(listener) {
  window.addEventListener('hashchange', listener);
  return () => window.removeEventListener('hashchange', listener);
}

/** Volta para o topo da página. */
export function scrollToTop() {
  window.scrollTo(0, 0);
}
