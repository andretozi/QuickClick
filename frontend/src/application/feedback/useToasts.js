import { useSyncExternalStore } from 'react';
import { dismissToast, getToastsSnapshot, subscribeToToasts } from './toastStore.js';

/** Aplicação · Lista de avisos na tela e a ação de fechar um aviso. */
export default function useToasts() {
  const toasts = useSyncExternalStore(subscribeToToasts, getToastsSnapshot);
  return { toasts, dismiss: dismissToast };
}
