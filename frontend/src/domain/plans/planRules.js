/**
 * Domínio · Regras dos planos no front
 * Espelha backend/domain/plano.py: Grátis e Essencial conectam 1 marketplace;
 * Pro e Business conectam vários (o multicanal começa no Pro). Mudou lá, mude aqui.
 * Os nomes, preços e recursos de cada plano ficam em domain/content/landingContent.js (PLANS).
 */

export const PLAN_IDS = { FREE: 'gratis', ESSENTIAL: 'essencial', PRO: 'pro', BUSINESS: 'business' };

/** null = vários marketplaces */
const MARKETPLACE_LIMIT = {
  [PLAN_IDS.FREE]: 1,
  [PLAN_IDS.ESSENTIAL]: 1,
  [PLAN_IDS.PRO]: null,
  [PLAN_IDS.BUSINESS]: null
};

/** Plano indicado para quem quer conectar mais de um marketplace. */
export const MULTICHANNEL_PLAN = PLAN_IDS.PRO;

export function marketplaceLimit(planId) {
  return planId in MARKETPLACE_LIMIT ? MARKETPLACE_LIMIT[planId] : 1;
}

export function canConnectMore(planId, connectedCount) {
  const limit = marketplaceLimit(planId);
  return limit === null || connectedCount < limit;
}

export function isMultichannel(planId) {
  return marketplaceLimit(planId) === null;
}
