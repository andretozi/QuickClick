import { useCallback, useEffect, useState } from 'react';
import { fetchQuota } from '@/infrastructure/ai/iaService.js';

/**
 * Aplicação · Cota da IA do mês: plano, análises restantes, o que o plano tem e se a IA
 * está disponível agora. `refreshKey` muda quando uma análise termina (a cota é relida).
 * Com a aba oculta, nada é pedido; quando ela volta, a cota é relida (o plano pode ter
 * mudado em outra aba, ou o dia virou e o orçamento da IA voltou).
 */
export default function useCotaIA({ enabled, refreshKey, mounted }) {
  const [quota, setQuota] = useState(null);
  const [status, setStatus] = useState('loading');

  const refresh = useCallback(async () => {
    try {
      const data = await fetchQuota();
      if (!mounted.current) return;
      setQuota(data);
      setStatus('ready');
    } catch {
      if (mounted.current) setStatus('error');
    }
  }, [mounted]);

  useEffect(() => {
    if (enabled) refresh();
  }, [enabled, refresh, refreshKey]);

  useEffect(() => {
    if (!enabled) return undefined;
    const onVisibility = () => {
      if (!document.hidden) refresh();
    };
    document.addEventListener('visibilitychange', onVisibility);
    return () => document.removeEventListener('visibilitychange', onVisibility);
  }, [enabled, refresh]);

  return { quota, status, refresh };
}
