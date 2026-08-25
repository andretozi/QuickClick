import CheckCompare from '../components/CheckCompare.jsx';

const ITEMS = [
  'Cadastro por foto, feito pela IA',
  'A IA recomenda o canal item a item',
  'Preço de saída rápida + reajuste',
  'Comissão só quando vende'
];

export default function SceneCompare() {
  return (
    <div data-reveal="left" data-scene="compare" className="qc-compare__winner">
      <div className="qc-compare__ribbon">QUICK CLICK</div>
      <p className="qc-compare__winner-title">Quick Click</p>
      <div className="qc-compare__winner-list">
        {ITEMS.map((text) => (
          <div key={text} className="qc-compare__row">
            <CheckCompare />
            {text}
          </div>
        ))}
      </div>
    </div>
  );
}
