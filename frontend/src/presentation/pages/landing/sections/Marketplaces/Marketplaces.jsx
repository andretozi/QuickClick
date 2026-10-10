import BrandBackdrop from '@/presentation/components/BrandBackdrop/BrandBackdrop.jsx';
import Icon from '@/presentation/components/Icon/Icon.jsx';
import MarketplaceLogo from '@/presentation/components/MarketplaceLogo/MarketplaceLogo.jsx';
import ParticleBurst from '@/presentation/components/ParticleBurst/ParticleBurst.jsx';
import { cx } from '@/presentation/utils/cx.js';
import { MARKETPLACES } from '@/domain/content/landingContent.js';
import {
  MARKETPLACE_CATALOG,
  getMarketplacePalette,
  showcaseWordFor
} from '@/domain/content/marketplacesContent.js';
import './Marketplaces.css';

const SCENES = MARKETPLACE_CATALOG.map((marketplace) => ({
  ...marketplace,
  palette: getMarketplacePalette(marketplace.slug),
  word: showcaseWordFor(marketplace)
}));

/**
 * Vitrine dos marketplaces (seção #marketplaces): uma cena de tela cheia por marketplace,
 * com o fundo nas cores da marca e o logo enorme no centro. Sem botão de conectar.
 * A coreografia (troca de cenas, cursor, clique e partículas que viram palavra) mora em
 * infrastructure/animation/landing/scenes/marketplaces.js (cena "marketplaces").
 * As cenas são decorativas; o leitor de tela recebe a lista escondida ("Mercado Livre, já integrado").
 */
export default function Marketplaces() {
  const { title, lead, listLabel, itemLabel } = MARKETPLACES;

  return (
    <section id="marketplaces" data-surface="dark" className="showcase" aria-labelledby="vitrine-titulo">
      <div data-scene="marketplaces" className="showcase__stage">
        <ul className="showcase__scenes" aria-hidden="true">
          {SCENES.map((scene, i) => (
            <li
              key={scene.slug}
              data-part="slide"
              data-slug={scene.slug}
              data-word={scene.word}
              data-title-tone={scene.palette.titleTone}
              className={cx('showcase__slide', i === 0 && 'showcase__slide--current')}
            >
              <BrandBackdrop slug={scene.slug} palette={scene.palette} className="showcase__backdrop" />
              <div data-part="logo" className="showcase__logo">
                <MarketplaceLogo slug={scene.slug} size="hero" decorative />
              </div>
            </li>
          ))}
        </ul>

        <header data-part="header" className="showcase__header">
          <h2 id="vitrine-titulo" className="heading showcase__title">
            {title}
          </h2>
          <p className="showcase__lead">{lead}</p>
        </header>

        <span data-part="ring" className="showcase__ring" />
        <ParticleBurst data-part="particles" className="showcase__particles" />
        <span data-part="cursor" className="showcase__cursor">
          <Icon name="logo-spark" size={96} className="showcase__cursor-icon" />
        </span>

        <ul className="visually-hidden" aria-label={listLabel}>
          {SCENES.map((scene) => (
            <li key={scene.slug}>{itemLabel(scene.name, scene.word)}</li>
          ))}
        </ul>
      </div>
    </section>
  );
}
