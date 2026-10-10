/** Todo o texto da aba Insights do painel. As vendas são simuladas (veja o SimulationBadge). */

const plural = (count, one, many) => (count === 1 ? one : many);

export const INSIGHTS = {
  label: 'Insights da loja',
  loading: 'Calculando os insights…',
  loadError: { title: 'Não deu pra calcular os insights.', retry: 'Tentar de novo' },
  empty: 'Crie anúncios para este gráfico ganhar vida.',
  emptyAll: {
    title: 'Os insights nascem dos seus anúncios.',
    text: 'Crie o primeiro anúncio e a gente monta o faturamento, as categorias e o estoque da sua loja.',
    cta: { label: 'Criar meu primeiro anúncio', href: '#/anuncios/novo' }
  },
  legend: 'Legenda',
  revenue: {
    title: 'Faturamento nos últimos 30 dias',
    chartLabel: 'Gráfico de área com o faturamento de cada dia dos últimos 30 dias',
    orders: (count) => `${count} ${plural(count, 'pedido', 'pedidos')}`,
    ticket: (value) => `Ticket médio de ${value}`,
    change: (percent) =>
      percent >= 0
        ? `${percent}% a mais que nos 30 dias anteriores`
        : `${Math.abs(percent)}% a menos que nos 30 dias anteriores`,
    tableCaption: 'Faturamento por dia',
    columns: { day: 'Dia', revenue: 'Faturamento', orders: 'Pedidos' }
  },
  categories: {
    title: 'Vendas por categoria',
    subtitle: 'Unidades vendidas nos últimos 30 dias',
    chartLabel: 'Gráfico de barras com as unidades vendidas por categoria',
    value: (units) => `${units} ${plural(units, 'vendida', 'vendidas')}`
  },
  stock: {
    title: 'Distribuição do estoque',
    subtitle: 'Unidades paradas em cada categoria',
    chartLabel: 'Gráfico de rosca com as unidades em estoque por categoria',
    centerLabel: 'unidades',
    value: (units, percent) => `${units} ${plural(units, 'unidade', 'unidades')} (${percent}%)`
  },
  prices: {
    title: 'Seu preço x o sugerido pela IA',
    subtitle: 'Onde um ajuste pode fazer o item vender mais rápido',
    chartLabel: 'Gráfico que compara o seu preço com o preço sugerido pela IA em cada anúncio',
    current: 'Seu preço',
    suggested: 'Sugerido pela IA',
    above: (value) => `${value} acima do sugerido`,
    below: (value) => `${value} abaixo do sugerido`,
    equal: 'No preço sugerido'
  },
  stalled: {
    title: 'Itens parados há mais tempo',
    subtitle: 'Sem vendas há dias. Hora de girar o estoque.',
    days: (count) => `${count} ${plural(count, 'dia', 'dias')} sem vender`,
    stock: (units) => `${units} em estoque`,
    action: 'Girar o estoque',
    actionLabel: (title) => `Girar o estoque: ${title}`
  }
};
