/** Todo o texto da tela de cadastro (#/cadastro). */

export const SIGNUP_PANEL = {
  back: { label: 'Voltar ao site', href: '#/' },
  eyebrow: 'COMECE GRÁTIS',
  titleLines: ['Sua loja vendendo', 'ainda hoje.'],
  lead: 'Crie a conta em menos de um minuto. Plano Grátis pra sempre, sem cartão e sem comissão sobre as suas vendas.'
};

export const SIGNUP_FORM = {
  title: 'Criar sua conta',
  lead: 'Só o básico pra começar. O resto a gente preenche junto, com a ajuda da IA.',
  name: { label: 'Seu nome', placeholder: 'Como podemos te chamar?' },
  email: { label: 'Email', placeholder: 'voce@sualoja.com.br' },
  store: {
    label: 'Nome da loja',
    placeholder: 'Ex.: Bazar da Ana',
    hint: 'É o nome que aparece no seu painel. Dá pra mudar quando quiser.'
  },
  password: {
    label: 'Senha',
    placeholder: 'Pelo menos 8 caracteres',
    hint: 'Use 8 caracteres ou mais, misturando letras e números.'
  },
  confirmation: { label: 'Confirme a senha', placeholder: 'Digite a senha de novo' },
  submit: { label: 'Criar conta grátis', loading: 'Criando sua conta…' },
  login: { text: 'Já tem conta?', link: 'Entrar', href: '#/login' },
  terms: {
    before: 'Ao criar a conta, você concorda com os',
    terms: 'Termos',
    between: 'e a',
    privacy: 'Política de Privacidade',
    end: '.'
  },
  errors: {
    emailTaken: 'Esse email já tem conta. Que tal entrar?',
    storage: {
      title: 'O navegador não deixou criar a conta.',
      text: 'O espaço do site acabou. Libere espaço nas configurações do navegador e tente de novo.'
    },
    unknown: {
      title: 'Não deu pra criar a conta agora.',
      text: 'Tente de novo em instantes.'
    }
  }
};
