/**
 * Textos dos anúncios: categorias, condição e situação.
 * Os textos do assistente "criar anúncio" e da edição ficam em LISTING_WIZARD e LISTING_EDITOR.
 */

/** Categorias (o id é o que fica guardado no anúncio). */
export const LISTING_CATEGORIES = [
  { id: 'moda', label: 'Moda' },
  { id: 'calcados', label: 'Calçados' },
  { id: 'acessorios', label: 'Bolsas e acessórios' },
  { id: 'casa', label: 'Casa e decoração' },
  { id: 'cozinha', label: 'Cozinha' },
  { id: 'eletronicos', label: 'Eletrônicos' },
  { id: 'livros', label: 'Livros' },
  { id: 'esporte', label: 'Esporte e lazer' },
  { id: 'beleza', label: 'Beleza' },
  { id: 'brinquedos', label: 'Brinquedos' },
  { id: 'outros', label: 'Outros' }
];

export function categoryLabel(id) {
  const other = LISTING_CATEGORIES[LISTING_CATEGORIES.length - 1];
  return LISTING_CATEGORIES.find((category) => category.id === id)?.label ?? other.label;
}

export const LISTING_CONDITIONS = [
  { value: 'new', label: 'Novo' },
  { value: 'used', label: 'Usado' }
];

export function conditionLabel(value) {
  return LISTING_CONDITIONS.find((condition) => condition.value === value)?.label ?? LISTING_CONDITIONS[0].label;
}

/** Situação do anúncio no Mercado Livre, com o tom do selo. */
export const LISTING_STATUS_LABELS = {
  published: { label: 'Publicado', tone: 'green' },
  paused: { label: 'Pausado', tone: 'honey' },
  unpublished: { label: 'Não publicado', tone: 'muted' }
};

const plural = (count, one, many) => (count === 1 ? one : many);

/** Assistente "criar anúncio" (#/anuncios/novo) e a edição (#/anuncios/:id). */
export const LISTING_WIZARD = {
  eyebrow: 'DA FOTO AO ANÚNCIO PRONTO',
  title: 'Criar anúncio',
  lead: 'Cinco passos curtos. A gente salva o rascunho sozinho enquanto você preenche.',
  draftSaved: (time) => `Rascunho salvo às ${time}`,
  draftRestored: { title: 'Seu rascunho voltou.', text: 'Continuamos de onde você parou.' },
  discardDraft: 'Começar do zero',
  steps: {
    label: 'Passos do anúncio',
    items: {
      photos: { label: 'Fotos', hint: 'Até 6' },
      details: { label: 'Detalhes', hint: 'Título e estoque' },
      price: { label: 'Preço', hint: 'Com sugestão' },
      channels: { label: 'Canais', hint: 'Onde vender' },
      publish: { label: 'Publicar', hint: 'Revisar' }
    },
    current: (index, total) => `Passo ${index} de ${total}`
  },
  nav: { back: 'Voltar', next: 'Continuar', publish: 'Publicar anúncio', publishing: 'Publicando…', save: 'Salvar alterações', saving: 'Salvando…' },
  photos: {
    title: 'Comece pelas fotos',
    lead: 'Boa luz e fundo limpo vendem mais. A primeira foto vira a capa, mas você escolhe.',
    drop: {
      title: 'Arraste as fotos pra cá',
      text: 'ou clique para escolher no aparelho',
      button: 'Escolher fotos',
      hint: (max) => `JPG, PNG ou WEBP. Até ${max} fotos, a gente reduz o tamanho sozinho.`,
      active: 'Pode soltar!',
      processing: 'Preparando as fotos…'
    },
    cover: 'Capa',
    makeCover: 'Usar como capa',
    makeCoverLabel: (index) => `Usar a foto ${index} como capa`,
    remove: 'Remover',
    removeLabel: (index) => `Remover a foto ${index}`,
    photoAlt: (index) => `Foto ${index} do produto`,
    count: (count, max) => `${count} de ${max} ${plural(max, 'foto', 'fotos')}`,
    full: (max) => `Você já tem ${max} fotos. Remova uma para trocar.`,
    invalid: 'Esse arquivo não é uma imagem. Tente JPG, PNG ou WEBP.'
  },
  details: {
    title: 'Conte o que você está vendendo',
    lead: 'Ou deixe a IA olhar a foto e preencher pra você.',
    ai: {
      button: 'Sugestão da IA',
      working: 'Analisando a foto…',
      steps: ['Olhando a foto', 'Reconhecendo o produto', 'Escrevendo o anúncio'],
      done: { title: 'A IA preencheu os campos.', text: 'Confira e ajuste o que quiser antes de seguir.' },
      needsPhoto: 'Adicione uma foto primeiro: é dela que a IA tira as ideias.'
    },
    fields: {
      title: { label: 'Título', placeholder: 'Ex.: Tênis de corrida azul, tamanho 39', counter: (used, max) => `${used} de ${max}` },
      description: { label: 'Descrição', placeholder: 'Estado, medidas, o que vem junto, por que vale a pena…' },
      category: { label: 'Categoria', placeholder: 'Escolha a categoria' },
      condition: { label: 'Condição' },
      stock: { label: 'Estoque', hint: 'Quantas unidades você tem pra vender.' }
    }
  },
  price: {
    title: 'Quanto vai custar?',
    lead: 'A régua mostra a faixa em que itens parecidos vendem. Aceite a sugestão ou digite o seu.',
    ruler: {
      label: 'Faixa de preço de itens parecidos',
      min: 'Mínimo',
      suggested: 'Sugerido',
      max: 'Máximo',
      yours: 'O seu'
    },
    accept: (value) => `Usar ${value}`,
    accepted: 'Preço sugerido aplicado',
    field: { label: 'Seu preço', hint: 'Em reais. Sem comissão da Quick Click sobre a venda.', placeholder: '0,00', currency: 'R$' },
    position: {
      below: 'Abaixo da faixa: tende a vender rápido, mas você pode estar deixando dinheiro na mesa.',
      fair: 'Dentro da faixa: bom equilíbrio entre preço e velocidade de venda.',
      above: 'Acima da faixa: pode demorar mais pra vender.'
    },
    loading: 'Calculando a faixa de preço…',
    simulated: 'Faixa simulada a partir da categoria e da condição.'
  },
  channels: {
    title: 'Onde você quer vender?',
    lead: 'Por enquanto, a Quick Click publica no Mercado Livre. Os outros estão chegando.',
    available: 'Disponível',
    soon: 'Em breve',
    connected: (nickname) => `Conectado como ${nickname}`,
    notConnected: 'Conecte sua conta do Mercado Livre para publicar.',
    connect: { label: 'Conectar o Mercado Livre', href: '#/marketplaces' },
    toggleLabel: 'Publicar no Mercado Livre',
    preview: 'Prévia no Mercado Livre',
    previewFree: 'Frete calculado no anúncio',
    previewStock: (units) => (units === 1 ? 'Último disponível!' : `${units} disponíveis`),
    previewNew: 'Novo',
    previewUsed: 'Usado',
    previewBuy: 'Comprar agora',
    noneSelected: 'Sem canal escolhido, o anúncio fica salvo no painel, fora do ar.'
  },
  publish: {
    title: 'Tudo pronto. Bora vender?',
    lead: 'Confira o resumo. Dá pra voltar a qualquer passo.',
    summary: {
      photos: 'Fotos',
      title: 'Título',
      category: 'Categoria',
      condition: 'Condição',
      price: 'Preço',
      stock: 'Estoque',
      channels: 'Canais',
      edit: 'Alterar',
      editLabel: (name) => `Alterar ${name.toLowerCase()}`
    },
    channelsNone: 'Nenhum (fica salvo fora do ar)',
    channelsMl: 'Mercado Livre',
    word: 'Publicado',
    wordSaved: 'Salvo'
  },
  success: {
    eyebrow: 'CLICOU, VENDEU.',
    title: 'Seu anúncio está no ar!',
    titleSaved: 'Seu anúncio foi salvo!',
    text: 'Ele já aparece no Mercado Livre. Quando vender, o estoque baixa sozinho.',
    textSaved: 'Ele ficou no painel, fora do ar. Publique quando quiser.',
    dashboard: { label: 'Ver no painel', href: '#/painel' },
    another: 'Criar outro'
  },
  errors: {
    storage: {
      title: 'O espaço do navegador acabou.',
      text: 'As fotos ocupam bastante espaço. Remova uma foto ou apague anúncios antigos e tente de novo.'
    },
    generic: { title: 'Não deu pra salvar agora.', text: 'Tente de novo em instantes.' }
  }
};

/** Ver e editar um anúncio (#/anuncios/:id). */
export const LISTING_EDITOR = {
  eyebrow: 'SEU ANÚNCIO',
  title: 'Ver e editar',
  lead: 'Mexa em qualquer passo e salve. O anúncio no Mercado Livre se atualiza junto.',
  back: { label: 'Voltar ao painel', href: '#/painel' },
  loading: 'Carregando o anúncio…',
  notFound: {
    title: 'Não achamos esse anúncio.',
    text: 'Ele pode ter sido excluído. Que tal voltar ao painel?',
    action: { label: 'Voltar ao painel', href: '#/painel' }
  },
  saved: { title: 'Alterações salvas.', text: 'O anúncio já está atualizado.' }
};
