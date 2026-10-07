/** Todo o texto da tela de login em um só lugar. */

export const BRAND_PANEL = {
  back: { label: 'Voltar ao site', href: '#/' },
  eyebrow: 'ÁREA DO VENDEDOR',
  titleLines: ['Bem-vindo', 'de volta.'],
  lead: 'Entre e continue transformando estoque parado em dinheiro. É só uma foto — a IA cuida do resto.',
  proof: {
    title: 'Nova venda no Bazar da Ana',
    amount: '+ R$ 189,00'
  }
};

export const SOCIAL_PROVIDERS = [
  { id: 'google', label: 'Continuar com Google', icon: 'google', iconSize: 21, variant: 'light' },
  { id: 'apple', label: 'Continuar com Apple', icon: 'apple', iconSize: 18, variant: 'dark' },
  { id: 'facebook', label: 'Continuar com Facebook', icon: 'facebook', iconSize: 18, variant: 'dark' }
];

export const LOGIN_FORM = {
  title: 'Entrar na sua conta',
  lead: 'Escolha como quer entrar — leva alguns segundos.',
  divider: 'ou entre com e-mail',
  email: { label: 'E-mail', placeholder: 'voce@sualoja.com.br' },
  password: { label: 'Senha', placeholder: 'Sua senha', forgot: 'Esqueci a senha' },
  submit: { label: 'Entrar', loading: 'Entrando…' },
  signup: { text: 'Novo por aqui?', link: 'Criar conta grátis', href: '#/' },
  terms: {
    before: 'Ao continuar, você concorda com os',
    terms: 'Termos',
    between: 'e a',
    privacy: 'Política de Privacidade'
  }
};
