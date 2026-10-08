import { useLayoutEffect } from 'react';
import { runDialogEntrance, runDialogStep } from '@/infrastructure/animation/marketplaces/dialog.js';

/**
 * Aplicação · Animações do diálogo de conexão: a entrada (uma vez) e cada etapa
 * (confirmar, autorizando, erro). Rodam antes da pintura, sem piscar.
 */
export default function useDialogAnimations(dialogRef, stepRef, step) {
  useLayoutEffect(() => (dialogRef.current ? runDialogEntrance(dialogRef.current) : undefined), [dialogRef]);
  useLayoutEffect(() => (stepRef.current ? runDialogStep(stepRef.current) : undefined), [stepRef, step]);
}
