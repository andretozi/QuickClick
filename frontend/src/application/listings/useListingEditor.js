import { useCallback, useEffect, useMemo, useRef, useState } from 'react';
import useMountedRef from '@/application/ui/useMountedRef.js';
import useSession from '@/application/session/useSession.js';
import useDraftAutosave from '@/application/listings/useDraftAutosave.js';
import useListingPhotos from '@/application/listings/useListingPhotos.js';
import useAnaliseIA from '@/application/listings/useAnaliseIA.js';
import useCotaIA from '@/application/listings/useCotaIA.js';
import { showToast, TOAST_TONES } from '@/application/feedback/toastStore.js';
import {
  createListing,
  getListing,
  mergeMercadoLivreItem,
  updateListing
} from '@/infrastructure/storage/listingsRepository.js';
import { fetchConnectedMarketplaces } from '@/infrastructure/marketplaces/marketplacesService.js';
import {
  fetchMercadoLivreItem,
  publishToMercadoLivre,
  updateMercadoLivreItem,
  updateMercadoLivreStatus
} from '@/infrastructure/ai/iaService.js';
import { clearDraft, getDraft, saveDraft } from '@/infrastructure/storage/draftsRepository.js';
import { StorageFullError } from '@/infrastructure/storage/localStore.js';
import { focusFirstInvalid } from '@/infrastructure/browser/focus.js';
import {
  AI_STEPS,
  LISTING_STATUS,
  PRIMARY_CHANNEL,
  WIZARD_STEPS,
  listingStatus,
  validateListingStep
} from '@/domain/listings/listingRules.js';
import {
  EMPTY_DRAFT,
  isBlankDraft,
  pricePositionIn,
  statusAfterSave,
  toDraft,
  toListingData
} from '@/domain/listings/listingDraft.js';
import {
  CARD,
  cardsFromReading,
  conditionFromAi,
  confirmationPayload,
  defectsFromReading,
  draftPatchFromResult,
  priceRangeFrom
} from '@/domain/listings/aiAnalysis.js';
import { centsToInput, parseMoney } from '@/domain/format/format.js';
import { LISTING_EDITOR, LISTING_WIZARD, aiErrorText } from '@/domain/content/listingContent.js';

const EDIT_STEPS = WIZARD_STEPS.filter((name) => !AI_STEPS.includes(name));
const USER_FIELDS = ['title', 'description', 'category'];

/** Uma marca das fotos que foram para a análise (fotos novas pedem análise nova). */
const photosKey = (photos) => photos.map((photo) => photo.slice(-24)).join('|');

/**
 * Aplicação · Caso de uso "criar anúncio" e "ver e editar anúncio".
 *
 * Criar: fotos → análise da IA (no back, em etapas) → confirmar o que a IA viu → detalhes
 * (título e descrição escritos pela IA) → preço (faixa real) → canais → publicar (o back
 * monta o anúncio do Mercado Livre). Editar: só os passos do anúncio, sem IA, sincronizando
 * com o Mercado Livre quando o anúncio já está publicado.
 *
 * - listingId: com id, abre o anúncio para editar; sem id, é um anúncio novo
 * - celebrate(word): animação de publicar (cursor, clique e partículas); devolve uma Promise
 */
export default function useListingEditor({ listingId, celebrate }) {
  const { account } = useSession();
  const accountId = account?.id;
  const editing = Boolean(listingId);
  const steps = editing ? EDIT_STEPS : WIZARD_STEPS;

  const [status, setStatus] = useState('loading');
  const [stepIndex, setStepIndex] = useState(0);
  const [draft, setDraft] = useState(EMPTY_DRAFT);
  const [errors, setErrors] = useState({});
  const [original, setOriginal] = useState(null);
  const [connection, setConnection] = useState(null);
  const [publishing, setPublishing] = useState(false);
  const [result, setResult] = useState(null);
  const [visited, setVisited] = useState(0);

  const mounted = useMountedRef();
  const formRef = useRef(null);
  const loaded = useRef(false);
  const finishing = useRef(false); // publicando: o rascunho não é mais salvo
  const appliedResult = useRef(null); // id da análise cujo resultado já entrou no rascunho
  const advanced = useRef(null); // id da análise que já levou ao passo Confirmar

  // ---------- Carregar ----------
  useEffect(() => {
    if (!accountId) return;
    loaded.current = false;
    (async () => {
      try {
        const connections = await fetchConnectedMarketplaces().catch(() => []);
        if (!mounted.current) return;
        const mlConn = connections.find((item) => item.slug === PRIMARY_CHANNEL) ?? null;
        setConnection(mlConn);
        if (editing) {
          let listing = await getListing(accountId, listingId);
          if (mlConn && listing.mlItemId) {
            try {
              const mlFresh = await fetchMercadoLivreItem(listing.mlItemId);
              listing = await mergeMercadoLivreItem(accountId, listingId, mlFresh);
            } catch {
              // Mantém os dados locais se a sincronização falhar
            }
          }
          if (!mounted.current) return;
          setOriginal(listing);
          setDraft({ ...EMPTY_DRAFT, ...toDraft(listing) });
          setVisited(EDIT_STEPS.length - 1);
        } else {
          const saved = await getDraft(accountId);
          if (!mounted.current) return;
          if (saved?.data && !isBlankDraft({ ...EMPTY_DRAFT, ...saved.data })) {
            const restored = { ...EMPTY_DRAFT, ...saved.data };
            setDraft(restored);
            // resultado já aplicado antes de recarregar não entra de novo por cima do que o vendedor mexeu
            appliedResult.current = restored.resultAppliedFor ?? null;
            advanced.current = restored.analysisId;
            setStepIndex(Math.min(saved.step ?? 0, WIZARD_STEPS.length - 1));
            setVisited(Math.min(saved.step ?? 0, WIZARD_STEPS.length - 1));
            showToast({ tone: TOAST_TONES.INFO, ...LISTING_WIZARD.draftRestored });
          }
        }
        setStatus('ready');
        loaded.current = true;
      } catch {
        if (mounted.current) setStatus(editing ? 'not-found' : 'ready');
        loaded.current = true;
      }
    })();
  }, [accountId, editing, listingId, mounted]);

  // ---------- Rascunho salvo sozinho (só no criar) ----------
  const autosave = useDraftAutosave({
    accountId,
    draft,
    stepIndex,
    enabled: !editing && !result,
    loaded,
    finishing,
    mounted
  });

  const step = steps[stepIndex];

  // ---------- Campos ----------
  const update = useCallback((patch) => {
    setDraft((current) => {
      const edited = USER_FIELDS.filter((key) => key in patch);
      const aiFilled = edited.length
        ? { ...current.aiFilled, ...Object.fromEntries(edited.map((key) => [key, false])) }
        : current.aiFilled;
      return { ...current, ...patch, aiFilled };
    });
    setErrors((current) => {
      const next = { ...current };
      Object.keys(patch).forEach((key) => {
        delete next[key === 'priceInput' ? 'price' : key];
      });
      return next;
    });
  }, []);

  const setField = useCallback(
    (event) => {
      const { name, value, type, checked } = event.target;
      update({ [name]: type === 'checkbox' ? checked : value });
    },
    [update]
  );

  // ---------- Fotos, análise da IA e cota ----------
  const photos = useListingPhotos({ photoCount: draft.photos.length, setDraft, setErrors, update, mounted });
  const onAnalysisId = useCallback((id) => setDraft((current) => ({ ...current, analysisId: id })), []);
  const ai = useAnaliseIA({ analysisId: editing ? null : draft.analysisId, onAnalysisId, mounted });
  const { analysis } = ai;
  const cota = useCotaIA({
    enabled: !editing && Boolean(accountId),
    refreshKey: ai.phase === 'ready' ? analysis?.id : null,
    mounted
  });

  // A leitura chegou (ou mudou com a foto extra): cartões, defeitos e o que a IA reconheceu
  const reading = analysis?.reading;
  useEffect(() => {
    if (!reading) return;
    setDraft((current) => ({
      ...current,
      cards: cardsFromReading(reading, current.cards),
      defects: defectsFromReading(reading, current.defects),
      product: current.product || reading.product,
      category: current.category || (reading.recognized ? reading.category : current.category),
      condition: reading.condition.confidence !== 'baixa' ? (conditionFromAi(reading.condition.value) ?? current.condition) : current.condition
    }));
  }, [reading]);

  // Leitura pronta no passo Análise: segue sozinho para Confirmar (uma vez por análise)
  useEffect(() => {
    if (ai.phase === 'waiting' && step === 'analysis' && advanced.current !== analysis?.id) {
      advanced.current = analysis.id;
      setStepIndex(steps.indexOf('confirm'));
      setVisited((current) => Math.max(current, steps.indexOf('confirm')));
    }
  }, [ai.phase, analysis, step, steps]);

  // Resultado pronto: título, descrição, categoria e condição entram no rascunho
  useEffect(() => {
    if (ai.phase !== 'ready' || !analysis || appliedResult.current === analysis.id) return;
    appliedResult.current = analysis.id;
    setDraft((current) => ({ ...current, ...draftPatchFromResult(current, analysis), resultAppliedFor: analysis.id }));
    showToast({ tone: TOAST_TONES.SUCCESS, ...LISTING_WIZARD.details.aiDone });
  }, [ai.phase, analysis]);

  const startAnalysis = useCallback(async () => {
    if (!draft.photos.length) return;
    const key = photosKey(draft.photos);
    if (draft.analysisId && draft.analysisPhotos === key) return; // essas fotos já foram analisadas
    if (cota.quota && (!cota.quota.available || cota.quota.remaining <= 0)) return; // o passo mostra o motivo
    const cover = draft.photos[draft.coverIndex] ?? draft.photos[0];
    const ordered = [cover, ...draft.photos.filter((photo) => photo !== cover)];
    setDraft((current) => ({ ...current, analysisPhotos: key, cards: [], defects: [], product: '' }));
    await ai.start(photos.readingBlobs(ordered));
  }, [ai, cota.quota, draft.analysisId, draft.analysisPhotos, draft.coverIndex, draft.photos, photos]);

  // ---------- Navegação entre os passos ----------
  const validateStep = useCallback(
    (name) => validateListingStep(name, { ...draft, priceCents: parseMoney(draft.priceInput) }),
    [draft]
  );

  const showErrors = useCallback((found) => {
    setErrors(found);
    window.requestAnimationFrame(() => focusFirstInvalid(formRef.current));
  }, []);

  const goTo = useCallback(
    (index) => {
      if (index < 0 || index >= steps.length) return;
      // para a frente, cada passo do caminho precisa estar certo
      for (let i = stepIndex; i < index; i += 1) {
        const found = validateStep(steps[i]);
        if (Object.keys(found).length) {
          setStepIndex(i);
          showErrors(found);
          return;
        }
      }
      setErrors({});
      setStepIndex(index);
      setVisited((current) => Math.max(current, index));
      if (!editing && steps[index] === 'analysis' && step === 'photos') startAnalysis();
    },
    [editing, showErrors, startAnalysis, step, stepIndex, steps, validateStep]
  );

  const next = useCallback(() => goTo(stepIndex + 1), [goTo, stepIndex]);
  const back = useCallback(() => goTo(stepIndex - 1), [goTo, stepIndex]);
  /** Sem IA (fora do ar, sem cota ou com erro): direto para os campos manuais. */
  const fillByHand = useCallback(() => goTo(steps.indexOf('details')), [goTo, steps]);

  // ---------- Passo Confirmar ----------
  const setCard = useCallback((key, patch) => {
    setDraft((current) => ({
      ...current,
      cards: current.cards.map((card) => {
        if (card.key !== key) return card;
        if (patch.answer === 'no') return { ...card, answer: 'no', value: '', card: CARD.ASK, edited: false };
        return { ...card, ...patch };
      })
    }));
  }, []);

  const setDefect = useCallback((index, keep) => {
    setDraft((current) => ({
      ...current,
      defects: current.defects.map((defect, i) => (i === index ? { ...defect, keep } : defect))
    }));
  }, []);

  const confirm = useCallback(async () => {
    const payload = confirmationPayload({
      product: draft.product || reading?.product || draft.title,
      category: draft.category || reading?.category || 'outros',
      condition: draft.condition,
      cards: draft.cards,
      defects: draft.defects
    });
    const done = await ai.confirm(payload);
    if (done !== null && mounted.current) {
      setStepIndex(steps.indexOf('details'));
      setVisited((current) => Math.max(current, steps.indexOf('details')));
    }
  }, [ai, draft, mounted, reading, steps]);

  const resume = useCallback(() => {
    const blobs = analysis?.needsPhotosToResume ? photos.readingBlobs(draft.photos) : null;
    return ai.resume(blobs);
  }, [ai, analysis, draft.photos, photos]);

  // ---------- Preço ----------
  const range = useMemo(() => (editing || !analysis ? { status: 'none' } : priceRangeFrom(analysis)), [analysis, editing]);
  const priceCents = parseMoney(draft.priceInput);
  const pricePosition = pricePositionIn(range, priceCents);
  const acceptSuggestedPrice = useCallback(() => {
    if (range.status === 'ready') update({ priceInput: centsToInput(range.suggestedCents) });
  }, [range, update]);

  // ---------- Publicar ou salvar ----------
  const canPublishMl = Boolean(connection);
  const willPublish = draft.publishMl && canPublishMl;

  const publishOnMl = useCallback(
    async (data) => {
      const cover = data.photos[data.coverIndex] ?? data.photos[0];
      const ordered = [cover, ...data.photos.filter((photo) => photo !== cover)];
      const keptPhotos = ordered.filter((p) => String(p).startsWith('https://'));
      return publishToMercadoLivre(
        {
          title: data.title,
          description: data.description,
          priceCents: data.priceCents,
          stock: data.stock,
          condition: data.condition,
          attributes: draft.attributes,
          analysisId: draft.analysisId,
          mlCategoryId: draft.mlCategoryId,
          keptPhotos
        },
        photos.readingBlobs(ordered)
      );
    },
    [draft.analysisId, draft.attributes, draft.mlCategoryId, photos]
  );

  const updateOnMl = useCallback(
    async (itemId, data) => {
      const cover = data.photos[data.coverIndex] ?? data.photos[0];
      const ordered = [cover, ...data.photos.filter((photo) => photo !== cover)];
      const keptPhotos = ordered.filter((p) => String(p).startsWith('https://'));
      return updateMercadoLivreItem(
        itemId,
        {
          title: data.title,
          description: data.description,
          priceCents: data.priceCents,
          stock: data.stock,
          condition: data.condition,
          attributes: draft.attributes,
          analysisId: draft.analysisId,
          mlCategoryId: draft.mlCategoryId ?? original?.mlCategoryId,
          keptPhotos
        },
        photos.readingBlobs(ordered)
      );
    },
    [draft.analysisId, draft.attributes, draft.mlCategoryId, original?.mlCategoryId, photos]
  );

  const finish = useCallback(async () => {
    if (publishing) return;
    for (let i = 0; i < steps.length; i += 1) {
      const found = validateStep(steps[i]);
      if (Object.keys(found).length) {
        setStepIndex(i);
        showErrors(found);
        return;
      }
    }
    setPublishing(true);
    finishing.current = true;
    const data = toListingData(draft, range.status === 'ready' ? range : null);
    try {
      if (editing) {
        const previousStatus = listingStatus(original);
        const nextStatus = statusAfterSave({
          previous: previousStatus,
          publish: draft.publishMl,
          canPublish: canPublishMl
        });
        let mlPatch = {};
        if (original.mlItemId && canPublishMl) {
          const mlUpdated = await updateOnMl(original.mlItemId, data);
          if (!draft.publishMl && previousStatus === LISTING_STATUS.PUBLISHED) {
            await updateMercadoLivreStatus(original.mlItemId, LISTING_STATUS.PAUSED);
          } else if (draft.publishMl && previousStatus !== LISTING_STATUS.PUBLISHED) {
            await updateMercadoLivreStatus(original.mlItemId, LISTING_STATUS.PUBLISHED);
          }
          mlPatch = {
            mlItemId: mlUpdated.id ?? original.mlItemId,
            permalink: mlUpdated.permalink ?? original.permalink,
            mlCategoryId: mlUpdated.category_id ?? original.mlCategoryId,
            health: mlUpdated.health ?? original.health,
            soldQuantity: mlUpdated.sold_quantity ?? original.soldQuantity,
            photos: Array.isArray(mlUpdated.pictures) && mlUpdated.pictures.length ? mlUpdated.pictures : data.photos,
            coverIndex: 0
          };
        } else if (nextStatus === LISTING_STATUS.PUBLISHED && previousStatus === LISTING_STATUS.UNPUBLISHED) {
          const published = await publishOnMl(data);
          mlPatch = {
            mlItemId: published.id,
            permalink: published.permalink,
            mlCategoryId: published.categoryId ?? data.mlCategoryId
          };
        }
        const finalChannelStatus =
          original.mlItemId && !draft.publishMl ? LISTING_STATUS.PAUSED : nextStatus;
        const updated = await updateListing(accountId, listingId, {
          ...data,
          ...mlPatch,
          suggestedPriceCents: data.suggestedPriceCents ?? original.suggestedPriceCents,
          channels: { ...original.channels, [PRIMARY_CHANNEL]: finalChannelStatus }
        });
        photos.release();
        finishing.current = false;
        if (!mounted.current) return;
        setOriginal(updated);
        setPublishing(false);
        showToast({ tone: TOAST_TONES.SUCCESS, ...LISTING_EDITOR.saved });
        return;
      }
      // Publicar de verdade primeiro: se o Mercado Livre recusar, nada é gravado e o rascunho fica
      const published = willPublish ? await publishOnMl(data) : null;
      // O rascunho sai antes: as fotos não ocupam o espaço duas vezes na hora de gravar.
      await clearDraft(accountId);
      let created;
      try {
        created = await createListing(accountId, {
          ...data,
          mlItemId: published?.id ?? null,
          permalink: published?.permalink ?? null,
          mlCategoryId: published?.categoryId ?? data.mlCategoryId ?? null,
          channels: { [PRIMARY_CHANNEL]: published ? LISTING_STATUS.PUBLISHED : LISTING_STATUS.UNPUBLISHED }
        });
      } catch (error) {
        // Não gravou: o rascunho volta, para nada se perder.
        await saveDraft(accountId, { step: stepIndex, data: draft }).catch(() => {});
        throw error;
      }
      photos.release();
      // A comemoração só depois de gravar de verdade.
      const word = published ? LISTING_WIZARD.publish.word : LISTING_WIZARD.publish.wordSaved;
      if (celebrate) await celebrate(word).catch(() => {});
      if (!mounted.current) return;
      setPublishing(false);
      setResult({ published: Boolean(published), id: created.id, permalink: published?.permalink ?? null });
      published?.notices?.forEach((notice) => showToast({ tone: TOAST_TONES.INFO, ...aiErrorText(notice.code, notice.message) }));
    } catch (error) {
      finishing.current = false;
      if (!mounted.current) return;
      setPublishing(false);
      let message = LISTING_WIZARD.errors.generic;
      if (error instanceof StorageFullError) message = LISTING_WIZARD.errors.storage;
      else if (error?.code) message = aiErrorText(error.code, error.userMessage);
      showToast({ tone: TOAST_TONES.ERROR, ...message });
    }
  }, [
    accountId,
    canPublishMl,
    celebrate,
    draft,
    editing,
    listingId,
    original,
    photos,
    publishOnMl,
    publishing,
    range,
    showErrors,
    stepIndex,
    steps,
    updateOnMl,
    validateStep,
    willPublish,
    mounted
  ]);

  /** Joga o rascunho fora e volta para o primeiro passo. */
  const { clearSavedAt, savedAt, storageFull } = autosave;
  const restart = useCallback(async () => {
    if (accountId) await clearDraft(accountId);
    if (!mounted.current) return;
    finishing.current = false;
    appliedResult.current = null;
    advanced.current = null;
    ai.reset();
    photos.release();
    setDraft(EMPTY_DRAFT);
    setErrors({});
    setStepIndex(0);
    setVisited(0);
    setResult(null);
    clearSavedAt();
  }, [accountId, ai, clearSavedAt, mounted, photos]);

  return {
    editing,
    status,
    steps,
    step,
    stepIndex,
    visited,
    goTo,
    next,
    back,
    fillByHand,
    startAnalysis,
    draft,
    errors,
    setField,
    update,
    formRef,
    photos,
    ai,
    quota: cota.quota,
    setCard,
    setDefect,
    confirm,
    resume,
    range,
    priceCents,
    pricePosition,
    acceptSuggestedPrice,
    connection,
    canPublishMl,
    willPublish,
    finish,
    publishing,
    result,
    restart,
    savedAt,
    storageFull,
    clearSavedAt
  };
}
