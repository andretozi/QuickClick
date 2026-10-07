import { useState } from 'react';
import Field from './Field.jsx';
import Icon from '@/presentation/components/Icon/Icon.jsx';

/** Campo de senha com botão para mostrar/ocultar. Props extras vão para o <input>. */
export default function PasswordField({ id, label, aside, ...inputProps }) {
  const [visible, setVisible] = useState(false);

  return (
    <Field id={id} label={label} aside={aside}>
      <div className="field__control">
        <input
          id={id}
          type={visible ? 'text' : 'password'}
          className="field__input field__input--with-action"
          {...inputProps}
        />
        <button
          type="button"
          className="field__action"
          aria-label={visible ? 'Ocultar senha' : 'Mostrar senha'}
          aria-pressed={visible}
          onClick={() => setVisible((current) => !current)}
        >
          <Icon name={visible ? 'eye-off' : 'eye'} size={20} />
        </button>
      </div>
    </Field>
  );
}
