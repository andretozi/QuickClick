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
  mergeQuickStoreItem,
  updateListing
} from '@/infrastructure/storage/listingsRepository.js';
import { fetchConnectedMarketplaces } from '@/infrastructure/marketplaces/marketplacesService.js';
import {
  fetchMercadoLivreItem,
  fetchQuickStoreItem,
  publishToMercadoLivre,
  publishToQuickStore,
  updateMercadoLivreItem,
  updateMercadoLivreStatus,
  updateQuickStoreItem,
  updateQuickStoreStatus
} from '@/infrastructure/ai/iaService.js';
import { clearDraft, getDraft, saveDraft } from '@/infrastructure/storage/draftsRepository.js';
import { StorageFullError } from '@/infrastructure/storage/localStore.js';
import { focusFirstInvalid } from '@/infrastructure/browser/focus.js';
import {
  AI_STEPS,
  LISTING_STATUS,
  PRIMARY_CHANNEL,
  QUICKSTORE_CHANNEL,
  WIZARD_STEPS,
  channelStatus,
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
import {
  coveredCardKeys,
  requirementAnswers,
  requirementFields,
  requirementsConfirmation
} from '@/domain/listings/exigencias.js';
import { centsToInput, parseMoney } from '@/domain/format/format.js';
import { LISTING_EDITOR, LISTING_WIZARD, aiErrorText } from '@/domain/content/listingContent.js';

const EDIT_STEPS = WIZARD_STEPS.filter((name) => !AI_STEPS.includes(name));
const USER_FIELDS = ['title', 'description', 'category'];
const CHANNEL_NAMES = {
  [PRIMARY_CHANNEL]: 'Mercado Livre',
  [QUICKSTORE_CHANNEL]: 'QuickStore'
};

/** Uma marca das fotos que foram para a análise (fotos novas pedem análise nova). */
const photosKey = (photos) => photos.map((photo) => photo.slice(-24)).join('|');

/**
 * Aplicação · Caso de uso "criar anúncio" e "ver e editar anúncio".
 *
 * Criar: fotos → análise da IA (no back, em etapas) → confirmar o que a IA viu → detalhes
 * (título e descrição escritos pela IA) → preço (faixa real) → canais → publicar (o back
 * monta o anúncio do Mercado Livre e da QuickStore). Editar: só os passos do anúncio, sem IA,
 * sincronizando com o Mercado Livre e a QuickStore quando o anúncio já está publicado.
 *
 * - listingId: com id, abre o anúncio para editar; sem id, é um anúncio novo
 * - channelScope: opcional ('mercado-livre' | 'quickstore' | null), restringe a edição a um canal
 * - celebrate(word): animação de publicar (cursor, clique e partículas); devolve uma Promise
 */
export default function useListingEditor({ listingId, channelScope: rawChannelScope = null, celebrate }) {
  const { account } = useSession();
  const accountId = account?.id;
  const editing = Boolean(listingId);
  const channelScope =
    editing && (rawChannelScope === PRIMARY_CHANNEL || rawChannelScope === QUICKSTORE_CHANNEL)
      ? rawChannelScope
      : null;
  const steps = editing ? EDIT_STEPS : WIZARD_STEPS;

  const [status, setStatus] = useState('loading');
  const [stepIndex, setStepIndex] = useState(0);
  const [draft, setDraft] = useState(EMPTY_DRAFT);
  const [errors, setErrors] = useState({});
  const [original, setOriginal] = useState(null);
  const [connection, setConnection] = useState(null);
  const [qsConnection, setQsConnection] = useState(null);
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
        let mlConn = connections.find((item) => item.slug === PRIMARY_CHANNEL) ?? null;
        let qsConn = connections.find((item) => item.slug === QUICKSTORE_CHANNEL) ?? null;
        if (editing) {
          let listing = await getListing(accountId, listingId);
          const syncMl = !channelScope || channelScope === PRIMARY_CHANNEL;
          const syncQs = !channelScope || channelScope === QUICKSTORE_CHANNEL;
          if (syncMl && mlConn && listing.mlItemId) {
            try {
              const mlFresh = await fetchMercadoLivreItem(listing.mlItemId);
              listing = await mergeMercadoLivreItem(accountId, listingId, mlFresh);
            } catch (error) {
              if (error?.code === 'mercado_livre_desconectado') mlConn = null;
            }
          }
          if (syncQs && qsConn && listing.qsItemId) {
            try {
              const qsFresh = await fetchQuickStoreItem(listing.qsItemId);
              listing = await mergeQuickStoreItem(accountId, listingId, qsFresh);
            } catch (error) {
              if (error?.code === 'quickstore_desconectada') qsConn = null;
            }
          }
          if (!mounted.current) return;
          setConnection(mlConn);
          setQsConnection(qsConn);
          setOriginal(listing);
          setDraft({ ...EMPTY_DRAFT, ...toDraft(listing) });
          setVisited(EDIT_STEPS.length - 1);
        } else {
          setConnection(mlConn);
          setQsConnection(qsConn);
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
  }, [accountId, channelScope, editing, listingId, mounted]);

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

  // A leitura chegou (ou mudou com a foto extra): cartões, defeitos, exigências dos canais e o que a IA reconheceu
  const reading = analysis?.reading;
  const fields = useMemo(() => requirementFields(reading?.requirements), [reading]);
  useEffect(() => {
    if (!reading) return;
    setDraft((current) => ({
      ...current,
      cards: cardsFromReading(reading, current.cards),
      defects: defectsFromReading(reading, current.defects),
      requirementAnswers: requirementAnswers(fields, current.requirementAnswers),
      product: current.product || reading.product,
      category: current.category || (reading.recognized ? reading.category : current.category),
      condition: reading.condition.confidence !== 'baixa' ? (conditionFromAi(reading.condition.value) ?? current.condition) : current.condition
    }));
  }, [fields, reading]);

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
    setDraft((current) => ({ ...current, analysisPhotos: key, cards: [], defects: [], requirementAnswers: {}, product: '' }));
    await ai.start(photos.readingBlobs(ordered));
  }, [ai, cota.quota, draft.analysisId, draft.analysisPhotos, draft.coverIndex, draft.photos, photos]);

  // ---------- Navegação entre os passos ----------
  // as exigências só seguram o passo enquanto a análise espera a confirmação (à mão ou depois de confirmar, não)
  const pendingFields = ai.phase === 'waiting' ? fields : null;
  const validateStep = useCallback(
    (name) =>
      validateListingStep(name, { ...draft, priceCents: parseMoney(draft.priceInput), requirementFields: pendingFields }),
    [draft, pendingFields]
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

  const setRequirement = useCallback((id, patch) => {
    setDraft((current) => ({
      ...current,
      requirementAnswers: { ...current.requirementAnswers, [id]: { ...current.requirementAnswers?.[id], ...patch } }
    }));
  }, []);

  const setDefect = useCallback((index, keep) => {
    setDraft((current) => ({
      ...current,
      defects: current.defects.map((defect, i) => (i === index ? { ...defect, keep } : defect))
    }));
  }, []);

  const confirm = useCallback(async () => {
    const found = validateStep('confirm');
    if (Object.keys(found).length) {
      showErrors(found);
      return;
    }
    const covered = coveredCardKeys(fields);
    const payload = confirmationPayload({
      product: draft.product || reading?.product || draft.title,
      category: draft.category || reading?.category || 'outros',
      condition: draft.condition,
      cards: draft.cards.filter((card) => !covered.has(card.key)),
      defects: draft.defects,
      requirements: requirementsConfirmation(fields, draft.requirementAnswers)
    });
    const done = await ai.confirm(payload);
    if (done !== null && mounted.current) {
      setStepIndex(steps.indexOf('details'));
      setVisited((current) => Math.max(current, steps.indexOf('details')));
    }
  }, [ai, draft, fields, mounted, reading, showErrors, steps, validateStep]);

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
  const canPublishQs = Boolean(qsConnection);
  const channelDisconnected =
    Boolean(editing && channelScope) &&
    (channelScope === QUICKSTORE_CHANNEL ? !canPublishQs : !canPublishMl);
  const willPublishMl = Boolean(
    (!channelScope || channelScope === PRIMARY_CHANNEL) && draft.publishMl && canPublishMl
  );
  const willPublishQs = Boolean(
    (!channelScope || channelScope === QUICKSTORE_CHANNEL) && draft.publishQs && canPublishQs
  );
  const willPublish = willPublishMl || willPublishQs;

  const prepareChannelPayload = useCallback(
    (data, categoryFallback) => {
      const cover = data.photos[data.coverIndex] ?? data.photos[0];
      const ordered = [cover, ...data.photos.filter((photo) => photo !== cover)];
      const keptPhotos = ordered.filter((p) => String(p).startsWith('https://'));
      return {
        payload: {
          title: data.title,
          description: data.description,
          priceCents: data.priceCents,
          stock: data.stock,
          condition: data.condition,
          attributes: draft.attributes,
          analysisId: draft.analysisId,
          mlCategoryId: draft.mlCategoryId ?? categoryFallback,
          keptPhotos
        },
        blobs: photos.readingBlobs(ordered)
      };
    },
    [draft.analysisId, draft.attributes, draft.mlCategoryId, photos]
  );

  const publishOnMl = useCallback(
    async (data) => {
      const { payload, blobs } = prepareChannelPayload(data, original?.mlCategoryId);
      return publishToMercadoLivre(payload, blobs);
    },
    [original?.mlCategoryId, prepareChannelPayload]
  );

  const updateOnMl = useCallback(
    async (itemId, data) => {
      const { payload, blobs } = prepareChannelPayload(data, original?.mlCategoryId);
      return updateMercadoLivreItem(itemId, payload, blobs);
    },
    [original?.mlCategoryId, prepareChannelPayload]
  );

  const publishOnQs = useCallback(
    async (data) => {
      const { payload, blobs } = prepareChannelPayload(data, original?.qsCategoryId ?? original?.mlCategoryId);
      return publishToQuickStore(payload, blobs);
    },
    [original?.mlCategoryId, original?.qsCategoryId, prepareChannelPayload]
  );

  const updateOnQs = useCallback(
    async (itemId, data) => {
      const { payload, blobs } = prepareChannelPayload(data, original?.qsCategoryId ?? original?.mlCategoryId);
      return updateQuickStoreItem(itemId, payload, blobs);
    },
    [original?.mlCategoryId, original?.qsCategoryId, prepareChannelPayload]
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
    if (editing && channelScope && channelDisconnected) {
      const hasRemoteItem = channelScope === QUICKSTORE_CHANNEL ? Boolean(original?.qsItemId) : Boolean(original?.mlItemId);
      const wantsPublish = channelScope === QUICKSTORE_CHANNEL ? draft.publishQs : draft.publishMl;
      if (hasRemoteItem || wantsPublish) {
        showToast({
          tone: TOAST_TONES.ERROR,
          ...aiErrorText(channelScope === QUICKSTORE_CHANNEL ? 'quickstore_desconectada' : 'mercado_livre_desconectado')
        });
        return;
      }
    }

    setPublishing(true);
    finishing.current = true;
    const data = toListingData(draft, range.status === 'ready' ? range : null);
    try {
      if (editing) {
        const shouldRunMl = !channelScope || channelScope === PRIMARY_CHANNEL;
        const shouldRunQs = !channelScope || channelScope === QUICKSTORE_CHANNEL;

        const previousMlStatus = channelStatus(original, PRIMARY_CHANNEL);
        const nextMlStatus = shouldRunMl
          ? statusAfterSave({
              previous: previousMlStatus,
              publish: draft.publishMl,
              canPublish: canPublishMl
            })
          : previousMlStatus;
        let mlPatch = {};
        let finalMlStatus = nextMlStatus;
        if (shouldRunMl && canPublishMl) {
          if (original.mlItemId && previousMlStatus !== LISTING_STATUS.UNPUBLISHED) {
            try {
              const mlUpdated = await updateOnMl(original.mlItemId, data);
              if (!draft.publishMl && previousMlStatus === LISTING_STATUS.PUBLISHED) {
                await updateMercadoLivreStatus(original.mlItemId, LISTING_STATUS.PAUSED);
                finalMlStatus = LISTING_STATUS.PAUSED;
              } else if (draft.publishMl && previousMlStatus !== LISTING_STATUS.PUBLISHED) {
                await updateMercadoLivreStatus(original.mlItemId, LISTING_STATUS.PUBLISHED);
                finalMlStatus = LISTING_STATUS.PUBLISHED;
              } else {
                finalMlStatus = previousMlStatus;
              }
              mlPatch = {
                mlItemId: mlUpdated.id ?? original.mlItemId,
                permalink: mlUpdated.permalink ?? original.permalink,
                mlCategoryId: mlUpdated.category_id ?? original.mlCategoryId,
                health: mlUpdated.health ?? original.health,
                mlSoldQuantity: mlUpdated.sold_quantity ?? original.mlSoldQuantity ?? original.soldQuantity,
                photos: Array.isArray(mlUpdated.pictures) && mlUpdated.pictures.length ? mlUpdated.pictures : data.photos,
                coverIndex: 0
              };
            } catch (error) {
              if (draft.publishMl && (error?.code === 'anuncio_nao_encontrado' || error?.code === 'publicacao_recusada')) {
                const published = await publishOnMl(data);
                finalMlStatus = LISTING_STATUS.PUBLISHED;
                mlPatch = {
                  mlItemId: published.id,
                  permalink: published.permalink,
                  mlCategoryId: published.categoryId ?? data.mlCategoryId
                };
              } else {
                throw error;
              }
            }
          } else if (draft.publishMl) {
            const published = await publishOnMl(data);
            finalMlStatus = LISTING_STATUS.PUBLISHED;
            mlPatch = {
              mlItemId: published.id,
              permalink: published.permalink,
              mlCategoryId: published.categoryId ?? data.mlCategoryId
            };
          }
        }

        const previousQsStatus = channelStatus(original, QUICKSTORE_CHANNEL);
        const nextQsStatus = shouldRunQs
          ? statusAfterSave({
              previous: previousQsStatus,
              publish: draft.publishQs,
              canPublish: canPublishQs
            })
          : previousQsStatus;
        let qsPatch = {};
        let finalQsStatus = nextQsStatus;
        if (shouldRunQs && canPublishQs) {
          if (original.qsItemId && previousQsStatus !== LISTING_STATUS.UNPUBLISHED) {
            try {
              const qsUpdated = await updateOnQs(original.qsItemId, data);
              if (!draft.publishQs && previousQsStatus === LISTING_STATUS.PUBLISHED) {
                await updateQuickStoreStatus(original.qsItemId, LISTING_STATUS.PAUSED);
                finalQsStatus = LISTING_STATUS.PAUSED;
              } else if (draft.publishQs && previousQsStatus !== LISTING_STATUS.PUBLISHED) {
                await updateQuickStoreStatus(original.qsItemId, LISTING_STATUS.PUBLISHED);
                finalQsStatus = LISTING_STATUS.PUBLISHED;
              } else {
                finalQsStatus = previousQsStatus;
              }
              const qsHttpsPhotos = (Array.isArray(qsUpdated.pictures) ? qsUpdated.pictures : []).filter((p) =>
                String(p).startsWith('https://')
              );
              qsPatch = {
                qsItemId: qsUpdated.id ?? original.qsItemId,
                qsPermalink: qsUpdated.permalink ?? original.qsPermalink,
                qsCategoryId: qsUpdated.category_id ?? original.qsCategoryId ?? data.qsCategoryId,
                qsHealth: qsUpdated.health ?? original.qsHealth,
                qsSoldQuantity: qsUpdated.sold_quantity ?? original.qsSoldQuantity ?? 0,
                ...(qsHttpsPhotos.length && !mlPatch.photos ? { photos: qsHttpsPhotos, coverIndex: 0 } : {})
              };
            } catch (error) {
              if (
                draft.publishQs &&
                previousQsStatus === LISTING_STATUS.PUBLISHED &&
                (error?.code === 'anuncio_nao_encontrado' || error?.code === 'publicacao_recusada')
              ) {
                const publishedQs = await publishOnQs(data);
                finalQsStatus = LISTING_STATUS.PUBLISHED;
                qsPatch = {
                  qsItemId: publishedQs.id,
                  qsPermalink: publishedQs.permalink,
                  qsCategoryId: publishedQs.categoryId ?? data.qsCategoryId ?? data.mlCategoryId
                };
              } else {
                throw error;
              }
            }
          } else if (draft.publishQs) {
            const publishedQs = await publishOnQs(data);
            finalQsStatus = LISTING_STATUS.PUBLISHED;
            qsPatch = {
              qsItemId: publishedQs.id,
              qsPermalink: publishedQs.permalink,
              qsCategoryId: publishedQs.categoryId ?? data.qsCategoryId ?? data.mlCategoryId
            };
          }
        }

        const updatedChannels = {
          ...original.channels,
          [PRIMARY_CHANNEL]: finalMlStatus,
          ...(original.channels?.[QUICKSTORE_CHANNEL] !== undefined || qsPatch.qsItemId || (shouldRunQs && draft.publishQs)
            ? { [QUICKSTORE_CHANNEL]: finalQsStatus }
            : {})
        };
        const updated = await updateListing(
          accountId,
          listingId,
          {
            ...data,
            ...mlPatch,
            ...qsPatch,
            suggestedPriceCents: data.suggestedPriceCents ?? original.suggestedPriceCents,
            channels: updatedChannels
          },
          { syncQuickStore: channelScope !== PRIMARY_CHANNEL }
        );
        photos.release();
        finishing.current = false;
        if (!mounted.current) return;
        setOriginal(updated);
        setPublishing(false);
        const savedToast = channelScope
          ? LISTING_EDITOR.savedChannel(CHANNEL_NAMES[channelScope] ?? channelScope)
          : LISTING_EDITOR.saved;
        showToast({ tone: TOAST_TONES.SUCCESS, ...savedToast });
        return;
      }

      // Publicar de verdade primeiro nos canais escolhidos
      const [publishedMl, publishedQs] = await Promise.all([
        willPublishMl ? publishOnMl(data) : Promise.resolve(null),
        willPublishQs ? publishOnQs(data) : Promise.resolve(null)
      ]);
      const anyPublished = Boolean(publishedMl || publishedQs);
      // O rascunho sai antes: as fotos não ocupam o espaço duas vezes na hora de gravar.
      await clearDraft(accountId);
      let created;
      try {
        created = await createListing(accountId, {
          ...data,
          mlItemId: publishedMl?.id ?? null,
          permalink: publishedMl?.permalink ?? null,
          mlCategoryId: publishedMl?.categoryId ?? data.mlCategoryId ?? null,
          qsItemId: publishedQs?.id ?? null,
          qsPermalink: publishedQs?.permalink ?? null,
          qsCategoryId: publishedQs?.categoryId ?? data.qsCategoryId ?? data.mlCategoryId ?? null,
          channels: {
            [PRIMARY_CHANNEL]: publishedMl ? LISTING_STATUS.PUBLISHED : LISTING_STATUS.UNPUBLISHED,
            ...(publishedQs ? { [QUICKSTORE_CHANNEL]: LISTING_STATUS.PUBLISHED } : {})
          }
        });
      } catch (error) {
        // Não gravou: o rascunho volta, para nada se perder.
        await saveDraft(accountId, { step: stepIndex, data: draft }).catch(() => {});
        throw error;
      }
      photos.release();
      // A comemoração só depois de gravar de verdade.
      const word = anyPublished ? LISTING_WIZARD.publish.word : LISTING_WIZARD.publish.wordSaved;
      if (celebrate) await celebrate(word).catch(() => {});
      if (!mounted.current) return;
      setPublishing(false);
      setResult({
        published: anyPublished,
        id: created.id,
        permalink: publishedMl?.permalink ?? null,
        qsPermalink: publishedQs?.permalink ?? null
      });
      publishedMl?.notices?.forEach((notice) =>
        showToast({ tone: TOAST_TONES.INFO, ...aiErrorText(notice.code, notice.message) })
      );
      publishedQs?.notices?.forEach((notice) =>
        showToast({ tone: TOAST_TONES.INFO, ...aiErrorText(notice.code, notice.message) })
      );
    } catch (error) {
      finishing.current = false;
      if (!mounted.current) return;
      setPublishing(false);
      if (error?.code === 'mercado_livre_desconectado') setConnection(null);
      if (error?.code === 'quickstore_desconectada') setQsConnection(null);
      let message = LISTING_WIZARD.errors.generic;
      if (error instanceof StorageFullError) message = LISTING_WIZARD.errors.storage;
      else if (error?.code) message = aiErrorText(error.code, error.userMessage);
      showToast({ tone: TOAST_TONES.ERROR, ...message });
    }
  }, [
    accountId,
    canPublishMl,
    canPublishQs,
    celebrate,
    channelDisconnected,
    channelScope,
    draft,
    editing,
    listingId,
    original,
    photos,
    publishOnMl,
    publishOnQs,
    publishing,
    range,
    showErrors,
    stepIndex,
    steps,
    updateOnMl,
    updateOnQs,
    validateStep,
    willPublishMl,
    willPublishQs,
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
    channelScope,
    channelDisconnected,
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
    requirementFields: fields,
    setRequirement,
    confirm,
    resume,
    range,
    priceCents,
    pricePosition,
    acceptSuggestedPrice,
    connection,
    qsConnection,
    canPublishMl,
    canPublishQs,
    willPublishMl,
    willPublishQs,
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
