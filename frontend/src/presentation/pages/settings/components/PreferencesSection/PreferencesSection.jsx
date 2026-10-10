import Toggle from '@/presentation/components/Toggle/Toggle.jsx';
import SettingsSection from '../SettingsSection/SettingsSection.jsx';
import { PREFERENCES_SECTION } from '@/domain/content/settingsContent.js';
import './PreferencesSection.css';

const NAMES = ['saleAlerts', 'lowStock', 'priceTips'];

/** Preferências: interruptores que salvam na hora (com toast). */
export default function PreferencesSection({ preferences, onToggle }) {
  return (
    <SettingsSection id="preferencias" title={PREFERENCES_SECTION.title} lead={PREFERENCES_SECTION.lead}>
      <ul className="preferences-section__list">
        {NAMES.map((name) => (
          <li key={name} className="preferences-section__item">
            <Toggle
              name={name}
              checked={Boolean(preferences?.[name])}
              disabled={!preferences}
              onChange={(checked) => onToggle(name, checked)}
              label={PREFERENCES_SECTION.items[name].label}
              description={PREFERENCES_SECTION.items[name].description}
            />
          </li>
        ))}
      </ul>
    </SettingsSection>
  );
}
