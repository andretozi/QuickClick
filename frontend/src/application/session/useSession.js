import { useSyncExternalStore } from 'react';
import { getSessionSnapshot, subscribeToSession } from './sessionStore.js';

export { SESSION_STATUS } from './sessionStore.js';

/**
 * Aplicação · Sessão atual: { status: 'checking' | 'guest' | 'signed-in', account, welcome }.
 * Todas as telas leem a mesma sessão. As ações (entrar, sair...) ficam nos hooks de cada caso de uso.
 */
export default function useSession() {
  return useSyncExternalStore(subscribeToSession, getSessionSnapshot);
}
