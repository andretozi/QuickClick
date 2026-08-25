import CheckCircle from '../components/CheckCircle.jsx';

const FIELDS = ['Nome da loja', 'Categoria', 'WhatsApp'];

export default function SceneRegister() {
  return (
    <div data-reveal="right" data-scene="cadastro" style={{ order: 0 }}>
      <div data-c-card className="qc-c-card">
        <div className="qc-c-card__topbar">
          <span className="qc-c-card__dot qc-c-card__dot--red" />
          <span className="qc-c-card__dot qc-c-card__dot--yel" />
          <span className="qc-c-card__dot qc-c-card__dot--dim" />
          <span className="qc-c-card__label">Cadastrar loja</span>
        </div>
        <div className="qc-c-card__fields">
          {FIELDS.map((label) => (
            <div key={label}>
              <div className="qc-c-field__label">{label}</div>
              <div className="qc-c-field__row">
                <div className="qc-c-field__bar">
                  <div data-c-fill className="qc-c-fill" />
                </div>
                <span data-c-check className="qc-c-check">
                  <CheckCircle />
                </span>
              </div>
            </div>
          ))}
        </div>
        <div className="qc-c-card__footer">
          <button data-c-btn className="qc-c-btn">Cadastrar loja</button>
          <span data-c-done className="qc-c-done">
            Loja criada
            <svg width="16" height="16" viewBox="0 0 24 24" fill="none">
              <path
                d="M5 12.5l4 4L19 7"
                stroke="#37A06A"
                strokeWidth="2.6"
                strokeLinecap="round"
                strokeLinejoin="round"
              />
            </svg>
          </span>
        </div>
      </div>
    </div>
  );
}
