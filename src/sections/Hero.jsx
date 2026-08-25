export default function Hero() {
  return (
    <header id="top" data-tex className="qc-hero">
      <div className="qc-hero__parallax qc-hero__parallax--a" data-parallax="0.18">
        <div data-blob className="qc-blob qc-blob--hero-a" />
      </div>
      <div className="qc-hero__parallax qc-hero__parallax--b" data-parallax="0.10">
        <div data-blob className="qc-blob qc-blob--hero-b" />
      </div>
      <div className="qc-hero__parallax qc-hero__parallax--c" data-parallax="0.26">
        <div data-blob className="qc-blob qc-blob--hero-c" />
      </div>

      <div className="qc-hero__inner">
        <div data-reveal="up" data-delay="0" className="qc-hero__badge">
          <span data-badge-dot className="qc-hero__badge-dot" />
          Feito para quem precisa vender agora
        </div>

        <h1 className="qc-hero__title">
          <span className="qc-hero__line">
            <span data-hero-word="1" className="qc-hero__word--1">Clicou…</span>
          </span>
          <span className="qc-hero__line qc-hero__line--2">
            <span data-hero-word="2" className="qc-hero__word--2">vendeu.</span>
          </span>
          <span data-cursor className="qc-hero__cursor">
            <span data-ripple className="qc-hero__cursor-ripple" />
            <svg
              width="30"
              height="34"
              viewBox="0 0 24 24"
              fill="none"
              className="qc-hero__cursor-svg"
            >
              <path
                d="M6 3l13 8.2-5.3 1.5 3 5.8-3 1.3-2.9-5.7L6 19V3z"
                fill="#2B1D15"
                stroke="#fff"
                strokeWidth="1.4"
                strokeLinejoin="round"
              />
            </svg>
          </span>
        </h1>

        <p data-reveal="up" data-delay="1350" className="qc-hero__sub">
          O jeito mais simples de transformar estoque parado em dinheiro. Você tira uma
          foto — a nossa IA cuida do resto e anuncia nos marketplaces certos.
        </p>

        <div data-reveal="up" data-delay="1550" className="qc-hero__cta-wrap">
          <a href="#preco" className="qc-btn-hero">
            Anunciar meu estoque
            <svg width="19" height="19" viewBox="0 0 24 24" fill="none">
              <path
                d="M5 12h14M13 6l6 6-6 6"
                stroke="#fff"
                strokeWidth="2.4"
                strokeLinecap="round"
                strokeLinejoin="round"
              />
            </svg>
          </a>
        </div>

        <a href="#como" data-reveal="up" data-delay="1750" className="qc-hero__scroll">
          Veja como é simples
          <span data-arrow>
            <svg width="20" height="20" viewBox="0 0 24 24" fill="none">
              <path
                d="M12 5v14M6 13l6 6 6-6"
                stroke="currentColor"
                strokeWidth="2"
                strokeLinecap="round"
                strokeLinejoin="round"
              />
            </svg>
          </span>
        </a>
      </div>
    </header>
  );
}
