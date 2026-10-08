import Brand from '@/presentation/components/Brand/Brand.jsx';
import Button from '@/presentation/components/Button/Button.jsx';
import { NAV } from '@/domain/content/landingContent.js';
import './Nav.css';

/** Menu fixo do topo. O efeito de esconder/mostrar ao rolar fica em animations/navigation.js. */
export default function Nav() {
  return (
    <nav data-nav className="site-nav" aria-label={NAV.ariaLabel}>
      <div className="site-nav__inner">
        <Brand href="#top" size="lg" tone="light" />

        <div className="site-nav__actions">
          {NAV.links.map((link) => (
            <a key={link.href} href={link.href} className="site-nav__link">
              {link.label}
            </a>
          ))}
          <Button href={NAV.login.href} variant="outline" size="sm" icon="user" iconPosition="start" iconSize={16}>
            {NAV.login.label}
          </Button>
          <Button href={NAV.cta.href} size="sm" className="site-nav__cta">
            {NAV.cta.label}
          </Button>
        </div>
      </div>
    </nav>
  );
}
