import { useRef } from 'react';
import Button from '@/presentation/components/Button/Button.jsx';
import Eyebrow from '@/presentation/components/Eyebrow/Eyebrow.jsx';
import Icon from '@/presentation/components/Icon/Icon.jsx';
import IconButton from '@/presentation/components/IconButton/IconButton.jsx';
import ParticleBurst from '@/presentation/components/ParticleBurst/ParticleBurst.jsx';
import useWelcomeAnimation from '@/application/animation/useWelcomeAnimation.js';
import { WELCOME } from '@/domain/content/dashboardContent.js';
import './WelcomeBanner.css';

/** Comemoração logo depois de criar a conta, com os dois próximos passos. Aparece uma vez. */
export default function WelcomeBanner({ firstName, onClose }) {
  const ref = useRef(null);
  useWelcomeAnimation(ref);

  return (
    <section ref={ref} className="welcome-banner" aria-labelledby="boas-vindas-titulo">
      <ParticleBurst data-part="particles" className="welcome-banner__burst" />
      <span className="welcome-banner__badge-wrap" aria-hidden="true">
        <span data-part="wave" className="welcome-banner__wave" />
        <span data-part="badge" className="welcome-banner__badge">
          <Icon name="check" size={30} />
        </span>
      </span>

      <div className="welcome-banner__text">
        <Eyebrow tone="coral" className="welcome-banner__eyebrow">
          {WELCOME.eyebrow}
        </Eyebrow>
        <h2 id="boas-vindas-titulo" className="heading welcome-banner__title">
          {WELCOME.title(firstName)}
        </h2>
        <p className="welcome-banner__lead">{WELCOME.text}</p>
        <div className="welcome-banner__actions">
          <Button href={WELCOME.connect.href} size="sm" icon="link" iconPosition="start" iconSize={16}>
            {WELCOME.connect.label}
          </Button>
          <Button href={WELCOME.create.href} size="sm" variant="light" icon="camera" iconPosition="start" iconSize={16}>
            {WELCOME.create.label}
          </Button>
        </div>
      </div>

      <IconButton icon="x" label={WELCOME.close} tone="glass" size="sm" className="welcome-banner__close" onClick={onClose} />
    </section>
  );
}
