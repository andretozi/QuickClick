import { useEffect, useRef } from 'react';
import Button from '@/presentation/components/Button/Button.jsx';
import Icon from '@/presentation/components/Icon/Icon.jsx';
import MarketplaceLogo from '@/presentation/components/MarketplaceLogo/MarketplaceLogo.jsx';
import Modal from '@/presentation/components/Modal/Modal.jsx';
import ParticleBurst from '@/presentation/components/ParticleBurst/ParticleBurst.jsx';
import useCelebration from '@/application/animation/useCelebration.js';
import { CONNECT_STEPS } from '@/application/marketplaces/useMarketplaces.js';
import { CONNECT_DIALOG, getMarketplaceInfo } from '@/domain/content/marketplacesContent.js';
import './ConnectDialog.css';

/**
 * Palco do "Conectado": o selo recebe o clique do cursor da marca, o check se desenha
 * e as partículas formam a palavra. Dispara sozinho ao aparecer.
 */
function ConnectedStage() {
  const ref = useRef(null);
  const celebrate = useCelebration(ref);

  useEffect(() => {
    const timer = window.setTimeout(() => celebrate(CONNECT_DIALOG.connected.word), 160);
    return () => window.clearTimeout(timer);
  }, [celebrate]);

  return (
    <div ref={ref} className="connect-dialog__stage" aria-hidden="true">
      <ParticleBurst data-part="particles" />
      <span data-part="celebrate-cursor" className="connect-dialog__cursor">
        <Icon name="logo-spark" size={58} className="connect-dialog__cursor-icon" />
      </span>
      <span data-part="celebrate-target" className="connect-dialog__badge">
        <svg viewBox="0 0 24 24" className="connect-dialog__check">
          <path data-part="celebrate-check" d="M5 12.5l4.5 4.5L19 7.5" pathLength="1" />
        </svg>
      </span>
    </div>
  );
}

/** Logo do marketplace numa pastilha clara (acima do título). */
const LogoMedia = ({ slug }) => (
  <span className="connect-dialog__logo">
    <MarketplaceLogo slug={slug} size="lg" decorative />
  </span>
);

/**
 * Diálogo de conexão, que simula o OAuth do marketplace:
 * confirmar as permissões → "Indo para o Mercado Livre" (no amarelo da marca) →
 * "Autorizando" → "Conectado" (check se desenhando e partículas).
 * Também mostra o limite do plano e o erro. Recebe o que o useMarketplaces devolve.
 */
export default function ConnectDialog({ marketplaces }) {
  const { dialog, busyDialog, closeDialog, confirmConnect } = marketplaces;
  const info = dialog ? getMarketplaceInfo(dialog.slug) : getMarketplaceInfo('mercado-livre');
  const texts = CONNECT_DIALOG;

  const views = {
    [CONNECT_STEPS.CONFIRM]: {
      media: <LogoMedia slug={info.slug} />,
      title: texts.confirm.title(info.name),
      description: texts.confirm.text(info),
      body: (
        <div className="connect-dialog__permissions">
          <p className="connect-dialog__list-title">{texts.confirm.permissionsTitle}</p>
          <ul className="connect-dialog__list">
            {texts.confirm.permissions.map((permission) => (
              <li key={permission} className="connect-dialog__item">
                <Icon name="check-circle" size={18} className="connect-dialog__item-icon" />
                {permission}
              </li>
            ))}
          </ul>
          <p className="connect-dialog__never">
            <Icon name="shield" size={17} className="connect-dialog__never-icon" />
            {texts.confirm.never}
          </p>
        </div>
      ),
      actions: (
        <>
          <Button variant="outline" onClick={closeDialog}>
            {texts.confirm.cancel}
          </Button>
          <Button onClick={confirmConnect} icon="external" iconSize={16} data-autofocus>
            {texts.confirm.confirm(info)}
          </Button>
        </>
      )
    },
    [CONNECT_STEPS.REDIRECT]: {
      brand: true,
      media: (
        <span className="connect-dialog__redirect" role="status">
          <MarketplaceLogo slug={info.slug} size="xl" decorative />
          <span data-spin className="connect-dialog__spinner connect-dialog__spinner--brand" aria-hidden="true" />
        </span>
      ),
      title: texts.redirect.title(info.name),
      description: texts.redirect.text
    },
    [CONNECT_STEPS.AUTHORIZING]: {
      media: (
        <span className="connect-dialog__waiting" role="status">
          <span data-spin className="connect-dialog__spinner" aria-hidden="true" />
        </span>
      ),
      title: texts.authorizing.title,
      description: texts.authorizing.text(info)
    },
    [CONNECT_STEPS.CONNECTED]: {
      media: <ConnectedStage />,
      title: texts.connected.title,
      description: texts.connected.text(dialog?.nickname ?? ''),
      actions: (
        <Button onClick={closeDialog} icon="arrow-right" iconSize={16} data-autofocus>
          {texts.connected.done}
        </Button>
      )
    },
    [CONNECT_STEPS.LIMIT]: {
      icon: 'lock',
      iconTone: 'honey',
      title: texts.limit.title,
      description: texts.limit.text,
      actions: (
        <>
          <Button variant="outline" onClick={closeDialog}>
            {texts.close}
          </Button>
          <Button href={texts.limit.link.href} data-autofocus>
            {texts.limit.link.label}
          </Button>
        </>
      )
    },
    [CONNECT_STEPS.ERROR]: {
      icon: 'alert',
      iconTone: 'danger',
      title: texts.error.title,
      description: texts.error.text,
      actions: (
        <>
          <Button variant="outline" onClick={closeDialog}>
            {texts.close}
          </Button>
          <Button onClick={confirmConnect} data-autofocus>
            {texts.error.retry}
          </Button>
        </>
      )
    }
  };

  const view = views[dialog?.step] ?? views[CONNECT_STEPS.CONFIRM];

  return (
    <Modal
      open={Boolean(dialog)}
      onClose={closeDialog}
      dismissible={!busyDialog}
      size="md"
      media={view.media}
      icon={view.icon}
      iconTone={view.iconTone}
      title={view.title}
      description={view.description}
      actions={view.actions}
      className={view.brand ? 'connect-dialog connect-dialog--brand' : 'connect-dialog'}
    >
      {view.body}
    </Modal>
  );
}
