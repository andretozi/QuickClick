import AuthForm from '@/presentation/components/AuthForm/AuthForm.jsx';
import Button from '@/presentation/components/Button/Button.jsx';
import Divider from '@/presentation/components/Divider/Divider.jsx';
import TextField from '@/presentation/components/Field/TextField.jsx';
import PasswordField from '@/presentation/components/Field/PasswordField.jsx';
import SocialLogin from '../SocialLogin/SocialLogin.jsx';
import useLoginForm from '@/application/auth/useLoginForm.js';
import { LOGIN_FORM, SOCIAL_PROVIDERS } from '@/domain/content/loginContent.js';
import { FIELD_ERRORS } from '@/domain/content/commonContent.js';
import './LoginForm.css';

/** Formulário de login. O estado, a validação e o envio ficam no hook useLoginForm. */
export default function LoginForm() {
  const {
    values,
    errors,
    formRef,
    handleChange,
    handleSubmit,
    loading,
    formError,
    announceSocialSoon,
    announceForgotSoon
  } = useLoginForm();
  const { title, lead, divider, email, password, submit, signup, terms } = LOGIN_FORM;

  return (
    <AuthForm
      title={title}
      lead={lead}
      alert={formError ? LOGIN_FORM.errors[formError] : null}
      switchTo={signup}
      terms={terms}
    >
      <SocialLogin providers={SOCIAL_PROVIDERS} onSelect={announceSocialSoon} />

      <Divider>{divider}</Divider>

      <form ref={formRef} className="login-form" onSubmit={handleSubmit} noValidate>
        <TextField
          id="login-email"
          name="email"
          type="email"
          value={values.email}
          onChange={handleChange}
          label={email.label}
          placeholder={email.placeholder}
          autoComplete="email"
          error={FIELD_ERRORS[errors.email]}
        />
        <PasswordField
          id="login-password"
          name="password"
          value={values.password}
          onChange={handleChange}
          label={password.label}
          placeholder={password.placeholder}
          autoComplete="current-password"
          error={FIELD_ERRORS[errors.password]}
          aside={
            <a href="#" className="login-form__forgot" onClick={announceForgotSoon}>
              {password.forgot}
            </a>
          }
        />
        <Button
          type="submit"
          size="block"
          loading={loading}
          loadingText={submit.loading}
          disabled={loading}
          className="login-form__submit"
        >
          {submit.label}
        </Button>
      </form>
    </AuthForm>
  );
}
