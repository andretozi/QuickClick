import { useId, useRef } from 'react';
import { createPortal } from 'react-dom';
import Icon from '@/presentation/components/Icon/Icon.jsx';
import usePresence from '@/application/ui/usePresence.js';
import useModal from '@/application/ui/useModal.js';
import { useModalAnimation } from '@/application/animation/useOverlayAnimation.js';
import { cx } from '@/presentation/utils/cx.js';
import { MODAL } from '@/domain/content/commonContent.js';
import './Modal.css';

const EXIT_MS = 260;

/**
 * Diálogo acessível do projeto (nunca window.confirm).
 * - Abre por cima de tudo (portal no body), com o resto do site inerte.
 * - Esc, o X e o clique no fundo fecham (menos quando `dismissible` é false).
 * - O foco entra no [data-autofocus] (ou no primeiro botão), fica preso e volta ao fechar.
 *
 * Props: open, onClose, title, description, icon, iconTone ('coral' | 'green' | 'honey' | 'danger'),
 * media (algo acima do título, no lugar do ícone: um logo, uma ilustração),
 * size ('sm' | 'md' | 'lg'), dismissible, actions (botões no rodapé), className, children.
 */
export default function Modal({ open, ...props }) {
  const { mounted, closing } = usePresence(open, EXIT_MS);
  if (!mounted) return null;
  return createPortal(<ModalLayer closing={closing} {...props} />, document.body);
}

function ModalLayer({
  closing,
  onClose,
  title,
  description,
  icon,
  iconTone = 'coral',
  media,
  size = 'md',
  dismissible = true,
  actions,
  className,
  children
}) {
  const rootRef = useRef(null);
  const panelRef = useRef(null);
  const id = useId();
  const titleId = `${id}titulo`;
  const textId = `${id}texto`;

  useModalAnimation(rootRef, closing);
  const { onKeyDown } = useModal({ active: !closing, panelRef, onClose, dismissible });

  return (
    <div ref={rootRef} className={cx('modal', closing && 'modal--closing')} onKeyDown={onKeyDown}>
      <div data-part="backdrop" className="modal__backdrop" onClick={dismissible ? onClose : undefined} />
      <div
        ref={panelRef}
        data-part="panel"
        role="dialog"
        aria-modal="true"
        aria-labelledby={titleId}
        aria-describedby={description ? textId : undefined}
        className={cx('modal__panel', `modal__panel--${size}`, className)}
      >
        {dismissible && (
          <button type="button" className="modal__close" aria-label={MODAL.close} onClick={onClose}>
            <Icon name="x" size={20} />
          </button>
        )}
        {media}
        {icon && (
          <span className={cx('modal__icon', `modal__icon--${iconTone}`)} aria-hidden="true">
            <Icon name={icon} size={26} />
          </span>
        )}
        <h2 id={titleId} className="heading modal__title">
          {title}
        </h2>
        {description && (
          <p id={textId} className="modal__text">
            {description}
          </p>
        )}
        {children}
        {actions && <div className="modal__actions">{actions}</div>}
      </div>
    </div>
  );
}
