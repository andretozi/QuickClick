/**
 * Domínio · Regras de um anúncio
 * Limites, situações possíveis e a validação de cada etapa do assistente.
 */
import { FIELD_ERROR, maxLength, required } from '@/domain/validation/validators.js';
import { writingProblems } from '@/domain/listings/writingRules.js';
import { canContinue } from '@/domain/listings/exigencias.js';

export const LISTING_LIMITS = {
  /** Limite de caracteres do título no Mercado Livre */
  TITLE_MAX: 60,
  DESCRIPTION_MAX: 2000,
  PHOTOS_MAX: 6,
  STOCK_MAX: 99999,
  PRICE_MIN_CENTS: 100,
  PRICE_MAX_CENTS: 10000000
};

/** Situação do anúncio nos canais de venda. */
export const LISTING_STATUS = {
  PUBLISHED: 'published',
  PAUSED: 'paused',
  UNPUBLISHED: 'unpublished'
};

/** Canais de venda integrados à Quick Click. */
export const PRIMARY_CHANNEL = 'mercado-livre';
export const QUICKSTORE_CHANNEL = 'quickstore';
export const INTEGRATED_CHANNELS = [PRIMARY_CHANNEL, QUICKSTORE_CHANNEL];

/** Situação do anúncio em um canal específico. */
export function channelStatus(listing, channel = PRIMARY_CHANNEL) {
  return listing?.channels?.[channel] ?? LISTING_STATUS.UNPUBLISHED;
}

/** Situação geral do anúncio: publicado se ativo em algum canal, pausado se pausado em algum canal, senão em standby. */
export function listingStatus(listing) {
  const ml = channelStatus(listing, PRIMARY_CHANNEL);
  const qs = channelStatus(listing, QUICKSTORE_CHANNEL);
  if (ml === LISTING_STATUS.PUBLISHED || qs === LISTING_STATUS.PUBLISHED) return LISTING_STATUS.PUBLISHED;
  if (ml === LISTING_STATUS.PAUSED || qs === LISTING_STATUS.PAUSED) return LISTING_STATUS.PAUSED;
  return LISTING_STATUS.UNPUBLISHED;
}

/** Canais integrados em que o anúncio tem publicação ativa ou pausada (ou código externo), mas a conta está desconectada. */
export function disconnectedChannelsWithListing(listing, connectedByChannel = {}) {
  if (!listing) return [];
  return INTEGRATED_CHANNELS.filter((slug) => {
    const status = channelStatus(listing, slug);
    const hasItem = slug === QUICKSTORE_CHANNEL ? Boolean(listing.qsItemId) : Boolean(listing.mlItemId);
    const hasListing = status !== LISTING_STATUS.UNPUBLISHED || hasItem;
    return hasListing && !connectedByChannel[slug];
  });
}

/**
 * Calcula os canais alvo de uma ação geral (pausar todos os publicados, reativar todos os pausados
 * ou publicar nos conectados quando em standby), separando conectados e desconectados.
 */
export function channelActionTargets(listing, connectedByChannel = {}) {
  const overall = listingStatus(listing);
  let targetChannels;
  let nextStatus;
  if (overall === LISTING_STATUS.PUBLISHED) {
    targetChannels = INTEGRATED_CHANNELS.filter((slug) => channelStatus(listing, slug) === LISTING_STATUS.PUBLISHED);
    nextStatus = LISTING_STATUS.PAUSED;
  } else if (overall === LISTING_STATUS.PAUSED) {
    targetChannels = INTEGRATED_CHANNELS.filter((slug) => channelStatus(listing, slug) === LISTING_STATUS.PAUSED);
    nextStatus = LISTING_STATUS.PUBLISHED;
  } else {
    const connectedOnes = INTEGRATED_CHANNELS.filter((slug) => Boolean(connectedByChannel[slug]));
    targetChannels = connectedOnes.length ? connectedOnes : [...INTEGRATED_CHANNELS];
    nextStatus = LISTING_STATUS.PUBLISHED;
  }
  const connectedTargets = targetChannels.filter((slug) => Boolean(connectedByChannel[slug]));
  const disconnectedTargets = targetChannels.filter((slug) => !connectedByChannel[slug]);
  return { overall, nextStatus, targetChannels, connectedTargets, disconnectedTargets };
}

function isActive(listing) {
  return listingStatus(listing) === LISTING_STATUS.PUBLISHED;
}

/** Foto de capa de um anúncio ou rascunho (a primeira, se a capa escolhida não existir mais). */
export function coverPhoto(item) {
  const photos = item?.photos ?? [];
  return photos[item?.coverIndex ?? 0] ?? photos[0];
}

/** Etapas do assistente "criar anúncio", na ordem: a IA lê as fotos, o vendedor confirma e ela escreve. */
export const WIZARD_STEPS = ['photos', 'analysis', 'confirm', 'details', 'price', 'channels', 'publish'];

/** Passos que só existem no criar (na edição, o anúncio já tem tudo e a IA não roda de novo). */
export const AI_STEPS = ['analysis', 'confirm'];

/** Texto fora da regra de escrita (emoji, barra, travessão, traço solto ou marcador de lista). */
function writing(value) {
  return writingProblems(value).length ? FIELD_ERROR.WRITING : null;
}

/**
 * Erros de cada campo de uma etapa (objeto vazio = pode seguir). No Confirmar, requirementFields são
 * as exigências dos canais que ainda contam (vazio quando a análise não espera a confirmação).
 */
export function validateListingStep(step, draft) {
  const errors = {};
  if (step === 'photos') {
    if (!draft.photos?.length) errors.photos = FIELD_ERROR.REQUIRED;
  }
  if (step === 'confirm' && !canContinue(draft.requirementFields ?? [], draft.requirementAnswers)) {
    errors.requirements = FIELD_ERROR.REQUIRED;
  }
  if (step === 'details') {
    errors.title = required(draft.title) ?? maxLength(draft.title, LISTING_LIMITS.TITLE_MAX) ?? writing(draft.title);
    errors.description = maxLength(draft.description, LISTING_LIMITS.DESCRIPTION_MAX) ?? writing(draft.description);
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
function stockValueCents(listing) {
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
