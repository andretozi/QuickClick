import { useCallback, useEffect, useRef, useState } from 'react';
import { rememberFocus } from '@/infrastructure/browser/focus.js';
import {
  connectMarketplace,
  describeError,
  disconnectMarketplace,
  fetchMarketplaces,
  fetchSeller
} from '@/infrastructure/marketplaces/marketplacesService.js';

/** Etapas do diálogo de conexão. */
export const DIALOG_STEPS = { CONFIRM: 'confirm', AUTHORIZING: 'authorizing', ERROR: 'error' };

/**
 * Aplicação · Caso de uso "conectar meus marketplaces".
 *
 * Carrega o vendedor (plano e uso) e o catálogo, conduz o diálogo de conexão
 * (confirmar → autorizando → conectado ou erro) e a desconexão. Quem decide as
 * regras (limite do plano, "em breve") é o back: aqui só mostramos o que ele responde.
 * A tela só desenha o que este hook devolve.
 */
export default function useMarketplaces() {
  const [data, setData] = useState({ status: 'loading', seller: null, marketplaces: [], error: null });
  const [dialog, setDialog] = useState(null); // { marketplace, step, error }
  const [busySlug, setBusySlug] = useState(null); // desconectando
  const [failedSlug, setFailedSlug] = useState(null); // desconexão que falhou
  const [celebratedSlug, setCelebratedSlug] = useState(null); // acabou de conectar
  const mounted = useRef(true);
  const restoreFocus = useRef(null); // devolve o teclado ao botão que abriu o diálogo

  /** `silent` atualiza os dados sem voltar para "carregando" (depois de conectar ou desconectar). */
  const load = useCallback(async ({ silent = false } = {}) => {
    if (!silent) setData((current) => ({ ...current, status: 'loading', error: null }));
    try {
      const [seller, marketplaces] = await Promise.all([fetchSeller(), fetchMarketplaces()]);
      if (mounted.current) setData({ status: 'ready', seller, marketplaces, error: null });
    } catch (error) {
      if (mounted.current && !silent) setData((current) => ({ ...current, status: 'error', error: describeError(error) }));
    }
  }, []);

  useEffect(() => {
    mounted.current = true;
    load();
    return () => {
      mounted.current = false;
    };
  }, [load]);

  // Depois que o diálogo fecha (e a página volta a aceitar foco), o teclado volta para o card
  useEffect(() => {
    if (dialog || !restoreFocus.current) return;
    const restore = restoreFocus.current;
    restoreFocus.current = null;
    restore();
  }, [dialog]);

  const retry = useCallback(() => load(), [load]);

  const replaceMarketplace = useCallback((updated) => {
    setData((current) => ({
      ...current,
      marketplaces: current.marketplaces.map((item) => (item.slug === updated.slug ? updated : item))
    }));
  }, []);

  const openConnect = useCallback(
    (slug) => {
      const marketplace = data.marketplaces.find((item) => item.slug === slug);
      if (!marketplace || !marketplace.available || marketplace.connected) return;
      setCelebratedSlug(null);
      setFailedSlug(null);
      restoreFocus.current = rememberFocus();
      setDialog({ marketplace, step: DIALOG_STEPS.CONFIRM, error: null });
    },
    [data.marketplaces]
  );

  /** Fecha o diálogo, menos no meio da autorização. */
  const closeDialog = useCallback(() => {
    setDialog((current) => (current?.step === DIALOG_STEPS.AUTHORIZING ? current : null));
  }, []);

  const confirmConnect = useCallback(async () => {
    if (!dialog || dialog.step === DIALOG_STEPS.AUTHORIZING) return;
    const { marketplace } = dialog;
    setDialog({ marketplace, step: DIALOG_STEPS.AUTHORIZING, error: null });
    try {
      const updated = await connectMarketplace(marketplace.slug);
      if (!mounted.current) return;
      replaceMarketplace(updated);
      setDialog(null);
      setCelebratedSlug(updated.slug);
      load({ silent: true });
    } catch (error) {
      if (mounted.current) setDialog({ marketplace, step: DIALOG_STEPS.ERROR, error: describeError(error) });
    }
  }, [dialog, load, replaceMarketplace]);

  const disconnect = useCallback(
    async (slug) => {
      setCelebratedSlug(null);
      setFailedSlug(null);
      setBusySlug(slug);
      try {
        const updated = await disconnectMarketplace(slug);
        if (!mounted.current) return;
        replaceMarketplace(updated);
        load({ silent: true });
      } catch {
        if (mounted.current) setFailedSlug(slug);
      } finally {
        if (mounted.current) setBusySlug(null);
      }
    },
    [load, replaceMarketplace]
  );

  return {
    ...data,
    dialog,
    busySlug,
    failedSlug,
    celebratedSlug,
    retry,
    openConnect,
    closeDialog,
    confirmConnect,
    disconnect
  };
}
