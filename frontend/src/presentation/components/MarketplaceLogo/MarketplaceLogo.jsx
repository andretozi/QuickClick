import { cx } from '@/presentation/utils/cx.js';
import { getMarketplaceInfo } from '@/domain/content/marketplacesContent.js';
import { MARKETPLACE_LOGO } from '@/domain/content/commonContent.js';
import mercadoLivre from '@/presentation/assets/marketplaces/mercado-livre.svg';
import shopee from '@/presentation/assets/marketplaces/shopee.svg';
import amazon from '@/presentation/assets/marketplaces/amazon.svg';
import magalu from '@/presentation/assets/marketplaces/magalu.svg';
import americanas from '@/presentation/assets/marketplaces/americanas.svg';
import casasBahia from '@/presentation/assets/marketplaces/casas-bahia.svg';
import shein from '@/presentation/assets/marketplaces/shein.svg';
import tiktokShop from '@/presentation/assets/marketplaces/tiktok-shop.svg';
import aliexpress from '@/presentation/assets/marketplaces/aliexpress.svg';
import './MarketplaceLogo.css';

/**
 * Logos oficiais dos marketplaces, sem nenhuma alteração de cor, forma ou proporção: oito do
 * Wikimedia Commons (domínio público por serem só texto e formas simples) e o do TikTok Shop do
 * site oficial da TikTok. Continuam marcas registradas dos donos e só indicam com quais
 * marketplaces o produto trabalha, sem sugerir parceria.
 */
const LOGOS = {
  'mercado-livre': mercadoLivre,
  shopee,
  amazon,
  magalu,
  americanas,
  'casas-bahia': casasBahia,
  shein,
  'tiktok-shop': tiktokShop,
  aliexpress
};

/** Logos com a escrita branca, feitos para fundo escuro: fora das cenas ganham um fundo escuro próprio. */
const LIGHT_ART = new Set(['tiktok-shop']);

/**
 * Logo oficial de um marketplace, sem mudar cor nem proporção (cabe numa caixa).
 * Um marketplace novo, ainda sem logo, mostra o monograma em coral e o nome como reserva.
 * Use sobre fundo claro ou na cena da marca.
 * - size: 'xs' | 'sm' | 'md' | 'lg' | 'xl' | 'hero' (enche a caixa do pai)
 * - muted: logo apagado, para os marketplaces que ainda vão chegar
 * - decorative: quando o nome já está escrito ao lado (o logo some para o leitor de tela)
 */
export default function MarketplaceLogo({ slug, size = 'md', muted = false, decorative = false, className }) {
  const info = getMarketplaceInfo(slug);
  const src = LOGOS[slug];
  const classes = cx(
    'marketplace-logo',
    `marketplace-logo--${size}`,
    `marketplace-logo--${slug}`,
    muted && 'marketplace-logo--muted',
    LIGHT_ART.has(slug) && 'marketplace-logo--light-art',
    !src && 'marketplace-logo--fallback',
    className
  );

  if (!src) {
    return (
      <span className={classes} role={decorative ? undefined : 'img'} aria-label={decorative ? undefined : info.name}>
        <span className="marketplace-logo__monogram" aria-hidden="true">
          {info.monogram}
        </span>
        <span className="marketplace-logo__name" aria-hidden="true">
          {info.name}
        </span>
      </span>
    );
  }

  return (
    <span className={classes}>
      <img
        className="marketplace-logo__image"
        src={src}
        alt={decorative ? '' : MARKETPLACE_LOGO.alt(info.name)}
        draggable="false"
        decoding="async"
      />
    </span>
  );
}
