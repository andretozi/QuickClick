/**
 * Infraestrutura · Planos pela API real
 *
 * GET /api/plans diz se a troca de plano está livre (MVP, sem pagamento) ou se espera o
 * pagamento (versão final, interruptor TROCA_DE_PLANO_LIVRE). PUT /api/me/plano troca o plano
 * da conta do token e devolve o usuário atualizado, que entra na conta guardada como no
 * restoreSession.
 */
import { requestJson } from '../http/httpClient.js';
import { upsertAccount } from '../storage/accountsRepository.js';

export async function fetchPlanSwitching() {
  const data = await requestJson('/plans');
  return { free: Boolean(data.troca_de_plano_livre) };
}

/** Troca o plano ('gratis', 'essencial', 'pro' ou 'business') e devolve a conta atualizada. */
export async function changePlan(planId) {
  const data = await requestJson('/me/plano', { method: 'PUT', body: { plano: planId } });
  return upsertAccount({ id: data.id, name: data.nome, email: data.email, store: data.loja, plan: data.plano });
}
