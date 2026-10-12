import { useId } from 'react';
import { cx } from '@/presentation/utils/cx.js';
import './Toggle.css';

/**
 * Interruptor (role="switch") com o botão andando com mola.
 * - checked, onChange(next)
 * - label: o que ele liga; description: uma linha explicando (ligada pelo aria-describedby)
 */
export default function Toggle({ checked, onChange, label, description, disabled = false, name, className }) {
  const id = useId();
  return (
    <div className={cx('toggle', disabled && 'toggle--disabled', className)}>
      <span className="toggle__text">
        <label htmlFor={id} className="toggle__label">
          {label}
        </label>
        {description && (
          <span id={`${id}-dica`} className="toggle__description">
            {description}
          </span>
        )}
      </span>
      <button
        id={id}
        type="button"
        role="switch"
        name={name}
        aria-checked={checked}
        aria-describedby={description ? `${id}-dica` : undefined}
        disabled={disabled}
        className={cx('toggle__switch', checked && 'toggle__switch--on')}
        onClick={() => onChange(!checked)}
      >
        <span className="toggle__thumb" aria-hidden="true" />
      </button>
    </div>
  );
}
