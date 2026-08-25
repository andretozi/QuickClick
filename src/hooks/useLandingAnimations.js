import { useEffect } from 'react';
import { runLandingAnimations } from '../animations/landing.js';

/**
 * Hook fino que amarra o setup/teardown de src/animations/landing.js
 * ao ciclo de vida React. Toda a logica de animacao vive no runtime.
 */
export default function useLandingAnimations(rootRef, options) {
  const motion = options?.motion;
  const loopScenes = options?.loopScenes;
  const parallax = options?.parallax;
  const showTexture = options?.showTexture;
  const respectReducedMotion = options?.respectReducedMotion;

  useEffect(() => {
    const el = rootRef.current;
    if (!el) return undefined;
    return runLandingAnimations(el, {
      motion,
      loopScenes,
      parallax,
      showTexture,
      respectReducedMotion
    });
  }, [rootRef, motion, loopScenes, parallax, showTexture, respectReducedMotion]);
}
