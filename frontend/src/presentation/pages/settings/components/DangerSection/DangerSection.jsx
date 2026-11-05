import Button from '@/presentation/components/Button/Button.jsx';
import Modal from '@/presentation/components/Modal/Modal.jsx';
import TextField from '@/presentation/components/Field/TextField.jsx';
import SettingsSection from '../SettingsSection/SettingsSection.jsx';
import { DANGER_SECTION } from '@/domain/content/settingsContent.js';
import { FIELD_ERRORS } from '@/domain/content/commonContent.js';
import './DangerSection.css';

/** Zona de risco: excluir a conta, com modal que pede o nome da loja para confirmar. */
export default function DangerSection({ danger }) {
  const { modal } = DANGER_SECTION;
  const target = danger.expectedConfirmation || '';
  const fieldLabel = danger.hasStoreName ? modal.confirmation.label : modal.confirmation.fallbackLabel;

  return (
    <SettingsSection id="risco" tone="glass" title={DANGER_SECTION.title} lead={DANGER_SECTION.lead} className="danger-section">
      <div className="danger-section__actions">
        <Button icon="trash" iconPosition="start" iconSize={16} onClick={danger.open} className="danger-section__button">
          {DANGER_SECTION.button}
        </Button>
      </div>

      <Modal
        open={danger.confirming}
        onClose={danger.cancel}
        dismissible={!danger.deleting}
        size="sm"
        icon="trash"
        iconTone="danger"
        title={modal.title}
        description={modal.text(target)}
        actions={
          <>
            <Button variant="outline" onClick={danger.cancel} disabled={danger.deleting}>
              {modal.cancel}
            </Button>
            <Button onClick={danger.confirm} loading={danger.deleting} loadingText={modal.confirming} disabled={danger.deleting} className="danger-section__button">
              {modal.confirm}
            </Button>
          </>
        }
      >
        <form ref={danger.formRef} className="danger-section__form" onSubmit={danger.confirm} noValidate>
          <TextField
            id="excluir-confirmacao"
            name="confirmation"
            label={fieldLabel}
            placeholder={modal.confirmation.placeholder(target)}
            value={danger.values.confirmation}
            onChange={danger.handleChange}
            autoComplete="off"
            error={FIELD_ERRORS[danger.errors.confirmation]}
            data-autofocus
          />
        </form>
      </Modal>
    </SettingsSection>
  );
}
