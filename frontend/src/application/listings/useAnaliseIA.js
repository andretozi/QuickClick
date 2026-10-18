import { useCallback, useEffect, useRef, useState } from 'react';
import {
  confirmAnalysis,
  createAnalysis,
  fetchAnalysis,
  resumeAnalysis,
  sendExtraPhoto
} from '@/infrastructure/ai/iaService.js';
import { readingPhoto } from '@/infrastructure/media/imageResizer.js';
import { analysisPhase } from '@/domain/listings/aiAnalysis.js';

const POLL_MS = 1500;

function toError(error) {
  return { code: error?.code ?? 'erro_desconhecido', message: error?.userMessage ?? '' };
}

/**
 * Aplicação · A análise da IA de um anúncio novo.
 *
 * Cria a análise com as fotos de leitura, pergunta o andamento a cada 1,5 s enquanto ela
 * trabalha (e para quando a aba fica oculta, voltando quando ela reaparece), retoma, manda
 * foto extra e confirma os atributos. O id da análise mora no rascunho (onAnalysisId),
 * então ao recarregar a página o acompanhamento continua de onde estava.
 */
export default function useAnaliseIA({ analysisId, onAnalysisId, mounted }) {
  const [analysis, setAnalysis] = useState(null);
  const [sending, setSending] = useState(false);
  const [error, setError] = useState(null);
  const timer = useRef(null);
  const current = useRef({ id: analysisId, analysis: null });

  const stop = useCallback(() => {
    window.clearTimeout(timer.current);
    timer.current = null;
  }, []);

  const keep = useCallback(
    (data) => {
      if (!mounted.current || !data || data.id !== current.current.id) return;
      current.current.analysis = data;
      setAnalysis(data);
    },
    [mounted]
  );

  const load = useCallback(
    async (id) => {
      try {
        const data = await fetchAnalysis(id);
        keep(data);
        return data;
      } catch (failure) {
        if (!mounted.current) return null;
        if (failure?.status === 404) {
          // análise de outra conta ou que não existe mais: o rascunho segue sem ela
          current.current = { id: null, analysis: null };
          setAnalysis(null);
          onAnalysisId(null);
        }
        return null;
      }
    },
    [keep, mounted, onAnalysisId]
  );

  const follow = useCallback(
    (id) => {
      stop();
      if (document.hidden) return; // volta no visibilitychange
      timer.current = window.setTimeout(async () => {
        const data = await load(id);
        if (data?.running && current.current.id === id) follow(id);
      }, POLL_MS);
    },
    [load, stop]
  );

  const show = useCallback(
    (data) => {
      keep(data);
      if (data?.running) follow(data.id);
    },
    [follow, keep]
  );

  // Abriu (ou recarregou) com uma análise no rascunho: busca e acompanha
  useEffect(() => {
    current.current = { id: analysisId, analysis: current.current.id === analysisId ? current.current.analysis : null };
    if (!analysisId) {
      stop();
      setAnalysis(null);
      return stop;
    }
    load(analysisId).then((data) => {
      if (data?.running) follow(analysisId);
    });
    return stop;
  }, [analysisId, follow, load, stop]);

  // Aba oculta: para de perguntar. Voltou: pergunta na hora e segue
  useEffect(() => {
    const onVisibility = () => {
      if (document.hidden) {
        stop();
        return;
      }
      const { id, analysis: last } = current.current;
      if (id && last?.running) load(id).then((data) => data?.running && follow(id));
    };
    document.addEventListener('visibilitychange', onVisibility);
    return () => document.removeEventListener('visibilitychange', onVisibility);
  }, [follow, load, stop]);

  const run = useCallback(
    async (work) => {
      setSending(true);
      setError(null);
      try {
        return await work();
      } catch (failure) {
        if (mounted.current) setError(toError(failure));
        return null;
      } finally {
        if (mounted.current) setSending(false);
      }
    },
    [mounted]
  );

  /** Começa uma análise nova com as fotos de leitura (Blob). */
  const start = useCallback(
    (readingBlobs) =>
      run(async () => {
        stop();
        const id = await createAnalysis(readingBlobs);
        if (!mounted.current) return null;
        current.current = { id, analysis: null };
        onAnalysisId(id);
        const data = await load(id);
        if (data?.running) follow(id);
        return id;
      }),
    [follow, load, mounted, onAnalysisId, run, stop]
  );

  const resume = useCallback(
    (readingBlobs = null) => run(async () => show(await resumeAnalysis(current.current.id, readingBlobs))),
    [run, show]
  );

  /** Foto da etiqueta, do verso ou de um detalhe (kind: etiqueta, verso, detalhe). */
  const extraPhoto = useCallback(
    (file, kind) =>
      run(async () => {
        const blob = await readingPhoto(file);
        show(await sendExtraPhoto(current.current.id, blob, kind));
      }),
    [run, show]
  );

  const confirm = useCallback(
    (confirmation) => run(async () => show(await confirmAnalysis(current.current.id, confirmation))),
    [run, show]
  );

  const reset = useCallback(() => {
    stop();
    current.current = { id: null, analysis: null };
    setAnalysis(null);
    setError(null);
    onAnalysisId(null);
  }, [onAnalysisId, stop]);

  return {
    analysis,
    phase: analysisPhase(analysis),
    sending,
    error,
    clearError: () => setError(null),
    start,
    resume,
    extraPhoto,
    confirm,
    reset
  };
}
