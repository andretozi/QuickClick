import { useCallback, useEffect, useRef, useState } from 'react';
import { focusMenuItem } from '@/infrastructure/browser/focus.js';
import { onPointerDownOutside } from '@/infrastructure/browser/events.js';

/**
 * Aplicação · Menu suspenso acessível (o menu do usuário no navbar)
 *
 * - O botão abre e fecha; Enter, Espaço e seta para baixo abrem já no primeiro item.
 * - Dentro do menu: setas, Home e End andam entre os itens ([data-menu-item]).
 * - Esc fecha e devolve o foco ao botão; Tab fecha e segue a ordem da página.
 * - Clicar fora fecha.
 */
export default function useMenu() {
  const [open, setOpen] = useState(false);
  const [focusOnOpen, setFocusOnOpen] = useState('first');
  const buttonRef = useRef(null);
  const menuRef = useRef(null);

  const openMenu = useCallback((focusTarget = 'first') => {
    setFocusOnOpen(focusTarget);
    setOpen(true);
  }, []);

  const close = useCallback(({ returnFocus = true } = {}) => {
    setOpen(false);
    if (returnFocus) buttonRef.current?.focus();
  }, []);

  const toggle = useCallback(() => {
    setFocusOnOpen('first');
    setOpen((current) => !current);
  }, []);

  useEffect(() => {
    if (!open) return undefined;
    focusMenuItem(menuRef.current, focusOnOpen);
    return onPointerDownOutside([buttonRef.current, menuRef.current], () => setOpen(false));
  }, [open, focusOnOpen]);

  const onButtonKeyDown = useCallback(
    (event) => {
      if (event.key === 'ArrowDown' || event.key === 'Enter' || event.key === ' ') {
        event.preventDefault();
        openMenu('first');
      } else if (event.key === 'ArrowUp') {
        event.preventDefault();
        openMenu('last');
      }
    },
    [openMenu]
  );

  const onMenuKeyDown = useCallback(
    (event) => {
      const moves = { ArrowDown: 'next', ArrowUp: 'previous', Home: 'first', End: 'last' };
      if (moves[event.key]) {
        event.preventDefault();
        focusMenuItem(menuRef.current, moves[event.key]);
      } else if (event.key === 'Escape') {
        event.preventDefault();
        close();
      } else if (event.key === 'Tab') {
        close({ returnFocus: false });
      }
    },
    [close]
  );

  return { open, toggle, close, buttonRef, menuRef, onButtonKeyDown, onMenuKeyDown };
}
