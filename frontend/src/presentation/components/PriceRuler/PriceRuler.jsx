import { useRef } from 'react';
import useChartAnimation from '@/application/animation/useChartAnimation.js';
import { cx } from '@/presentation/utils/cx.js';
import './PriceRuler.css';

/**
 * Régua de preço: a faixa de itens parecidos (mínimo, sugerido e máximo) e o preço do
 * vendedor andando com mola por cima dela. Valores em centavos; `format` escreve em reais.
 * - texts: { label, min, suggested, max, yours }
 * - position: 'below' | 'fair' | 'above' (a cor do marcador do vendedor)
 */
export default function PriceRuler({ minCents, suggestedCents, maxCents, valueCents, position, format, texts, className }) {
  const ref = useRef(null);
  useChartAnimation(ref);
  const start = minCents * 0.75;
  const end = maxCents * 1.2;
  const at = (cents) => Math.max(0, Math.min(100, ((cents - start) / (end - start)) * 100));
  const hasValue = valueCents !== null && valueCents !== undefined;

  return (
    <div ref={ref} className={cx('price-ruler', className)} role="img" aria-label={`${texts.label}: ${texts.min} ${format(minCents)}, ${texts.suggested} ${format(suggestedCents)}, ${texts.max} ${format(maxCents)}`}>
      <div className="price-ruler__track" aria-hidden="true">
        <span className="price-ruler__ticks" />
        <span
          data-chart-grow
          className="price-ruler__band"
          style={{ left: `${at(minCents)}%`, width: `${at(maxCents) - at(minCents)}%` }}
        />
        <span data-chart-pop data-delay="300" className="price-ruler__mark price-ruler__mark--suggested" style={{ left: `${at(suggestedCents)}%` }}>
          <span className="price-ruler__flag">
            <span className="price-ruler__flag-label">{texts.suggested}</span>
            {format(suggestedCents)}
          </span>
        </span>
        {hasValue && (
          <span className={cx('price-ruler__yours', position && `price-ruler__yours--${position}`)} style={{ left: `${at(valueCents)}%` }}>
            <span className="price-ruler__yours-label">{texts.yours}</span>
          </span>
        )}
      </div>
      <div className="price-ruler__scale" aria-hidden="true">
        <span className="price-ruler__end" style={{ left: `${at(minCents)}%` }}>
          <span className="price-ruler__end-label">{texts.min}</span>
          {format(minCents)}
        </span>
        <span className="price-ruler__end price-ruler__end--max" style={{ left: `${at(maxCents)}%` }}>
          <span className="price-ruler__end-label">{texts.max}</span>
          {format(maxCents)}
        </span>
      </div>
    </div>
  );
}
