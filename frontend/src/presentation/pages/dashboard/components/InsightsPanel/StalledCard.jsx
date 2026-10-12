import BarChart from '@/presentation/components/charts/BarChart/BarChart.jsx';
import Icon from '@/presentation/components/Icon/Icon.jsx';
import { hrefForListing } from '@/application/navigation/routes.js';
import { INSIGHTS } from '@/domain/content/insightsContent.js';
import InsightCard from './InsightCard.jsx';

/** Itens parados há mais tempo, com o atalho para editar os dois primeiros. */
export default function StalledCard({ data }) {
  const { stalled } = INSIGHTS;
  return (
    <InsightCard id="ins-parados" title={stalled.title} subtitle={stalled.subtitle}>
      {data.stalled.length > 0 ? (
        <>
          <BarChart
            tone="honey"
            label={stalled.title}
            items={data.stalled.map((item) => ({
              id: item.id,
              label: item.title,
              value: item.days,
              display: stalled.days(item.days)
            }))}
          />
          <ul className="insights-panel__actions">
            {data.stalled.slice(0, 2).map((item) => (
              <li key={item.id}>
                <a href={hrefForListing(item.id)} className="insights-panel__action" aria-label={stalled.actionLabel(item.title)}>
                  {stalled.action}
                  <span className="insights-panel__action-meta">{stalled.stock(item.stock)}</span>
                  <Icon name="arrow-right" size={15} />
                </a>
              </li>
            ))}
          </ul>
        </>
      ) : (
        <p className="insights-panel__empty">{INSIGHTS.empty}</p>
      )}
    </InsightCard>
  );
}
