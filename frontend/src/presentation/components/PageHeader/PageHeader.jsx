import Eyebrow from '@/presentation/components/Eyebrow/Eyebrow.jsx';
import { cx } from '@/presentation/utils/cx.js';
import './PageHeader.css';

/**
 * Topo das páginas logadas: eyebrow, título (recebe o foco ao abrir a página),
 * texto de apoio e as ações à direita. `children` entra embaixo do texto (selos, metadados).
 */
export default function PageHeader({ eyebrow, title, lead, actions, children, className }) {
  return (
    <header className={cx('page-header', className)}>
      <div className="page-header__text">
        {eyebrow && (
          <Eyebrow data-enter="1" tone="honey" className="page-header__eyebrow">
            {eyebrow}
          </Eyebrow>
        )}
        <h1 data-enter="1" data-page-focus tabIndex={-1} className="heading page-header__title">
          {title}
        </h1>
        {lead && (
          <p data-enter="1" className="page-header__lead">
            {lead}
          </p>
        )}
        {children && (
          <div data-enter="2" className="page-header__extra">
            {children}
          </div>
        )}
      </div>
      {actions && (
        <div data-enter="2" className="page-header__actions">
          {actions}
        </div>
      )}
    </header>
  );
}
