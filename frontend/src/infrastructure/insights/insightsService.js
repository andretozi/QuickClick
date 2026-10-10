/**
 * Infraestrutura · Insights da loja (SIMULADO)
 *
 * Ainda não existem vendas de verdade. Este serviço SIMULA um histórico de vendas a partir
 * dos anúncios da própria conta (preços, categorias, estoque, datas e quantos estão
 * publicados), sempre igual para a mesma conta (gerador pseudoaleatório com semente).
 * Sem anúncios, não há o que simular: devolve null e a tela mostra o estado vazio.
 * A tela mostra o selo "Simulação" em tudo que vem daqui.
 *
 * Com o back, vira GET /api/insights, calculado a partir dos pedidos dos marketplaces.
 */
import { listListings } from '../storage/listingsRepository.js';
import { simulateLatency } from '../storage/localStore.js';

const DAY = 24 * 60 * 60 * 1000;
const PERIOD_DAYS = 30;
const DEFAULT_TICKET_CENTS = 12900;

/** Gerador pseudoaleatório com semente (mulberry32 sobre um hash do texto). */
function seededRandom(seedText) {
  let hash = 2166136261;
  for (let i = 0; i < seedText.length; i += 1) {
    hash ^= seedText.charCodeAt(i);
    hash = Math.imul(hash, 16777619);
  }
  let state = hash >>> 0;
  return () => {
    state = (state + 0x6d2b79f5) | 0;
    let t = Math.imul(state ^ (state >>> 15), 1 | state);
    t = (t + Math.imul(t ^ (t >>> 7), 61 | t)) ^ t;
    return ((t ^ (t >>> 14)) >>> 0) / 4294967296;
  };
}

const average = (values) => (values.length ? values.reduce((sum, value) => sum + value, 0) / values.length : 0);

function startOfToday() {
  const now = new Date();
  return new Date(now.getFullYear(), now.getMonth(), now.getDate()).getTime();
}

/** Faturamento diário: mais movimento no fim de semana e uma leve tendência de alta. */
function dailySeries(random, ticketCents, days, offsetDays = 0, volume = 1) {
  const today = startOfToday();
  return Array.from({ length: days }, (_, i) => {
    const date = new Date(today - (days - 1 - i + offsetDays) * DAY);
    const weekend = date.getDay() === 0 || date.getDay() === 6;
    const trend = 0.72 + 0.56 * (i / (days - 1));
    const orders = Math.max(0, Math.round((random() * 2.4 + 0.3) * trend * volume * (weekend ? 1.4 : 1)));
    const cents = Math.round(orders * ticketCents * (0.82 + random() * 0.36));
    return { date: date.toISOString(), cents, orders };
  });
}

/** Agrupa os anúncios por categoria. */
function byCategory(listings) {
  const groups = new Map();
  listings.forEach((listing) => {
    const group = groups.get(listing.category) ?? { category: listing.category, listings: [] };
    group.listings.push(listing);
    groups.set(listing.category, group);
  });
  return [...groups.values()];
}

export async function getInsights(accountId) {
  const listings = await listListings(accountId);
  await simulateLatency(280);
  if (!listings.length) return null;
  const random = seededRandom(`${accountId}:${listings.length}`);

  // quanto mais anúncios publicados, mais pedidos por dia (entre 0,4 e 1,8 do básico)
  const published = listings.filter((listing) => listing.channels?.['mercado-livre'] === 'published').length;
  const volume = Math.min(1.8, 0.4 + published * 0.25 + listings.length * 0.05);
  const ticketCents = Math.round(average(listings.map((listing) => listing.priceCents))) || DEFAULT_TICKET_CENTS;
  const revenue = dailySeries(random, ticketCents, PERIOD_DAYS, 0, volume);
  const previous = dailySeries(seededRandom(`${accountId}:anterior`), ticketCents * 0.92, PERIOD_DAYS, PERIOD_DAYS, volume);
  const totalCents = revenue.reduce((sum, day) => sum + day.cents, 0);
  const previousCents = previous.reduce((sum, day) => sum + day.cents, 0);
  const orders = revenue.reduce((sum, day) => sum + day.orders, 0);

  const groups = byCategory(listings);

  const salesByCategory = groups
    .map((group) => ({
      category: group.category,
      units: Math.round(3 + random() * 9 + group.listings.length * (2 + random() * 4))
    }))
    .sort((a, b) => b.units - a.units)
    .slice(0, 6);

  const stockByCategory = groups
    .map((group) => ({
      category: group.category,
      units: group.listings.reduce((sum, listing) => sum + (Number(listing.stock) || 0), 0)
    }))
    .filter((group) => group.units > 0)
    .sort((a, b) => b.units - a.units);

  const now = Date.now();
  const stalled = listings
    .filter((listing) => listing.stock > 0)
    .map((listing) => {
      const age = Math.max(1, Math.floor((now - new Date(listing.createdAt).getTime()) / DAY));
      return {
        id: listing.id,
        title: listing.title,
        stock: listing.stock,
        days: Math.min(age, Math.round(6 + random() * 70))
      };
    })
    .sort((a, b) => b.days - a.days)
    .slice(0, 4);

  const priceComparison = listings
    .filter((listing) => listing.suggestedPriceCents)
    .map((listing) => ({
      id: listing.id,
      title: listing.title,
      priceCents: listing.priceCents,
      suggestedCents: listing.suggestedPriceCents
    }))
    .sort((a, b) => Math.abs(b.priceCents - b.suggestedCents) - Math.abs(a.priceCents - a.suggestedCents))
    .slice(0, 5);

  return {
    revenue,
    totals: {
      revenueCents: totalCents,
      orders,
      ticketCents: orders ? Math.round(totalCents / orders) : 0,
      changePercent: previousCents ? Math.round(((totalCents - previousCents) / previousCents) * 100) : 0
    },
    salesByCategory,
    stockByCategory,
    stalled,
    priceComparison
  };
}
