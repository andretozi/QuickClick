import Button from '@/presentation/components/Button/Button.jsx';
import Icon from '@/presentation/components/Icon/Icon.jsx';
import PasswordField from '@/presentation/components/Field/PasswordField.jsx';
import SettingsSection from '../SettingsSection/SettingsSection.jsx';
import { SECURITY_SECTION } from '@/domain/content/settingsContent.js';
import { FIELD_ERRORS } from '@/domain/content/commonContent.js';
import './SecuritySection.css';

/** Segurança: trocar a senha (confere a atual antes). */
export default function SecuritySection({ security }) {
  const { values, errors, handleChange, formRef, save, saving } = security;
  const { fields } = SECURITY_SECTION;

  return (
    <SettingsSection id="seguranca" title={SECURITY_SECTION.title} lead={SECURITY_SECTION.lead}>
      <form ref={formRef} className="security-section" onSubmit={save} noValidate>
        <PasswordField id="senha-atual" name="current" label={fields.current.label} placeholder={fields.current.placeholder} value={values.current} onChange={handleChange} autoComplete="current-password" error={FIELD_ERRORS[errors.current]} />
        <div className="security-section__pair">
          <PasswordField id="senha-nova" name="next" label={fields.next.label} placeholder={fields.next.placeholder} value={values.next} onChange={handleChange} autoComplete="new-password" error={FIELD_ERRORS[errors.next]} />
          <PasswordField id="senha-confirmacao" name="confirmation" label={fields.confirmation.label} placeholder={fields.confirmation.placeholder} value={values.confirmation} onChange={handleChange} autoComplete="new-password" error={FIELD_ERRORS[errors.confirmation]} />
        </div>
        <p className="security-section__note">
          <Icon name="shield" size={16} />
          {SECURITY_SECTION.note}
        </p>
        <div className="security-section__actions">
          <Button type="submit" icon="lock" iconPosition="start" iconSize={16} loading={saving} loadingText={SECURITY_SECTION.submitting} disabled={saving}>
            {SECURITY_SECTION.submit}
          </Button>
        </div>
      </form>
    </SettingsSection>
  );
}
