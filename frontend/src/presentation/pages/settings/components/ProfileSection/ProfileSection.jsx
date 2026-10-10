import Avatar from '@/presentation/components/Avatar/Avatar.jsx';
import Button from '@/presentation/components/Button/Button.jsx';
import TextField from '@/presentation/components/Field/TextField.jsx';
import SettingsSection from '../SettingsSection/SettingsSection.jsx';
import { cx } from '@/presentation/utils/cx.js';
import { PROFILE_SECTION, SETTINGS } from '@/domain/content/settingsContent.js';
import { FIELD_ERRORS } from '@/domain/content/commonContent.js';
import './ProfileSection.css';

/** Perfil: nome, email, telefone, loja e a cor do avatar (a navbar muda na hora). */
export default function ProfileSection({ profile }) {
  const { values, errors, handleChange, formRef, save, saving, pickAvatarColor } = profile;
  const { fields, avatar } = PROFILE_SECTION;

  return (
    <SettingsSection id="perfil" title={PROFILE_SECTION.title} lead={PROFILE_SECTION.lead}>
      <form ref={formRef} className="profile-section" onSubmit={save} noValidate>
        <div className="profile-section__identity">
          <Avatar name={values.name || '?'} color={values.avatarColor} size="xl" />
          <fieldset className="profile-section__colors">
            <legend className="profile-section__legend">{avatar.label}</legend>
            {avatar.options.map((option) => (
              <label
                key={option.value}
                className={cx(
                  'profile-section__color',
                  `profile-section__color--${option.value}`,
                  values.avatarColor === option.value && 'profile-section__color--active'
                )}
              >
                <input
                  type="radio"
                  name="avatarColor"
                  value={option.value}
                  checked={values.avatarColor === option.value}
                  onChange={() => pickAvatarColor(option.value)}
                  className="visually-hidden"
                />
                <span className="profile-section__swatch" aria-hidden="true" />
                <span className="profile-section__color-label">{option.label}</span>
              </label>
            ))}
          </fieldset>
        </div>

        <div className="profile-section__grid">
          <TextField id="perfil-nome" name="name" label={fields.name.label} placeholder={fields.name.placeholder} value={values.name} onChange={handleChange} autoComplete="name" error={FIELD_ERRORS[errors.name]} />
          <TextField id="perfil-email" name="email" type="email" label={fields.email.label} placeholder={fields.email.placeholder} value={values.email} onChange={handleChange} autoComplete="email" error={FIELD_ERRORS[errors.email]} />
          <TextField id="perfil-telefone" name="phone" type="tel" inputMode="tel" label={fields.phone.label} placeholder={fields.phone.placeholder} hint={fields.phone.hint} value={values.phone} onChange={handleChange} autoComplete="tel" error={FIELD_ERRORS[errors.phone]} />
          <TextField id="perfil-loja" name="store" label={fields.store.label} placeholder={fields.store.placeholder} value={values.store} onChange={handleChange} error={FIELD_ERRORS[errors.store]} />
        </div>

        <div className="profile-section__actions">
          <Button type="submit" icon="check" iconPosition="start" iconSize={17} loading={saving} loadingText={SETTINGS.saving} disabled={saving}>
            {SETTINGS.save}
          </Button>
        </div>
      </form>
    </SettingsSection>
  );
}
