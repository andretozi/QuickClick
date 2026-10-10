import { useCallback, useEffect, useRef, useState } from 'react';
import useForm from '@/application/ui/useForm.js';
import useSession from '@/application/session/useSession.js';
import { forgetSession, setSessionAccount } from '@/application/session/sessionStore.js';
import { showToast, TOAST_TONES } from '@/application/feedback/toastStore.js';
import {
  ACCOUNT_ERRORS,
  AccountError,
  changePassword,
  deleteAccount,
  updateAccount
} from '@/infrastructure/storage/accountsRepository.js';
import { endSession } from '@/infrastructure/storage/sessionRepository.js';
import { getPreferences, savePreferences } from '@/infrastructure/storage/preferencesRepository.js';
import {
  required,
  validateEmail,
  validateName,
  validateNewPassword,
  validatePasswordConfirmation,
  validatePhone
} from '@/domain/validation/validators.js';
import { DANGER_SECTION, SECURITY_SECTION, SETTINGS } from '@/domain/content/settingsContent.js';

export const SETTINGS_SECTIONS = ['profile', 'security', 'plan', 'connections', 'preferences', 'danger'];

const validateProfile = (values) => ({
  name: validateName(values.name),
  email: validateEmail(values.email),
  phone: values.phone.trim() ? validatePhone(values.phone) : null,
  store: validateName(values.store)
});

const validateSecurity = (values) => ({
  current: required(values.current),
  next: validateNewPassword(values.next),
  confirmation: validatePasswordConfirmation(values.next, values.confirmation)
});

const validateDanger = (values) => ({ password: required(values.password) });

const EMPTY_SECURITY = { current: '', next: '', confirmation: '' };

/**
 * Aplicação · Caso de uso "configurações da conta".
 * Perfil (a navbar se atualiza na hora), troca de senha, preferências com interruptores
 * e a exclusão da conta (apaga tudo dela deste navegador). A tela só desenha o que volta daqui.
 */
export default function useSettings() {
  const { account } = useSession();
  const accountId = account?.id;
  const [section, setSection] = useState(SETTINGS_SECTIONS[0]);
  const mounted = useRef(true);

  useEffect(() => {
    mounted.current = true;
    return () => {
      mounted.current = false;
    };
  }, []);

  const failed = () => showToast({ tone: TOAST_TONES.ERROR, ...SETTINGS.errorToast });

  // ---------- Perfil ----------
  const profile = useForm(
    {
      name: account?.name ?? '',
      email: account?.email ?? '',
      phone: account?.phone ?? '',
      store: account?.store ?? '',
      avatarColor: account?.avatarColor ?? 'coral'
    },
    validateProfile
  );
  const [savingProfile, setSavingProfile] = useState(false);

  const saveProfile = useCallback(
    async (event) => {
      event.preventDefault();
      if (savingProfile || !profile.check()) return;
      setSavingProfile(true);
      try {
        const updated = await updateAccount(accountId, profile.values);
        if (!mounted.current) return;
        setSessionAccount(updated);
        showToast({ tone: TOAST_TONES.SUCCESS, ...SETTINGS.savedToast });
      } catch (error) {
        if (!mounted.current) return;
        if (error instanceof AccountError && error.code === ACCOUNT_ERRORS.EMAIL_TAKEN) {
          profile.setFieldError('email', 'email-taken');
        } else failed();
      } finally {
        if (mounted.current) setSavingProfile(false);
      }
    },
    [accountId, profile, savingProfile]
  );

  /** A cor do avatar já aparece na navbar enquanto o vendedor escolhe. */
  const pickAvatarColor = useCallback(
    (color) => {
      profile.setField('avatarColor', color);
      if (account) setSessionAccount({ ...account, avatarColor: color });
    },
    [account, profile]
  );

  // ---------- Segurança ----------
  const security = useForm(EMPTY_SECURITY, validateSecurity);
  const [savingPassword, setSavingPassword] = useState(false);

  const savePassword = useCallback(
    async (event) => {
      event.preventDefault();
      if (savingPassword || !security.check()) return;
      setSavingPassword(true);
      try {
        await changePassword(accountId, security.values.current, security.values.next);
        if (!mounted.current) return;
        security.reset(EMPTY_SECURITY);
        showToast({ tone: TOAST_TONES.SUCCESS, ...SECURITY_SECTION.done });
      } catch (error) {
        if (!mounted.current) return;
        if (error instanceof AccountError && error.code === ACCOUNT_ERRORS.WRONG_PASSWORD) {
          security.setFieldError('current', 'wrong-password');
        } else failed();
      } finally {
        if (mounted.current) setSavingPassword(false);
      }
    },
    [accountId, savingPassword, security]
  );

  // ---------- Preferências ----------
  const [preferences, setPreferences] = useState(null);

  useEffect(() => {
    if (!accountId) return;
    getPreferences(accountId).then((value) => {
      if (mounted.current) setPreferences(value);
    });
  }, [accountId]);

  const togglePreference = useCallback(
    async (name, checked) => {
      const next = { ...preferences, [name]: checked };
      setPreferences(next);
      try {
        await savePreferences(accountId, next);
        if (mounted.current) showToast({ tone: TOAST_TONES.SUCCESS, ...SETTINGS.savedToast });
      } catch {
        if (mounted.current) failed();
      }
    },
    [accountId, preferences]
  );

  // ---------- Zona de risco ----------
  const [deleting, setDeleting] = useState(false);
  const [confirmingDelete, setConfirmingDelete] = useState(false);
  const danger = useForm({ password: '' }, validateDanger);

  const openDelete = useCallback(() => {
    danger.reset({ password: '' });
    setConfirmingDelete(true);
  }, [danger]);

  const cancelDelete = useCallback(() => {
    if (!deleting) setConfirmingDelete(false);
  }, [deleting]);

  const confirmDelete = useCallback(
    async (event) => {
      event?.preventDefault();
      if (deleting || !danger.check()) return;
      setDeleting(true);
      try {
        await deleteAccount(accountId, danger.values.password);
        await endSession();
        showToast({ tone: TOAST_TONES.INFO, ...DANGER_SECTION.done });
        forgetSession();
      } catch (error) {
        if (!mounted.current) return;
        setDeleting(false);
        if (error instanceof AccountError && error.code === ACCOUNT_ERRORS.WRONG_PASSWORD) {
          danger.setFieldError('password', 'password-incorrect');
        } else failed();
      }
    },
    [accountId, danger, deleting]
  );

  return {
    account,
    section,
    setSection,
    profile: { ...profile, save: saveProfile, saving: savingProfile, pickAvatarColor },
    security: { ...security, save: savePassword, saving: savingPassword },
    preferences,
    togglePreference,
    danger: { ...danger, open: openDelete, cancel: cancelDelete, confirm: confirmDelete, confirming: confirmingDelete, deleting }
  };
}
