import Panel from '@/presentation/components/Panel/Panel.jsx';
import { cx } from '@/presentation/utils/cx.js';
import './SettingsSection.css';

/** Moldura de cada seção das configurações: título, apoio e o conteúdo, num painel. */
export default function SettingsSection({ id, title, lead, tone = 'paper', className, children }) {
  return (
    <Panel tone={tone} data-enter="2" className={cx('settings-section', `settings-section--${tone}`, className)} aria-labelledby={`${id}-titulo`}>
      <header className="settings-section__head">
        <h2 id={`${id}-titulo`} className="heading settings-section__title">
          {title}
        </h2>
        {lead && <p className="settings-section__lead">{lead}</p>}
      </header>
      {children}
    </Panel>
  );
}
