import BarChart from '@/presentation/components/charts/BarChart/BarChart.jsx';
import { categoryLabel } from '@/domain/content/listingContent.js';
import { INSIGHTS } from '@/domain/content/insightsContent.js';
import InsightCard from './InsightCard.jsx';

/** Vendas por categoria, em barras. */
export default function CategoriesCard({ data }) {
  const { categories } = INSIGHTS;
  return (
    <InsightCard id="ins-categorias" title={categories.title} subtitle={categories.subtitle}>
      <BarChart
        label={categories.chartLabel}
        items={data.salesByCategory.map((item) => ({
          id: item.category,
          label: categoryLabel(item.category),
          value: item.units,
          display: categories.value(item.units)
        }))}
      />
    </InsightCard>
  );
}
