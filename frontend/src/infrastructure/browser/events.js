/**
 * Infraestrutura · Eventos globais do navegador
 * Clique fora de um elemento e teclas no documento. Cada função devolve a limpeza.
 */

/** Chama `handler` quando o usuário clica ou toca fora de todos os elementos dados. */
export function onPointerDownOutside(elements, handler) {
  const listener = (event) => {
    const inside = elements.some((element) => element && element.contains(event.target));
    if (!inside) handler(event);
  };
  document.addEventListener('pointerdown', listener);
  return () => document.removeEventListener('pointerdown', listener);
}

/** Chama `handler` a cada tecla pressionada em qualquer lugar da página. */
export function onDocumentKeyDown(handler) {
  document.addEventListener('keydown', handler);
  return () => document.removeEventListener('keydown', handler);
}

/** Hora atual do relógio do aparelho (0 a 23), para a saudação do painel. */
export function currentHour() {
  return new Date().getHours();
}
