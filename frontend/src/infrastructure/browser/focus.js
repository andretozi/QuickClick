/**
 * Infraestrutura · Foco do teclado
 * Guarda quem estava com o foco e devolve uma função que devolve o foco a ele
 * (usado quando um diálogo fecha, para o teclado voltar ao botão que o abriu).
 */
export function rememberFocus() {
  const previous = document.activeElement;
  return () => {
    if (previous instanceof HTMLElement && previous.isConnected) previous.focus();
  };
}
