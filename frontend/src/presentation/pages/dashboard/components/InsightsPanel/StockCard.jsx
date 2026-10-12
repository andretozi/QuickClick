import DonutChart from '@/presentation/components/charts/DonutChart/DonutChart.jsx';
import { formatNumber } from '@/domain/format/format.js';
import { categoryLabel } from '@/domain/content/listingContent.js';
import { INSIGHTS } from '@/domain/content/insightsContent.js';
import InsightCard from './InsightCard.jsx';

/** Estoque por categoria, em rosca (sem estoque, a frase de vazio). */
export default function StockCard({ data }) {
  const { stock } = INSIGHTS;
  const total = data.stockByCategory.reduce((sum, item) => sum + item.units, 0);
  return (
    <InsightCard id="ins-estoque" title={stock.title} subtitle={stock.subtitle}>
      {total > 0 ? (
        <DonutChart
          label={stock.chartLabel}
          legendLabel={INSIGHTS.legend}
          total={formatNumber(total)}
          centerLabel={stock.centerLabel}
          items={data.stockByCategory.map((item) => ({
            id: item.category,
            label: categoryLabel(item.category),
            value: item.units,
            display: stock.value(item.units, Math.round((item.units / total) * 100))
          }))}
        />
      ) : (
        <p className="insights-panel__empty">{INSIGHTS.empty}</p>
      )}
    </InsightCard>
  );
}
