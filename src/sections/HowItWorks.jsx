import SceneRegister from '../scenes/SceneRegister.jsx';
import ScenePhoto from '../scenes/ScenePhoto.jsx';
import SceneAI from '../scenes/SceneAI.jsx';
import SceneSale from '../scenes/SceneSale.jsx';

function StepText({ order, num, title, desc }) {
  return (
    <div style={{ order }}>
      <div data-reveal="up" className="qc-step__num">{num}</div>
      <h3 data-reveal="up" data-delay="80" className="qc-step__title">{title}</h3>
      <p data-reveal="up" data-delay="140" className="qc-step__desc">{desc}</p>
    </div>
  );
}

export default function HowItWorks() {
  return (
    <section id="como" data-tex className="qc-como">
      <div data-blob className="qc-como__blob-a" />
      <div data-blob className="qc-como__blob-b" />
      <div className="qc-como__inner">
        <div className="qc-como__intro">
          <p data-reveal="up" className="qc-eyebrow">COMO FUNCIONA</p>
          <h2 data-reveal="up" data-delay="80" className="qc-h2">
            Clicou aqui, vendeu ali
          </h2>
          <p data-reveal="up" data-delay="160" className="qc-como__lead">
            É só descer a página — a gente te mostra o passo a passo.
          </p>
        </div>

        <div className="qc-steps">
          <div className="qc-step">
            <SceneRegister />
            <StepText
              order={1}
              num="01"
              title="Você faz um cadastro rápido"
              desc="Uma vez só. Você preenche os dados da loja no computador ou no celular — sem planilha, sem complicação."
            />
          </div>

          <div className="qc-step">
            <StepText
              order={0}
              num="02"
              title="Você tira as fotos"
              desc="Aponta a câmera para os produtos (ou para a prateleira toda). Cada foto vira um anúncio — você não digita nada."
            />
            <ScenePhoto />
          </div>

          <div className="qc-step">
            <SceneAI />
            <StepText
              order={1}
              num="03"
              title="A nossa IA analisa o mercado"
              desc="Ela olha o que está vendendo agora e sugere o melhor canal, o preço e o prazo para cada item."
            />
          </div>

          <div className="qc-step">
            <StepText
              order={0}
              num="04"
              title="Você comemora a venda"
              desc="A gente publica e acompanha. Quando vende, o dinheiro entra — e você só paga uma comissão quando isso acontece."
            />
            <SceneSale />
          </div>
        </div>
      </div>
    </section>
  );
}
