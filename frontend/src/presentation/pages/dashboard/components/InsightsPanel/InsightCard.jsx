import Panel from '@/presentation/components/Panel/Panel.jsx';
import { cx } from '@/presentation/utils/cx.js';

/**
 * Cartão de vidro da aba Insights: título (com subtítulo opcional), um selo ao lado e o gráfico.
 * Usa os elementos do bloco insights-panel (CSS em InsightsPanel.css, na mesma pasta).
 * - id: liga o título ao cartão (aria-labelledby); enter: ordem da entrada (data-enter)
 */
export default function InsightCard({ id, title, subtitle, badge, wide = false, enter = '3', children }) {
  return (
    <Panel
      tone="glass"
      data-enter={enter}
      className={cx('insights-panel__card', wide && 'insights-panel__card--wide')}
      aria-labelledby={id}
    >
      <header className="insights-panel__head">
        {subtitle ? (
          <div>
            <h2 id={id} className="heading insights-panel__title">
              {title}
            </h2>
            <p className="insights-panel__subtitle">{subtitle}</p>
          </div>
        ) : (
          <h2 id={id} className="heading insights-panel__title">
            {title}
          </h2>
        )}
        {badge}
      </header>
      {children}
    </Panel>
  );
}
