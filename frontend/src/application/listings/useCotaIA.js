import { useCallback, useEffect, useState } from 'react';
import { fetchQuota } from '@/infrastructure/ai/iaService.js';

/**
 * Aplicação · Cota da IA do mês: plano, análises restantes, o que o plano tem e se a IA
 * está disponível agora. `refreshKey` muda quando uma análise termina (a cota é relida).
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

  return { quota, status, refresh };
}
