import { useCallback, useEffect, useRef, useState } from 'react';
import useSession from '@/application/session/useSession.js';
import { showToast, TOAST_TONES } from '@/application/feedback/toastStore.js';
import {
  CONNECTION_ERRORS,
  ConnectionError,
  SYNC_DURATION_MS,
  connectMarketplace,
  disconnectMarketplace,
  listConnections,
  syncMarketplace
} from '@/infrastructure/storage/connectionsRepository.js';
import { rememberFocus } from '@/infrastructure/browser/focus.js';
import { canConnectMore } from '@/domain/plans/planRules.js';
import { DISCONNECT_DIALOG, MARKETPLACE_CARD, MARKETPLACE_CATALOG } from '@/domain/content/marketplacesContent.js';

/** Passos do diálogo de conexão (simulando o OAuth do marketplace). */
export const CONNECT_STEPS = {
  CONFIRM: 'confirm',
  REDIRECT: 'redirect',
  AUTHORIZING: 'authorizing',
  CONNECTED: 'connected',
  LIMIT: 'limit',
  ERROR: 'error'
};

const REDIRECT_MS = 1400; // "Indo para o Mercado Livre"
const SYNC_TICK_MS = 120;

const wait = (ms) => new Promise((resolve) => window.setTimeout(resolve, ms));

/**
 * Aplicação · Caso de uso "conectar meus marketplaces" (da conta logada, no localStorage).
 *
 * Junta o catálogo com as conexões da conta e conduz:
 * - conectar: confirmar as permissões → "Indo para o Mercado Livre" → "Autorizando" → "Conectado";
 * - sincronizar: progresso simulado até 100%;
 * - desconectar: com confirmação.
 * Só o que está disponível no catálogo pode ser conectado, e o plano limita quantos.
 * A comemoração do "Conectado" fica com o diálogo, quando ele chega no último passo.
 */
export default function useMarketplaces() {
  const { account } = useSession();
  const accountId = account?.id;
  const plan = account?.plan;

  const [status, setStatus] = useState('loading');
  const [connections, setConnections] = useState([]);
  const [dialog, setDialog] = useState(null); // { slug, step }
  const [pendingDisconnect, setPendingDisconnect] = useState(null);
  const [disconnecting, setDisconnecting] = useState(false);
  const [sync, setSync] = useState(null); // { slug, progress }
  const mounted = useRef(true);
  const restoreFocus = useRef(null);

  const load = useCallback(async () => {
    if (!accountId) return;
    setStatus('loading');
    try {
      const list = await listConnections(accountId);
      if (!mounted.current) return;
      setConnections(list);
      setStatus('ready');
    } catch {
      if (mounted.current) setStatus('error');
    }
  }, [accountId]);

  useEffect(() => {
    mounted.current = true;
    load();
    return () => {
      mounted.current = false;
    };
  }, [load]);

  // Quando o diálogo fecha, o teclado volta para o botão que o abriu
  useEffect(() => {
    if (dialog || pendingDisconnect || !restoreFocus.current) return;
    const restore = restoreFocus.current;
    restoreFocus.current = null;
    restore();
  }, [dialog, pendingDisconnect]);

  const marketplaces = MARKETPLACE_CATALOG.map((marketplace) => ({
    ...marketplace,
    connection: connections.find((connection) => connection.slug === marketplace.slug) ?? null
  }));
  const canConnect = canConnectMore(plan, connections.length);

  // ---------- Conectar ----------
  const openConnect = useCallback(
    (slug) => {
      const marketplace = MARKETPLACE_CATALOG.find((item) => item.slug === slug);
      // em breve ou já conectado: não há o que conectar
      if (!marketplace?.available || connections.some((item) => item.slug === slug)) return;
      restoreFocus.current = rememberFocus();
      setDialog({ slug, step: canConnect ? CONNECT_STEPS.CONFIRM : CONNECT_STEPS.LIMIT });
    },
    [canConnect, connections]
  );

  const busyDialog = dialog && [CONNECT_STEPS.REDIRECT, CONNECT_STEPS.AUTHORIZING].includes(dialog.step);

  const closeDialog = useCallback(() => {
    if (!busyDialog) setDialog(null);
  }, [busyDialog]);

  const confirmConnect = useCallback(async () => {
    if (!dialog || busyDialog) return;
    const { slug } = dialog;
    setDialog({ slug, step: CONNECT_STEPS.REDIRECT });
    try {
      await wait(REDIRECT_MS);
      if (!mounted.current) return;
      setDialog({ slug, step: CONNECT_STEPS.AUTHORIZING });
      const connection = await connectMarketplace(accountId, slug);
      if (!mounted.current) return;
      setConnections((current) => [...current.filter((item) => item.slug !== slug), connection]);
      setDialog({ slug, step: CONNECT_STEPS.CONNECTED, nickname: connection.nickname });
    } catch (error) {
      if (!mounted.current) return;
      const limit = error instanceof ConnectionError && error.code === CONNECTION_ERRORS.PLAN_LIMIT;
      setDialog({ slug, step: limit ? CONNECT_STEPS.LIMIT : CONNECT_STEPS.ERROR });
    }
  }, [accountId, busyDialog, dialog]);

  // ---------- Sincronizar ----------
  const syncNow = useCallback(
    async (slug) => {
      if (sync) return;
      setSync({ slug, progress: 0 });
      const started = Date.now();
      const ticker = window.setInterval(() => {
        const progress = Math.min(96, Math.round(((Date.now() - started) / SYNC_DURATION_MS) * 100));
        setSync((current) => (current ? { ...current, progress } : current));
      }, SYNC_TICK_MS);
      try {
        const updated = await syncMarketplace(accountId, slug);
        if (!mounted.current) return;
        if (!updated) {
          // a conexão sumiu (desconectada em outra aba, por exemplo): recarrega a lista
          showToast({ tone: TOAST_TONES.ERROR, ...MARKETPLACE_CARD.syncError });
          load();
          return;
        }
        setSync({ slug, progress: 100 });
        setConnections((current) => current.map((item) => (item.slug === slug ? updated : item)));
        showToast({ tone: TOAST_TONES.SUCCESS, ...MARKETPLACE_CARD.syncedToast });
        await wait(500);
      } catch {
        if (mounted.current) showToast({ tone: TOAST_TONES.ERROR, ...MARKETPLACE_CARD.syncError });
      } finally {
        window.clearInterval(ticker);
        if (mounted.current) setSync(null);
      }
    },
    [accountId, load, sync]
  );

  // ---------- Desconectar ----------
  const requestDisconnect = useCallback((slug) => {
    restoreFocus.current = rememberFocus();
    setPendingDisconnect(slug);
  }, []);

  const cancelDisconnect = useCallback(() => {
    if (!disconnecting) setPendingDisconnect(null);
  }, [disconnecting]);

  const confirmDisconnect = useCallback(async () => {
    if (!pendingDisconnect) return;
    setDisconnecting(true);
    try {
      await disconnectMarketplace(accountId, pendingDisconnect);
      if (!mounted.current) return;
      setConnections((current) => current.filter((item) => item.slug !== pendingDisconnect));
      setPendingDisconnect(null);
      showToast({ tone: TOAST_TONES.INFO, ...DISCONNECT_DIALOG.done });
    } catch {
      if (mounted.current) showToast({ tone: TOAST_TONES.ERROR, ...DISCONNECT_DIALOG.error });
    } finally {
      if (mounted.current) setDisconnecting(false);
    }
  }, [accountId, pendingDisconnect]);

  return {
    status,
    retry: load,
    plan,
    marketplaces,
    connections,
    canConnect,
    dialog,
    busyDialog,
    openConnect,
    closeDialog,
    confirmConnect,
    sync,
    syncNow,
    pendingDisconnect,
    disconnecting,
    requestDisconnect,
    cancelDisconnect,
    confirmDisconnect
  };
}
