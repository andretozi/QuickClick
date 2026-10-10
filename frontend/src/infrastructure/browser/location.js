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

/** Vai para outro endereço da aplicação (ex.: "#/marketplaces"). */
export function navigateTo(hash) {
  window.location.hash = hash;
}

/**
 * Troca o endereço sem criar uma entrada nova no histórico (redirecionamentos).
 * Assim o "voltar" do navegador não cai de novo na página que redirecionou.
 */
export function replaceHash(hash) {
  const { pathname, search } = window.location;
  window.location.replace(`${pathname}${search}${hash}`);
}

/** Volta para o topo da página. */
export function scrollToTop() {
  window.scrollTo(0, 0);
}

/** Rola até o elemento com esse id (ex.: a seção "planos" da landing). */
export function scrollToAnchor(id) {
  document.getElementById(id)?.scrollIntoView();
}
