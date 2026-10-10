/**
 * Domínio · Formatação para a tela
 * Dinheiro, números, datas e iniciais no jeito brasileiro. Funções puras, sem DOM.
 * Datas nunca usam barra (regra de escrita): "8 de out. de 2026", "há 3 dias".
 */

const MONEY = new Intl.NumberFormat('pt-BR', { style: 'currency', currency: 'BRL' });
const MONEY_ROUND = new Intl.NumberFormat('pt-BR', {
  style: 'currency',
  currency: 'BRL',
  maximumFractionDigits: 0
});
const NUMBER = new Intl.NumberFormat('pt-BR');
const DATE_LONG = new Intl.DateTimeFormat('pt-BR', { day: 'numeric', month: 'long', year: 'numeric' });
const DATE_SHORT = new Intl.DateTimeFormat('pt-BR', { day: 'numeric', month: 'short' });
const RELATIVE = new Intl.RelativeTimeFormat('pt-BR', { numeric: 'auto' });
const LIST = new Intl.ListFormat('pt-BR', { style: 'long', type: 'conjunction' });

/** ["Shopee", "Amazon", "Magalu"] → "Shopee, Amazon e Magalu" */
export function formatList(items) {
  return LIST.format(items);
}

const MINUTE = 60 * 1000;
const HOUR = 60 * MINUTE;
const DAY = 24 * HOUR;

/** 18990 → "R$ 189,90" */
export function formatMoney(cents) {
  return MONEY.format((Number(cents) || 0) / 100);
}

/** 18990 → "R$ 190" (eixos de gráfico, números grandes) */
export function formatMoneyRound(cents) {
  return MONEY_ROUND.format((Number(cents) || 0) / 100);
}

/** 1234 → "1.234" */
export function formatNumber(value) {
  return NUMBER.format(Number(value) || 0);
}

/** "2026-10-08T12:00:00Z" → "8 de outubro de 2026" */
export function formatDate(iso) {
  return iso ? DATE_LONG.format(new Date(iso)) : '';
}

/** "2026-10-08T12:00:00Z" → "8 de out." */
export function formatShortDate(dateOrIso) {
  return dateOrIso ? DATE_SHORT.format(new Date(dateOrIso)) : '';
}

/** Quanto tempo passou: "agora", "há 5 minutos", "ontem", "há 3 dias"... */
export function formatRelative(iso, now = Date.now()) {
  if (!iso) return '';
  const diff = new Date(iso).getTime() - now;
  const abs = Math.abs(diff);
  if (abs < MINUTE) return RELATIVE.format(0, 'second');
  if (abs < HOUR) return RELATIVE.format(Math.round(diff / MINUTE), 'minute');
  if (abs < DAY) return RELATIVE.format(Math.round(diff / HOUR), 'hour');
  if (abs < 30 * DAY) return RELATIVE.format(Math.round(diff / DAY), 'day');
  if (abs < 365 * DAY) return RELATIVE.format(Math.round(diff / (30 * DAY)), 'month');
  return RELATIVE.format(Math.round(diff / (365 * DAY)), 'year');
}

/** Dias inteiros entre a data e agora. */
export function daysSince(iso, now = Date.now()) {
  if (!iso) return 0;
  return Math.max(0, Math.floor((now - new Date(iso).getTime()) / DAY));
}

/** "Ana Oliveira" → "AO"; "Ana" → "A" */
export function initials(name) {
  const words = String(name ?? '')
    .trim()
    .split(/\s+/)
    .filter(Boolean);
  if (words.length === 0) return '';
  const first = words[0][0];
  const last = words.length > 1 ? words[words.length - 1][0] : '';
  return `${first}${last}`.toUpperCase();
}

/** "Ana Oliveira" → "Ana" */
export function firstName(name) {
  return String(name ?? '').trim().split(/\s+/)[0] ?? '';
}

/**
 * Lê o que o vendedor digitou como preço e devolve centavos.
 * Aceita "189,90", "R$ 189,90", "1.234,5" e "189.90". Devolve null se não der para ler.
 */
export function parseMoney(text) {
  const clean = String(text ?? '')
    .replace(/[^\d.,]/g, '')
    .trim();
  if (!clean) return null;
  const lastComma = clean.lastIndexOf(',');
  const lastDot = clean.lastIndexOf('.');
  let normalized;
  if (lastComma > lastDot) {
    normalized = clean.replace(/\./g, '').replace(',', '.');
  } else if (lastDot > -1 && clean.length - lastDot - 1 <= 2) {
    normalized = clean.replace(/,/g, '');
  } else {
    normalized = clean.replace(/[.,]/g, '');
  }
  const value = Number(normalized);
  return Number.isFinite(value) ? Math.round(value * 100) : null;
}

/** Centavos para o campo de preço: 18990 → "189,90" */
export function centsToInput(cents) {
  if (cents === null || cents === undefined || cents === '') return '';
  return (Number(cents) / 100).toFixed(2).replace('.', ',');
}
