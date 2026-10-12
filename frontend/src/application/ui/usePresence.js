import { useEffect, useState } from 'react';

/**
 * Aplicação · Presença de algo que abre e fecha com animação (modal, menu, aviso).
 * Quando `open` vira false, o elemento continua na tela por `exitMs` com
 * `closing = true`, para a animação de saída tocar antes de ele sumir.
 *
 * @returns {{ mounted: boolean, closing: boolean }}
 */
export default function usePresence(open, exitMs = 240) {
  const [phase, setPhase] = useState(open ? 'open' : 'closed');

  useEffect(() => {
    if (open) {
      setPhase('open');
      return undefined;
    }
    setPhase((current) => (current === 'closed' ? 'closed' : 'closing'));
    const timer = setTimeout(() => setPhase('closed'), exitMs);
    return () => clearTimeout(timer);
  }, [open, exitMs]);

  return { mounted: open || phase !== 'closed', closing: !open && phase === 'closing' };
}
