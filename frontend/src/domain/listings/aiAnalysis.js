/**
 * Domínio · Análise da IA no criar anúncio
 *
 * Estados e etapas (os mesmos do back), os cartões do passo Confirmar, o que vai para a
 * confirmação e como o resultado pronto entra no rascunho sem apagar o que o vendedor escreveu.
 * Só entra como fato o que o vendedor confirmou: "A IA viu", "Confere?" com sim, ou o que ele digitou.
 */

/** Etapas mostradas no progresso: a leitura (antes de confirmar) e a escrita (depois). */
export const READING_STAGES = ['preparando_fotos', 'lendo_produto'];
export const WRITING_STAGES = ['pesquisando_mercado', 'precificando', 'escrevendo'];

const ORDER = [
  'recebida',
  'preparando_fotos',
  'tratando_fotos',
  'verificando_fotos',
  'lendo_produto',
  'aguardando_confirmacao',
  'pesquisando_mercado',
  'precificando',
  'escrevendo',
  'pronta'
];

/** Cartão de cada atributo no passo Confirmar (vem do back em "cartao"). */
export const CARD = { SEEN: 'a_ia_viu', CHECK: 'confere', ASK: 'pergunta' };

/** Situação da análise para a tela. */
export function analysisPhase(analysis) {
  if (!analysis) return 'idle';
  if (analysis.status === 'pronta') return 'ready';
  if (analysis.status === 'aguardando_confirmacao') return 'waiting';
  if (analysis.status === 'falhou' || analysis.status === 'interrompida') return 'failed';
  return 'running';
}

/** Cada etapa da lista como 'done', 'active' ou 'todo', pela etapa em que a análise está. */
export function stagesProgress(stages, analysis) {
  const current = ORDER.indexOf(analysis?.status === 'falhou' || analysis?.status === 'interrompida'
    ? analysis?.stage
    : analysis?.status);
  return stages.map((id) => {
    const position = ORDER.indexOf(id);
    const state = current > position ? 'done' : current === position ? 'active' : 'todo';
    return { id, state };
  });
}

/** Fotos com problema de qualidade (escura, tremida ou pequena): a tela mostra a dica sem bloquear. */
export function photoQualityTips(analysis) {
  return (analysis?.photos ?? []).filter((photo) => photo.quality && photo.quality !== 'ok');
}

/** Leitura → cartões, guardando o que o vendedor já respondeu ou digitou em cada chave. */
export function cardsFromReading(reading, previous = []) {
  const before = new Map(previous.map((card) => [card.key, card]));
  const questions = new Map((reading?.questions ?? []).map((q) => [q.key, q]));
  const cards = (reading?.attributes ?? []).map((attribute) => {
    const old = before.get(attribute.key);
    const question = questions.get(attribute.key);
    // a releitura (foto extra) pode ter preenchido o que antes era pergunta: vale o valor novo
    const keepTyped = old?.edited && !(attribute.card === CARD.SEEN && old.card === CARD.ASK);
    return {
      key: attribute.key,
      value: keepTyped ? old.value : attribute.value,
      card: attribute.card,
      origin: attribute.origin,
      evidence: attribute.evidence,
      question: question?.question ?? '',
      suggestPhoto: question?.suggestPhoto ?? 'nenhuma',
      answer: attribute.card === CARD.CHECK ? (old?.card === CARD.CHECK ? old.answer : null) : null,
      edited: Boolean(keepTyped)
    };
  });
  for (const question of reading?.questions ?? []) {
    if (cards.some((card) => card.key === question.key)) continue;
    const old = before.get(question.key);
    cards.push({
      key: question.key,
      value: old?.value ?? '',
      card: CARD.ASK,
      origin: 'desconhecido',
      evidence: '',
      question: question.question,
      suggestPhoto: question.suggestPhoto,
      answer: null,
      edited: Boolean(old?.edited)
    });
  }
  return cards;
}

/** Defeitos vistos pela IA, cada um com "Está certo?" (todos entram, até o vendedor dizer que não). */
export function defectsFromReading(reading, previous = []) {
  return (reading?.defects ?? []).map((text) => ({
    text,
    keep: previous.find((defect) => defect.text === text)?.keep ?? true
  }));
}

/** O cartão "Confere?" ainda sem resposta. */
export function isPendingCheck(card) {
  return card.card === CARD.CHECK && card.answer === null && !card.edited;
}

/** O valor do cartão entra como fato? */
function isConfirmed(card) {
  if (!String(card.value ?? '').trim()) return false;
  if (card.edited) return true;
  if (card.card === CARD.SEEN) return true;
  return card.card === CARD.CHECK && card.answer === 'yes';
}

/** Condição da IA ('novo', 'usado', 'recondicionado') → a do anúncio ('new' ou 'used'). */
export function conditionFromAi(value) {
  if (value === 'novo') return 'new';
  if (value === 'usado' || value === 'recondicionado') return 'used';
  return null;
}

/** O que vai para a confirmação da análise. */
export function confirmationPayload({ product, category, condition, cards, defects }) {
  return {
    product: String(product ?? '').trim(),
    category,
    condition: condition === 'used' ? 'usado' : 'novo',
    attributes: cards.filter(isConfirmed).map((card) => ({ key: card.key, value: String(card.value).trim() })),
    defects: defects.filter((defect) => defect.keep).map((defect) => defect.text)
  };
}

/**
 * Resultado pronto → campos do rascunho. Só troca o que está vazio ou o que a própria IA
 * preencheu antes e o vendedor não mexeu (aiFilled).
 */
export function draftPatchFromResult(draft, analysis) {
  const patch = {};
  const filled = { ...(draft.aiFilled ?? {}) };
  const canFill = (field) => !String(draft[field] ?? '').trim() || filled[field];
  const text = analysis?.text;
  if (text?.title && canFill('title')) {
    patch.title = text.title;
    filled.title = true;
  }
  if (text?.description && canFill('description')) {
    patch.description = text.description;
    filled.description = true;
  }
  const confirmed = analysis?.confirmed;
  if (confirmed?.category && canFill('category')) {
    patch.category = confirmed.category;
    filled.category = true;
  }
  const condition = conditionFromAi(confirmed?.condition);
  if (condition) patch.condition = condition;
  if (confirmed?.attributes) patch.attributes = confirmed.attributes;
  if (text?.specs) patch.specs = text.specs;
  if (analysis?.mercadoLivre?.categoryId) patch.mlCategoryId = analysis.mercadoLivre.categoryId;
  patch.aiFilled = filled;
  return patch;
}

/** Faixa de preço para a régua, a partir do preço da análise ({ status: 'ready' | 'loading' | 'none' }). */
export function priceRangeFrom(analysis) {
  const phase = analysisPhase(analysis);
  if (phase === 'running' && analysis.status !== 'escrevendo') return { status: 'loading' };
  const price = analysis?.price;
  if (!price || price.noData) return { status: 'none', reason: price?.reason ?? null };
  return {
    status: 'ready',
    minCents: Math.min(price.range.min, price.suggestedCents),
    suggestedCents: price.suggestedCents,
    maxCents: Math.max(price.range.max, price.suggestedCents)
  };
}
