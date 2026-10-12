import BrandBackdrop from '@/presentation/components/BrandBackdrop/BrandBackdrop.jsx';
import Button from '@/presentation/components/Button/Button.jsx';
import MarketplaceLogo from '@/presentation/components/MarketplaceLogo/MarketplaceLogo.jsx';
import StatusPill from '@/presentation/components/StatusPill/StatusPill.jsx';
import { cx } from '@/presentation/utils/cx.js';
import { formatDate, formatRelative } from '@/domain/format/format.js';
import { MARKETPLACE_CARD, getMarketplacePalette } from '@/domain/content/marketplacesContent.js';
import './MarketplacePlate.css';

/**
 * Placa grande de um marketplace, com o fundo nas cores da marca e o logo real.
 * - Disponível e desconectado: botão "Conectar".
 * - Conectado: apelido da conta, "conectado desde", "Sincronizar agora" com progresso e "Desconectar".
 * - Em breve: logo apagado e um brilho passando.
 * - sync: { slug, progress } da sincronização em andamento (ou null)
 */
export default function MarketplacePlate({ marketplace, sync, canConnect, onConnect, onSync, onDisconnect, featured = false }) {
  const { slug, name, available, connection } = marketplace;
  const soon = !available;
  const syncing = sync?.slug === slug;
  const status = connection ? 'connected' : soon ? 'soon' : 'available';
  const pillTone = { connected: 'mint', available: 'cream', soon: 'cream' }[status];

  return (
    <li
      data-enter="3"
      className={cx(
        'marketplace-plate',
        featured && 'marketplace-plate--featured',
        soon && 'marketplace-plate--soon',
        connection && 'marketplace-plate--connected'
      )}
    >
      <div className="marketplace-plate__stage">
        <BrandBackdrop slug={slug} palette={getMarketplacePalette(slug)} className="marketplace-plate__backdrop" />
        {soon && <span data-shimmer className="marketplace-plate__shine" aria-hidden="true" />}
        <span className="marketplace-plate__logo">
          <MarketplaceLogo slug={slug} size="hero" muted={soon} />
        </span>
        <StatusPill tone={pillTone} size="sm" className="marketplace-plate__pill">
          {MARKETPLACE_CARD.status[status]}
        </StatusPill>
      </div>

      <div className="marketplace-plate__info">
        <h3 className="marketplace-plate__name">{name}</h3>

        {connection && (
          <dl className="marketplace-plate__facts">
            <div className="marketplace-plate__fact">
              <dt>{MARKETPLACE_CARD.nickname}</dt>
              <dd className="marketplace-plate__nickname">{connection.nickname}</dd>
            </div>
            <div className="marketplace-plate__fact">
              <dt className="visually-hidden">{MARKETPLACE_CARD.status.connected}</dt>
              <dd>{MARKETPLACE_CARD.since(formatDate(connection.connectedAt))}</dd>
              <dd className="marketplace-plate__muted">{MARKETPLACE_CARD.synced(formatRelative(connection.syncedAt))}</dd>
            </div>
          </dl>
        )}

        {syncing && (
          <div className="marketplace-plate__sync" role="status">
            <span className="marketplace-plate__sync-text">{MARKETPLACE_CARD.syncProgress(sync.progress)}</span>
            <span className="marketplace-plate__sync-track" aria-hidden="true">
              <span className="marketplace-plate__sync-fill" style={{ transform: `scaleX(${sync.progress / 100})` }} />
            </span>
          </div>
        )}

        <div className="marketplace-plate__actions">
          {connection && (
            <>
              <Button
                size="sm"
                variant="light"
                icon="sync"
                iconPosition="start"
                iconSize={16}
                onClick={() => onSync(slug)}
                loading={syncing}
                loadingText={MARKETPLACE_CARD.syncing}
                disabled={Boolean(sync)}
              >
                {MARKETPLACE_CARD.sync}
              </Button>
              <Button size="sm" variant="outline" onClick={() => onDisconnect(slug)} aria-label={MARKETPLACE_CARD.disconnectLabel(name)} className="marketplace-plate__disconnect">
                {MARKETPLACE_CARD.disconnect}
              </Button>
            </>
          )}
          {!connection && available && (
            <Button
              size="sm"
              icon="link"
              iconPosition="start"
              iconSize={16}
              onClick={() => onConnect(slug)}
              aria-label={MARKETPLACE_CARD.connectLabel(name)}
            >
              {canConnect ? MARKETPLACE_CARD.connect : MARKETPLACE_CARD.limitReached}
            </Button>
          )}
          {soon && <p className="marketplace-plate__soon">{MARKETPLACE_CARD.soonLabel(name)}</p>}
        </div>
      </div>
    </li>
  );
}
