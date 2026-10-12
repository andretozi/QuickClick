import { useCallback, useEffect } from 'react';
import { focusFirst, makeAppInert, rememberFocus, trapTabKey } from '@/infrastructure/browser/focus.js';

/**
 * Aplicação · Comportamento de um diálogo acessível
 *
 * Enquanto `active`:
 * - o resto do site fica inerte (teclado e leitor de tela só enxergam o diálogo);
 * - o foco entra no diálogo ([data-autofocus] ou o primeiro botão) e fica preso nele;
 * - Esc fecha (quando `dismissible`).
 * Ao fechar, o foco volta para quem abriu o diálogo.
 */
export default function useModal({ active, panelRef, onClose, dismissible = true }) {
  useEffect(() => {
    if (!active) return undefined;
    const restoreFocus = rememberFocus();
    const undoInert = makeAppInert();
    focusFirst(panelRef.current);
    return () => {
      undoInert();
      restoreFocus();
    };
  }, [active, panelRef]);

  const onKeyDown = useCallback(
    (event) => {
      if (event.key === 'Escape') {
        event.stopPropagation();
        if (dismissible) onClose?.();
        return;
      }
      trapTabKey(event, panelRef.current);
    },
    [dismissible, onClose, panelRef]
  );

  return { onKeyDown };
}
