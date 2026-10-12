import Button from '@/presentation/components/Button/Button.jsx';
import usePressFeedback from '@/application/animation/usePressFeedback.js';
import './SocialLogin.css';

/**
 * Botões "Continuar com Google, Apple e Facebook". Ainda não entram: dão o
 * feedback de clique e chamam `onSelect(provider)`, que mostra o aviso de "em breve".
 */
export default function SocialLogin({ providers, onSelect }) {
  const handlePress = usePressFeedback();

  return (
    <div className="social-login">
      {providers.map((provider) => (
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
      ))}
    </div>
  );
}
