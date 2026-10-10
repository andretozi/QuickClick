/** Textos dos componentes compartilhados (usados em mais de uma página). */

export const BRAND = {
  homeLabel: 'Quick Click, página inicial'
};

export const PASSWORD_FIELD = {
  show: 'Mostrar senha',
  hide: 'Ocultar senha'
};

/** Mensagem embaixo do campo para cada código de erro (domain/validation/validators.js). */
export const FIELD_ERRORS = {
  required: 'Preencha este campo.',
  email: 'Esse email parece incompleto. Confere pra gente?',
  'name-short': 'Escreva pelo menos 2 letras.',
  'password-short': 'Use pelo menos 8 caracteres.',
  'password-weak': 'Misture letras e números pra senha ficar mais forte.',
  'password-mismatch': 'As duas senhas não estão iguais.',
  phone: 'Confira o telefone, com o DDD.',
  'too-long': 'Passou do limite de caracteres.',
  price: 'Escolha um preço entre R$ 1,00 e R$ 100.000,00.',
  stock: 'Use um número inteiro, de 0 em diante.',
  'email-taken': 'Esse email já tem conta. Que tal entrar?',
  'wrong-password': 'A senha atual não confere.',
  'invalid-credentials': 'Email ou senha não conferem. Confira os dois e tente de novo.',
  'password-incorrect': 'A senha não confere.'
};

export const MODAL = {
  close: 'Fechar'
};

export const TOASTS = {
  region: 'Avisos',
  close: 'Fechar aviso'
};

export const SPLASH = {
  label: 'Carregando a Quick Click'
};

/** Selo discreto nos números que ainda não vêm de vendas de verdade. */
export const SIMULATION_BADGE = {
  label: 'Simulação',
  hint: 'As vendas ainda são simuladas, calculadas a partir dos seus próprios anúncios. Com os marketplaces conectados de verdade, viram números reais.'
};

/** Texto alternativo dos logos oficiais: o próprio nome do marketplace. */
export const MARKETPLACE_LOGO = {
  alt: (name) => name
};

/** Erros que podem aparecer em qualquer tela que grava dados. */
export const STORAGE_ERRORS = {
  full: {
    title: 'O espaço do navegador acabou',
    text: 'As fotos ocupam bastante espaço. Remova uma foto ou apague anúncios antigos e tente de novo.'
  },
  generic: {
    title: 'Não deu pra salvar agora',
    text: 'Tente de novo em instantes.'
  }
};
