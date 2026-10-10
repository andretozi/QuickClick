import Button from '@/presentation/components/Button/Button.jsx';
import ConnectDialog from '@/presentation/components/ConnectDialog/ConnectDialog.jsx';
import Icon from '@/presentation/components/Icon/Icon.jsx';
import MarketplacePlate from '@/presentation/components/MarketplacePlate/MarketplacePlate.jsx';
import Modal from '@/presentation/components/Modal/Modal.jsx';
import Panel from '@/presentation/components/Panel/Panel.jsx';
import { cx } from '@/presentation/utils/cx.js';
import { isMultichannel } from '@/domain/plans/planRules.js';
import {
  DISCONNECT_DIALOG,
  MARKETPLACES_PAGE,
  PLAN_NOTICE,
  getMarketplaceInfo
} from '@/domain/content/marketplacesContent.js';
import { planName } from '@/domain/content/appContent.js';
import './MarketplaceBoard.css';

/**
 * Quadro de marketplaces: o aviso do plano, as placas (o Mercado Livre em destaque) e os
 * diálogos de conectar e desconectar. Usado na página #/marketplaces e na aba Conexões
 * das configurações. Recebe o que o useMarketplaces devolve.
 */
export default function MarketplaceBoard({ marketplaces, compact = false, className }) {
  const { status, plan, sync, canConnect, pendingDisconnect, disconnecting } = marketplaces;
  const pending = pendingDisconnect ? getMarketplaceInfo(pendingDisconnect) : null;
  const multichannel = isMultichannel(plan);
  const notice = multichannel
    ? PLAN_NOTICE.unlimited(planName(plan))
    : plan === 'gratis'
      ? PLAN_NOTICE.limited
      : PLAN_NOTICE.limitedOther(planName(plan));

  if (status === 'loading') {
    return (
      <Panel tone="glass" className="marketplace-board__status" role="status">
        <span data-spin className="marketplace-board__spinner" aria-hidden="true" />
        {MARKETPLACES_PAGE.loading}
      </Panel>
    );
  }

  if (status === 'error') {
    return (
      <Panel tone="glass" className="marketplace-board__status" role="alert">
        {MARKETPLACES_PAGE.loadError.title}
        <Button size="sm" variant="light" onClick={marketplaces.retry}>
          {MARKETPLACES_PAGE.loadError.retry}
        </Button>
      </Panel>
    );
  }

  return (
    <div className={cx('marketplace-board', compact && 'marketplace-board--compact', className)}>
      <p data-enter="2" className="marketplace-board__notice">
        <Icon name="info" size={18} className="marketplace-board__notice-icon" />
        <span>{notice}</span>
        {!multichannel && (
          <a href={PLAN_NOTICE.link.href} className="marketplace-board__notice-link">
            {PLAN_NOTICE.link.label}
            <Icon name="arrow-right" size={15} />
          </a>
        )}
      </p>

      <ul className="marketplace-board__grid" aria-label={MARKETPLACES_PAGE.listLabel}>
        {marketplaces.marketplaces.map((marketplace) => (
          <MarketplacePlate
            key={marketplace.slug}
            marketplace={marketplace}
            featured={marketplace.available && !compact}
            sync={sync}
            canConnect={canConnect}
            onConnect={marketplaces.openConnect}
            onSync={marketplaces.syncNow}
            onDisconnect={marketplaces.requestDisconnect}
          />
        ))}
      </ul>

      <ConnectDialog marketplaces={marketplaces} />

      <Modal
        open={Boolean(pendingDisconnect)}
        onClose={marketplaces.cancelDisconnect}
        dismissible={!disconnecting}
        size="sm"
        icon="link"
        iconTone="danger"
        title={pending ? DISCONNECT_DIALOG.title(pending.name) : ''}
        description={pending ? DISCONNECT_DIALOG.text(pending) : ''}
        actions={
          <>
            <Button variant="outline" onClick={marketplaces.cancelDisconnect} disabled={disconnecting} data-autofocus>
              {DISCONNECT_DIALOG.cancel}
            </Button>
            <Button
              onClick={marketplaces.confirmDisconnect}
              loading={disconnecting}
              loadingText={DISCONNECT_DIALOG.confirming}
              disabled={disconnecting}
            >
              {DISCONNECT_DIALOG.confirm}
            </Button>
          </>
        }
      />
    </div>
  );
}
