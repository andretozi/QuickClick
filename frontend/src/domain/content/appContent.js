/**
 * Textos da área logada que aparecem em várias telas: navbar de quem entrou,
 * menu do usuário, casca das páginas e a página 404.
 */
import { PLANS } from './landingContent.js';

export const APP_NAV = {
  ariaLabel: 'Principal',
  brandHref: '#/painel',
  dashboard: { label: 'Painel', href: '#/painel' },
  newListing: { label: 'Criar anúncio', href: '#/anuncios/novo' },
  skipLink: 'Pular para o conteúdo'
};

export const USER_MENU = {
  button: (name) => `Abrir o menu da conta de ${name}`,
  label: 'Menu da conta',
  plan: (name) => `Plano ${name}`,
  /** compactOnly: só aparece no menu quando a tela é estreita (no desktop já está no navbar) */
  links: [
    { id: 'dashboard', label: 'Painel', href: '#/painel', icon: 'grid', compactOnly: true },
    { id: 'new-listing', label: 'Criar anúncio', href: '#/anuncios/novo', icon: 'plus', compactOnly: true },
    { id: 'marketplaces', label: 'Marketplaces', href: '#/marketplaces', icon: 'link' },
    { id: 'settings', label: 'Configurações', href: '#/configuracoes', icon: 'sliders' },
    { id: 'site', label: 'Ver site', href: '#/', icon: 'home' }
  ],
  signOut: 'Sair',
  signingOut: 'Saindo…'
};

export const SESSION_TOASTS = {
  signedOut: { title: 'Você saiu da sua conta.', text: 'Até a próxima venda!' }
};

/** Nome do plano para a tela: "gratis" → "Grátis". */
export function planName(planId) {
  return PLANS.items.find((plan) => plan.id === planId)?.name ?? PLANS.items[0].name;
}

export const NOT_FOUND = {
  code: '404',
  eyebrow: 'PÁGINA NÃO ENCONTRADA',
  title: 'Essa página não existe.',
  lead: 'O endereço pode ter mudado ou ter sido digitado errado. Que tal voltar para um lugar conhecido?',
  home: { label: 'Voltar ao início', href: '#/' },
  dashboard: { label: 'Ir para o painel', href: '#/painel' }
};
