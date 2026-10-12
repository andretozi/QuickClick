import Icon from '@/presentation/components/Icon/Icon.jsx';
import { cx } from '@/presentation/utils/cx.js';
import './FormAlert.css';

/**
 * Erro de um formulário inteiro (ex.: "Não deu pra entrar agora").
 * É anunciado pelo leitor de tela assim que aparece.
 */
export default function FormAlert({ title, text, className }) {
  return (
    <div role="alert" className={cx('form-alert', 'form-alert--error', className)}>
      <span className="form-alert__icon" aria-hidden="true">
        <Icon name="alert" size={18} />
      </span>
      <div>
        <p className="form-alert__title">{title}</p>
        {text && <p className="form-alert__text">{text}</p>}
      </div>
    </div>
  );
}
