import { useRef } from 'react';
import Backdrop from '@/presentation/components/Backdrop/Backdrop.jsx';
import Brand from '@/presentation/components/Brand/Brand.jsx';
import Button from '@/presentation/components/Button/Button.jsx';
import Eyebrow from '@/presentation/components/Eyebrow/Eyebrow.jsx';
import Icon from '@/presentation/components/Icon/Icon.jsx';
import useSession, { SESSION_STATUS } from '@/application/session/useSession.js';
import { useStandaloneAnimations } from '@/application/animation/useShellAnimations.js';
import { NOT_FOUND } from '@/domain/content/appContent.js';
import './NotFoundPage.css';

/** Página 404: fundo cinematográfico, um "404" enorme e o caminho de volta. */
export default function NotFoundPage() {
  const rootRef = useRef(null);
  useStandaloneAnimations(rootRef);
  const session = useSession();
  const signedIn = session.status === SESSION_STATUS.SIGNED_IN;
  const { code, eyebrow, title, lead, home, dashboard } = NOT_FOUND;

  return (
    <div ref={rootRef} className="not-found">
      <Backdrop mode="contained" />
      <header className="not-found__top">
        <Brand href={home.href} size="md" tone="dark" />
      </header>

      <main className="not-found__main">
        <p data-enter="1" className="not-found__code" aria-hidden="true">
          {code}
          <Icon name="logo-spark" size={64} className="not-found__cursor" />
        </p>
        <Eyebrow data-enter="1" tone="coral">
          {eyebrow}
        </Eyebrow>
        <h1 data-enter="1" data-page-focus tabIndex={-1} className="heading not-found__title">
          {title}
        </h1>
        <p data-enter="2" className="not-found__lead">
          {lead}
        </p>
        <div data-enter="3" className="not-found__actions">
          <Button href={home.href} icon="arrow-left" iconPosition="start">
            {home.label}
          </Button>
          {signedIn && (
            <Button href={dashboard.href} variant="light" icon="grid" iconPosition="start">
              {dashboard.label}
            </Button>
          )}
        </div>
      </main>
    </div>
  );
}
