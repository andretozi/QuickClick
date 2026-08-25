export default function ScenePrice() {
  return (
    <div data-reveal="up" data-scene="price" className="qc-preco__card">
      <span data-price-shine className="qc-preco__shine" />
      <p className="qc-preco__eyebrow">PREÇO HONESTO</p>
      <h2 className="qc-preco__price">R$ 0 pra começar.</h2>
      <p className="qc-preco__sub">
        Cadastrar é grátis. Você paga uma comissão só quando um produto é vendido —
        e nada até lá. O nosso sucesso é vender o seu.
      </p>
      <a href="#final" className="qc-btn-dark">
        Quero anunciar
        <svg width="18" height="18" viewBox="0 0 24 24" fill="none">
          <path
            d="M5 12h14M13 6l6 6-6 6"
            stroke="#FBF3E7"
            strokeWidth="2.4"
            strokeLinecap="round"
            strokeLinejoin="round"
          />
        </svg>
      </a>
    </div>
  );
}
