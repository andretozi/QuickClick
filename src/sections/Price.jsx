import ScenePrice from '../scenes/ScenePrice.jsx';

export default function Price() {
  return (
    <section id="preco" className="qc-preco">
      <div data-blob className="qc-preco__blob-a" />
      <div data-blob className="qc-preco__blob-b" />
      <div className="qc-preco__inner">
        <ScenePrice />
      </div>
    </section>
  );
}
