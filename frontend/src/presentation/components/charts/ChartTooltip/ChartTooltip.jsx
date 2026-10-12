import { cx } from '@/presentation/utils/cx.js';
import './ChartTooltip.css';

/**
 * Balão de um gráfico, por cima do ponto em foco. `x` é a posição horizontal em %
 * (o balão nunca sai das bordas). O conteúdo também é anunciado (aria-live).
 */
export default function ChartTooltip({ x = 50, title, lines = [], className }) {
  const clamped = Math.max(12, Math.min(88, x));
  return (
    <div className={cx('chart-tooltip', className)} style={{ left: `${clamped}%` }} role="status" aria-live="polite">
      {title && <p className="chart-tooltip__title">{title}</p>}
      {lines.map((line) => (
        <p key={line} className="chart-tooltip__line">
          {line}
        </p>
      ))}
    </div>
  );
}
