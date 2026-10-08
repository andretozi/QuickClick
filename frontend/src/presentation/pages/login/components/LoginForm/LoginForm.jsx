import Button from '@/presentation/components/Button/Button.jsx';
import Divider from '@/presentation/components/Divider/Divider.jsx';
import TextField from '@/presentation/components/Field/TextField.jsx';
import PasswordField from '@/presentation/components/Field/PasswordField.jsx';
import SocialLogin from '../SocialLogin/SocialLogin.jsx';
import useLoginForm from '@/application/auth/useLoginForm.js';
import { LOGIN_FORM, SOCIAL_PROVIDERS } from '@/domain/content/loginContent.js';
import './LoginForm.css';

/** Links que ainda não têm página: não saem da tela atual. */
const preventNavigation = (event) => event.preventDefault();

/** Formulário de login. O estado e o envio ficam no hook useLoginForm (camada de aplicação). */
export default function LoginForm() {
  const { credentials, loading, handleChange, handleSubmit } = useLoginForm();
  const { title, lead, divider, email, password, submit, signup, terms } = LOGIN_FORM;

  return (
    <div data-enter="4" className="login-form">
      <header className="login-form__header">
        <h2 className="heading login-form__title">{title}</h2>
        <p className="login-form__lead">{lead}</p>
      </header>

      <SocialLogin providers={SOCIAL_PROVIDERS} />

      <Divider>{divider}</Divider>

      <form className="login-form__fields" onSubmit={handleSubmit}>
        <TextField
          id="login-email"
          name="email"
          type="email"
          value={credentials.email}
          onChange={handleChange}
          label={email.label}
          placeholder={email.placeholder}
          autoComplete="email"
        />
        <PasswordField
          id="login-password"
          name="password"
          value={credentials.password}
          onChange={handleChange}
          label={password.label}
          placeholder={password.placeholder}
          autoComplete="current-password"
          aside={
            <a href="#" className="login-form__forgot" onClick={preventNavigation}>
              {password.forgot}
            </a>
          }
        />
        <Button
          type="submit"
          size="block"
          loading={loading}
          loadingText={submit.loading}
          className="login-form__submit"
        >
          {submit.label}
        </Button>
      </form>

      <p className="login-form__signup">
        {signup.text}{' '}
        <a href={signup.href} className="login-form__signup-link">
          {signup.link}
        </a>
      </p>

      <p className="login-form__terms">
        {terms.before}{' '}
        <a href="#" className="login-form__terms-link" onClick={preventNavigation}>
          {terms.terms}
        </a>{' '}
        {terms.between}{' '}
        <a href="#" className="login-form__terms-link" onClick={preventNavigation}>
          {terms.privacy}
        </a>
        .
      </p>
    </div>
  );
}
