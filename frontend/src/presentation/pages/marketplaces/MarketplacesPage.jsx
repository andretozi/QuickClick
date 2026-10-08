import { useRef } from 'react';
import Section from '@/presentation/components/Section/Section.jsx';
import Blob from '@/presentation/components/Blob/Blob.jsx';
import Brand from '@/presentation/components/Brand/Brand.jsx';
import Button from '@/presentation/components/Button/Button.jsx';
import Eyebrow from '@/presentation/components/Eyebrow/Eyebrow.jsx';
import Icon from '@/presentation/components/Icon/Icon.jsx';
import MarketplaceGrid from './components/MarketplaceGrid/MarketplaceGrid.jsx';
import ConnectDialog from './components/ConnectDialog/ConnectDialog.jsx';
import useMarketplaces from '@/application/marketplaces/useMarketplaces.js';
import useMarketplacesAnimations from '@/application/animation/useMarketplacesAnimations.js';
import { MARKETPLACES_PAGE } from '@/domain/content/marketplacesContent.js';
import './MarketplacesPage.css';

const backdrop = (
  <>
    <Blob tone="coral" className="marketplaces-page__blob marketplaces-page__blob--a" />
    <Blob tone="honey" className="marketplaces-page__blob marketplaces-page__blob--b" />
    <Blob tone="coral" className="marketplaces-page__blob marketplaces-page__blob--c" />
  </>
);

/** Tela "Conecte seus marketplaces": o plano do vendedor, o catálogo e o diálogo de conexão. */
export default function MarketplacesPage() {
  const rootRef = useRef(null);
  useMarketplacesAnimations(rootRef);
  const marketplaces = useMarketplaces();
  const { status, seller, error, dialog } = marketplaces;
  const { back, eyebrow, title, lead, loading, loadError } = MARKETPLACES_PAGE;

  return (
    <div ref={rootRef} className="marketplaces-page">
      {/* Com o diálogo aberto, o resto da página fica fora do alcance do teclado */}
      <div inert={dialog ? '' : undefined}>
        <Section as="main" dotted className="marketplaces-page__body" backdrop={backdrop}>
          <header className="marketplaces-page__topbar">
            <Brand href="#/" size="md" tone="light" />
            <a href={back.href} className="marketplaces-page__back">
              <Icon name="chevron-left" size={17} />
              {back.label}
            </a>
          </header>

          <div className="marketplaces-page__intro">
            <Eyebrow tone="coral" data-enter>
              {eyebrow}
            </Eyebrow>
            <h1 data-enter className="heading marketplaces-page__title">
              {title}
            </h1>
            <p data-enter className="marketplaces-page__lead">
              {lead}
            </p>
          </div>

          {status === 'ready' && (
            <MarketplaceGrid
              seller={seller}
              marketplaces={marketplaces.marketplaces}
              busySlug={marketplaces.busySlug}
              failedSlug={marketplaces.failedSlug}
              celebratedSlug={marketplaces.celebratedSlug}
              onConnect={marketplaces.openConnect}
              onDisconnect={marketplaces.disconnect}
            />
          )}

          {status === 'loading' && (
            <p className="marketplaces-page__status marketplaces-page__status--loading" role="status">
              <span className="marketplaces-page__spinner" aria-hidden="true" />
              {loading}
            </p>
          )}

          {status === 'error' && (
            <div className="marketplaces-page__status marketplaces-page__status--error" role="alert">
              <p className="marketplaces-page__status-title">{loadError.title}</p>
              <p className="marketplaces-page__status-text">{error?.message || loadError.fallback}</p>
              <Button variant="dark" size="sm" onClick={marketplaces.retry}>
                {loadError.retry}
              </Button>
            </div>
          )}
        </Section>
      </div>

      {dialog && (
        <ConnectDialog dialog={dialog} onConfirm={marketplaces.confirmConnect} onClose={marketplaces.closeDialog} />
      )}
    </div>
  );
}
