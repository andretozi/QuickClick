import { useCallback, useEffect, useRef, useState } from 'react';
import { signOut } from './sessionStore.js';
import { showToast, TOAST_TONES } from '@/application/feedback/toastStore.js';
import { SESSION_TOASTS } from '@/domain/content/appContent.js';

/**
 * Aplicação · Caso de uso "sair da conta".
 * Fecha a sessão e avisa com um toast. Se o vendedor estava numa página privada,
 * a guarda de rotas leva para a landing.
 */
export default function useSignOut() {
  const [signingOut, setSigningOut] = useState(false);
  const mounted = useRef(true);

  useEffect(() => {
    mounted.current = true;
    return () => {
      mounted.current = false;
    };
  }, []);

  const signOutNow = useCallback(async () => {
    setSigningOut(true);
    try {
      await signOut();
      showToast({ tone: TOAST_TONES.INFO, ...SESSION_TOASTS.signedOut });
    } finally {
      if (mounted.current) setSigningOut(false);
    }
  }, []);

  return { signOut: signOutNow, signingOut };
}
