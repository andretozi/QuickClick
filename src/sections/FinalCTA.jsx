export default function FinalCTA() {
  return (
    <section id="final" data-tex className="qc-final">
      <div data-blob className="qc-final__blob-a" />
      <div data-blob className="qc-final__blob-b" />
      <div className="qc-final__inner">
        <h2 data-reveal="up" className="qc-final__title">
          Pronto pra girar seu estoque?
        </h2>
        <p data-reveal="up" data-delay="90" className="qc-final__sub">
          Cadastre sua loja em minutos e deixe a primeira foto virar dinheiro.
        </p>
        <div data-reveal="up" data-delay="180" className="qc-final__cta-wrap">
          <a href="#top" className="qc-btn-final">
            Começar agora
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
        <p data-reveal="up" data-delay="260" className="qc-final__fineprint">
          Sem cartão · sem mensalidade · a gente só ganha quando você vende
        </p>
      </div>
    </section>
  );
}
