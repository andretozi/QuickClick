import { useCallback, useEffect, useMemo, useRef, useState } from 'react';
import useMountedRef from '@/application/ui/useMountedRef.js';
import useForm from '@/application/ui/useForm.js';
import useSession from '@/application/session/useSession.js';
import usePlanChange from '@/application/settings/usePlanChange.js';
import {
  deleteCurrentAccount,
  setSessionAccount,
  updateCurrentAccount
} from '@/application/session/sessionStore.js';
import { showToast, TOAST_TONES } from '@/application/feedback/toastStore.js';
import {
  ACCOUNT_ERRORS,
  AccountError,
  changeAccountPassword
} from '@/infrastructure/auth/authService.js';
import { getPreferences, savePreferences } from '@/infrastructure/storage/preferencesRepository.js';
import {
  required,
  validateEmail,
  validateName,
  validateNewPassword,
  validatePasswordConfirmation,
  validatePhone,
  validateTextConfirmation
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

const EMPTY_SECURITY = { current: '', next: '', confirmation: '' };

/**
 * Aplicação · Caso de uso "configurações da conta".
 * Perfil (persistido no servidor e refletido na hora na navbar), troca de senha (apenas quando
 * a conta tem senha local), troca de plano (usePlanChange), preferências e exclusão da conta
 * confirmada pelo nome da loja.
 */
export default function useSettings() {
  const { account } = useSession();
  const accountId = account?.id;
  const hasPassword = account?.hasPassword !== false;
  const availableSections = useMemo(
    () => (hasPassword ? SETTINGS_SECTIONS : SETTINGS_SECTIONS.filter((id) => id !== 'security')),
    [hasPassword]
  );
  const [section, setSection] = useState(availableSections[0]);
  const mounted = useMountedRef();

  useEffect(() => {
    if (!availableSections.includes(section)) {
      setSection(availableSections[0]);
    }
  }, [availableSections, section]);

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
  const savedColor = useRef(account?.avatarColor ?? 'coral');
  const latestAccount = useRef(account);

  useEffect(() => {
    latestAccount.current = account;
  }, [account]);

  // Saiu das configurações sem salvar: a navbar volta para a cor que está salva.
  useEffect(
    () => () => {
      const current = latestAccount.current;
      if (current && current.avatarColor !== savedColor.current) {
        setSessionAccount({ ...current, avatarColor: savedColor.current });
      }
    },
    []
  );

  const saveProfile = useCallback(
    async (event) => {
      event.preventDefault();
      if (savingProfile || !profile.check()) return;
      setSavingProfile(true);
      try {
        const updated = await updateCurrentAccount(profile.values);
        savedColor.current = updated.avatarColor;
        if (!mounted.current) return;
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
    [profile, savingProfile, mounted]
  );

  /** A cor do avatar já aparece na navbar enquanto o vendedor escolhe (só fica se ele salvar). */
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
      if (!hasPassword || savingPassword || !security.check()) return;
      setSavingPassword(true);
      try {
        await changeAccountPassword(security.values.current, security.values.next);
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
    [hasPassword, savingPassword, security, mounted]
  );

  // ---------- Preferências ----------
  const [preferences, setPreferences] = useState(null);

  useEffect(() => {
    if (!accountId) return;
    getPreferences(accountId).then((value) => {
      if (mounted.current) setPreferences(value);
    });
  }, [accountId, mounted]);

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
    [accountId, preferences, mounted]
  );

  // ---------- Plano (troca na hora, sem pagamento, no MVP) ----------
  const plan = usePlanChange({ mounted });

  // ---------- Zona de risco ----------
  const [deleting, setDeleting] = useState(false);
  const [confirmingDelete, setConfirmingDelete] = useState(false);
  const expectedStoreName = (account?.store || account?.email || '').trim();
  const validateDanger = useCallback(
    (values) => ({ confirmation: validateTextConfirmation(values.confirmation, expectedStoreName) }),
    [expectedStoreName]
  );
  const danger = useForm({ confirmation: '' }, validateDanger);

  const openDelete = useCallback(() => {
    danger.reset({ confirmation: '' });
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
        await deleteCurrentAccount(danger.values.confirmation);
        showToast({ tone: TOAST_TONES.INFO, ...DANGER_SECTION.done });
      } catch (error) {
        if (!mounted.current) return;
        setDeleting(false);
        if (error instanceof AccountError && error.code === ACCOUNT_ERRORS.CONFIRMATION_MISMATCH) {
          danger.setFieldError('confirmation', 'confirmation-mismatch');
        } else failed();
      }
    },
    [danger, deleting, mounted]
  );

  return {
    account,
    hasPassword,
    availableSections,
    section,
    setSection,
    profile: { ...profile, save: saveProfile, saving: savingProfile, pickAvatarColor },
    security: { ...security, save: savePassword, saving: savingPassword },
    preferences,
    togglePreference,
    plan,
    danger: {
      ...danger,
      expectedConfirmation: expectedStoreName,
      open: openDelete,
      cancel: cancelDelete,
      confirm: confirmDelete,
      confirming: confirmingDelete,
      deleting
    }
  };
}
