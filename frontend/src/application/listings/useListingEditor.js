import { useCallback, useEffect, useMemo, useRef, useState } from 'react';
import useMountedRef from '@/application/ui/useMountedRef.js';
import useSession from '@/application/session/useSession.js';
import useDraftAutosave from '@/application/listings/useDraftAutosave.js';
import useListingPhotos from '@/application/listings/useListingPhotos.js';
import useAnaliseIA from '@/application/listings/useAnaliseIA.js';
import useCotaIA from '@/application/listings/useCotaIA.js';
import { showToast, TOAST_TONES } from '@/application/feedback/toastStore.js';
import { CHANNEL_ADAPTERS, getChannelAdapter } from '@/application/listings/channels/channelRegistry.js';
import {
  createListing,
  getListing,
  updateListing
} from '@/infrastructure/storage/listingsRepository.js';
import { safeHttpsUrl } from '@/infrastructure/storage/listingRecord.js';
import { fetchConnectedMarketplaces } from '@/infrastructure/marketplaces/marketplacesService.js';
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

/** Uma marca das fotos que foram para a análise (fotos novas pedem análise nova). */
const photosKey = (photos) => photos.map((photo) => photo.slice(-24)).join('|');

/**
 * Aplicação · Caso de uso "criar anúncio" e "ver e editar anúncio".
 *
 * Criar: fotos → análise da IA (no back, em etapas) → confirmar o que a IA viu → detalhes
 * (título e descrição escritos pela IA) → preço (faixa real) → canais → publicar (o back
 * monta o anúncio do Mercado Livre e da QuickStore). Editar: só os passos do anúncio, sem IA,
 * sincronizando com os canais conectados quando o anúncio já está publicado.
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
        const connBySlug = {
          [PRIMARY_CHANNEL]: connections.find((item) => item.slug === PRIMARY_CHANNEL) ?? null,
          [QUICKSTORE_CHANNEL]: connections.find((item) => item.slug === QUICKSTORE_CHANNEL) ?? null
        };
        if (editing) {
          let listing = await getListing(accountId, listingId);
          for (const adapter of Object.values(CHANNEL_ADAPTERS)) {
            const shouldSync = !channelScope || channelScope === adapter.slug;
            if (!shouldSync || !connBySlug[adapter.slug]) continue;
            try {
              listing = await adapter.reconcileIfNeeded(accountId, listing);
              if (adapter.getItemId(listing)) {
                listing = await adapter.syncOne(accountId, listing);
              }
            } catch (error) {
              if (error?.code === adapter.disconnectedCode) connBySlug[adapter.slug] = null;
            }
          }
          if (!mounted.current) return;
          setConnection(connBySlug[PRIMARY_CHANNEL]);
          setQsConnection(connBySlug[QUICKSTORE_CHANNEL]);
          setOriginal(listing);
          const baseDraft = { ...EMPTY_DRAFT, ...toDraft(listing) };
          if (channelScope) {
            baseDraft.priceInput = centsToInput(getChannelAdapter(channelScope).getPriceCents(listing));
          }
          setDraft(baseDraft);
          setVisited(EDIT_STEPS.length - 1);
        } else {
          const mlConn = connBySlug[PRIMARY_CHANNEL];
          const qsConn = connBySlug[QUICKSTORE_CHANNEL];
          setConnection(mlConn);
          setQsConnection(qsConn);
          const saved = await getDraft(accountId);
          if (!mounted.current) return;
          if (saved?.data && !isBlankDraft({ ...EMPTY_DRAFT, ...saved.data })) {
            const restored = { ...EMPTY_DRAFT, ...saved.data };
            if (saved.data.publishMl === undefined || saved.data.publishMl === null) {
              restored.publishMl = Boolean(mlConn);
            }
            if (saved.data.publishQs === undefined || saved.data.publishQs === null) {
              restored.publishQs = Boolean(qsConn);
            } else if (!mlConn && qsConn && restored.publishMl === true && restored.publishQs === false) {
              restored.publishMl = false;
              restored.publishQs = true;
            }
            setDraft(restored);
            // resultado já aplicado antes de recarregar não entra de novo por cima do que o vendedor mexeu
            appliedResult.current = restored.resultAppliedFor ?? null;
            advanced.current = restored.analysisId;
            setStepIndex(Math.min(saved.step ?? 0, WIZARD_STEPS.length - 1));
            setVisited(Math.min(saved.step ?? 0, WIZARD_STEPS.length - 1));
            showToast({ tone: TOAST_TONES.INFO, ...LISTING_WIZARD.draftRestored });
          } else {
            setDraft((current) => ({
              ...current,
              publishMl: Boolean(mlConn),
              publishQs: Boolean(qsConn)
            }));
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

  const prepareChannelInputs = useCallback(
    (channelSlug, data) => {
      const adapter = getChannelAdapter(channelSlug);
      const cover = data.photos[data.coverIndex] ?? data.photos[0];
      const ordered = [cover, ...data.photos.filter((photo) => photo !== cover)];
      const keptPhotos = ordered.filter((p) => String(p).startsWith('https://'));
      const categoryFallback =
        channelSlug === QUICKSTORE_CHANNEL
          ? (original?.qsCategoryId ?? original?.mlCategoryId)
          : original?.mlCategoryId;
      return adapter.buildPayload(
        { ...(original ?? {}), ...(editing && listingId ? { id: listingId } : {}) },
        {
          title: data.title,
          description: data.description,
          priceCents: data.priceCents,
          stock: data.stock,
          condition: data.condition,
          attributes: draft.attributes,
          analysisId: draft.analysisId,
          mlCategoryId: draft.mlCategoryId ?? categoryFallback,
          keptPhotos,
          photoBlobs: photos.readingBlobs(ordered)
        }
      );
    },
    [draft.analysisId, draft.attributes, draft.mlCategoryId, editing, listingId, original, photos]
  );

  const publishOnChannel = useCallback(
    async (channelSlug, data) => {
      const adapter = getChannelAdapter(channelSlug);
      const { payload, photoBlobs } = prepareChannelInputs(channelSlug, data);
      return adapter.publish(payload, photoBlobs);
    },
    [prepareChannelInputs]
  );

  const updateOnChannel = useCallback(
    async (channelSlug, itemId, data) => {
      const adapter = getChannelAdapter(channelSlug);
      const { payload, photoBlobs } = prepareChannelInputs(channelSlug, data);
      return adapter.update(itemId, payload, photoBlobs);
    },
    [prepareChannelInputs]
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
      const scopedAdapter = getChannelAdapter(channelScope);
      const hasRemoteItem = Boolean(scopedAdapter.getItemId(original));
      const wantsPublish = channelScope === QUICKSTORE_CHANNEL ? draft.publishQs : draft.publishMl;
      if (hasRemoteItem || wantsPublish) {
        showToast({
          tone: TOAST_TONES.ERROR,
          ...aiErrorText(scopedAdapter.disconnectedCode)
        });
        return;
      }
    }

    const data = toListingData(draft, range.status === 'ready' ? range : null);
    if (data.stock === 0) {
      const creatingNewMl = (!editing || !original?.mlItemId) && willPublishMl;
      const creatingNewQs = (!editing || !original?.qsItemId) && willPublishQs;
      const reactivatingMl =
        editing &&
        (!channelScope || channelScope === PRIMARY_CHANNEL) &&
        Boolean(original?.mlItemId) &&
        channelStatus(original, PRIMARY_CHANNEL) !== LISTING_STATUS.PUBLISHED &&
        draft.publishMl &&
        canPublishMl;
      const reactivatingQs =
        editing &&
        (!channelScope || channelScope === QUICKSTORE_CHANNEL) &&
        Boolean(original?.qsItemId) &&
        channelStatus(original, QUICKSTORE_CHANNEL) !== LISTING_STATUS.PUBLISHED &&
        draft.publishQs &&
        canPublishQs;

      if (creatingNewMl || creatingNewQs || reactivatingMl || reactivatingQs) {
        const detailsIdx = steps.indexOf('details');
        if (detailsIdx >= 0) setStepIndex(detailsIdx);
        showErrors({ stock: 'Informe pelo menos 1 unidade em estoque para publicar ou reativar o anúncio.' });
        return;
      }
    }

    setPublishing(true);
    finishing.current = true;
    try {
      if (editing) {
        const mlAdapter = getChannelAdapter(PRIMARY_CHANNEL);
        const qsAdapter = getChannelAdapter(QUICKSTORE_CHANNEL);
        const shouldRunMl = !channelScope || channelScope === PRIMARY_CHANNEL;
        const shouldRunQs = !channelScope || channelScope === QUICKSTORE_CHANNEL;
        const effectivePublishMl = data.stock === 0 ? false : draft.publishMl;
        const effectivePublishQs = data.stock === 0 ? false : draft.publishQs;

        const previousMlStatus = channelStatus(original, PRIMARY_CHANNEL);
        const nextMlStatus = shouldRunMl
          ? statusAfterSave({
              previous: previousMlStatus,
              publish: effectivePublishMl,
              canPublish: canPublishMl
            })
          : previousMlStatus;
        let mlPatch = {};
        let finalMlStatus = nextMlStatus;
        if (shouldRunMl && canPublishMl) {
          const mlItemId = mlAdapter.getItemId(original);
          if (mlItemId) {
            try {
              const mlUpdated = await updateOnChannel(PRIMARY_CHANNEL, mlItemId, data);
              if (!effectivePublishMl && previousMlStatus === LISTING_STATUS.PUBLISHED) {
                await mlAdapter.setStatus(null, null, mlItemId, LISTING_STATUS.PAUSED);
                finalMlStatus = LISTING_STATUS.PAUSED;
              } else if (effectivePublishMl && previousMlStatus !== LISTING_STATUS.PUBLISHED) {
                await mlAdapter.setStatus(null, null, mlItemId, LISTING_STATUS.PUBLISHED);
                finalMlStatus = LISTING_STATUS.PUBLISHED;
              } else {
                finalMlStatus = previousMlStatus;
              }
              mlPatch = mlAdapter.toUpdatedPatch(original, mlUpdated, data.photos);
            } catch (error) {
              if (effectivePublishMl && error?.code === 'anuncio_nao_encontrado') {
                const published = await publishOnChannel(PRIMARY_CHANNEL, data);
                finalMlStatus = LISTING_STATUS.PUBLISHED;
                mlPatch = {
                  mlItemId: published.id,
                  permalink: safeHttpsUrl(published.permalink),
                  mlCategoryId: published.categoryId ?? data.mlCategoryId
                };
              } else {
                throw error;
              }
            }
          } else if (effectivePublishMl) {
            const published = await publishOnChannel(PRIMARY_CHANNEL, data);
            finalMlStatus = LISTING_STATUS.PUBLISHED;
            mlPatch = {
              mlItemId: published.id,
              permalink: safeHttpsUrl(published.permalink),
              mlCategoryId: published.categoryId ?? data.mlCategoryId
            };
          }
        }

        const previousQsStatus = channelStatus(original, QUICKSTORE_CHANNEL);
        const nextQsStatus = shouldRunQs
          ? statusAfterSave({
              previous: previousQsStatus,
              publish: effectivePublishQs,
              canPublish: canPublishQs
            })
          : previousQsStatus;
        let qsPatch = {};
        let finalQsStatus = nextQsStatus;
        if (shouldRunQs && canPublishQs) {
          const qsItemId = qsAdapter.getItemId(original);
          if (qsItemId) {
            try {
              const qsUpdated = await updateOnChannel(QUICKSTORE_CHANNEL, qsItemId, data);
              if (!effectivePublishQs && previousQsStatus === LISTING_STATUS.PUBLISHED) {
                await qsAdapter.setStatus(null, null, qsItemId, LISTING_STATUS.PAUSED);
                finalQsStatus = LISTING_STATUS.PAUSED;
              } else if (effectivePublishQs && previousQsStatus !== LISTING_STATUS.PUBLISHED) {
                await qsAdapter.setStatus(null, null, qsItemId, LISTING_STATUS.PUBLISHED);
                finalQsStatus = LISTING_STATUS.PUBLISHED;
              } else {
                finalQsStatus = previousQsStatus;
              }
              qsPatch = qsAdapter.toUpdatedPatch(original, qsUpdated, data.photos, !mlPatch.photos);
            } catch (error) {
              if (effectivePublishQs && error?.code === 'anuncio_nao_encontrado') {
                const publishedQs = await publishOnChannel(QUICKSTORE_CHANNEL, data);
                finalQsStatus = LISTING_STATUS.PUBLISHED;
                qsPatch = {
                  qsItemId: publishedQs.id,
                  qsPermalink: safeHttpsUrl(publishedQs.permalink),
                  qsCategoryId: publishedQs.categoryId ?? data.qsCategoryId ?? data.mlCategoryId
                };
              } else {
                throw error;
              }
            }
          } else if (effectivePublishQs) {
            const publishedQs = await publishOnChannel(QUICKSTORE_CHANNEL, data);
            finalQsStatus = LISTING_STATUS.PUBLISHED;
            qsPatch = {
              qsItemId: publishedQs.id,
              qsPermalink: safeHttpsUrl(publishedQs.permalink),
              qsCategoryId: publishedQs.categoryId ?? data.qsCategoryId ?? data.mlCategoryId
            };
          }
        }

        const updatedChannels = {
          ...original.channels,
          [PRIMARY_CHANNEL]: finalMlStatus,
          ...(original.channels?.[QUICKSTORE_CHANNEL] !== undefined || qsPatch.qsItemId || (shouldRunQs && effectivePublishQs)
            ? { [QUICKSTORE_CHANNEL]: finalQsStatus }
            : {})
        };

        const priceFields = channelScope
          ? getChannelAdapter(channelScope).buildPriceFieldsWhenScoped(original, data.priceCents)
          : {
              priceCents: data.priceCents,
              mlPriceCents: data.priceCents,
              qsPriceCents: data.priceCents
            };

        const updated = await updateListing(
          accountId,
          listingId,
          {
            ...data,
            ...priceFields,
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
          ? LISTING_EDITOR.savedChannel(getChannelAdapter(channelScope).name)
          : LISTING_EDITOR.saved;
        showToast({ tone: TOAST_TONES.SUCCESS, ...savedToast });
        return;
      }

      // Publicar de verdade primeiro nos canais escolhidos
      const [publishedMl, publishedQs] = await Promise.all([
        willPublishMl ? publishOnChannel(PRIMARY_CHANNEL, data) : Promise.resolve(null),
        willPublishQs ? publishOnChannel(QUICKSTORE_CHANNEL, data) : Promise.resolve(null)
      ]);
      const anyPublished = Boolean(publishedMl || publishedQs);
      // O rascunho sai antes: as fotos não ocupam o espaço duas vezes na hora de gravar.
      await clearDraft(accountId);
      let created;
      try {
        created = await createListing(accountId, {
          ...data,
          mlItemId: publishedMl?.id ?? null,
          permalink: safeHttpsUrl(publishedMl?.permalink),
          mlCategoryId: publishedMl?.categoryId ?? data.mlCategoryId ?? null,
          qsItemId: publishedQs?.id ?? null,
          qsPermalink: safeHttpsUrl(publishedQs?.permalink),
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
        showToast({
          tone: TOAST_TONES.INFO,
          ...aiErrorText(notice.code, notice.message, { channel: notice.channel ?? PRIMARY_CHANNEL })
        })
      );
      publishedQs?.notices?.forEach((notice) =>
        showToast({
          tone: TOAST_TONES.INFO,
          ...aiErrorText(notice.code, notice.message, { channel: notice.channel ?? QUICKSTORE_CHANNEL })
        })
      );
    } catch (error) {
      finishing.current = false;
      if (!mounted.current) return;
      setPublishing(false);
      if (error?.code === getChannelAdapter(PRIMARY_CHANNEL).disconnectedCode) setConnection(null);
      if (error?.code === getChannelAdapter(QUICKSTORE_CHANNEL).disconnectedCode) setQsConnection(null);
      let message = LISTING_WIZARD.errors.generic;
      if (error instanceof StorageFullError) message = LISTING_WIZARD.errors.storage;
      else if (error?.code) {
        const inferredChannel =
          error.channel ??
          channelScope ??
          (willPublishQs && !willPublishMl
            ? QUICKSTORE_CHANNEL
            : willPublishMl && !willPublishQs
              ? PRIMARY_CHANNEL
              : null);
        message = aiErrorText(error.code, error.userMessage, {
          channel: inferredChannel,
          details: error.details
        });
      }
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
    publishOnChannel,
    publishing,
    range,
    showErrors,
    stepIndex,
    steps,
    updateOnChannel,
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
    setDraft({
      ...EMPTY_DRAFT,
      publishMl: Boolean(connection),
      publishQs: Boolean(qsConnection)
    });
    setErrors({});
    setStepIndex(0);
    setVisited(0);
    setResult(null);
    clearSavedAt();
  }, [accountId, ai, clearSavedAt, connection, mounted, photos, qsConnection]);

  const linkedIds = useMemo(
    () => ({
      mlItemId: original?.mlItemId ?? null,
      qsItemId: original?.qsItemId ?? null
    }),
    [original?.mlItemId, original?.qsItemId]
  );

  return {
    editing,
    channelScope,
    channelDisconnected,
    linkedIds,
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
