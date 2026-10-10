/** Todo o texto do painel (#/painel): topo, números, anúncios e boas vindas. */

const plural = (count, one, many) => (count === 1 ? one : many);

/** Saudação pelo horário do aparelho. */
function greetingWord(hour) {
  if (hour >= 5 && hour < 12) return 'Bom dia';
  if (hour >= 12 && hour < 18) return 'Boa tarde';
  return 'Boa noite';
}

export const DASHBOARD = {
  greeting: (hour, firstName) => `${greetingWord(hour)}, ${firstName}`,
  /** Linha embaixo da saudação: "Ateliê da Marina · Plano Grátis" */
  storeLine: 'Sua loja',
  lead: 'Seus anúncios, seu estoque e o que está vendendo, tudo num lugar só.',
  plan: (name) => `Plano ${name}`,
  connected: (count) =>
    count === 0 ? 'Nenhum marketplace conectado' : `${count} ${plural(count, 'marketplace conectado', 'marketplaces conectados')}`,
  newListing: { label: 'Criar anúncio', href: '#/anuncios/novo' },
  stats: {
    label: 'Resumo da loja',
    active: {
      label: 'Anúncios ativos',
      foot: (total) => `de ${total} ${plural(total, 'anúncio', 'anúncios')} no painel`
    },
    connected: {
      label: 'Marketplaces conectados',
      foot: (names) => (names.length ? names.join(', ') : 'Conecte o primeiro')
    },
    units: {
      label: 'Unidades em estoque',
      foot: (listings) => `em ${listings} ${plural(listings, 'anúncio', 'anúncios')}`
    },
    value: { label: 'Valor em estoque', foot: 'pelo seu preço de venda' }
  },
  tabs: {
    label: 'Seções do painel',
    idPrefix: 'painel',
    listings: 'Anúncios',
    insights: 'Insights'
  }
};

export const LISTINGS_PANEL = {
  title: 'Seus anúncios',
  count: (shown, total) =>
    shown === total ? `${total} ${plural(total, 'anúncio', 'anúncios')}` : `${shown} de ${total} anúncios`,
  search: { label: 'Buscar anúncios', placeholder: 'Buscar pelo título' },
  filter: {
    label: 'Situação',
    options: [
      { value: 'all', label: 'Todas as situações' },
      { value: 'published', label: 'Publicados' },
      { value: 'paused', label: 'Pausados' },
      { value: 'unpublished', label: 'Não publicados' }
    ]
  },
  sort: {
    label: 'Ordenar por',
    options: [
      { value: 'recent', label: 'Mais recentes' },
      { value: 'price-desc', label: 'Maior preço' },
      { value: 'price-asc', label: 'Menor preço' },
      { value: 'stock-desc', label: 'Mais estoque' },
      { value: 'title', label: 'Título, de A a Z' }
    ]
  },
  listLabel: 'Lista de anúncios',
  stock: (units) => (units === 0 ? 'Sem estoque' : `${units} em estoque`),
  updated: (relative) => `Atualizado ${relative}`,
  photoAlt: (title) => `Foto de ${title}`,
  channels: 'Canais',
  channelStatus: (name, status) => `${name}: ${status}`,
  channelSoon: (name) => `${name}: em breve`,
  columns: { listing: 'Anúncio', price: 'Preço', stock: 'Estoque', channels: 'Canais', actions: 'Ações' },
  soon: {
    more: (count) => `+${count}`,
    label: (names) => `${names} chegam em breve`
  },
  actions: {
    edit: 'Ver e editar',
    pause: 'Pausar',
    resume: 'Reativar',
    publish: 'Publicar no Mercado Livre',
    publishBlocked: 'Conecte o Mercado Livre para publicar',
    duplicate: 'Duplicar',
    remove: 'Excluir'
  },
  actionLabel: (action, title) => `${action}: ${title}`,
  copySuffix: '(cópia)',
  empty: {
    title: 'Nenhum anúncio por aqui ainda.',
    text: 'Tire uma foto, deixe a IA escrever o anúncio e publique no Mercado Livre em poucos minutos.',
    cta: { label: 'Criar meu primeiro anúncio', href: '#/anuncios/novo' }
  },
  noResults: {
    title: 'Nada encontrado com esses filtros.',
    text: 'Tente outra busca ou mostre todas as situações.',
    clear: 'Limpar filtros'
  },
  loading: 'Carregando seus anúncios…',
  loadError: {
    title: 'Não deu pra carregar os anúncios.',
    text: 'Tente de novo em instantes.',
    retry: 'Tentar de novo'
  },
  confirmDelete: {
    title: 'Excluir este anúncio?',
    text: (title) => `"${title}" sai do painel e do Mercado Livre. Não dá pra desfazer.`,
    confirm: 'Excluir anúncio',
    deleting: 'Excluindo…',
    cancel: 'Cancelar'
  },
  toasts: {
    paused: { title: 'Anúncio pausado.', text: 'Ele sai do ar no Mercado Livre até você reativar.' },
    resumed: { title: 'Anúncio reativado.', text: 'Ele voltou a aparecer no Mercado Livre.' },
    published: { title: 'Anúncio publicado.', text: 'Ele já aparece no Mercado Livre.' },
    duplicated: { title: 'Anúncio duplicado.', text: 'A cópia ficou fora do ar, pronta pra você ajustar.' },
    removed: { title: 'Anúncio excluído.', text: 'Ele saiu do painel e do Mercado Livre.' },
    error: { title: 'Não deu pra salvar agora.', text: 'Tente de novo em instantes.' }
  }
};

/** Aparece uma vez, logo depois de criar a conta. */
export const WELCOME = {
  eyebrow: 'CONTA CRIADA',
  title: (firstName) => `Sua loja está no ar, ${firstName}!`,
  text: 'Agora é só conectar o Mercado Livre e criar o primeiro anúncio. A IA ajuda em cada passo.',
  connect: { label: 'Conectar o Mercado Livre', href: '#/marketplaces' },
  create: { label: 'Criar meu primeiro anúncio', href: '#/anuncios/novo' },
  close: 'Fechar as boas vindas'
};
