/**
 * Aplicação · Client ID público do Google OAuth
 *
 * Lê primeiro da variável de ambiente exposta pelo Vite (VITE_GOOGLE_CLIENT_ID / GOOGLE_CLIENT_ID)
 * e, quando ausente no build estático, consulta a API em /api/auth/google/config para suportar
 * injeção exclusiva em tempo de execução no Azure App Service.
 */
import { useSyncExternalStore } from 'react';
import { fetchGoogleClientId, getBuildGoogleClientId } from '@/infrastructure/auth/authService.js';

let clientId = getBuildGoogleClientId();
let loadingPromise = null;
const listeners = new Set();

function loadOnce() {
  if (clientId || loadingPromise) return;
  loadingPromise = fetchGoogleClientId().then((resolved) => {
    if (resolved && resolved !== clientId) {
      clientId = resolved;
      listeners.forEach((listener) => listener());
    }
  });
}

function subscribe(listener) {
  listeners.add(listener);
  loadOnce();
  return () => listeners.delete(listener);
}

function getSnapshot() {
  return clientId;
}

export default function useGoogleClientId() {
  return useSyncExternalStore(subscribe, getSnapshot, getSnapshot);
}
