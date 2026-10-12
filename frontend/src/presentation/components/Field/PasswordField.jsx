import { useState } from 'react';
import Field, { describedBy } from './Field.jsx';
import Icon from '@/presentation/components/Icon/Icon.jsx';
import { PASSWORD_FIELD } from '@/domain/content/commonContent.js';

/** Campo de senha com botão para mostrar ou ocultar. Props extras vão para o <input>. */
export default function PasswordField({ id, label, aside, hint, error, className, ...inputProps }) {
  const [visible, setVisible] = useState(false);

  return (
    <Field id={id} label={label} aside={aside} hint={hint} error={error} className={className}>
      <div className="field__control">
        <input
          id={id}
          type={visible ? 'text' : 'password'}
          className="field__input field__input--with-action"
          aria-invalid={error ? true : undefined}
          aria-describedby={describedBy(id, { hint, error })}
          {...inputProps}
        />
        <button
          type="button"
          className="field__action"
          aria-label={visible ? PASSWORD_FIELD.hide : PASSWORD_FIELD.show}
          aria-pressed={visible}
          onClick={() => setVisible((current) => !current)}
        >
          <Icon name={visible ? 'eye-off' : 'eye'} size={20} />
        </button>
      </div>
    </Field>
  );
}
