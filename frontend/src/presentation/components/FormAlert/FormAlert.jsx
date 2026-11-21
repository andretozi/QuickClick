import Icon from '@/presentation/components/Icon/Icon.jsx';
import { cx } from '@/presentation/utils/cx.js';
import './FormAlert.css';

/**
 * Alerta ou aviso de formulário (ex.: "Não deu pra entrar agora" ou banner informativo).
 * É anunciado pelo leitor de tela assim que aparece.
 */
export default function FormAlert({ tone = 'error', title, text, children, className }) {
  const isInfo = tone === 'info';
  return (
    <div role={isInfo ? 'status' : 'alert'} className={cx('form-alert', `form-alert--${tone}`, className)}>
      <span className="form-alert__icon" aria-hidden="true">
        <Icon name={isInfo ? 'info' : 'alert'} size={18} />
      </span>
      <div className="form-alert__body">
        {title && <p className="form-alert__title">{title}</p>}
        {text && <p className="form-alert__text">{text}</p>}
        {children && <div className="form-alert__text">{children}</div>}
      </div>
    </div>
  );
}
