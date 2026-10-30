/**
 * Conferência da regra das exigências dos canais (src/domain/listings/exigencias.js), com uma
 * Shopee falsa que só existe aqui. Roda dentro do npm run check (scripts/check.mjs).
 * Sem problema, não imprime nada; com problema, o assert lança o erro.
 */
import assert from 'node:assert/strict';
import {
  canContinue,
  coveredCardKeys,
  missingRequirements,
  requirementAnswers,
  requirementFields,
  requirementGroups,
  requirementsConfirmation
} from '../src/domain/listings/exigencias.js';
import { cardsFromReading, confirmationPayload } from '../src/domain/listings/aiAnalysis.js';

const suggestion = (value, readKey, card = 'a_ia_viu') => ({ value, origin: 'foto', confidence: 'alta', card, readKey });

// leitura.exigencias já convertida pela infraestrutura (iaService.toReading)
const requirements = [
  {
    key: 'marca', name: 'Marca', type: 'lista', values: ['Nike', 'Adidas'], unit: '', required: true,
    channels: ['mercado-livre', 'shopee'], own: null, suggestion: suggestion('Nike', 'marca')
  },
  {
    key: 'peso_g', name: 'Peso', type: 'numero', values: [], unit: 'g', required: true,
    channels: ['mercado-livre'], own: null, suggestion: suggestion('350 g', 'peso', 'confere')
  },
  {
    key: 'a_prova_dagua', name: 'À prova d’água', type: 'booleano', values: ['Sim', 'Não'], unit: '', required: true,
    channels: ['shopee'], own: null, suggestion: null
  },
  {
    key: '', name: 'Tipo de garantia', type: 'texto', values: [], unit: '', required: true,
    channels: ['shopee'], own: { channel: 'shopee', id: '100017' }, suggestion: null
  }
];

const fields = requirementFields(requirements);
const [marca, peso, agua, garantia] = fields;

// ML e Shopee na mesma chave viram "Mercado Livre e Shopee"; o campo próprio fica no grupo da Shopee
assert.equal(marca.channels, 'Mercado Livre e Shopee');
assert.equal(garantia.id, 'shopee:100017');
assert.deepEqual(
  requirementGroups(fields).map((group) => [group.id, group.name, group.fields.map((field) => field.id)]),
  [
    ['comum', '', ['marca', 'peso_g', 'a_prova_dagua']],
    ['shopee', 'Shopee', ['shopee:100017']]
  ]
);
assert.equal(peso.unit, 'g');
assert.equal(peso.suggestion.value, '350');
assert.deepEqual(agua.options, ['Sim', 'Não']);
assert.deepEqual([...coveredCardKeys(fields)].sort(), ['a_prova_dagua', 'marca', 'peso', 'peso_g']);

// sugestão pré-preenchida, mas não conta antes de o vendedor confirmar
let answers = requirementAnswers(fields);
assert.deepEqual(answers.marca, { value: 'Nike', confirmed: false });
assert.equal(canContinue(fields, answers), false);
assert.deepEqual(missingRequirements(fields, answers), ['marca', 'peso_g', 'a_prova_dagua', 'shopee:100017']);
assert.deepEqual(requirementsConfirmation(fields, answers), { attributes: [], ownFields: [] });

// confirma tudo menos a garantia: ainda não continua
answers = {
  ...answers,
  marca: { ...answers.marca, confirmed: true },
  peso_g: { value: '1,5', confirmed: true },
  a_prova_dagua: { value: 'Não', confirmed: true }
};
assert.equal(canContinue(fields, answers), false);
assert.deepEqual(missingRequirements(fields, answers), ['shopee:100017']);

// lista fora dos valores não conta
assert.equal(canContinue(fields, { ...answers, marca: { value: 'Puma', confirmed: true } }), false);

// número só positivo, sem sinal nem notação científica
for (const invalid of ['-5', '0', '1e3']) {
  assert.ok(missingRequirements(fields, { ...answers, peso_g: { value: invalid, confirmed: true } }).includes('peso_g'), invalid);
}

// GTIN e embalagem lidos não viram cartão da leitura; só aparecem pelas exigências
assert.deepEqual(
  cardsFromReading({ attributes: [
    { key: 'cor', value: 'Azul', card: 'a_ia_viu' },
    { key: 'peso_g', value: '350', card: 'confere' },
    { key: 'gtin', value: '7891234567895', card: 'a_ia_viu' }
  ] }).map((card) => card.key),
  ['cor']
);

answers = { ...answers, 'shopee:100017': { value: ' Garantia do vendedor ', confirmed: true } };
assert.equal(canContinue(fields, answers), true);

// formato do contrato: número com ponto e unidade, booleano Sim ou Não, campos próprios à parte
const piece = requirementsConfirmation(fields, answers);
assert.deepEqual(piece, {
  attributes: [
    { key: 'marca', value: 'Nike' },
    { key: 'peso_g', value: '1.5 g' },
    { key: 'a_prova_dagua', value: 'Não' }
  ],
  ownFields: [{ channel: 'shopee', id: '100017', value: 'Garantia do vendedor' }]
});

// o confirmado da leitura entra junto; na mesma chave, a exigência ganha do cartão
const payload = confirmationPayload({
  product: 'Tênis',
  category: 'calcados',
  condition: 'new',
  cards: [
    { key: 'cor', value: 'Azul', card: 'a_ia_viu', answer: null, edited: false },
    { key: 'marca', value: 'Adidas', card: 'a_ia_viu', answer: null, edited: false }
  ],
  defects: [],
  requirements: piece
});
assert.deepEqual(payload.attributes, [{ key: 'cor', value: 'Azul' }, ...piece.attributes]);
assert.deepEqual(payload.ownFields, piece.ownFields);

// o que o vendedor já confirmou fica quando a leitura muda (foto extra)
assert.deepEqual(requirementAnswers(fields, answers).peso_g, { value: '1,5', confirmed: true });

// sem exigências (análise antiga): nada muda
assert.deepEqual(requirementFields(null), []);
assert.equal(canContinue([], {}), true);
assert.deepEqual(confirmationPayload({ product: 'x', category: 'outros', condition: 'new', cards: [], defects: [] }).ownFields, []);
