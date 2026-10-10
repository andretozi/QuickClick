import AuthForm from '@/presentation/components/AuthForm/AuthForm.jsx';
import Button from '@/presentation/components/Button/Button.jsx';
import TextField from '@/presentation/components/Field/TextField.jsx';
import PasswordField from '@/presentation/components/Field/PasswordField.jsx';
import useSignupForm from '@/application/auth/useSignupForm.js';
import { SIGNUP_FORM } from '@/domain/content/authContent.js';
import { FIELD_ERRORS } from '@/domain/content/commonContent.js';
import './SignupForm.css';

/** Formulário de cadastro. Validação, envio e erros ficam no hook useSignupForm. */
export default function SignupForm() {
  const { values, errors, formRef, handleChange, handleSubmit, loading, formError } = useSignupForm();
  const { title, lead, name, email, store, password, confirmation, submit, login, terms } = SIGNUP_FORM;
  const errorOf = (field) => FIELD_ERRORS[errors[field]];

  return (
    <AuthForm
      title={title}
      lead={lead}
      alert={formError ? SIGNUP_FORM.errors[formError] : null}
      switchTo={login}
      terms={terms}
    >
      <form ref={formRef} className="signup-form" onSubmit={handleSubmit} noValidate>
        <TextField
          id="signup-name"
          name="name"
          value={values.name}
          onChange={handleChange}
          label={name.label}
          placeholder={name.placeholder}
          autoComplete="name"
          error={errorOf('name')}
        />
        <TextField
          id="signup-email"
          name="email"
          type="email"
          value={values.email}
          onChange={handleChange}
          label={email.label}
          placeholder={email.placeholder}
          autoComplete="email"
          error={errorOf('email')}
        />
        <TextField
          id="signup-store"
          name="store"
          value={values.store}
          onChange={handleChange}
          label={store.label}
          placeholder={store.placeholder}
          autoComplete="organization"
          hint={store.hint}
          error={errorOf('store')}
        />
        <div className="signup-form__pair">
          <PasswordField
            id="signup-password"
            name="password"
            value={values.password}
            onChange={handleChange}
            label={password.label}
            placeholder={password.placeholder}
            autoComplete="new-password"
            error={errorOf('password')}
          />
          <PasswordField
            id="signup-confirmation"
            name="confirmation"
            value={values.confirmation}
            onChange={handleChange}
            label={confirmation.label}
            placeholder={confirmation.placeholder}
            autoComplete="new-password"
            error={errorOf('confirmation')}
          />
        </div>
        <p className="signup-form__hint">{password.hint}</p>
        <Button
          type="submit"
          size="block"
          icon="arrow-right"
          loading={loading}
          loadingText={submit.loading}
          disabled={loading}
          className="signup-form__submit"
        >
          {submit.label}
        </Button>
      </form>
    </AuthForm>
  );
}
