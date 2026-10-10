import { useCallback } from 'react';
import { focusOption } from '@/infrastructure/browser/focus.js';

/**
 * Aplicação · Setas do teclado num grupo de opções (abas, seletor segmentado).
 * Setas andam e já escolhem (com o foco junto); Home e End vão para as pontas.
 * orientation: 'horizontal' (← →) | 'vertical' (↑ ↓) | 'both'
 */
export default function useRovingKeys({ options, value, onChange, containerRef, orientation = 'horizontal' }) {
  return useCallback(
    (event) => {
      const forward = { horizontal: ['ArrowRight'], vertical: ['ArrowDown'], both: ['ArrowRight', 'ArrowDown'] }[orientation];
      const backward = { horizontal: ['ArrowLeft'], vertical: ['ArrowUp'], both: ['ArrowLeft', 'ArrowUp'] }[orientation];
      const index = Math.max(0, options.findIndex((option) => option.value === value));
      let next = null;
      if (forward.includes(event.key)) next = (index + 1) % options.length;
      else if (backward.includes(event.key)) next = (index - 1 + options.length) % options.length;
      else if (event.key === 'Home') next = 0;
      else if (event.key === 'End') next = options.length - 1;
      if (next === null) return;
      event.preventDefault();
      onChange(options[next].value);
      focusOption(containerRef.current, next);
    },
    [containerRef, onChange, options, orientation, value]
  );
}
