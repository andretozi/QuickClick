/** Todo o texto da tela de login em um só lugar. */

export const BRAND_PANEL = {
  back: { label: 'Voltar ao site', href: '#/' },
  eyebrow: 'ÁREA DO VENDEDOR',
  titleLines: ['Que bom te ver', 'de novo.'],
  lead: 'Entre e continue transformando estoque parado em dinheiro. Uma foto e a IA cuida do resto.'
};

export const SOCIAL_PROVIDERS = [
  { id: 'google', name: 'Google', label: 'Continuar com Google', icon: 'google', iconSize: 21, variant: 'light' }
];

export const LOGIN_FORM = {
  title: 'Entrar na sua conta',
  lead: 'Escolha como quer entrar, leva poucos segundos.',
  divider: 'ou entre com seu email',
  email: { label: 'Email', placeholder: 'voce@sualoja.com.br' },
  password: { label: 'Senha', placeholder: 'Sua senha', forgot: 'Esqueci a senha' },
  submit: { label: 'Entrar', loading: 'Entrando…' },
  googleStore: {
    title: 'Quase lá',
    lead: (email) => `Conta Google ${email} verificada. Só falta dar um nome para sua loja.`,
    label: 'Qual o nome da sua loja?',
    placeholder: 'Ex.: Bazar da Ana',
    submit: { label: 'Confirmar e entrar', loading: 'Criando sua conta…' }
  },
  signup: { text: 'Novo por aqui?', link: 'Criar conta grátis', href: '#/cadastro' },
  terms: {
    before: 'Ao continuar, você concorda com os',
    terms: 'Termos',
    between: 'e a',
    privacy: 'Política de Privacidade',
    end: '.'
  },
  /** Erro do formulário inteiro (o de cada campo vem do FIELD_ERRORS). */
  errors: {
    storage: {
      title: 'O navegador não deixou entrar.',
      text: 'O espaço do site acabou. Libere espaço nas configurações do navegador e tente de novo.'
    },
    google: {
      title: 'Não deu pra entrar com o Google.',
      text: 'Confira sua conta do Google e tente novamente.'
    },
    emailTaken: {
      title: 'Esse email já está cadastrado.',
      text: 'Tente entrar normalmente com a sua conta.'
    },
    rateLimit: {
      title: 'Muitas tentativas seguidas.',
      text: 'Aguarde alguns minutos e tente novamente.'
    },
    unknown: {
      title: 'Não deu pra entrar agora.',
      text: 'Tente de novo em instantes.'
    }
  }
};

/** Avisos dos botões que ainda não funcionam. */
export const LOGIN_SOON = {
  social: (name) => ({
    title: `Entrar com ${name} chega em breve.`,
    text: 'Por enquanto, entre com o Google ou com o email e a senha da sua conta Quick Click.'
  }),
  googleUnavailable: {
    title: 'Login com Google não configurado neste ambiente.',
    text: 'Defina GOOGLE_CLIENT_ID ou VITE_GOOGLE_CLIENT_ID para habilitar o login pelo Google.'
  },
  forgot: {
    title: 'Recuperar a senha chega em breve.',
    text: 'Enquanto isso, se não lembrar a senha, crie uma conta nova com outro email.'
  },
  terms: {
    title: 'Termos e Política de Privacidade em breve.',
    text: 'Os dois textos estão sendo escritos. Por enquanto, nada do que você cadastra sai do seu navegador.'
  }
};
