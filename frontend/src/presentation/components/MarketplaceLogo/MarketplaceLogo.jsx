import MarketplaceMark from '@/presentation/components/MarketplaceMark/MarketplaceMark.jsx';
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
import aliexpress from '@/presentation/assets/marketplaces/aliexpress.svg';
import './MarketplaceLogo.css';

/** Logos oficiais (fontes em assets/marketplaces/FONTES.md). TikTok Shop não tem: usa o monograma. */
const LOGOS = {
  'mercado-livre': mercadoLivre,
  shopee,
  amazon,
  magalu,
  americanas,
  'casas-bahia': casasBahia,
  shein,
  aliexpress
};

const MARK_SIZE = { xs: 'xs', sm: 'xs', md: 'sm', lg: 'md', xl: 'lg', hero: 'xl' };

/**
 * Logo oficial de um marketplace, sem mudar cor nem proporção (cabe numa caixa).
 * Sem logo, mostra o monograma e o nome. Use sobre fundo claro.
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
    !src && 'marketplace-logo--fallback',
    className
  );

  if (!src) {
    return (
      <span className={classes} role={decorative ? undefined : 'img'} aria-label={decorative ? undefined : info.name}>
        <MarketplaceMark slug={slug} monogram={info.monogram} size={MARK_SIZE[size]} />
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
