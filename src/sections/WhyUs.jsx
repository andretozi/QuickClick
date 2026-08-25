const BENEFITS = [
  {
    delay: 0,
    tint: 'o',
    title: 'Você só paga quando vende',
    desc: 'Sem mensalidade e sem contrato preso. Se o produto não girar, não custa nada. Simples assim.',
    icon: (
      <svg width="26" height="26" viewBox="0 0 24 24" fill="none">
        <path
          d="M12 2v20M17 6.5C17 4.6 14.8 4 12 4S7 4.9 7 7s2.5 2.6 5 3 5 1 5 3.4S14.8 20 12 20s-5-.7-5-2.8"
          stroke="#FF6A3D"
          strokeWidth="2"
          strokeLinecap="round"
        />
      </svg>
    )
  },
  {
    delay: 110,
    tint: 'y',
    title: 'Uma foto e o anúncio tá pronto',
    desc: 'A IA escreve o título, a descrição e escolhe a categoria certa pra cada canal. Horas de cadastro viram minutos.',
    icon: (
      <svg width="26" height="26" viewBox="0 0 24 24" fill="none">
        <rect x="3" y="6" width="18" height="14" rx="3" stroke="#d98c1a" strokeWidth="2" />
        <circle cx="12" cy="13" r="3.4" stroke="#d98c1a" strokeWidth="2" />
        <path
          d="M8 6l1.4-2.2h5.2L16 6"
          stroke="#d98c1a"
          strokeWidth="2"
          strokeLinejoin="round"
        />
      </svg>
    )
  },
  {
    delay: 220,
    tint: 'g',
    title: 'A IA fica de olho no mercado',
    desc: 'Ela indica o canal, o preço e o prazo com mais chance de vender — e aprende com cada venda pra acertar mais.',
    icon: (
      <svg width="26" height="26" viewBox="0 0 24 24" fill="none">
        <path
          d="M4 18l5-5 3 3 7-8"
          stroke="#2f8f5c"
          strokeWidth="2"
          strokeLinecap="round"
          strokeLinejoin="round"
        />
        <path
          d="M17 8h3v3"
          stroke="#2f8f5c"
          strokeWidth="2"
          strokeLinecap="round"
          strokeLinejoin="round"
        />
      </svg>
    )
  }
];

export default function WhyUs() {
  return (
    <section data-tex className="qc-porque">
      <div data-blob className="qc-porque__blob-a" />
      <div data-blob className="qc-porque__blob-b" />
      <div className="qc-porque__inner">
        <div className="qc-porque__intro">
          <p data-reveal="up" className="qc-eyebrow qc-eyebrow--orange">
            POR QUE ANUNCIAR COM A QUICK CLICK
          </p>
          <h2 data-reveal="up" data-delay="80" className="qc-h2">
            O risco é nosso, a grana é sua.
          </h2>
        </div>
        <div className="qc-porque__grid">
          {BENEFITS.map((b) => (
            <div
              key={b.title}
              data-reveal="up"
              data-delay={b.delay}
              className="qc-benefit"
            >
              <div className={`qc-benefit__icon qc-benefit__icon--${b.tint}`}>
                {b.icon}
              </div>
              <h3 className="qc-benefit__title">{b.title}</h3>
              <p className="qc-benefit__desc">{b.desc}</p>
            </div>
          ))}
        </div>
      </div>
    </section>
  );
}
