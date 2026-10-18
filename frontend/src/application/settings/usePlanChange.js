import { useCallback, useEffect, useState } from 'react';
import { setSessionAccount } from '@/application/session/sessionStore.js';
import { showToast, TOAST_TONES } from '@/application/feedback/toastStore.js';
import { changePlan, fetchPlanSwitching } from '@/infrastructure/plans/plansService.js';
import { planName } from '@/domain/content/appContent.js';
import { PLAN_SECTION } from '@/domain/content/settingsContent.js';

/**
 * Aplicação · O vendedor troca o próprio plano na tela de Configurações (MVP: na hora e sem
 * pagamento). Confirmando no modal, o back troca o plano e devolve a conta: a sessão é
 * atualizada e tudo o que lê o plano dela (selo do menu, limite de marketplaces) muda junto; a
 * cota da IA é relida quando o assistente abre. Com a troca livre desligada (versão final), os
 * botões viram "Em breve".
 */
export default function usePlanChange({ mounted }) {
  const [free, setFree] = useState(true);
  const [target, setTarget] = useState(null); // fica depois de fechar, para o modal sair com o texto certo
  const [confirming, setConfirming] = useState(false);
  const [changing, setChanging] = useState(false);

  useEffect(() => {
    fetchPlanSwitching()
      .then((switching) => {
        if (mounted.current) setFree(switching.free);
      })
      .catch(() => {}); // sem resposta: os botões ficam, e a própria troca diz se não der
  }, [mounted]);

  const open = useCallback((planId) => {
    setTarget(planId);
    setConfirming(true);
  }, []);

  const cancel = useCallback(() => {
    if (!changing) setConfirming(false);
  }, [changing]);

  const confirm = useCallback(async () => {
    if (!confirming || changing) return;
    setChanging(true);
    try {
      const account = await changePlan(target);
      if (!mounted.current) return;
      setSessionAccount(account);
      setConfirming(false);
      showToast({ tone: TOAST_TONES.SUCCESS, ...PLAN_SECTION.done(planName(account.plan)) });
    } catch (error) {
      if (!mounted.current) return;
      if (error?.status === 402) {
        setFree(false);
        setConfirming(false);
        showToast({ tone: TOAST_TONES.INFO, title: PLAN_SECTION.soon, text: PLAN_SECTION.soonReason });
      } else {
        showToast({ tone: TOAST_TONES.ERROR, ...PLAN_SECTION.failed });
      }
    } finally {
      if (mounted.current) setChanging(false);
    }
  }, [changing, confirming, mounted, target]);

  return { free, target, confirming, changing, open, cancel, confirm };
}
