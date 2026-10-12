import { useCallback, useEffect, useRef, useState } from 'react';
import useMountedRef from '@/application/ui/useMountedRef.js';
import useSession from '@/application/session/useSession.js';
import useDraftAutosave from '@/application/listings/useDraftAutosave.js';
import usePriceRange from '@/application/listings/usePriceRange.js';
import useListingPhotos from '@/application/listings/useListingPhotos.js';
import useAiDetails from '@/application/listings/useAiDetails.js';
import { showToast, TOAST_TONES } from '@/application/feedback/toastStore.js';
import { createListing, getListing, updateListing } from '@/infrastructure/storage/listingsRepository.js';
import { listConnections } from '@/infrastructure/storage/connectionsRepository.js';
import { clearDraft, getDraft, saveDraft } from '@/infrastructure/storage/draftsRepository.js';
import { StorageFullError } from '@/infrastructure/storage/localStore.js';
import { focusFirstInvalid } from '@/infrastructure/browser/focus.js';
import {
  LISTING_STATUS,
  PRIMARY_CHANNEL,
  WIZARD_STEPS,
  listingStatus,
  validateListingStep
} from '@/domain/listings/listingRules.js';
import { EMPTY_DRAFT, isBlankDraft, statusAfterSave, toDraft, toListingData } from '@/domain/listings/listingDraft.js';
import { parseMoney } from '@/domain/format/format.js';
import { LISTING_EDITOR, LISTING_WIZARD } from '@/domain/content/listingContent.js';

/**
 * Aplicação · Caso de uso "criar anúncio" e "ver e editar anúncio".
 *
 * Guarda o rascunho e o passo do assistente (fotos, detalhes, preço, canais e publicar)
 * e publica ou salva. As partes com estado próprio moram em hooks vizinhos: fotos
 * (useListingPhotos), IA dos detalhes (useAiDetails), faixa de preço (usePriceRange) e
 * rascunho salvo sozinho (useDraftAutosave). A tela só desenha o que este hook devolve.
 *
 * - listingId: com id, abre o anúncio para editar; sem id, é um anúncio novo
 * - celebrate(word): animação de publicar (cursor, clique e partículas); devolve uma Promise
 */
export default function useListingEditor({ listingId, celebrate }) {
  const { account } = useSession();
  const accountId = account?.id;
  const editing = Boolean(listingId);

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

  // ---------- Carregar ----------
  useEffect(() => {
    if (!accountId) return;
    loaded.current = false;
    (async () => {
      try {
        const connections = await listConnections(accountId);
        if (!mounted.current) return;
        setConnection(connections.find((item) => item.slug === PRIMARY_CHANNEL) ?? null);
        if (editing) {
          const listing = await getListing(accountId, listingId);
          if (!mounted.current) return;
          setOriginal(listing);
          setDraft(toDraft(listing));
          setVisited(WIZARD_STEPS.length - 1);
        } else {
          const saved = await getDraft(accountId);
          if (!mounted.current) return;
          if (saved?.data && !isBlankDraft({ ...EMPTY_DRAFT, ...saved.data })) {
            setDraft({ ...EMPTY_DRAFT, ...saved.data });
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

  const step = WIZARD_STEPS[stepIndex];

  // ---------- Campos ----------
  const update = useCallback((patch) => {
    setDraft((current) => ({ ...current, ...patch }));
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

  // ---------- Faixa de preço, fotos e IA ----------
  const price = usePriceRange({ active: step === 'price', draft, update, mounted });
  const { range, reset: resetRange } = price;
  const photos = useListingPhotos({ photoCount: draft.photos.length, setDraft, setErrors, update, mounted });
  const { ai, suggest, reset: resetAi } = useAiDetails({ draft, update, mounted });

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
      if (index < 0 || index >= WIZARD_STEPS.length) return;
      // para a frente, cada passo do caminho precisa estar certo
      for (let i = stepIndex; i < index; i += 1) {
        const found = validateStep(WIZARD_STEPS[i]);
        if (Object.keys(found).length) {
          setStepIndex(i);
          showErrors(found);
          return;
        }
      }
      setErrors({});
      setStepIndex(index);
      setVisited((current) => Math.max(current, index));
    },
    [showErrors, stepIndex, validateStep]
  );

  const next = useCallback(() => goTo(stepIndex + 1), [goTo, stepIndex]);
  const back = useCallback(() => goTo(stepIndex - 1), [goTo, stepIndex]);

  // ---------- Publicar ou salvar ----------
  const canPublishMl = Boolean(connection);
  const willPublish = draft.publishMl && canPublishMl;

  const finish = useCallback(async () => {
    if (publishing) return;
    for (let i = 0; i < WIZARD_STEPS.length; i += 1) {
      const found = validateStep(WIZARD_STEPS[i]);
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
        const nextStatus = statusAfterSave({
          previous: listingStatus(original),
          publish: draft.publishMl,
          canPublish: canPublishMl
        });
        const updated = await updateListing(accountId, listingId, {
          ...data,
          suggestedPriceCents: data.suggestedPriceCents ?? original.suggestedPriceCents,
          channels: { ...original.channels, [PRIMARY_CHANNEL]: nextStatus }
        });
        finishing.current = false;
        if (!mounted.current) return;
        setOriginal(updated);
        setPublishing(false);
        showToast({ tone: TOAST_TONES.SUCCESS, ...LISTING_EDITOR.saved });
        return;
      }
      // O rascunho sai antes: as fotos não ocupam o espaço duas vezes na hora de gravar.
      await clearDraft(accountId);
      let created;
      try {
        created = await createListing(accountId, {
          ...data,
          channels: { [PRIMARY_CHANNEL]: willPublish ? LISTING_STATUS.PUBLISHED : LISTING_STATUS.UNPUBLISHED }
        });
      } catch (error) {
        // Não gravou: o rascunho volta, para nada se perder.
        await saveDraft(accountId, { step: stepIndex, data: draft }).catch(() => {});
        throw error;
      }
      // A comemoração só depois de gravar de verdade.
      const word = willPublish ? LISTING_WIZARD.publish.word : LISTING_WIZARD.publish.wordSaved;
      if (celebrate) await celebrate(word).catch(() => {});
      if (!mounted.current) return;
      setPublishing(false);
      setResult({ published: willPublish, id: created.id });
    } catch (error) {
      finishing.current = false;
      if (!mounted.current) return;
      setPublishing(false);
      const message = error instanceof StorageFullError ? LISTING_WIZARD.errors.storage : LISTING_WIZARD.errors.generic;
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
    publishing,
    range,
    showErrors,
    stepIndex,
    validateStep,
    willPublish,
    mounted
  ]);

  /** Joga o rascunho fora e volta para o primeiro passo. */
  const { clearSavedAt } = autosave;
  const restart = useCallback(async () => {
    if (accountId) await clearDraft(accountId);
    if (!mounted.current) return;
    finishing.current = false;
    setDraft(EMPTY_DRAFT);
    setErrors({});
    setStepIndex(0);
    setVisited(0);
    setResult(null);
    resetAi();
    resetRange();
    clearSavedAt();
  }, [accountId, mounted, resetAi, resetRange, clearSavedAt]);

  return {
    editing,
    status,
    steps: WIZARD_STEPS,
    step,
    stepIndex,
    visited,
    goTo,
    next,
    back,
    draft,
    errors,
    setField,
    update,
    formRef,
    photos,
    ai,
    suggest,
    range,
    priceCents: price.priceCents,
    pricePosition: price.position,
    acceptSuggestedPrice: price.acceptSuggested,
    connection,
    canPublishMl,
    willPublish,
    finish,
    publishing,
    result,
    restart,
    savedAt: autosave.savedAt,
    storageFull: autosave.storageFull,
    original
  };
}
