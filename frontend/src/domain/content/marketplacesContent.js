/**
 * Textos da tela de marketplaces (#/marketplaces) e o catálogo que a landing e a área logada mostram.
 *
 * PENDÊNCIA: no front, por enquanto, só o Mercado Livre está disponível para conectar.
 * O back (backend/domain/marketplace.py) ainda marca Shopee e Amazon como disponíveis;
 * os dois catálogos serão alinhados quando o back voltar a ser usado pela área logada.
 */

/**
 * Catálogo: nome, monograma (reserva para quando não há logo oficial, como no TikTok Shop),
 * o artigo usado nas frases ("direto no Mercado Livre", "direto na Shopee") e se já dá para conectar.
 * Os logos oficiais ficam em presentation/assets/marketplaces.
 */
export const MARKETPLACE_CATALOG = [
  { slug: 'mercado-livre', name: 'Mercado Livre', monogram: 'ML', article: 'no', available: true },
  { slug: 'shopee', name: 'Shopee', monogram: 'S', article: 'na', available: false },
  { slug: 'amazon', name: 'Amazon', monogram: 'A', article: 'na', available: false },
  { slug: 'magalu', name: 'Magalu', monogram: 'M', article: 'na', available: false },
  { slug: 'americanas', name: 'Americanas', monogram: 'A', article: 'na', available: false },
  { slug: 'casas-bahia', name: 'Casas Bahia', monogram: 'CB', article: 'na', available: false },
  { slug: 'shein', name: 'Shein', monogram: 'S', article: 'na', available: false },
  { slug: 'tiktok-shop', name: 'TikTok Shop', monogram: 'TS', article: 'no', available: false },
  { slug: 'aliexpress', name: 'AliExpress', monogram: 'AE', article: 'no', available: false }
];

/**
 * Paleta de cada marca, para o fundo cinematográfico da vitrine e das placas da área logada.
 * As cores saíram do próprio SVG do logo (fill e stop-color, em assets/marketplaces):
 * - primary e secondary: as cores do logo;
 * - deep: a primária bem escura, para as bordas e a vinheta;
 * - glow: a luz clara atrás do logo (o logo precisa ler sobre ela).
 * Exceções: o logo do Mercado Livre é só a escrita azul, então o amarelo vem da marca
 * (o mesmo de --color-mercado-livre); o TikTok Shop não tem SVG e usa as cores do monograma.
 * titleTone: 'coral' (padrão) ou 'cream', onde o coral some no fundo da marca.
 */
export const MARKETPLACE_PALETTES = {
  'mercado-livre': { primary: '#ffe600', secondary: '#fff159', deep: '#9c7c00', glow: '#fffbe0', titleTone: 'coral' },
  shopee: { primary: '#ee4d2d', secondary: '#ff9f7a', deep: '#4a1205', glow: '#fff1ec', titleTone: 'cream' },
  amazon: { primary: '#ff6201', secondary: '#171d27', deep: '#0d1118', glow: '#fff4ea', titleTone: 'cream' },
  magalu: { primary: '#0e87fe', secondary: '#097db6', deep: '#031c3a', glow: '#eaf5ff', titleTone: 'coral' },
  americanas: { primary: '#f80032', secondary: '#ff6680', deep: '#40000d', glow: '#fff0f3', titleTone: 'cream' },
  'casas-bahia': { primary: '#0032c5', secondary: '#e71a3b', deep: '#000d36', glow: '#eef2ff', titleTone: 'coral' },
  shein: { primary: '#000000', secondary: '#5c5c5c', deep: '#000000', glow: '#f5f5f5', titleTone: 'coral' },
  'tiktok-shop': { primary: '#fe2c55', secondary: '#25f4ee', deep: '#050505', glow: '#f7f7f7', titleTone: 'coral' },
  aliexpress: { primary: '#fd2751', secondary: '#fcc836', deep: '#3d0610', glow: '#fff6ea', titleTone: 'cream' }
};

/** A palavra que as partículas formam na vitrine. Troque aqui. */
export const SHOWCASE_WORDS = {
  available: 'Já integrado',
  soon: 'Em breve'
};

/** Paleta de um marketplace (um marketplace novo, sem paleta, usa a do Mercado Livre). */
export function getMarketplacePalette(slug) {
  return MARKETPLACE_PALETTES[slug] ?? MARKETPLACE_PALETTES['mercado-livre'];
}

/** "Já integrado" ou "Em breve", conforme o marketplace. */
export function showcaseWordFor(marketplace) {
  return marketplace.available ? SHOWCASE_WORDS.available : SHOWCASE_WORDS.soon;
}

/** Monograma e artigo de um marketplace. Um marketplace novo, ainda fora desta lista, usa as iniciais. */
export function getMarketplaceInfo(slug, name = slug) {
  const known = MARKETPLACE_CATALOG.find((marketplace) => marketplace.slug === slug);
  if (known) return known;
  const initials = String(name)
    .split(/[\s-]+/)
    .map((word) => word[0] ?? '')
    .join('')
    .slice(0, 2)
    .toUpperCase();
  return { slug, name, monogram: initials, article: 'no', available: false };
}


/** Tela "Marketplaces" (#/marketplaces) e a aba Conexões das configurações. */
export const MARKETPLACES_PAGE = {
  eyebrow: 'MARKETPLACES',
  title: 'Suas lojas, conectadas.',
  lead: 'Você autoriza direto no marketplace. A gente nunca vê a sua senha.',
  listLabel: 'Marketplaces',
  loading: 'Carregando suas conexões…',
  loadError: { title: 'Não deu pra carregar as conexões.', retry: 'Tentar de novo' }
};

/** Aviso do plano, com o link para os planos da landing. */
export const PLAN_NOTICE = {
  limited: 'No Grátis você conecta 1 marketplace. Multicanal a partir do Pro.',
  limitedOther: (planName) => `No ${planName} você conecta 1 marketplace. Multicanal a partir do Pro.`,
  unlimited: (planName) => `No ${planName} você conecta vários marketplaces e vende em todos ao mesmo tempo.`,
  link: { label: 'Ver os planos', href: '#planos' }
};

export const MARKETPLACE_CARD = {
  status: { connected: 'Conectado', available: 'Disponível', soon: 'Em breve' },
  nickname: 'Conta',
  since: (date) => `Conectado desde ${date}`,
  synced: (relative) => `Sincronizado ${relative}`,
  connect: 'Conectar',
  connectLabel: (name) => `Conectar ${name}`,
  sync: 'Sincronizar agora',
  syncing: 'Sincronizando…',
  syncProgress: (percent) => `Sincronizando pedidos e estoque: ${percent}%`,
  syncedToast: { title: 'Tudo sincronizado.', text: 'Pedidos e estoque estão em dia com o Mercado Livre.' },
  syncError: { title: 'Não deu pra sincronizar agora.', text: 'Confira a conexão e tente de novo em instantes.' },
  disconnect: 'Desconectar',
  disconnectLabel: (name) => `Desconectar ${name}`,
  soon: 'Em breve',
  soonLabel: (name) => `${name} chega em breve`,
  limitReached: 'Limite do seu plano'
};

export const CONNECT_DIALOG = {
  close: 'Fechar',
  confirm: {
    title: (name) => `Conectar ${name}`,
    text: ({ name, article }) => `Você vai autorizar a Quick Click direto ${article} ${name}. A gente nunca vê a sua senha.`,
    permissionsTitle: 'A Quick Click vai poder:',
    permissions: [
      'Publicar, pausar e editar os seus anúncios',
      'Ler os pedidos para baixar o estoque sozinho',
      'Atualizar preço e estoque quando você mandar'
    ],
    never: 'Nunca: ver a sua senha, mexer no seu dinheiro ou falar com os seus clientes por você.',
    confirm: ({ name, article }) => `Ir para ${article === 'no' ? 'o' : 'a'} ${name}`,
    cancel: 'Agora não'
  },
  redirect: {
    title: (name) => `Indo para o ${name}…`,
    text: 'Abrindo a página de autorização com segurança.'
  },
  authorizing: {
    title: 'Autorizando…',
    text: ({ name, article }) => `Esperando a confirmação ${article} ${name}.`
  },
  connected: {
    title: 'Conectado!',
    text: (nickname) => `Sua conta ${nickname} já está ligada à Quick Click.`,
    word: 'Conectado',
    done: 'Bora vender'
  },
  error: {
    title: 'Não deu pra conectar agora.',
    text: 'Tente de novo em instantes.',
    retry: 'Tentar de novo'
  },
  limit: {
    title: 'Seu plano chegou no limite.',
    text: 'No Grátis você conecta 1 marketplace. Multicanal a partir do Pro.',
    link: { label: 'Ver os planos', href: '#planos' }
  }
};

export const DISCONNECT_DIALOG = {
  title: (name) => `Desconectar ${name}?`,
  text: ({ name, article }) =>
    `Os anúncios publicados ${article} ${name} continuam no ar, mas a Quick Click para de sincronizar pedidos e estoque.`,
  confirm: 'Desconectar',
  confirming: 'Desconectando…',
  cancel: 'Manter conectado',
  done: { title: 'Desconectado.', text: 'Quando quiser, é só conectar de novo.' },
  error: { title: 'Não deu pra desconectar agora.', text: 'Tente de novo em instantes.' }
};
