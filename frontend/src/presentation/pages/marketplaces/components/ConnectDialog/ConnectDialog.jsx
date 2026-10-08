import { useRef } from 'react';
import Button from '@/presentation/components/Button/Button.jsx';
import Icon from '@/presentation/components/Icon/Icon.jsx';
import LogoMark from '@/presentation/components/Brand/LogoMark.jsx';
import MarketplaceMark from '@/presentation/components/MarketplaceMark/MarketplaceMark.jsx';
import useDialogAnimations from '@/application/animation/useDialogAnimations.js';
import { DIALOG_STEPS } from '@/application/marketplaces/useMarketplaces.js';
import { cx } from '@/presentation/utils/cx.js';
import { CONNECT_DIALOG, getMarketplaceInfo } from '@/domain/content/marketplacesContent.js';
import './ConnectDialog.css';

const TITLE_ID = 'connect-dialog-title';
const TEXT_ID = 'connect-dialog-text';

/** Logo da Quick Click e monograma do marketplace, ligados pelo cadeado ou pelos pontos andando. */
function Handshake({ info, waiting = false }) {
  return (
    <div className="connect-dialog__handshake" aria-hidden="true">
      <LogoMark size="lg" />
      {waiting ? (
        <span className="connect-dialog__dots">
          <span data-part="dot" className="connect-dialog__dot" />
          <span data-part="dot" className="connect-dialog__dot" />
          <span data-part="dot" className="connect-dialog__dot" />
        </span>
      ) : (
        <span className="connect-dialog__lock">
          <Icon name="lock" size={18} />
        </span>
      )}
      <MarketplaceMark slug={info.slug} monogram={info.monogram} />
    </div>
  );
}

function ConfirmStep({ info, words, onConfirm, onClose }) {
  const { confirm } = CONNECT_DIALOG;
  return (
    <>
      <Handshake info={info} />
      <h2 id={TITLE_ID} className="heading connect-dialog__title">
        {confirm.title(words.name)}
      </h2>
      <p id={TEXT_ID} className="connect-dialog__text">
        {confirm.text(words)}
      </p>
      <div className="connect-dialog__actions">
        <Button size="block" onClick={onConfirm} autoFocus>
          {confirm.confirm(words)}
        </Button>
        <Button size="block" variant="outline" onClick={onClose}>
          {confirm.cancel}
        </Button>
      </div>
    </>
  );
}

function AuthorizingStep({ info, words }) {
  const { authorizing } = CONNECT_DIALOG;
  return (
    <>
      <Handshake info={info} waiting />
      <h2 id={TITLE_ID} className="heading connect-dialog__title">
        {authorizing.title}
      </h2>
      <p id={TEXT_ID} className="connect-dialog__text" role="status">
        {authorizing.text(words)}
      </p>
    </>
  );
}

/** Erro amigável: a mensagem vem do back; título e ações vêm do conteúdo de cada tipo de erro. */
function ErrorStep({ error, onRetry, onClose }) {
  const texts = CONNECT_DIALOG.errors[error.kind] ?? CONNECT_DIALOG.errors.unknown;
  const { action, canRetry } = texts;

  return (
    <>
      <span className={cx('connect-dialog__icon', action && 'connect-dialog__icon--plan')} aria-hidden="true">
        <Icon name={action ? 'trend-up' : 'x'} size={26} />
      </span>
      <h2 id={TITLE_ID} className="heading connect-dialog__title">
        {texts.title}
      </h2>
      <p id={TEXT_ID} className="connect-dialog__text" role="alert">
        {error.message || texts.fallback}
      </p>
      <div className="connect-dialog__actions">
        {action && (
          <Button size="block" href={action.href} icon="arrow-right" autoFocus>
            {action.label}
          </Button>
        )}
        {canRetry && (
          <Button size="block" onClick={onRetry} autoFocus>
            {CONNECT_DIALOG.retry}
          </Button>
        )}
        <Button size="block" variant={action || canRetry ? 'outline' : 'dark'} onClick={onClose} autoFocus={!action && !canRetry}>
          {CONNECT_DIALOG.dismiss}
        </Button>
      </div>
    </>
  );
}

/**
 * Diálogo de conexão, em três etapas: confirmar, "Autorizando…" e, se der errado, o erro.
 * Esc e o clique fora fecham (menos no meio da autorização).
 */
export default function ConnectDialog({ dialog, onConfirm, onClose }) {
  const dialogRef = useRef(null);
  const stepRef = useRef(null);
  const { marketplace, step, error } = dialog;
  useDialogAnimations(dialogRef, stepRef, step);

  const info = getMarketplaceInfo(marketplace.slug, marketplace.name);
  const words = { name: marketplace.name, article: info.article };
  const authorizing = step === DIALOG_STEPS.AUTHORIZING;

  const handleKeyDown = (event) => {
    if (event.key === 'Escape') onClose();
  };

  return (
    <div ref={dialogRef} className="connect-dialog" onKeyDown={handleKeyDown}>
      <div data-part="backdrop" className="connect-dialog__backdrop" onClick={onClose} />
      <div
        data-part="panel"
        className="connect-dialog__panel"
        role="dialog"
        aria-modal="true"
        aria-labelledby={TITLE_ID}
        aria-describedby={TEXT_ID}
        aria-busy={authorizing || undefined}
      >
        <button
          type="button"
          className="connect-dialog__close"
          aria-label={CONNECT_DIALOG.close}
          onClick={onClose}
          disabled={authorizing}
        >
          <Icon name="x" size={20} />
        </button>

        <div key={step} ref={stepRef} className="connect-dialog__step">
          {step === DIALOG_STEPS.CONFIRM && (
            <ConfirmStep info={info} words={words} onConfirm={onConfirm} onClose={onClose} />
          )}
          {step === DIALOG_STEPS.AUTHORIZING && <AuthorizingStep info={info} words={words} />}
          {step === DIALOG_STEPS.ERROR && <ErrorStep error={error} onRetry={onConfirm} onClose={onClose} />}
        </div>
      </div>
    </div>
  );
}
