import DumbbellChart from '@/presentation/components/charts/DumbbellChart/DumbbellChart.jsx';
import { formatMoney } from '@/domain/format/format.js';
import { INSIGHTS } from '@/domain/content/insightsContent.js';
import InsightCard from './InsightCard.jsx';

/** Preço de cada anúncio ao lado do preço sugerido. */
export default function PricesCard({ data }) {
  const { prices } = INSIGHTS;
  return (
    <InsightCard id="ins-precos" title={prices.title} subtitle={prices.subtitle}>
      {data.priceComparison.length > 0 ? (
        <DumbbellChart
          label={prices.chartLabel}
          legendLabel={INSIGHTS.legend}
          legend={{ current: prices.current, suggested: prices.suggested }}
          rows={data.priceComparison.map((item) => {
            const diff = item.priceCents - item.suggestedCents;
            const note =
              diff === 0 ? prices.equal : diff > 0 ? prices.above(formatMoney(diff)) : prices.below(formatMoney(-diff));
            return {
              id: item.id,
              title: item.title,
              current: item.priceCents,
              suggested: item.suggestedCents,
              note,
              description: prices.description({
                current: formatMoney(item.priceCents),
                suggested: formatMoney(item.suggestedCents),
                note
              })
            };
          })}
        />
      ) : (
        <p className="insights-panel__empty">{INSIGHTS.empty}</p>
      )}
    </InsightCard>
  );
}
