/**
 * Domínio · Rascunho do anúncio: o formulário do "criar anúncio" e do editar.
 * Funções puras (converter, tirar foto, posição do preço e situação ao salvar).
 * Quem usa: os casos de uso do editor (application/listings).
 */
import { centsToInput, parseMoney } from '@/domain/format/format.js';
import { LISTING_STATUS, listingStatus } from '@/domain/listings/listingRules.js';

/** Rascunho vazio: um anúncio novo começa assim. */
export const EMPTY_DRAFT = {
  photos: [],
  coverIndex: 0,
  title: '',
  description: '',
  category: '',
  condition: 'new',
  stock: '1',
  priceInput: '',
  publishMl: true,
  // IA (só no criar): a análise, o que o vendedor confirmou e o que a IA preencheu
  analysisId: null,
  analysisPhotos: '', // marca das fotos que foram para a análise
  resultAppliedFor: null, // análise cujo resultado já entrou no rascunho
  product: '',
  cards: [],
  defects: [],
  requirementAnswers: {}, // exigências dos canais: { [id]: { value, confirmed } }
  attributes: [], // confirmados: [{ key, value }], vão para o anúncio e para o Mercado Livre
  specs: [],
  mlCategoryId: null,
  aiFilled: {}
};

/** Rascunho do assistente → campos do anúncio guardado. */
export function toListingData(draft, range) {
  return {
    title: draft.title,
    description: draft.description,
    category: draft.category,
    condition: draft.condition,
    priceCents: parseMoney(draft.priceInput),
    suggestedPriceCents: range?.suggestedCents ?? null,
    stock: Number(draft.stock),
    photos: draft.photos,
    coverIndex: Math.min(draft.coverIndex, Math.max(0, draft.photos.length - 1)),
    attributes: (draft.attributes ?? []).map((attribute) => ({
      id: attribute.id ?? null,
      name: attribute.key ?? attribute.name,
      value: attribute.value
    })),
    mlCategoryId: draft.mlCategoryId ?? null
  };
}

/** Anúncio guardado → rascunho do formulário (para ver e editar). */
export function toDraft(listing) {
  return {
    photos: listing.photos,
    coverIndex: listing.coverIndex,
    title: listing.title,
    description: listing.description,
    category: listing.category,
    condition: listing.condition,
    stock: String(listing.stock),
    priceInput: centsToInput(listing.priceCents),
    publishMl: listingStatus(listing) !== LISTING_STATUS.UNPUBLISHED,
    mlCategoryId: listing.mlCategoryId ?? null,
    attributes: (listing.attributes ?? []).map((attribute) => ({
      id: attribute.id ?? null,
      key: attribute.name,
      value: attribute.value
    }))
  };
}

/** Ainda não tem nada digitado nem foto: não vale a pena guardar como rascunho. */
export function isBlankDraft(draft) {
  return !draft.photos.length && !draft.title.trim() && !draft.description.trim();
}

/** Tira a foto da posição `index` e acerta a capa (se a capa saiu, a primeira foto vira a capa). */
export function withoutPhoto(draft, index) {
  const photos = draft.photos.filter((_, i) => i !== index);
  const coverIndex =
    index === draft.coverIndex ? 0 : index < draft.coverIndex ? draft.coverIndex - 1 : draft.coverIndex;
  return { ...draft, photos, coverIndex: Math.min(coverIndex, Math.max(0, photos.length - 1)) };
}

/** Onde o preço cai na faixa de itens parecidos: 'below', 'fair' ou 'above' (null sem faixa ou sem preço). */
export function pricePositionIn(range, priceCents) {
  if (range.status !== 'ready' || priceCents === null) return null;
  if (priceCents < range.minCents) return 'below';
  if (priceCents > range.maxCents) return 'above';
  return 'fair';
}

/**
 * Situação no Mercado Livre ao salvar um anúncio editado.
 * Sem "publicar", ele sai do ar. Fora do ar, só vai ao ar com o Mercado Livre conectado.
 * Publicado ou pausado, continua como está.
 */
export function statusAfterSave({ previous, publish, canPublish }) {
  if (!publish) return LISTING_STATUS.UNPUBLISHED;
  if (previous === LISTING_STATUS.UNPUBLISHED) return canPublish ? LISTING_STATUS.PUBLISHED : LISTING_STATUS.UNPUBLISHED;
  return previous;
}
