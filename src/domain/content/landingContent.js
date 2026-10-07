/**
 * Todo o texto da landing em um só lugar.
 * Para mudar uma frase, mude aqui — os componentes só desenham.
 */

export const NAV = {
  links: [
    { label: 'Como funciona', href: '#como' },
    { label: 'Preço', href: '#preco' }
  ],
  login: { label: 'Entrar', href: '#/login' },
  cta: { label: 'Anunciar meu estoque', href: '#preco' }
};

export const HERO = {
  badge: 'Feito para quem precisa vender agora',
  titleLines: ['Clicou…', 'vendeu.'],
  lead: 'O jeito mais simples de transformar estoque parado em dinheiro. Você tira uma foto — a nossa IA cuida do resto e anuncia nos marketplaces certos.',
  cta: { label: 'Anunciar meu estoque', href: '#preco' },
  scrollHint: { label: 'Veja como é simples', href: '#como' }
};

export const HOW_IT_WORKS = {
  eyebrow: 'COMO FUNCIONA',
  title: 'Clicou aqui, vendeu ali',
  lead: 'É só descer a página — a gente te mostra o passo a passo.',
  steps: [
    {
      number: '01',
      scene: 'register',
      title: 'Você faz um cadastro rápido',
      description:
        'Uma vez só. Você preenche os dados da loja no computador ou no celular — sem planilha, sem complicação.'
    },
    {
      number: '02',
      scene: 'photo',
      title: 'Você tira as fotos',
      description:
        'Aponta a câmera para os produtos (ou para a prateleira toda). Cada foto vira um anúncio — você não digita nada.'
    },
    {
      number: '03',
      scene: 'ai',
      title: 'A nossa IA analisa o mercado',
      description:
        'Ela olha o que está vendendo agora e sugere o melhor canal, o preço e o prazo para cada item.'
    },
    {
      number: '04',
      scene: 'sale',
      title: 'Você comemora a venda',
      description:
        'A gente publica e acompanha. Quando vende, o dinheiro entra — e você só paga uma comissão quando isso acontece.'
    }
  ]
};

export const BENEFITS = {
  eyebrow: 'POR QUE ANUNCIAR COM A QUICK CLICK',
  title: 'O risco é nosso, a grana é sua.',
  items: [
    {
      icon: 'dollar',
      tone: 'coral',
      title: 'Você só paga quando vende',
      description:
        'Sem mensalidade e sem contrato preso. Se o produto não girar, não custa nada. Simples assim.'
    },
    {
      icon: 'camera',
      tone: 'honey',
      title: 'Uma foto e o anúncio tá pronto',
      description:
        'A IA escreve o título, a descrição e escolhe a categoria certa pra cada canal. Horas de cadastro viram minutos.'
    },
    {
      icon: 'trend-up',
      tone: 'green',
      title: 'A IA fica de olho no mercado',
      description:
        'Ela indica o canal, o preço e o prazo com mais chance de vender — e aprende com cada venda pra acertar mais.'
    }
  ]
};

export const COMPARISON = {
  title: 'Quick Click x os integradores de sempre',
  lead: 'Feito pra quem precisa girar rápido — não pra quem quer planilha.',
  others: {
    label: 'INTEGRADORES ATUAIS',
    items: [
      'Cadastro manual, item por item',
      'Você escolhe o canal na mão',
      'Você define e ajusta cada preço',
      'Mensalidade fixa, vendendo ou não'
    ]
  },
  ours: {
    ribbon: 'QUICK CLICK',
    title: 'Quick Click',
    items: [
      'Cadastro por foto, feito pela IA',
      'A IA recomenda o canal item a item',
      'Preço de saída rápida + reajuste',
      'Comissão só quando vende'
    ]
  }
};

export const PRICING = {
  eyebrow: 'PREÇO HONESTO',
  title: 'R$ 0 pra começar.',
  description:
    'Cadastrar é grátis. Você paga uma comissão só quando um produto é vendido — e nada até lá. O nosso sucesso é vender o seu.',
  cta: { label: 'Quero anunciar', href: '#final' }
};

export const FINAL_CTA = {
  title: 'Pronto pra girar seu estoque?',
  lead: 'Cadastre sua loja em minutos e deixe a primeira foto virar dinheiro.',
  cta: { label: 'Começar agora', href: '#top' },
  finePrint: 'Sem cartão · sem mensalidade · a gente só ganha quando você vende'
};

export const FOOTER = {
  tagline: 'Clicou, vendeu. Transforme estoque parado em dinheiro.',
  copyright: '© 2026 Quick Click · Protótipo'
};

/* ---------- Dados fictícios das cenas animadas ---------- */
export const SCENES = {
  register: {
    title: 'Cadastrar loja',
    fields: ['Nome da loja', 'Categoria', 'WhatsApp'],
    button: 'Cadastrar loja',
    done: 'Loja criada'
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
