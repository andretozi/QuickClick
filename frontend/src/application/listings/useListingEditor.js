import { useCallback, useEffect, useMemo, useRef, useState } from 'react';
import useSession from '@/application/session/useSession.js';
import { showToast, TOAST_TONES } from '@/application/feedback/toastStore.js';
import { createListing, getListing, updateListing } from '@/infrastructure/storage/listingsRepository.js';
import { listConnections } from '@/infrastructure/storage/connectionsRepository.js';
import { clearDraft, getDraft, saveDraft } from '@/infrastructure/storage/draftsRepository.js';
import { StorageFullError } from '@/infrastructure/storage/localStore.js';
import { resizeImage } from '@/infrastructure/media/imageResizer.js';
import { suggestListing, suggestPriceRange } from '@/infrastructure/ai/suggestionService.js';
import { focusFirstInvalid } from '@/infrastructure/browser/focus.js';
import {
  LISTING_LIMITS,
  LISTING_STATUS,
  PRIMARY_CHANNEL,
  WIZARD_STEPS,
  listingStatus,
  validateListingStep
} from '@/domain/listings/listingRules.js';
import { centsToInput, parseMoney } from '@/domain/format/format.js';
import { LISTING_EDITOR, LISTING_WIZARD } from '@/domain/content/listingContent.js';

const EMPTY_DRAFT = {
  photos: [],
  coverIndex: 0,
  title: '',
  description: '',
  category: '',
  condition: 'new',
  stock: '1',
  priceInput: '',
  publishMl: true
};

const AUTOSAVE_MS = 500;
const AI_STEP_MS = 700;

/** Rascunho do assistente → campos do anúncio guardado. */
function toListingData(draft, range) {
  return {
    title: draft.title,
    description: draft.description,
    category: draft.category,
    condition: draft.condition,
    priceCents: parseMoney(draft.priceInput),
    suggestedPriceCents: range?.suggestedCents ?? null,
    stock: Number(draft.stock),
    photos: draft.photos,
    coverIndex: Math.min(draft.coverIndex, Math.max(0, draft.photos.length - 1))
  };
}

/** Anúncio guardado → rascunho do formulário (para ver e editar). */
function toDraft(listing) {
  return {
    photos: listing.photos,
    coverIndex: listing.coverIndex,
    title: listing.title,
    description: listing.description,
    category: listing.category,
    condition: listing.condition,
    stock: String(listing.stock),
    priceInput: centsToInput(listing.priceCents),
    publishMl: listingStatus(listing) !== LISTING_STATUS.UNPUBLISHED
  };
}

/** Ainda não tem nada digitado nem foto: não vale a pena guardar como rascunho. */
const isBlankDraft = (draft) => !draft.photos.length && !draft.title.trim() && !draft.description.trim();

const timeNow = () => new Date().toLocaleTimeString('pt-BR', { hour: '2-digit', minute: '2-digit' });

/**
 * Aplicação · Caso de uso "criar anúncio" e "ver e editar anúncio".
 *
 * Guarda o rascunho e o passo do assistente (fotos, detalhes, preço, canais e publicar),
 * salva o rascunho sozinho (só no "criar"), reduz as fotos, chama a IA simulada (anúncio
 * e faixa de preço) e publica ou salva. A tela só desenha o que este hook devolve.
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
  const [photosBusy, setPhotosBusy] = useState(false);
  const [photoError, setPhotoError] = useState(null);
  const [ai, setAi] = useState({ status: 'idle', step: 0 });
  const [range, setRange] = useState({ status: 'idle' });
  const [savedAt, setSavedAt] = useState(null);
  const [storageFull, setStorageFull] = useState(false);
  const [publishing, setPublishing] = useState(false);
  const [result, setResult] = useState(null);
  const [visited, setVisited] = useState(0);

  const mounted = useRef(true);
  const formRef = useRef(null);
  const loaded = useRef(false);

  useEffect(() => {
    mounted.current = true;
    return () => {
      mounted.current = false;
    };
  }, []);

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
  }, [accountId, editing, listingId]);

  // ---------- Rascunho salvo sozinho (só no criar) ----------
  useEffect(() => {
    if (editing || !loaded.current || result || !accountId || isBlankDraft(draft)) return undefined;
    const timer = window.setTimeout(async () => {
      try {
        await saveDraft(accountId, { step: stepIndex, data: draft });
        if (!mounted.current) return;
        setSavedAt(timeNow());
        setStorageFull(false);
      } catch (error) {
        if (mounted.current && error instanceof StorageFullError) setStorageFull(true);
      }
    }, AUTOSAVE_MS);
    return () => window.clearTimeout(timer);
  }, [accountId, draft, editing, result, stepIndex]);

  const step = WIZARD_STEPS[stepIndex];

  // ---------- Faixa de preço (IA simulada) ----------
  useEffect(() => {
    if (step !== 'price' || !draft.category) return;
    let alive = true;
    setRange({ status: 'loading' });
    suggestPriceRange({ category: draft.category, condition: draft.condition, title: draft.title }).then((value) => {
      if (alive && mounted.current) setRange({ status: 'ready', ...value });
    });
    return () => {
      alive = false;
    };
  }, [step, draft.category, draft.condition, draft.title]);

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

  // ---------- Fotos ----------
  const addFiles = useCallback(
    async (fileList) => {
      const files = Array.from(fileList ?? []);
      if (!files.length) return;
      setPhotoError(null);
      const room = LISTING_LIMITS.PHOTOS_MAX - draft.photos.length;
      if (room <= 0) {
        setPhotoError('full');
        return;
      }
      setPhotosBusy(true);
      const added = [];
      let invalid = false;
      for (const file of files.slice(0, room)) {
        try {
          added.push(await resizeImage(file));
        } catch {
          invalid = true;
        }
      }
      if (!mounted.current) return;
      setPhotosBusy(false);
      if (invalid) setPhotoError('invalid');
      else if (files.length > room) setPhotoError('full');
      if (added.length) {
        setDraft((current) => ({ ...current, photos: [...current.photos, ...added].slice(0, LISTING_LIMITS.PHOTOS_MAX) }));
        setErrors((current) => ({ ...current, photos: undefined }));
      }
    },
    [draft.photos.length]
  );

  const removePhoto = useCallback((index) => {
    setPhotoError(null);
    setDraft((current) => {
      const photos = current.photos.filter((_, i) => i !== index);
      const coverIndex =
        index === current.coverIndex ? 0 : index < current.coverIndex ? current.coverIndex - 1 : current.coverIndex;
      return { ...current, photos, coverIndex: Math.min(coverIndex, Math.max(0, photos.length - 1)) };
    });
  }, []);

  const setCover = useCallback((index) => update({ coverIndex: index }), [update]);

  // ---------- IA simulada: preenche os detalhes a partir da capa ----------
  const suggest = useCallback(async () => {
    if (ai.status === 'working') return;
    const photo = draft.photos[draft.coverIndex] ?? draft.photos[0];
    if (!photo) {
      setAi({ status: 'needs-photo', step: 0 });
      return;
    }
    setAi({ status: 'working', step: 0 });
    const ticker = window.setInterval(() => {
      setAi((current) => (current.status === 'working' ? { ...current, step: Math.min(current.step + 1, 2) } : current));
    }, AI_STEP_MS);
    try {
      const suggestion = await suggestListing({ photo });
      if (!mounted.current) return;
      update(suggestion);
      setAi({ status: 'done', step: 2 });
      showToast({ tone: TOAST_TONES.SUCCESS, ...LISTING_WIZARD.details.ai.done });
    } finally {
      window.clearInterval(ticker);
    }
  }, [ai.status, draft.coverIndex, draft.photos, update]);

  // ---------- Preço ----------
  const acceptSuggestedPrice = useCallback(() => {
    if (range.status === 'ready') update({ priceInput: centsToInput(range.suggestedCents) });
  }, [range, update]);

  const priceCents = parseMoney(draft.priceInput);

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
    const data = toListingData(draft, range.status === 'ready' ? range : null);
    try {
      if (editing) {
        const previous = listingStatus(original);
        const nextStatus = !draft.publishMl
          ? LISTING_STATUS.UNPUBLISHED
          : previous === LISTING_STATUS.UNPUBLISHED
            ? canPublishMl
              ? LISTING_STATUS.PUBLISHED
              : LISTING_STATUS.UNPUBLISHED
            : previous;
        const updated = await updateListing(accountId, listingId, {
          ...data,
          suggestedPriceCents: data.suggestedPriceCents ?? original.suggestedPriceCents,
          channels: { ...original.channels, [PRIMARY_CHANNEL]: nextStatus }
        });
        if (!mounted.current) return;
        setOriginal(updated);
        setPublishing(false);
        showToast({ tone: TOAST_TONES.SUCCESS, ...LISTING_EDITOR.saved });
        return;
      }
      const word = willPublish ? LISTING_WIZARD.publish.word : LISTING_WIZARD.publish.wordSaved;
      const [created] = await Promise.all([
        createListing(accountId, {
          ...data,
          channels: { [PRIMARY_CHANNEL]: willPublish ? LISTING_STATUS.PUBLISHED : LISTING_STATUS.UNPUBLISHED }
        }),
        celebrate ? celebrate(word) : Promise.resolve()
      ]);
      await clearDraft(accountId);
      if (!mounted.current) return;
      setPublishing(false);
      setResult({ published: willPublish, id: created.id });
    } catch (error) {
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
    validateStep,
    willPublish
  ]);

  /** Joga o rascunho fora e volta para o primeiro passo. */
  const restart = useCallback(async () => {
    if (accountId) await clearDraft(accountId);
    if (!mounted.current) return;
    setDraft(EMPTY_DRAFT);
    setErrors({});
    setStepIndex(0);
    setVisited(0);
    setResult(null);
    setAi({ status: 'idle', step: 0 });
    setRange({ status: 'idle' });
    setSavedAt(null);
  }, [accountId]);

  const pricePosition = useMemo(() => {
    if (range.status !== 'ready' || priceCents === null) return null;
    if (priceCents < range.minCents) return 'below';
    if (priceCents > range.maxCents) return 'above';
    return 'fair';
  }, [priceCents, range]);

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
    photos: { add: addFiles, remove: removePhoto, setCover, busy: photosBusy, error: photoError },
    ai,
    suggest,
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
    original
  };
}
