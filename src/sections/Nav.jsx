import LogoMark from '../components/LogoMark.jsx';

export default function Nav() {
  return (
    <nav data-nav className="qc-nav">
      <div className="qc-nav__inner">
        <a href="#top" className="qc-nav__logo">
          <LogoMark variant="nav" />
          <span className="qc-brand">
            Quick <span className="qc-brand__accent">Click</span>
          </span>
        </a>
        <div className="qc-nav__links">
          <a href="#como" className="qc-nav__link">Como funciona</a>
          <a href="#preco" className="qc-nav__link">Preço</a>
          <a href="#/login" className="qc-nav__enter">
            <svg width="16" height="16" viewBox="0 0 24 24" fill="none">
              <path
                d="M12 12a4 4 0 100-8 4 4 0 000 8zM5 20c0-3.3 3.1-6 7-6s7 2.7 7 6"
                stroke="currentColor"
                strokeWidth="2"
                strokeLinecap="round"
                strokeLinejoin="round"
              />
            </svg>
            Entrar
          </a>
          <a href="#preco" className="qc-nav__cta">Anunciar meu estoque</a>
        </div>
      </div>
    </nav>
  );
}
