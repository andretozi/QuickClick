import Icon from '@/presentation/components/Icon/Icon.jsx';
import { cx } from '@/presentation/utils/cx.js';
import './FormAlert.css';

/**
 * Aviso de um formulário inteiro (ex.: "Email ou senha não conferem").
 * tone: 'error' | 'info' | 'success'. É anunciado pelo leitor de tela assim que aparece.
 */
export default function FormAlert({ tone = 'error', title, text, className }) {
  const icon = { error: 'alert', info: 'info', success: 'check' }[tone];
  return (
    <div role={tone === 'error' ? 'alert' : 'status'} className={cx('form-alert', `form-alert--${tone}`, className)}>
      <span className="form-alert__icon" aria-hidden="true">
        <Icon name={icon} size={18} />
      </span>
      <div>
        <p className="form-alert__title">{title}</p>
        {text && <p className="form-alert__text">{text}</p>}
      </div>
    </div>
  );
}
