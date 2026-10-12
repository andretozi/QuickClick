import { useCallback, useState } from 'react';

/**
 * Aplicação · Qual ponto de um gráfico está em foco (mouse, toque ou teclado).
 * - count: quantos pontos o gráfico tem
 * - onPointerMove: acha o ponto mais perto do ponteiro, pela posição horizontal
 * - onKeyDown: setas, Home e End andam pelos pontos (o gráfico é focável)
 */
export default function useChartHover(count) {
  const [active, setActive] = useState(null);

  const onPointerMove = useCallback(
    (event) => {
      const box = event.currentTarget.getBoundingClientRect();
      const ratio = (event.clientX - box.left) / box.width;
      setActive(Math.max(0, Math.min(count - 1, Math.round(ratio * (count - 1)))));
    },
    [count]
  );

  const onKeyDown = useCallback(
    (event) => {
      const moves = { ArrowRight: 1, ArrowLeft: -1 };
      if (event.key in moves) {
        event.preventDefault();
        setActive((current) => Math.max(0, Math.min(count - 1, (current ?? count - 1) + moves[event.key])));
      } else if (event.key === 'Home' || event.key === 'End') {
        event.preventDefault();
        setActive(event.key === 'Home' ? 0 : count - 1);
      }
    },
    [count]
  );

  const clear = useCallback(() => setActive(null), []);

  return { active, setActive, onPointerMove, onPointerLeave: clear, onBlur: clear, onKeyDown };
}
