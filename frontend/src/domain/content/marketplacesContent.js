/**
 * Textos da tela de marketplaces (#/marketplaces) e o catálogo que a landing mostra.
 * O catálogo acompanha backend/domain/marketplace.py: mudou lá, mude aqui também.
 */

/**
 * Catálogo: nome, monograma (as iniciais, nunca o logo oficial) e o artigo usado
 * nas frases ("direto no Mercado Livre", "direto na Shopee").
 */
export const MARKETPLACE_CATALOG = [
  { slug: 'mercado-livre', name: 'Mercado Livre', monogram: 'ML', article: 'no', available: true },
  { slug: 'shopee', name: 'Shopee', monogram: 'S', article: 'na', available: true },
  { slug: 'amazon', name: 'Amazon', monogram: 'A', article: 'na', available: true },
  { slug: 'magalu', name: 'Magalu', monogram: 'M', article: 'na', available: false },
  { slug: 'americanas', name: 'Americanas', monogram: 'A', article: 'na', available: false },
  { slug: 'casas-bahia', name: 'Casas Bahia', monogram: 'CB', article: 'na', available: false },
  { slug: 'shein', name: 'Shein', monogram: 'S', article: 'na', available: false },
  { slug: 'tiktok-shop', name: 'TikTok Shop', monogram: 'TS', article: 'no', available: false },
  { slug: 'aliexpress', name: 'AliExpress', monogram: 'AE', article: 'no', available: false }
];

/** Monograma e artigo de um marketplace. Um marketplace novo, ainda fora desta lista, usa as iniciais. */
export function getMarketplaceInfo(slug, name) {
  const known = MARKETPLACE_CATALOG.find((marketplace) => marketplace.slug === slug);
  if (known) return known;
  const initials = name
    .split(' ')
    .map((word) => word[0])
    .join('')
    .slice(0, 2)
    .toUpperCase();
  return { slug, name, monogram: initials, article: 'no' };
}

export const MARKETPLACES_PAGE = {
  back: { label: 'Voltar ao site', href: '#/' },
  eyebrow: 'ÁREA DO VENDEDOR',
  title: 'Conecte seus marketplaces',
  lead: 'Escolha onde você já vende. A autorização é feita direto no marketplace e a gente nunca vê a sua senha.',
  listLabel: 'Marketplaces do catálogo',
  loading: 'Carregando seus marketplaces…',
  loadError: {
    title: 'Não conseguimos carregar os seus marketplaces.',
    fallback: 'Não conseguimos falar com o servidor agora. Tente de novo em instantes.',
    retry: 'Tentar de novo'
  }
};

const marketplaces = (count) => (count === 1 ? 'marketplace' : 'marketplaces');

export const PLAN_PANEL = {
  label: 'Seu plano',
  eyebrow: 'SEU PLANO',
  planName: (name) => `Plano ${name}`,
  usage: ({ used, limit }) => {
    if (limit !== null) return `${used} de ${limit} ${marketplaces(limit)} ${limit === 1 ? 'conectado' : 'conectados'}`;
    if (used === 0) return 'Nenhum marketplace conectado ainda';
    return `${used} ${marketplaces(used)} ${used === 1 ? 'conectado' : 'conectados'}`;
  },
  limitNotice: ({ planName, limit, upgradePlanName }) =>
    `No plano ${planName} você conecta ${limit} ${marketplaces(limit)}. Pra vender em todos os canais ao mesmo tempo, conheça o plano ${upgradePlanName}.`,
  unlimitedNotice: ({ planName }) =>
    `No plano ${planName} você conecta vários marketplaces e vende em todos os canais ao mesmo tempo.`,
  plansLink: { label: 'Conhecer os planos', href: '#planos' }
};

export const MARKETPLACE_CARD = {
  status: { connected: 'Conectado', available: 'Disponível', soon: 'Em breve' },
  actions: {
    connect: 'Conectar',
    disconnect: 'Desconectar',
    disconnecting: 'Desconectando…',
    soon: 'Em breve'
  },
  actionLabel: {
    connect: (name) => `Conectar ${name}`,
    disconnect: (name) => `Desconectar ${name}`,
    soon: (name) => `${name} chega em breve`
  },
  disconnectError: 'Não deu pra desconectar agora. Tente de novo.'
};

export const CONNECT_DIALOG = {
  close: 'Fechar',
  confirm: {
    title: (name) => `Conectar ${name}`,
    text: ({ name, article }) => `Você vai autorizar o acesso direto ${article} ${name}. A gente nunca vê a sua senha.`,
    confirm: ({ name, article }) => `Autorizar ${article} ${name}`,
    cancel: 'Cancelar'
  },
  authorizing: {
    title: 'Autorizando…',
    text: ({ name, article }) => `Esperando a confirmação ${article} ${name}.`
  },
  errors: {
    'plan-limit': {
      title: 'Seu plano chegou no limite',
      fallback: 'O seu plano já conectou o máximo de marketplaces.',
      action: { label: 'Conhecer os planos', href: '#planos' }
    },
    'coming-soon': {
      title: 'Esse marketplace está chegando',
      fallback: 'A integração ainda não está pronta.'
    },
    'not-found': {
      title: 'Não achamos esse marketplace',
      fallback: 'Esse marketplace não existe no nosso catálogo.'
    },
    offline: {
      title: 'Sem conexão com o servidor',
      fallback: 'Não conseguimos falar com o servidor agora. Tente de novo em instantes.',
      canRetry: true
    },
    unknown: {
      title: 'Não deu pra conectar agora',
      fallback: 'Tente de novo em instantes.',
      canRetry: true
    }
  },
  retry: 'Tentar de novo',
  dismiss: 'Fechar'
};
