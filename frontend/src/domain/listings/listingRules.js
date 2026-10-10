/**
 * Domínio · Regras de um anúncio
 * Limites, situações possíveis e a validação de cada etapa do assistente.
 */
import { FIELD_ERROR, maxLength, required } from '@/domain/validation/validators.js';

export const LISTING_LIMITS = {
  /** Limite de caracteres do título no Mercado Livre */
  TITLE_MAX: 60,
  DESCRIPTION_MAX: 2000,
  PHOTOS_MAX: 6,
  STOCK_MAX: 99999,
  PRICE_MIN_CENTS: 100,
  PRICE_MAX_CENTS: 10000000
};

/** Situação do anúncio no Mercado Livre (o único canal disponível por enquanto). */
export const LISTING_STATUS = {
  PUBLISHED: 'published',
  PAUSED: 'paused',
  UNPUBLISHED: 'unpublished'
};

export const LISTING_CONDITION = { NEW: 'new', USED: 'used' };

/** Canal principal do produto hoje. */
export const PRIMARY_CHANNEL = 'mercado-livre';

/** Situação do anúncio, lida do canal principal. */
export function listingStatus(listing) {
  return listing?.channels?.[PRIMARY_CHANNEL] ?? LISTING_STATUS.UNPUBLISHED;
}

export function isActive(listing) {
  return listingStatus(listing) === LISTING_STATUS.PUBLISHED;
}

/** Etapas do assistente "criar anúncio", na ordem. */
export const WIZARD_STEPS = ['photos', 'details', 'price', 'channels', 'publish'];

/** Erros de cada campo de uma etapa (objeto vazio = pode seguir). */
export function validateListingStep(step, draft) {
  const errors = {};
  if (step === 'photos') {
    if (!draft.photos?.length) errors.photos = FIELD_ERROR.REQUIRED;
  }
  if (step === 'details') {
    errors.title = required(draft.title) ?? maxLength(draft.title, LISTING_LIMITS.TITLE_MAX);
    errors.description = maxLength(draft.description, LISTING_LIMITS.DESCRIPTION_MAX);
    errors.category = required(draft.category);
    const stock = Number(draft.stock);
    errors.stock =
      draft.stock === '' || draft.stock === null || draft.stock === undefined
        ? FIELD_ERROR.REQUIRED
        : !Number.isInteger(stock) || stock < 0 || stock > LISTING_LIMITS.STOCK_MAX
          ? FIELD_ERROR.STOCK
          : null;
  }
  if (step === 'price') {
    const cents = draft.priceCents;
    errors.price =
      cents === null || cents === undefined
        ? FIELD_ERROR.REQUIRED
        : cents < LISTING_LIMITS.PRICE_MIN_CENTS || cents > LISTING_LIMITS.PRICE_MAX_CENTS
          ? FIELD_ERROR.PRICE
          : null;
  }
  return Object.fromEntries(Object.entries(errors).filter(([, error]) => error));
}

/** Valor parado no estoque de um anúncio, em centavos. */
export function stockValueCents(listing) {
  return (Number(listing.priceCents) || 0) * (Number(listing.stock) || 0);
}

/** Números do topo do painel. */
export function summarizeListings(listings) {
  return {
    total: listings.length,
    active: listings.filter(isActive).length,
    units: listings.reduce((sum, listing) => sum + (Number(listing.stock) || 0), 0),
    withStock: listings.filter((listing) => Number(listing.stock) > 0).length,
    stockValueCents: listings.reduce((sum, listing) => sum + stockValueCents(listing), 0)
  };
}

/** Busca pelo título (sem diferenciar acentos e maiúsculas) e filtro pela situação. */
export function filterListings(listings, { query = '', status = 'all' } = {}) {
  const normalize = (text) =>
    String(text)
      .normalize('NFD')
      .replace(/[̀-ͯ]/g, '')
      .toLowerCase();
  const term = normalize(query.trim());
  return listings.filter(
    (listing) =>
      (status === 'all' || listingStatus(listing) === status) && (!term || normalize(listing.title).includes(term))
  );
}

export const LISTING_SORTS = ['recent', 'price-desc', 'price-asc', 'stock-desc', 'title'];

export function sortListings(listings, sort = 'recent') {
  const sorted = [...listings];
  const compare = {
    recent: (a, b) => String(b.updatedAt).localeCompare(String(a.updatedAt)),
    'price-desc': (a, b) => b.priceCents - a.priceCents,
    'price-asc': (a, b) => a.priceCents - b.priceCents,
    'stock-desc': (a, b) => b.stock - a.stock,
    title: (a, b) => a.title.localeCompare(b.title, 'pt-BR')
  }[sort];
  return compare ? sorted.sort(compare) : sorted;
}

/** Título da cópia de um anúncio, sem passar do limite do Mercado Livre. */
export function copyTitle(title, suffix) {
  const room = LISTING_LIMITS.TITLE_MAX - suffix.length - 1;
  return `${title.slice(0, room).trim()} ${suffix}`;
}
