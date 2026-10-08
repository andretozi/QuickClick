import { useRef } from 'react';
import Button from '@/presentation/components/Button/Button.jsx';
import MarketplaceMark from '@/presentation/components/MarketplaceMark/MarketplaceMark.jsx';
import useConnectedEffect from '@/application/animation/useConnectedEffect.js';
import { cx } from '@/presentation/utils/cx.js';
import { MARKETPLACE_CARD, getMarketplaceInfo } from '@/domain/content/marketplacesContent.js';
import './MarketplaceCard.css';

/** Check do selo "Conectado". O traço se desenha (JS) quando a conexão acaba de acontecer. */
function StatusCheck() {
  return (
    <svg width="14" height="14" viewBox="0 0 24 24" fill="none" className="marketplace-card__check" aria-hidden="true">
      <path data-part="check" d="M5 12.5l4 4L19 7" pathLength="1" className="marketplace-card__check-path" />
    </svg>
  );
}

/**
 * Card de um marketplace: monograma, nome, situação e a ação.
 * A ação é sempre o mesmo botão (muda só o texto), então o foco do teclado
 * continua nele depois de conectar ou desconectar.
 */
export default function MarketplaceCard({ marketplace, busy, failed, celebrate, onConnect, onDisconnect, ...rest }) {
  const cardRef = useRef(null);
  useConnectedEffect(cardRef, celebrate);

  const { slug, name, available, connected } = marketplace;
  const { monogram } = getMarketplaceInfo(slug, name);
  const status = connected ? 'connected' : available ? 'available' : 'soon';
  const { actions, actionLabel } = MARKETPLACE_CARD;

  const action = {
    connected: {
      label: actions.disconnect,
      ariaLabel: actionLabel.disconnect(name),
      variant: 'outline',
      onClick: () => onDisconnect(slug)
    },
    available: {
      label: actions.connect,
      ariaLabel: actionLabel.connect(name),
      variant: 'primary',
      onClick: () => onConnect(slug)
    },
    soon: { label: actions.soon, ariaLabel: actionLabel.soon(name), variant: 'light', disabled: true }
  }[status];

  return (
    <li ref={cardRef} className={cx('marketplace-card', `marketplace-card--${status}`)} {...rest}>
      <div className="marketplace-card__head">
        <span className="marketplace-card__mark">
          <span data-part="wave" className="marketplace-card__wave" aria-hidden="true" />
          <MarketplaceMark slug={slug} monogram={monogram} />
        </span>
        <div>
          <h2 className="marketplace-card__name">{name}</h2>
          <p data-part="status" className="marketplace-card__status">
            {connected ? <StatusCheck /> : <span className="marketplace-card__dot" aria-hidden="true" />}
            {MARKETPLACE_CARD.status[status]}
          </p>
        </div>
      </div>

      {failed && (
        <p className="marketplace-card__error" role="alert">
          {MARKETPLACE_CARD.disconnectError}
        </p>
      )}

      <Button
        variant={action.variant}
        size="sm"
        className="marketplace-card__action"
        aria-label={action.ariaLabel}
        disabled={action.disabled || busy}
        loading={busy}
        loadingText={actions.disconnecting}
        onClick={action.onClick}
      >
        {action.label}
      </Button>
    </li>
  );
}
