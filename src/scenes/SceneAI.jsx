const BARS = [
  { h: '40%', cls: 'a' },
  { h: '72%', cls: 'b' },
  { h: '54%', cls: 'c' },
  { h: '90%', cls: 'd' },
  { h: '64%', cls: 'e' }
];

export default function SceneAI() {
  return (
    <div data-reveal="right" data-scene="ia" style={{ order: 0 }}>
      <div className="qc-ia-card">
        <div className="qc-ia-card__head">
          <div className="qc-ia__radar-wrap">
            <div data-ia-radar className="qc-ia__radar" />
            <div className="qc-ia__ring-a" />
            <div className="qc-ia__ring-b" />
            <div data-ia-core className="qc-ia__core">
              <svg width="26" height="26" viewBox="0 0 24 24" fill="none">
                <path
                  d="M12 3l1.8 5.4L19 10l-5.2 1.6L12 17l-1.8-5.4L5 10l5.2-1.6L12 3z"
                  fill="#fff"
                />
              </svg>
            </div>
          </div>
          <div className="qc-ia__pills">
            <div data-ia-scan className="qc-ia__scan" />
            <div data-ia-pill className="qc-ia__pill">
              <span className="qc-ia__dot qc-ia__dot--y" />
              <div className="qc-ia__pill-body">
                <div className="qc-ia__pill-title">Mercado Livre</div>
                <div className="qc-ia__pill-sub">R$189 · vende rápido</div>
              </div>
            </div>
            <div data-ia-pill data-ia-rec className="qc-ia__pill qc-ia__pill--rec">
              <span className="qc-ia__dot qc-ia__dot--o" />
              <div className="qc-ia__pill-body">
                <div className="qc-ia__pill-title">Shopee</div>
                <div className="qc-ia__pill-sub qc-ia__pill-sub--strong">
                  R$179 · alta procura
                </div>
              </div>
              <span data-ia-tag className="qc-ia__tag">RECOMENDADO</span>
            </div>
            <div data-ia-pill className="qc-ia__pill">
              <span className="qc-ia__dot qc-ia__dot--d" />
              <div className="qc-ia__pill-body">
                <div className="qc-ia__pill-title">Amazon</div>
                <div className="qc-ia__pill-sub">R$199 · prazo maior</div>
              </div>
            </div>
          </div>
        </div>
        <div className="qc-ia__chart">
          <span className="qc-ia__chart-label">de olho no mercado</span>
          {BARS.map((b) => (
            <div
              key={b.cls}
              data-ia-bar
              data-h={b.h}
              className={`qc-ia__bar qc-ia__bar--${b.cls}`}
            />
          ))}
        </div>
      </div>
    </div>
  );
}
