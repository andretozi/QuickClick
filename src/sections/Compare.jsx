import SceneCompare from '../scenes/SceneCompare.jsx';

const CURRENT_INTEGRATORS = [
  'Cadastro manual, item por item',
  'Você escolhe o canal na mão',
  'Você define e ajusta cada preço',
  'Mensalidade fixa, vendendo ou não'
];

export default function Compare() {
  return (
    <section className="qc-compare">
      <div data-blob className="qc-compare__blob-a" />
      <div data-blob className="qc-compare__blob-b" />
      <div className="qc-compare__inner">
        <div className="qc-compare__head">
          <h2 data-reveal="up" className="qc-h2 qc-h2--compare">
            Quick Click x os integradores de sempre
          </h2>
          <p data-reveal="up" data-delay="80" className="qc-compare__lead">
            Feito pra quem precisa girar rápido — não pra quem quer planilha.
          </p>
        </div>
        <div className="qc-compare__grid">
          <div data-reveal="right" className="qc-compare__col">
            <p className="qc-compare__col-title">INTEGRADORES ATUAIS</p>
            <div className="qc-compare__list">
              {CURRENT_INTEGRATORS.map((text) => (
                <div key={text} className="qc-compare__row">
                  <span className="qc-compare__dash">—</span>
                  {text}
                </div>
              ))}
            </div>
          </div>
          <SceneCompare />
        </div>
      </div>
    </section>
  );
}
