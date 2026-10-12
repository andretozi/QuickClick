import Brand from '@/presentation/components/Brand/Brand.jsx';
import Button from '@/presentation/components/Button/Button.jsx';
import IconButton from '@/presentation/components/IconButton/IconButton.jsx';
import UserMenu from '@/presentation/components/UserMenu/UserMenu.jsx';
import useSession, { SESSION_STATUS } from '@/application/session/useSession.js';
import useSignOut from '@/application/session/useSignOut.js';
import { cx } from '@/presentation/utils/cx.js';
import { NAV } from '@/domain/content/landingContent.js';
import { APP_NAV } from '@/domain/content/appContent.js';
import './SiteNav.css';

/**
 * Navbar do site inteiro (landing e área logada).
 * - Visitante: links da landing, "Entrar" e "Começar grátis".
 * - Logado: Painel, Criar anúncio e o avatar com o menu da conta.
 * - tone: 'light' (landing, sobre areia) | 'dark' (área logada, sobre cacau)
 * - current: a rota aberta, para marcar o link da página atual
 * O efeito de vidro (e de sumir ao rolar, na landing) fica em animation/landing/navigation.js.
 */
export default function SiteNav({ tone = 'light', variant = 'landing', current }) {
  const session = useSession();
  const { signOut, signingOut } = useSignOut();
  const signedIn = session.status === SESSION_STATUS.SIGNED_IN;
  const checking = session.status === SESSION_STATUS.CHECKING;
  const brandHref = variant === 'app' ? APP_NAV.brandHref : '#top';

  return (
    <nav data-nav className={cx('site-nav', `site-nav--${tone}`)} aria-label={NAV.ariaLabel}>
      <div className="site-nav__inner">
        <Brand href={brandHref} size="lg" tone={tone === 'dark' ? 'dark' : 'light'} className="site-nav__brand" />

        {!checking && signedIn && (
          <div className="site-nav__actions">
            <a
              href={APP_NAV.dashboard.href}
              className={cx('site-nav__link', 'site-nav__link--app', current === 'dashboard' && 'site-nav__link--current')}
              aria-current={current === 'dashboard' ? 'page' : undefined}
            >
              {APP_NAV.dashboard.label}
            </a>
            <Button
              href={APP_NAV.newListing.href}
              variant="outline"
              size="sm"
              icon="plus"
              iconPosition="start"
              iconSize={16}
              className="site-nav__outline site-nav__cta site-nav__cta--wide"
              aria-current={current === 'new-listing' ? 'page' : undefined}
            >
              {APP_NAV.newListing.label}
            </Button>
            <IconButton
              href={APP_NAV.newListing.href}
              icon="plus"
              label={APP_NAV.newListing.label}
              tone={tone === 'dark' ? 'glass' : 'paper'}
              className="site-nav__cta-icon"
            />
            <UserMenu account={session.account} tone={tone} onSignOut={signOut} signingOut={signingOut} />
          </div>
        )}

        {!checking && !signedIn && (
          <div className="site-nav__actions">
            {NAV.links.map((link) => (
              <a key={link.href} href={link.href} className="site-nav__link site-nav__link--section">
                {link.label}
              </a>
            ))}
            <Button
              href={NAV.login.href}
              variant="outline"
              size="sm"
              icon="user"
              iconPosition="start"
              iconSize={16}
              className="site-nav__outline"
            >
              {NAV.login.label}
            </Button>
            <Button href={NAV.cta.href} size="sm" className="site-nav__cta">
              {NAV.cta.label}
            </Button>
          </div>
        )}
      </div>
    </nav>
  );
}
