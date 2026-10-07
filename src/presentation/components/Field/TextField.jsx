import Field from './Field.jsx';

/** Campo de texto simples (e-mail, nome, etc.). Props extras vão para o <input>. */
export default function TextField({ id, label, aside, type = 'text', ...inputProps }) {
  return (
    <Field id={id} label={label} aside={aside}>
      <input id={id} type={type} className="field__input" {...inputProps} />
    </Field>
  );
}
