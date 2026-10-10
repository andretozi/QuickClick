/**
 * Infraestrutura · Preferências do vendedor (localStorage)
 * Avisos de venda, de estoque baixo e sugestões de preço, por conta
 * (chave "quickclick:v1:usuario:<id>:preferencias").
 */
import { USER_KEYS, readJson, simulateLatency, userKey, writeJson } from './localStore.js';

const DEFAULTS = { aviso_venda: true, estoque_baixo: true, sugestoes_preco: true };

const toPreferences = (preferencias) => ({
  saleAlerts: preferencias.aviso_venda,
  lowStock: preferencias.estoque_baixo,
  priceTips: preferencias.sugestoes_preco
});

export async function getPreferences(accountId) {
  await simulateLatency(120);
  return toPreferences({ ...DEFAULTS, ...readJson(userKey(accountId, USER_KEYS.PREFERENCES), {}) });
}

export async function savePreferences(accountId, { saleAlerts, lowStock, priceTips }) {
  await simulateLatency(200);
  const preferencias = { aviso_venda: saleAlerts, estoque_baixo: lowStock, sugestoes_preco: priceTips };
  writeJson(userKey(accountId, USER_KEYS.PREFERENCES), preferencias);
  return toPreferences(preferencias);
}
