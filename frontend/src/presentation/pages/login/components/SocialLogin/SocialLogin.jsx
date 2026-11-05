import { GoogleLogin } from '@react-oauth/google';
import Button from '@/presentation/components/Button/Button.jsx';
import usePressFeedback from '@/application/animation/usePressFeedback.js';
import './SocialLogin.css';

/**
 * Botões de login social.
 * Para o Google, renderiza o botão oficial (@react-oauth/google) quando o Client ID está configurado;
 * para Apple e Facebook (ainda em breve), exibe o aviso informativo ao clicar.
 */
export default function SocialLogin({
  providers,
  googleEnabled = false,
  onGoogleSuccess,
  onGoogleError,
  onSelect
}) {
  const handlePress = usePressFeedback();

  return (
    <div className="social-login">
      {providers.map((provider) => {
        if (provider.id === 'google' && googleEnabled) {
          return (
            <div key={provider.id} className="social-login__google">
              <GoogleLogin
                onSuccess={onGoogleSuccess}
                onError={onGoogleError}
                text="continue_with"
                shape="pill"
                size="large"
                theme="outline"
                width="380"
              />
            </div>
          );
        }

        return (
          <Button
            key={provider.id}
            variant={provider.variant}
            size="block"
            icon={provider.icon}
            iconSize={provider.iconSize}
            iconPosition="start"
            className={`social-login__button social-login__button--${provider.id}`}
            onClick={(event) => {
              handlePress(event);
              onSelect?.(provider);
            }}
          >
            {provider.label}
          </Button>
        );
      })}
    </div>
  );
}
