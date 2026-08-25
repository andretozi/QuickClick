const BARS = [
  { h: '45%', tone: 'n' },
  { h: '62%', tone: 'n' },
  { h: '55%', tone: 'n' },
  { h: '80%', tone: 'm' },
  { h: '100%', tone: 'h' }
];

export default function SceneSale() {
  return (
    <div data-reveal="left" data-scene="venda" style={{ order: 1 }}>
      <div className="qc-v-card">
        <div data-v-badge className="qc-v-badge">
          <div className="qc-v-badge__avatar">A</div>
          <div>
            <div className="qc-v-badge__name">Bazar da Ana</div>
            <div className="qc-v-badge__sub">faturamento da semana</div>
          </div>
        </div>
        <div className="qc-v-bars">
          {BARS.map((b, i) => (
            <div
              key={i}
              data-v-bar
              data-h={b.h}
              className={`qc-v-bar qc-v-bar--${b.tone}`}
            />
          ))}
        </div>
        <div className="qc-v-toast-anchor">
          <div data-v-ring className="qc-v-ring" />
          <div data-v-toast className="qc-v-toast">
            <div className="qc-v-toast__ok">
              <svg width="18" height="18" viewBox="0 0 24 24" fill="none">
                <path
                  d="M5 12.5l4 4L19 7"
                  stroke="#fff"
                  strokeWidth="2.8"
                  strokeLinecap="round"
                  strokeLinejoin="round"
                />
              </svg>
            </div>
            <div>
              <div className="qc-v-toast__title">Vendido!</div>
              <div data-v-amount className="qc-v-toast__amount">
                + R$ 189,00
              </div>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}
