import { useCallback, useEffect, useState } from 'react';
import useMountedRef from '@/application/ui/useMountedRef.js';
import useSession from '@/application/session/useSession.js';
import { showToast, TOAST_TONES } from '@/application/feedback/toastStore.js';
import {
  disconnectMarketplace,
  fetchAuthorizeUrl,
  fetchConnectedMarketplaces
} from '@/infrastructure/marketplaces/marketplacesService.js';
import { canConnectMore } from '@/domain/plans/planRules.js';
import { DISCONNECT_DIALOG, MARKETPLACE_CARD, MARKETPLACE_CATALOG } from '@/domain/content/marketplacesContent.js';

/** Passos do diálogo de conexão OAuth do marketplace. */
export const CONNECT_STEPS = {
  CONFIRM: 'confirm',
  REDIRECT: 'redirect',
  AUTHORIZING: 'authorizing',
  CONNECTED: 'connected',
  LIMIT: 'limit',
  ERROR: 'error'
};

const SYNC_TICK_MS = 120;
const SYNC_DURATION_MS = 2000;

const wait = (ms) => new Promise((resolve) => window.setTimeout(resolve, ms));

/**
 * Aplicação · Caso de uso "conectar meus marketplaces".
 *
 * Conduz o fluxo OAuth real com o Mercado Livre e outros marketplaces:
 * - Redirecionamento oficial para o provedor (Mercado Livre);
 * - Tratamento do retorno de sucesso ou erro pelo callback;
 * - Consulta das contas conectadas direto da API do backend;
 * - Desconexão segura liberando vaga no plano.
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
  const mounted = useMountedRef();

  const load = useCallback(async () => {
    if (!accountId) return;
    setStatus('loading');
    try {
      const list = await fetchConnectedMarketplaces();
      if (!mounted.current) return;
      setConnections(list);
      setStatus('ready');
    } catch {
      if (mounted.current) setStatus('error');
    }
  }, [accountId, mounted]);

  useEffect(() => {
    load();
  }, [load]);

  // Captura o retorno do callback do Mercado Livre na URL (#/marketplaces?conectado=mercado-livre)
  useEffect(() => {
    const hash = window.location.hash || '';
    if (hash.includes('conectado=')) {
      const match = hash.match(/conectado=([^&]+)/);
      const conectadoSlug = match ? match[1] : '';
      if (conectadoSlug) {
        showToast({
          tone: TOAST_TONES.SUCCESS,
          title: 'Conta conectada com sucesso!',
          description: `Sua conta do ${conectadoSlug === 'mercado-livre' ? 'Mercado Livre' : conectadoSlug} foi vinculada à Quick Click.`
        });
        load();
        window.history.replaceState(null, '', window.location.pathname + '#/marketplaces');
      }
    } else if (hash.includes('erro=')) {
      showToast({
        tone: TOAST_TONES.ERROR,
        title: 'Não foi possível conectar a conta',
        description: 'A autorização com o marketplace não foi concluída. Tente novamente.'
      });
      window.history.replaceState(null, '', window.location.pathname + '#/marketplaces');
    }
  }, [load]);

  const marketplaces = MARKETPLACE_CATALOG.map((marketplace) => ({
    ...marketplace,
    connection: connections.find((connection) => connection.slug === marketplace.slug) ?? null
  }));
  const canConnect = canConnectMore(plan, connections.length);

  // ---------- Conectar via OAuth Real ----------
  const openConnect = useCallback(
    (slug) => {
      const marketplace = MARKETPLACE_CATALOG.find((item) => item.slug === slug);
      if (!marketplace?.available || connections.some((item) => item.slug === slug)) return;
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
      const url = await fetchAuthorizeUrl(slug);
      if (url && url.startsWith('http')) {
        window.location.href = url;
        return;
      }
      throw new Error('URL de autorização inválida.');
    } catch (error) {
      if (!mounted.current) return;
      const limit = error?.code === 'limite_do_plano' || error?.status === 403;
      setDialog({ slug, step: limit ? CONNECT_STEPS.LIMIT : CONNECT_STEPS.ERROR });
    }
  }, [busyDialog, dialog, mounted]);

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
        await wait(SYNC_DURATION_MS);
        if (!mounted.current) return;
        setSync({ slug, progress: 100 });
        setConnections((current) =>
          current.map((item) => (item.slug === slug ? { ...item, syncedAt: new Date().toISOString() } : item))
        );
        showToast({ tone: TOAST_TONES.SUCCESS, ...MARKETPLACE_CARD.syncedToast });
        await wait(500);
      } catch {
        if (mounted.current) showToast({ tone: TOAST_TONES.ERROR, ...MARKETPLACE_CARD.syncError });
      } finally {
        window.clearInterval(ticker);
        if (mounted.current) setSync(null);
      }
    },
    [sync, mounted]
  );

  // ---------- Desconectar via Backend Real ----------
  const requestDisconnect = useCallback((slug) => {
    setPendingDisconnect(slug);
  }, []);

  const cancelDisconnect = useCallback(() => {
    if (!disconnecting) setPendingDisconnect(null);
  }, [disconnecting]);

  const confirmDisconnect = useCallback(async () => {
    if (!pendingDisconnect) return;
    setDisconnecting(true);
    try {
      await disconnectMarketplace(pendingDisconnect);
      if (!mounted.current) return;
      setConnections((current) => current.filter((item) => item.slug !== pendingDisconnect));
      setPendingDisconnect(null);
      showToast({ tone: TOAST_TONES.INFO, ...DISCONNECT_DIALOG.done });
    } catch {
      if (mounted.current) showToast({ tone: TOAST_TONES.ERROR, ...DISCONNECT_DIALOG.error });
    } finally {
      if (mounted.current) setDisconnecting(false);
    }
  }, [pendingDisconnect, mounted]);

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
