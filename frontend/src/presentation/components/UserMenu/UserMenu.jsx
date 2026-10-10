import { useId } from 'react';
import Avatar from '@/presentation/components/Avatar/Avatar.jsx';
import Icon from '@/presentation/components/Icon/Icon.jsx';
import StatusPill from '@/presentation/components/StatusPill/StatusPill.jsx';
import useMenu from '@/application/ui/useMenu.js';
import usePresence from '@/application/ui/usePresence.js';
import { useMenuAnimation } from '@/application/animation/useOverlayAnimation.js';
import { cx } from '@/presentation/utils/cx.js';
import { USER_MENU, planName } from '@/domain/content/appContent.js';
import './UserMenu.css';

const EXIT_MS = 180;

function MenuPanel({ menu, menuId, account, closing, onSignOut, signingOut }) {
  useMenuAnimation(menu.menuRef, closing);
  const closeAfterChoice = () => menu.close({ returnFocus: false });

  return (
    <div ref={menu.menuRef} className={cx('user-menu__panel', closing && 'user-menu__panel--closing')} onKeyDown={menu.onMenuKeyDown}>
      <div className="user-menu__header">
        <Avatar name={account.name} color={account.avatarColor} size="lg" />
        <div className="user-menu__who">
          <p className="user-menu__name">{account.name}</p>
          <p className="user-menu__email">{account.email}</p>
          <StatusPill tone="cream" size="sm" className="user-menu__plan">
            {USER_MENU.plan(planName(account.plan))}
          </StatusPill>
        </div>
      </div>

      <ul id={menuId} role="menu" aria-label={USER_MENU.label} className="user-menu__list">
        {USER_MENU.links.map((link) => (
          <li key={link.id} role="none" className={cx('user-menu__entry', link.compactOnly && 'user-menu__entry--compact')}>
            <a
              role="menuitem"
              tabIndex={-1}
              data-menu-item
              data-part="item"
              href={link.href}
              className="user-menu__item"
              onClick={closeAfterChoice}
            >
              <Icon name={link.icon} size={18} className="user-menu__item-icon" />
              {link.label}
            </a>
          </li>
        ))}
        <li role="separator" className="user-menu__separator" />
        <li role="none" className="user-menu__entry">
          <button
            type="button"
            role="menuitem"
            tabIndex={-1}
            data-menu-item
            data-part="item"
            className="user-menu__item user-menu__item--exit"
            onClick={onSignOut}
            disabled={signingOut}
          >
            <Icon name="logout" size={18} className="user-menu__item-icon" />
            {signingOut ? USER_MENU.signingOut : USER_MENU.signOut}
          </button>
        </li>
      </ul>
    </div>
  );
}

/**
 * Avatar do vendedor no navbar, com o menu da conta: nome, email, plano,
 * Marketplaces, Configurações, Ver site e Sair. Abre com mola sobre vidro escuro.
 * Teclado: setas, Home e End; Esc fecha e devolve o foco ao avatar; clicar fora fecha.
 */
export default function UserMenu({ account, tone = 'light', onSignOut, signingOut }) {
  const menu = useMenu();
  const { mounted, closing } = usePresence(menu.open, EXIT_MS);
  const menuId = `${useId()}menu`;

  return (
    <div className={cx('user-menu', `user-menu--${tone}`)}>
      <button
        ref={menu.buttonRef}
        type="button"
        className={cx('user-menu__button', menu.open && 'user-menu__button--open')}
        aria-haspopup="menu"
        aria-expanded={menu.open}
        aria-controls={menu.open ? menuId : undefined}
        aria-label={USER_MENU.button(account.name)}
        onClick={menu.toggle}
        onKeyDown={menu.onButtonKeyDown}
      >
        <Avatar name={account.name} color={account.avatarColor} size="md" />
        <span className="user-menu__first-name" aria-hidden="true">
          {account.name.split(' ')[0]}
        </span>
        <Icon name="chevron-down" size={16} className="user-menu__chevron" />
      </button>

      {mounted && (
        <MenuPanel
          menu={menu}
          menuId={menuId}
          account={account}
          closing={closing}
          onSignOut={onSignOut}
          signingOut={signingOut}
        />
      )}
    </div>
  );
}
