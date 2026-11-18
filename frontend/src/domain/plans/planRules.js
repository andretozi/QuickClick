/**
 * Domínio · Regras dos planos no front
 * Espelha backend/domain/plano.py: o Essencial conecta 1 marketplace; Pro e Business conectam vários
 * (o multicanal começa no Pro); o Grátis, por enquanto, também. Mudou lá, mude aqui.
 * Os nomes, preços e recursos de cada plano ficam em domain/content/landingContent.js (PLANS).
 */

const PLAN_IDS = { FREE: 'gratis', ESSENTIAL: 'essencial', PRO: 'pro', BUSINESS: 'business' };

// PROVISÓRIO, em validação: espelha GRATIS_CONECTA_VARIOS_PROVISORIO em backend/domain/plano.py.
// Para voltar ao limite de 1 no Grátis, troque para false.
const FREE_CONNECTS_MANY = true;

/** null = vários marketplaces */
const MARKETPLACE_LIMIT = {
  [PLAN_IDS.FREE]: FREE_CONNECTS_MANY ? null : 1,
  [PLAN_IDS.ESSENTIAL]: 1,
  [PLAN_IDS.PRO]: null,
  [PLAN_IDS.BUSINESS]: null
};

function marketplaceLimit(planId) {
  return planId in MARKETPLACE_LIMIT ? MARKETPLACE_LIMIT[planId] : 1;
}

export function canConnectMore(planId, connectedCount) {
  const limit = marketplaceLimit(planId);
  return limit === null || connectedCount < limit;
}

export function isMultichannel(planId) {
  return marketplaceLimit(planId) === null;
}
