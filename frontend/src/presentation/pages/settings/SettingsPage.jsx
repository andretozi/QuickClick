import MarketplaceBoard from '@/presentation/components/MarketplaceBoard/MarketplaceBoard.jsx';
import PageHeader from '@/presentation/components/PageHeader/PageHeader.jsx';
import SegmentedControl from '@/presentation/components/SegmentedControl/SegmentedControl.jsx';
import SettingsSection from './components/SettingsSection/SettingsSection.jsx';
import ProfileSection from './components/ProfileSection/ProfileSection.jsx';
import SecuritySection from './components/SecuritySection/SecuritySection.jsx';
import PlanSection from './components/PlanSection/PlanSection.jsx';
import PreferencesSection from './components/PreferencesSection/PreferencesSection.jsx';
import DangerSection from './components/DangerSection/DangerSection.jsx';
import useSettings, { SETTINGS_SECTIONS } from '@/application/settings/useSettings.js';
import useMarketplaces from '@/application/marketplaces/useMarketplaces.js';
import { CONNECTIONS_SECTION, SETTINGS } from '@/domain/content/settingsContent.js';
import './SettingsPage.css';

/** Aba Conexões: o mesmo quadro da tela de marketplaces, mais compacto. */
function ConnectionsSection() {
  const marketplaces = useMarketplaces();
  return (
    <SettingsSection id="conexoes" tone="glass" title={CONNECTIONS_SECTION.title} lead={CONNECTIONS_SECTION.lead}>
      <MarketplaceBoard marketplaces={marketplaces} compact />
    </SettingsSection>
  );
}

/**
 * Configurações (#/configuracoes): navegação lateral com o indicador andando com mola
 * (no celular vira uma fileira de abas) e uma seção por vez.
 */
export default function SettingsPage() {
  const settings = useSettings();
  const { section, setSection } = settings;
  const { idPrefix } = SETTINGS;

  const views = {
    profile: <ProfileSection profile={settings.profile} />,
    security: <SecuritySection security={settings.security} />,
    plan: <PlanSection planId={settings.account?.plan} />,
    connections: <ConnectionsSection />,
    preferences: <PreferencesSection preferences={settings.preferences} onToggle={settings.togglePreference} />,
    danger: <DangerSection danger={settings.danger} />
  };

  return (
    <div className="settings-page">
      <PageHeader eyebrow={SETTINGS.eyebrow} title={SETTINGS.title} lead={SETTINGS.lead} />

      <div className="settings-page__layout">
        <SegmentedControl
          mode="tabs"
          orientation="vertical"
          idPrefix={idPrefix}
          label={SETTINGS.navLabel}
          value={section}
          onChange={setSection}
          options={SETTINGS_SECTIONS.map((id) => ({ value: id, ...SETTINGS.sections[id] }))}
          className="settings-page__nav"
        />
        <div
          key={section}
          role="tabpanel"
          id={`${idPrefix}-painel-${section}`}
          aria-labelledby={`${idPrefix}-aba-${section}`}
          className="settings-page__panel"
        >
          {views[section]}
        </div>
      </div>
    </div>
  );
}
