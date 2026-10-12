/** Todo o texto das configurações (#/configuracoes). */

export const SETTINGS = {
  eyebrow: 'SUA CONTA',
  title: 'Configurações',
  lead: 'Perfil, segurança, plano, conexões e preferências. Tudo num lugar só.',
  navLabel: 'Seções das configurações',
  idPrefix: 'config',
  sections: {
    profile: { label: 'Perfil', icon: 'user' },
    security: { label: 'Segurança', icon: 'lock' },
    plan: { label: 'Plano', icon: 'star' },
    connections: { label: 'Conexões', icon: 'link' },
    preferences: { label: 'Preferências', icon: 'bell' },
    danger: { label: 'Zona de risco', icon: 'alert' }
  },
  save: 'Salvar alterações',
  saving: 'Salvando…',
  savedToast: { title: 'Tudo salvo.', text: 'Suas alterações já valem.' },
  errorToast: { title: 'Não deu pra salvar agora.', text: 'Tente de novo em instantes.' }
};

export const PROFILE_SECTION = {
  title: 'Seu perfil',
  lead: 'É assim que você aparece na navbar e no painel.',
  fields: {
    name: { label: 'Nome', placeholder: 'Como podemos te chamar?' },
    email: { label: 'Email', placeholder: 'voce@sualoja.com.br' },
    phone: { label: 'Telefone', placeholder: '(11) 91234 5678', hint: 'Com DDD. Opcional.' },
    store: { label: 'Nome da loja', placeholder: 'Ex.: Bazar da Ana' }
  },
  avatar: {
    label: 'Cor do avatar',
    options: [
      { value: 'coral', label: 'Coral' },
      { value: 'honey', label: 'Mel' },
      { value: 'green', label: 'Verde' },
      { value: 'cocoa', label: 'Cacau' }
    ]
  }
};

export const SECURITY_SECTION = {
  title: 'Trocar a senha',
  lead: 'Use pelo menos 8 caracteres, misturando letras e números.',
  fields: {
    current: { label: 'Senha atual', placeholder: 'A senha de hoje' },
    next: { label: 'Nova senha', placeholder: 'Pelo menos 8 caracteres' },
    confirmation: { label: 'Confirme a nova senha', placeholder: 'Digite de novo' }
  },
  submit: 'Trocar a senha',
  submitting: 'Trocando…',
  done: { title: 'Senha trocada.', text: 'Na próxima vez, entre com a senha nova.' },
  note: 'Simulação: a senha fica só neste navegador, com hash. A segurança de verdade chega com o back.'
};

export const PLAN_SECTION = {
  title: 'Seu plano',
  lead: 'Nenhum plano cobra comissão sobre as suas vendas. A troca de plano chega junto com o pagamento.',
  current: 'Seu plano',
  recommended: 'Recomendado',
  soon: 'Troca de plano em breve'
};

export const CONNECTIONS_SECTION = {
  title: 'Conexões',
  lead: 'Os marketplaces ligados à sua conta.'
};

export const PREFERENCES_SECTION = {
  title: 'Preferências',
  lead: 'Escolha o que a Quick Click te avisa.',
  items: {
    saleAlerts: { label: 'Aviso de venda', description: 'Um aviso a cada venda em qualquer canal.' },
    lowStock: { label: 'Estoque baixo', description: 'Quando sobrar só 1 unidade de um anúncio.' },
    priceTips: { label: 'Dicas de preço', description: 'Quando a IA achar um preço melhor para um item parado.' }
  }
};

export const DANGER_SECTION = {
  title: 'Zona de risco',
  lead: 'Excluir a conta apaga deste navegador o perfil, os anúncios, as conexões e as preferências. Não dá pra desfazer.',
  button: 'Excluir minha conta',
  modal: {
    title: 'Excluir sua conta?',
    text: 'Tudo o que é seu some deste navegador. Para confirmar, digite a sua senha.',
    password: { label: 'Sua senha', placeholder: 'A senha da conta' },
    confirm: 'Excluir para sempre',
    confirming: 'Excluindo…',
    cancel: 'Cancelar'
  },
  done: { title: 'Conta excluída.', text: 'Foi bom vender com você. Volte quando quiser.' }
};
