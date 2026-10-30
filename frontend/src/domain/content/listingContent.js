/**
 * Textos dos anúncios: categorias, condição e situação.
 * Os textos do assistente "criar anúncio" e da edição ficam em LISTING_WIZARD e LISTING_EDITOR.
 */
import { plural } from '@/domain/format/format.js';

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

/** Assistente "criar anúncio" (#/anuncios/novo) e a edição (#/anuncios/:id/editar). */
export const LISTING_WIZARD = {
  eyebrow: 'DA FOTO AO ANÚNCIO PRONTO',
  title: 'Criar anúncio',
  lead: 'A IA lê as fotos, você confere e ela escreve o anúncio. A gente salva o rascunho sozinho.',
  draftSaved: (time) => `Rascunho salvo às ${time}`,
  draftRestored: { title: 'Seu rascunho voltou.', text: 'Continuamos de onde você parou.' },

  steps: {
    label: 'Passos do anúncio',
    items: {
      photos: { label: 'Fotos', hint: 'Até 6' },
      analysis: { label: 'Análise', hint: 'A IA olha' },
      confirm: { label: 'Confirmar', hint: 'O que ela viu' },
      details: { label: 'Detalhes', hint: 'Título e estoque' },
      price: { label: 'Preço', hint: 'Com sugestão' },
      channels: { label: 'Canais', hint: 'Onde vender' },
      publish: { label: 'Publicar', hint: 'Revisar' }
    },
    current: (index, total) => `Passo ${index} de ${total}`
  },
  nav: {
    back: 'Voltar',
    next: 'Continuar',
    publish: 'Publicar anúncio',
    publishing: 'Publicando…',
    saveNew: 'Salvar anúncio',
    save: 'Salvar alterações',
    saving: 'Salvando…'
  },
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

    removeLabel: (index) => `Remover a foto ${index}`,
    photoAlt: (index) => `Foto ${index} do produto`,
    count: (count, max) => `${count} de ${max} ${plural(max, 'foto', 'fotos')}`,
    qualityTip:
      'Dica de alcance: anúncios com 3 ou mais fotos em ângulos diferentes ganham destaque nas buscas do Mercado Livre.',
    full: (max) => `Você já tem ${max} fotos. Remova uma para trocar.`,
    invalid: 'Esse arquivo não é uma imagem. Tente JPG, PNG ou WEBP.',
    freeNotice:
      'No plano Grátis, a leitura usa a camada grátis do Google, que pode usar o que é enviado para melhorar os produtos dela. A gente apaga os dados escondidos das fotos, como a localização, antes de mandar.'
  },
  quota: {
    plans: { gratis: 'Grátis', essencial: 'Essencial', pro: 'Pro', business: 'Business' },
    badge: (plan) => `Plano ${plan}`,
    remaining: (left, total) => `${left} de ${total} ${plural(total, 'análise', 'análises')} da IA neste mês`,
    none: 'As análises da IA deste mês acabaram.',
    budget: 'Hoje a IA completa chegou no limite do dia: a análise usa a versão básica.'
  },
  analysis: {
    title: 'A IA está olhando as fotos',
    lead: 'Leva alguns segundos. Pode ficar por aqui que a gente avisa quando terminar.',
    doneTitle: 'A IA já olhou as fotos',
    doneLead: 'No próximo passo você confere o que ela viu. Só entra no anúncio o que você confirmar.',
    stages: {
      preparando_fotos: 'Preparando as fotos',
      lendo_produto: 'Lendo o produto',
      pesquisando_mercado: 'Pesquisando quem compra',
      precificando: 'Comparando os preços',
      escrevendo: 'Escrevendo o anúncio'
    },
    quality: {
      escura: (n) => `A foto ${n} ficou escura. Se der, tire de novo com mais luz.`,
      tremida: (n) => `A foto ${n} ficou tremida. Apoie o celular e tire de novo.`,
      pequena: (n) => `A foto ${n} está pequena. Uma foto maior ajuda a ler etiquetas.`
    },
    ready: 'Pronto! Agora confira o que a IA viu.',
    toConfirm: 'Conferir',
    retry: 'Tentar de novo',
    manual: 'Preencher à mão',
    start: 'Analisar as fotos',
    unavailable: {
      ia_desligada: { title: 'A IA está desligada agora.', text: 'Preencha o anúncio à mão. Fica pronto do mesmo jeito.' },
      provedor_indisponivel: { title: 'A IA está fora do ar agora.', text: 'Preencha à mão ou tente de novo daqui a pouco.' },
      cota_esgotada: { title: 'As análises da IA deste mês acabaram.', text: 'Dá pra terminar o anúncio à mão, ou mudar de plano para ter mais.' }
    }
  },
  confirm: {
    title: 'Confere o que a IA viu',
    lead: 'Diga se está certo. O que você não confirmar não entra no anúncio.',
    product: { label: 'Produto', placeholder: 'Ex.: Tênis de corrida masculino' },
    seen: 'A IA viu',
    check: 'Confere?',
    yes: 'Sim',
    no: 'Não',
    confirmed: 'Confirmado',
    answerPlaceholder: 'Digite aqui',
    wrongValue: 'Qual é o certo?',
    evidence: (text) => `Visto em: ${text}`,
    sendPhoto: {
      etiqueta: 'Mandar foto da etiqueta',
      verso: 'Mandar foto do verso',
      detalhe: 'Mandar foto do detalhe'
    },
    readingPhoto: 'Lendo a foto…',
    defects: { title: 'Defeitos e desgaste que a IA viu', question: 'Está certo?', removed: 'Fora do anúncio' },
    pending: (count) => `${count} ${plural(count, 'item', 'itens')} esperando a sua resposta`,
    requirements: {
      common: 'O que os canais pedem',
      lead: 'Confira a sugestão da IA ou preencha. Só conta o que você confirmar.',
      askedBy: (names) => `Quem pede: ${names}`,
      question: 'Está certo?',
      choose: 'Escolha',
      tapToConfirm: 'Toque na resposta certa para confirmar.',
      origin: {
        foto: 'Sugestão da IA, lida na foto',
        etiqueta: 'Sugestão da IA, lida na etiqueta',
        deducao: 'Sugestão da IA, deduzida pelas fotos'
      },
      confirmToContinue: 'Confirme este campo para continuar.',
      blocked: {
        title: 'Faltam campos que os canais pedem.',
        text: 'Confirme ou preencha os campos marcados para continuar.'
      }
    },
    notRecognized: {
      title: 'Não consegui reconhecer o produto nessa foto.',
      text: 'Preencha os campos à mão. Se quiser, volte e troque a foto.'
    },
    button: 'Confirmar e continuar',
    sending: 'Enviando…'
  },
  details: {
    title: 'Conte o que você está vendendo',
    lead: 'A IA escreve com o que você confirmou. Ajuste o que quiser.',
    aiDone: { title: 'A IA escreveu o título e a descrição.', text: 'Confira e ajuste o que quiser antes de seguir.' },
    writing: 'A IA está escrevendo. Os campos se preenchem sozinhos quando ela terminar.',
    failed: 'A IA não conseguiu escrever agora. Tente de novo ou escreva à mão.',
    retry: 'Tentar de novo',
    corrected: 'Ajustei o texto para seguir a regra de escrita da loja.',
    why: {
      title: 'Por que escrevi assim',
      profile: 'Quem compra',
      values: 'O que valoriza',
      objections: 'O que trava a compra',
      terms: 'Como procura',
      sources: 'Fontes consultadas'
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
    lead: 'A régua mostra a faixa real de anúncios parecidos. Aceite a sugestão ou digite o seu.',
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
    loading: 'Comparando os preços…',
    market: (count) => `Comparado com ${count} ${plural(count, 'anúncio parecido', 'anúncios parecidos')}`,
    median: (value) => `Mediana ${value}`,
    freeShipping: (count) => `${count} com frete grátis`,
    fee: 'Tarifa do Mercado Livre',
    net: 'Você recebe',
    fromWeb: 'Preços pesquisados nos marketplaces pela web.',
    strategy: {
      title: 'Estratégia',
      vender_rapido: 'Vender rápido',
      equilibrado: 'Equilibrado',
      maximo: 'Preço máximo'
    },
    noData: {
      mercado_livre_desconectado: {
        title: 'Sem dados de preço.',
        text: 'Conecte o Mercado Livre para ver os preços da concorrência, ou digite o seu preço.'
      },
      sem_resultados: { title: 'Sem anúncios parecidos para comparar.', text: 'Digite o preço que você quer.' }
    },
    manual: 'Sem análise da IA, digite o preço que você quer.',
    connect: { label: 'Conectar o Mercado Livre', href: '#/marketplaces' }
  },
  invites: {
    action: { label: 'Ver planos', href: '#/configuracoes' },
    research: {
      title: 'Pesquisa de mercado',
      text: 'Nos planos pagos, a IA pesquisa quem compra esse produto e escreve para essa pessoa.'
    },
    pricing: {
      title: 'Preço com análise da concorrência',
      text: 'Nos planos pagos, a IA compara os anúncios parecidos e sugere a estratégia de preço.'
    }
  },
  channels: {
    title: 'Onde você quer vender?',
    lead: 'Por enquanto, a Quick Click publica no Mercado Livre. Os outros estão chegando.',
    yours: 'Suas contas',
    publishHere: 'Publicar pela Quick Click',
    worthOpening: 'Vale abrir conta',
    openAccount: 'Abrir conta',
    publishesSoon: 'Publicação pela Quick Click em breve',
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
    viewOnMl: 'Ver no Mercado Livre',
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

/** Editar um anúncio (#/anuncios/:id/editar). */
export const LISTING_EDITOR = {
  eyebrow: 'SEU ANÚNCIO',
  title: 'Editar anúncio',
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

/** Visão geral das macroinformações de um anúncio (#/anuncios/:id). */
export const LISTING_DETAIL = {
  eyebrow: 'VISÃO GERAL DO ANÚNCIO',
  back: { label: 'Voltar ao painel', href: '#/painel' },
  loading: 'Carregando os dados do anúncio…',
  syncing: 'Sincronizando com o Mercado Livre…',
  actions: {
    edit: 'Editar anúncio',
    sync: 'Sincronizar agora',
    viewOnMl: 'Abrir no Mercado Livre',
    pause: 'Pausar anúncio',
    resume: 'Reativar anúncio',
    publish: 'Publicar no Mercado Livre',
    duplicate: 'Duplicar',
    remove: 'Excluir'
  },
  metrics: {
    price: 'Preço de venda',
    suggested: (value) => `Sugerido pela IA: ${value}`,
    stock: 'Estoque disponível',
    units: (count) => `${count} ${plural(count, 'unidade', 'unidades')}`,
    sold: 'Unidades vendidas',
    soldUnits: (count) => `${count} ${plural(count, 'venda', 'vendas')}`,
    condition: 'Condição e categoria',
    quality: 'Qualidade no Mercado Livre',
    qualityScore: (pct) => `${pct}% de preenchimento`,
    qualityEmpty: 'Aguardando publicação'
  },
  gallery: {
    title: 'Fotos do produto',
    count: (count) => `${count} ${plural(count, 'foto cadastrada', 'fotos cadastradas')}`,
    empty: 'Nenhuma foto cadastrada neste anúncio.',
    thumbLabel: (index) => `Ver foto ${index}`
  },
  specs: {
    title: 'Ficha técnica e atributos',
    empty: 'Nenhuma característica técnica cadastrada ainda.',
    mlCode: 'Código no Mercado Livre',
    mlCategory: 'Categoria no Mercado Livre',
    updatedAt: 'Última atualização'
  },
  description: {
    title: 'Descrição do anúncio',
    empty: 'Este anúncio ainda não tem descrição cadastrada.'
  },
  toasts: {
    synced: { title: 'Anúncio sincronizado.', text: 'As informações vieram direto do Mercado Livre.' },
    syncError: { title: 'Não deu pra sincronizar agora.', text: 'Mostrando os últimos dados salvos no painel.' }
  }
};

/** Nome de cada característica que a IA lê (a chave vem do back). */
export const ATTRIBUTE_LABELS = {
  marca: 'Marca',
  fabricante: 'Fabricante',
  modelo: 'Modelo',
  cor: 'Cor',
  material: 'Material',
  textura: 'Textura',
  tamanho: 'Tamanho',
  voltagem: 'Voltagem',
  quantidade: 'Quantidade',
  dimensoes: 'Dimensões',
  capacidade: 'Capacidade',
  genero: 'Gênero',
  estampa: 'Estampa',
  acabamento: 'Acabamento',
  potencia: 'Potência',
  compatibilidade: 'Compatibilidade',
  formato_de_venda: 'Formato de venda',
  unidades_por_kit: 'Unidades por kit',
  unidades_por_embalagem: 'Unidades por embalagem'
};

export function attributeLabel(key) {
  if (ATTRIBUTE_LABELS[key]) return ATTRIBUTE_LABELS[key];
  const text = String(key ?? '').replace(/_/g, ' ').trim();
  return text ? text[0].toUpperCase() + text.slice(1) : '';
}

/** Por que cada marketplace combina, no plano Grátis (no pago, a frase vem da IA). */
export const CHANNEL_REASONS = {
  'mercado-livre': 'O maior público do país, para quase todo tipo de produto.',
  shopee: 'Muito procurado para moda, casa e beleza com preço baixo.',
  amazon: 'Forte em eletrônicos, livros e casa, para produtos novos.',
  magalu: 'Bom para eletrônicos, casa e cozinha, com público fiel.',
  americanas: 'Público grande para eletrônicos, casa e brinquedos novos.',
  'casas-bahia': 'Forte em eletrodomésticos, casa e móveis de valor maior.',
  shein: 'Público jovem que compra moda e acessórios com frequência.',
  'tiktok-shop': 'Venda pelos vídeos, boa para moda, beleza e casa.',
  aliexpress: 'Alcance para acessórios e eletrônicos de preço baixo.'
};

/**
 * Onde abrir a conta de vendedor de cada marketplace.
 * Endereços levantados em 2026-10-17 em guias de vendedores (confira no site de cada um).
 */
export const CHANNEL_SIGNUP = {
  'mercado-livre': 'https://vendedores.mercadolivre.com.br',
  shopee: 'https://seller.shopee.com.br',
  amazon: 'https://venda.amazon.com.br',
  magalu: 'https://universo.magalu.com',
  americanas: 'https://venda.americanas.com.br/pre-cadastro',
  'casas-bahia': 'https://marketplace.via.com.br',
  shein: 'https://br.shein.com/campaign/venda-na-shein',
  'tiktok-shop': 'https://seller-br.tiktok.com',
  aliexpress: 'https://sell.aliexpress.com'
};

/** Mensagem de cada erro da IA e da publicação (o código vem do back). */
export const AI_ERRORS = {
  cota_esgotada: { title: 'As análises da IA deste mês acabaram.', text: 'Dá pra terminar o anúncio à mão, ou mudar de plano para ter mais.' },
  limite_por_hora: { title: 'Muitas análises na última hora.', text: 'Espera um pouco e tenta de novo, ou preencha à mão.' },
  analise_em_andamento: { title: 'Já tem uma análise rodando.', text: 'Espera ela terminar para começar outra.' },
  ia_indisponivel: { title: 'A IA está fora do ar agora.', text: 'Você pode preencher o anúncio à mão.' },
  foto_invalida: { title: 'Não deu pra abrir uma das fotos.', text: 'Use JPG, PNG ou WEBP de até 10 MB.' },
  fotos_necessarias: { title: 'Precisamos das fotos de novo.', text: 'Elas saíram da memória. Mande de novo para continuar.' },
  interrompida: { title: 'A análise parou no meio.', text: 'O servidor reiniciou. Toque em tentar de novo.' },
  mercado_livre_desconectado: { title: 'O Mercado Livre não está conectado.', text: 'Conecte a sua conta para publicar.' },
  publicacao_recusada: { title: 'O Mercado Livre recusou a operação.', text: 'Confira os dados do anúncio e tente de novo.' },
  anuncio_nao_encontrado: { title: 'Anúncio não encontrado no Mercado Livre.', text: 'Ele pode já ter sido removido por lá.' },
  descricao_nao_gravada: { title: 'O anúncio foi salvo, mas a descrição não entrou.', text: 'Confira no Mercado Livre.' },
  servico_indisponivel: { title: 'Esse serviço está fora do ar agora.', text: 'Tente de novo em instantes.' },
  sem_conexao: { title: 'Sem conexão com a Quick Click.', text: 'Confira a internet e tente de novo.' }
};

export function aiErrorText(code, message) {
  return AI_ERRORS[code] ?? { title: 'Algo deu errado.', text: message || 'Tente de novo em instantes.' };
}
