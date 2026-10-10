import { useRef } from 'react';
import useCountUp from '@/application/animation/useCountUp.js';
import { cx } from '@/presentation/utils/cx.js';
import { formatMoney, formatNumber } from '@/domain/format/format.js';
import './CountUp.css';

/**
 * Número que conta ao aparecer. O leitor de tela ouve só o valor final;
 * a contagem animada é decorativa.
 * format: 'number' (1.234) | 'money' (value em centavos → R$)
 */
export default function CountUp({ value, format = 'number', delay = 0, className }) {
  const ref = useRef(null);
  useCountUp(ref, { to: value, format, delay });
  const finalText = format === 'money' ? formatMoney(value) : formatNumber(value);

  return (
    <span className={cx('count-up', className)}>
      <span ref={ref} className="count-up__value" aria-hidden="true" />
      <span className="visually-hidden">{finalText}</span>
    </span>
  );
}
