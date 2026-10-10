/**
 * Infraestrutura · Foco do teclado
 * Quem estava com o foco, prender o foco dentro de um diálogo e levar o foco
 * para o conteúdo principal ao trocar de página.
 */

const FOCUSABLE = [
  'a[href]',
  'button:not([disabled])',
  'input:not([disabled]):not([type="hidden"])',
  'select:not([disabled])',
  'textarea:not([disabled])',
  '[tabindex]:not([tabindex="-1"])'
].join(',');

/**
 * Guarda quem estava com o foco e devolve uma função que devolve o foco a ele
 * (usado quando um diálogo fecha, para o teclado voltar ao botão que o abriu).
 */
export function rememberFocus() {
  const previous = document.activeElement;
  return () => {
    if (previous instanceof HTMLElement && previous.isConnected) previous.focus();
  };
}

/** Elementos que recebem foco pelo Tab, na ordem da página. */
export function focusableIn(container) {
  if (!container) return [];
  return Array.from(container.querySelectorAll(FOCUSABLE)).filter(
    (element) => !element.hasAttribute('inert') && element.getClientRects().length > 0
  );
}

/** Coloca o foco no elemento marcado com [data-autofocus] ou no primeiro focável. */
export function focusFirst(container) {
  if (!container) return;
  const preferred = container.querySelector('[data-autofocus]');
  const target = preferred ?? focusableIn(container)[0] ?? container;
  target.focus({ preventScroll: true });
}

/** Tab e Shift+Tab ficam circulando dentro do container (diálogos). */
export function trapTabKey(event, container) {
  if (event.key !== 'Tab' || !container) return;
  const items = focusableIn(container);
  if (items.length === 0) {
    event.preventDefault();
    return;
  }
  const first = items[0];
  const last = items[items.length - 1];
  if (event.shiftKey && document.activeElement === first) {
    event.preventDefault();
    last.focus();
  } else if (!event.shiftKey && document.activeElement === last) {
    event.preventDefault();
    first.focus();
  }
}

/**
 * Deixa o resto do site "inerte" (fora do alcance do teclado e do leitor de tela)
 * enquanto um diálogo está aberto. Devolve a função que desfaz.
 */
export function makeAppInert() {
  const app = document.getElementById('root');
  if (!app) return () => {};
  app.setAttribute('inert', '');
  return () => app.removeAttribute('inert');
}

/** Itens de um menu ([data-menu-item]), na ordem da tela. */
export function menuItems(container) {
  if (!container) return [];
  return Array.from(container.querySelectorAll('[data-menu-item]')).filter(
    (element) => element.getClientRects().length > 0
  );
}

/**
 * Move o foco entre os itens do menu.
 * `to`: 'first' | 'last' | 'next' | 'previous' (circula do último para o primeiro).
 */
export function focusMenuItem(container, to) {
  const items = menuItems(container);
  if (items.length === 0) return;
  const current = items.indexOf(document.activeElement);
  const index = {
    first: 0,
    last: items.length - 1,
    next: current < 0 ? 0 : (current + 1) % items.length,
    previous: current < 0 ? items.length - 1 : (current - 1 + items.length) % items.length
  }[to];
  items[index]?.focus();
}

/** Foco na opção de número `index` de um grupo ([data-option]), como abas e seletores. */
export function focusOption(container, index) {
  const options = container ? Array.from(container.querySelectorAll('[data-option]')) : [];
  options[index]?.focus();
}

/** Leva o foco ao primeiro campo com erro (aria-invalid) dentro do formulário. */
export function focusFirstInvalid(container) {
  const field = container?.querySelector('[aria-invalid="true"]');
  if (field instanceof HTMLElement) field.focus();
}

/** Depois de trocar de página, o foco vai para o título principal ([data-page-focus]). */
export function focusPageStart() {
  const target = document.querySelector('[data-page-focus]');
  if (target instanceof HTMLElement) target.focus({ preventScroll: true });
}
