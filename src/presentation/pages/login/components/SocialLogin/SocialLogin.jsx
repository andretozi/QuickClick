import Button from '@/presentation/components/Button/Button.jsx';
import usePressFeedback from '@/application/animation/usePressFeedback.js';
import './SocialLogin.css';

/** Botões "Continuar com Google/Apple/Facebook". Por enquanto só dão o feedback de clique. */
export default function SocialLogin({ providers }) {
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
          onClick={handlePress}
        >
          {provider.label}
        </Button>
      ))}
    </div>
  );
}
