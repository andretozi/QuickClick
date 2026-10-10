import { useCallback, useEffect, useRef, useState } from 'react';
import useSession from '@/application/session/useSession.js';
import { getInsights } from '@/infrastructure/insights/insightsService.js';

/**
 * Aplicação · Insights da loja (vendas simuladas, calculadas a partir dos anúncios da conta).
 * Só carrega quando a aba Insights abre.
 */
export default function useInsights(active) {
  const { account } = useSession();
  const accountId = account?.id;
  const [state, setState] = useState({ status: 'idle', data: null });
  const mounted = useRef(true);

  const load = useCallback(async () => {
    if (!accountId) return;
    setState({ status: 'loading', data: null });
    try {
      const data = await getInsights(accountId);
      if (mounted.current) setState({ status: 'ready', data });
    } catch {
      if (mounted.current) setState({ status: 'error', data: null });
    }
  }, [accountId]);

  useEffect(() => {
    mounted.current = true;
    if (active) load();
    return () => {
      mounted.current = false;
    };
  }, [active, load]);

  return { ...state, retry: load };
}
