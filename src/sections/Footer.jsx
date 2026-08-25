import LogoMark from '../components/LogoMark.jsx';

export default function Footer() {
  return (
    <footer className="qc-footer">
      <div className="qc-footer__inner">
        <div className="qc-footer__brand">
          <LogoMark variant="footer" />
          <div>
            <div className="qc-brand qc-brand--footer">
              Quick <span className="qc-brand__accent">Click</span>
            </div>
            <div className="qc-footer__tag">
              Clicou, vendeu. Transforme estoque parado em dinheiro.
            </div>
          </div>
        </div>
        <div className="qc-footer__copy">© 2026 Quick Click · Protótipo</div>
      </div>
    </footer>
  );
}
