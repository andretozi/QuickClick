/**
 * Todo o texto da landing em um só lugar.
 * Para mudar uma frase, mude aqui: os componentes só desenham.
 * Regra de escrita dos textos de tela: sem traço e sem barra (veja o CLAUDE.md).
 */

export const NAV = {
  ariaLabel: 'Principal',
  links: [
    { label: 'Como funciona', href: '#como' },
    { label: 'Planos', href: '#planos' }
  ],
  login: { label: 'Entrar', href: '#/login' },
  cta: { label: 'Começar grátis', href: '#planos' }
};

export const HERO = {
  titleLines: ['Clicou…', 'vendeu.'],
  lead: 'Tire uma foto e a nossa IA cria o anúncio, sugere o preço e publica nos marketplaces certos. Vendeu em um canal, sai de todos.',
  cta: { label: 'Começar grátis', href: '#planos' },
  secondary: { label: 'Ver como funciona', href: '#como' },
  finePrint: 'Grátis pra sempre. Sem comissão sobre as suas vendas.'
};

export const HOW_IT_WORKS = {
  eyebrow: 'COMO FUNCIONA',
  title: 'Clicou aqui, vendeu ali',
  lead: 'Quatro passos e o seu estoque começa a girar.',
  steps: [
    {
      number: '01',
      scene: 'register',
      title: 'Conecte as lojas que você já tem.',
      description:
        'Comece pelo Mercado Livre. Os outros grandes marketplaces estão chegando. Você autoriza direto no marketplace e a gente nunca vê a sua senha.'
    },
    {
      number: '02',
      scene: 'photo',
      title: 'Tire as fotos.',
      description: 'A IA reconhece o produto, você confirma os detalhes e o anúncio sai pronto pra cada canal.'
    },
    {
      number: '03',
      scene: 'ai',
      title: 'A IA acha o melhor preço e o melhor canal.',
      description: 'Ela compara com o mercado e indica onde o item vende mais rápido. Você aprova ou recusa.'
    },
    {
      number: '04',
      scene: 'sale',
      title: 'Vendeu em um canal, sai de todos.',
      description:
        'O estoque baixa sozinho em todos os marketplaces. Nada de venda duplicada, cancelamento ou punição na sua reputação. No Business, a NF-e sai automática.'
    }
  ]
};

/**
 * Vitrine animada dos marketplaces (seção #marketplaces). É propaganda: não tem botão
 * nem link para conectar conta. Os nomes vêm do catálogo em marketplacesContent.js.
 */
export const MARKETPLACES = {
  title: 'Integração com os maiores marketplaces do Brasil.',
  lead: 'Você vende onde o seu cliente já compra. A gente cuida do resto.',
  listLabel: 'Marketplaces da vitrine',
  /** O que o leitor de tela ouve em cada item: "Mercado Livre, já integrado". */
  itemLabel: (name, word) => `${name}, ${word.toLowerCase()}`
};

export const BENEFITS = {
  eyebrow: 'POR QUE A QUICK CLICK',
  title: ['A venda é sua.', 'A comissão não existe.'],
  items: [
    {
      icon: 'dollar',
      tone: 'coral',
      title: 'Grátis pra sempre.',
      description:
        'O plano Grátis não tem prazo pra acabar. Você conecta um marketplace, cria seus anúncios e só muda de plano se quiser crescer.'
    },
    {
      icon: 'camera',
      tone: 'honey',
      title: 'Da foto ao anúncio pronto.',
      description: 'A IA escreve título, descrição e atributos pra cada canal. Horas de cadastro viram minutos.'
    },
    {
      icon: 'sync',
      tone: 'green',
      title: 'Vendeu em um canal, sai de todos.',
      description: 'Sem venda duplicada e sem cancelamento. A sua reputação nos marketplaces agradece.'
    }
  ]
};

export const COMPARISON = {
  title: 'Quick Click x os integradores de sempre',
  lead: 'Feito pra quem quer vender rápido, não pra quem quer planilha.',
  others: {
    label: 'INTEGRADORES ATUAIS',
    items: [
      'Cadastro manual, item por item',
      'Você escolhe o canal no chute',
      'Preço definido no escuro',
      'Mensalidade desde o primeiro dia'
    ]
  },
  ours: {
    ribbon: 'QUICK CLICK',
    title: 'Quick Click',
    items: [
      'Anúncio pronto a partir de uma foto',
      'A IA indica o melhor canal pra cada item',
      'Preço sugerido com dados do mercado',
      'Plano Grátis pra sempre e zero comissão'
    ]
  }
};

/** Os preços dos planos pagos ainda não foram definidos: a equipe preenche o "R$ __". */
export const PLANS = {
  eyebrow: 'PREÇO HONESTO',
  title: ['Comece grátis.', 'Cresça quando quiser.'],
  lead: 'Nenhum plano cobra comissão sobre as suas vendas. Quanto mais o seu negócio cresce, mais a gente automatiza pra você.',
  recommendedLabel: 'Recomendado',
  items: [
    {
      id: 'gratis',
      name: 'Grátis',
      price: 'R$ 0',
      period: 'pra sempre',
      tagline: 'Pra começar a vender',
      features: ['1 marketplace', 'Poucos anúncios'],
      cta: { label: 'Começar grátis', href: '#/cadastro' }
    },
    {
      id: 'essencial',
      name: 'Essencial',
      price: 'R$ __',
      period: 'por mês',
      tagline: 'Pra vender mais rápido',
      features: ['1 marketplace', 'Anúncios com IA', 'Preço sugerido'],
      cta: { label: 'Escolher Essencial', href: '#/cadastro' }
    },
    {
      id: 'pro',
      name: 'Pro',
      price: 'R$ __',
      period: 'por mês',
      tagline: 'Pra vender em todos os canais',
      features: ['Vários marketplaces', 'Baixa automática de estoque', 'Monitor de preços'],
      featured: true,
      cta: { label: 'Escolher Pro', href: '#/cadastro' }
    },
    {
      id: 'business',
      name: 'Business',
      price: 'R$ __',
      period: 'por mês',
      tagline: 'Pra quem vende em escala',
      features: ['Automação completa', 'Emissão automática de NF-e'],
      cta: { label: 'Escolher Business', href: '#/cadastro' }
    }
  ]
};

export const FINAL_CTA = {
  title: 'Pronto pra girar seu estoque?',
  lead: 'Crie sua conta, conecte seu primeiro marketplace e transforme a primeira foto em venda.',
  cta: { label: 'Começar grátis', href: '#/cadastro' },
  finePrint: 'Grátis pra sempre · sem cartão · sem comissão sobre as vendas'
};

export const FOOTER = {
  tagline: 'Clicou, vendeu. Automação de vendas multicanal com IA pra pequenos e grandes vendedores.',
  copyright: '© 2026 Quick Click · Protótipo'
};

/* ---------- Dados fictícios das cenas animadas ---------- */
export const SCENES = {
  register: {
    title: 'Conectar lojas',
    fields: ['Mercado Livre', 'Shopee', 'Amazon'],
    button: 'Conectar',
    done: 'Lojas conectadas'
  },
  photo: {
    price: 'R$ 189',
    done: 'Anúncio criado'
  },
  ai: {
    channels: [
      { name: 'Mercado Livre', detail: 'R$189 · vende rápido', tone: 'honey' },
      { name: 'Shopee', detail: 'R$179 · alta procura', tone: 'coral', recommended: true },
      { name: 'Amazon', detail: 'R$199 · prazo maior', tone: 'muted' }
    ],
    recommendedLabel: 'RECOMENDADO',
    chartLabel: 'de olho no mercado',
    bars: [
      { height: '40%', alpha: 0.55 },
      { height: '72%', alpha: 0.7 },
      { height: '54%', alpha: 0.5 },
      { height: '90%', peak: true },
      { height: '64%', alpha: 0.6 }
    ]
  },
  sale: {
    store: 'Bazar da Ana',
    avatar: 'A',
    caption: 'faturamento da semana',
    toastTitle: 'Vendido!',
    amount: '+ R$ 189,00',
    bars: [
      { height: '45%', tone: 'base' },
      { height: '62%', tone: 'base' },
      { height: '55%', tone: 'base' },
      { height: '80%', tone: 'mid' },
      { height: '100%', tone: 'high' }
    ]
  }
};
