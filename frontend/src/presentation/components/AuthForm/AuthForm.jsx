import FormAlert from '@/presentation/components/FormAlert/FormAlert.jsx';
import './AuthForm.css';

/** Links que ainda não têm página: não saem da tela atual. */
const preventNavigation = (event) => event.preventDefault();

/**
 * Moldura comum dos formulários de entrada (login e cadastro): título, apoio,
 * aviso de erro do formulário, o conteúdo, o link para a outra tela e os termos.
 * - alert: { title, text } ou nada
 * - switchTo: { text, link, href } (ex.: "Novo por aqui? Criar conta grátis")
 * - terms: { before, terms, between, privacy, end }
 */
export default function AuthForm({ title, lead, alert, switchTo, terms, children }) {
  return (
    <div data-enter="4" className="auth-form">
      <header className="auth-form__header">
        <h2 data-page-focus tabIndex={-1} className="heading auth-form__title">
          {title}
        </h2>
        <p className="auth-form__lead">{lead}</p>
      </header>

      {alert && <FormAlert title={alert.title} text={alert.text} className="auth-form__alert" />}

      {children}

      <p className="auth-form__switch">
        {switchTo.text}{' '}
        <a href={switchTo.href} className="auth-form__switch-link">
          {switchTo.link}
        </a>
      </p>

      <p className="auth-form__terms">
        {terms.before}{' '}
        <a href="#" className="auth-form__terms-link" onClick={preventNavigation}>
          {terms.terms}
        </a>{' '}
        {terms.between}{' '}
        <a href="#" className="auth-form__terms-link" onClick={preventNavigation}>
          {terms.privacy}
        </a>
        {terms.end}
      </p>
    </div>
  );
}
