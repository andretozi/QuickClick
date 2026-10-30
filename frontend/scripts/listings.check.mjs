/**
 * Conferência das conversões puras dos anúncios (src/infrastructure/storage/listingRecord.js).
 * Roda dentro do npm run check (scripts/check.mjs).
 * Sem problema, não imprime nada; com problema, o assert lança o erro.
 */
import assert from 'node:assert/strict';
import {
  fromApi,
  matchMlItems,
  pickPhotos,
  sameRecord,
  toApi,
  toListing
} from '../src/infrastructure/storage/listingRecord.js';

const DATA_PHOTO = 'data:image/jpeg;base64,AAAA';
const ML_PHOTO = 'https://http2.mlstatic.com/D_1.jpg';

const base = {
  id: 'a_base',
  ml_item_id: null,
  permalink: null,
  ml_categoria_id: 'MLB1234',
  saude_ml: null,
  vendidos: 0,
  titulo: 'Caneca azul',
  descricao: 'Caneca de porcelana.',
  categoria: 'cozinha',
  condicao: 'novo',
  preco_centavos: 4990,
  preco_sugerido_centavos: 5200,
  estoque: 3,
  fotos: [ML_PHOTO, 'https://http2.mlstatic.com/D_2.jpg'],
  capa: 1,
  atributos: [{ id: 'BRAND', nome: 'Marca', valor: 'Oxford' }, { id: null, nome: 'Cor', valor: 'Azul' }],
  analise_id: 'an_1',
  canais: {},
  criado_em: '2026-10-01T10:00:00.000Z',
  atualizado_em: '2026-10-02T10:00:00.000Z'
};

const published = {
  ...base,
  id: 'a_pub',
  ml_item_id: 'MLB111',
  permalink: 'https://produto.mercadolivre.com.br/MLB111',
  saude_ml: 0.8,
  vendidos: 4,
  canais: { 'mercado-livre': 'publicado' }
};
const paused = { ...published, id: 'a_pausa', ml_item_id: 'MLB222', canais: { 'mercado-livre': 'pausado' } };
const unpublished = {
  ...base,
  id: 'a_sem',
  ml_categoria_id: null,
  fotos: [DATA_PHOTO, 'data:image/jpeg;base64,BBBB'],
  analise_id: null,
  canais: { 'mercado-livre': 'nao_publicado' }
};
const duplicated = {
  ...published,
  id: 'a_dup',
  ml_item_id: null,
  permalink: null,
  saude_ml: null,
  vendidos: 0,
  titulo: 'Caneca azul (cópia)',
  canais: { 'mercado-livre': 'nao_publicado' }
};

// registro → toApi → fromApi → toListing é o mesmo anúncio no painel (fotos fora do https voltam da chave local)
for (const record of [published, paused, unpublished, duplicated]) {
  const sent = toApi(record);
  assert.ok(!JSON.stringify(sent).includes('data:'), `${record.id}: dataURL no corpo da API`);
  const back = fromApi(sent);
  const local = sent.fotos.length ? null : record.fotos;
  assert.deepEqual(toListing({ ...back, fotos: pickPhotos(back, local, undefined) }), toListing(record), record.id);
}

// uma dataURL no meio já tira a lista inteira do servidor
assert.deepEqual(toApi({ ...published, fotos: [ML_PHOTO, DATA_PHOTO] }).fotos, []);
assert.deepEqual(toApi(published).publicacoes, [
  {
    canal: 'mercado-livre',
    status: 'publicado',
    id_externo: 'MLB111',
    permalink: 'https://produto.mercadolivre.com.br/MLB111',
    categoria_id: 'MLB1234',
    saude: 0.8,
    vendidos: 4
  }
]);

// leitura das fotos: servidor, chave do produto, registro antigo com dataURL, nada
assert.deepEqual(pickPhotos({ fotos: [ML_PHOTO] }, [DATA_PHOTO], unpublished), [ML_PHOTO]);
assert.deepEqual(pickPhotos({ fotos: [] }, [DATA_PHOTO], unpublished), [DATA_PHOTO]);
assert.deepEqual(pickPhotos({ fotos: [] }, null, unpublished), unpublished.fotos);
assert.deepEqual(pickPhotos({ fotos: [] }, null, published), []);

// o sync só grava o que mudou, sem contar atualizado_em
assert.ok(sameRecord(published, { ...published, atualizado_em: '2026-10-30T00:00:00Z' }));
assert.ok(!sameRecord(published, { ...published, preco_centavos: 5000 }));

// sync: dois itens do ML de mesmo título nunca caem no mesmo anúncio, nem depois de um item novo entrar no topo
const mlItem = (id, title) => ({ id, title, status: 'active', price: 49.9, pictures: [ML_PHOTO] });
const twins = [
  { ...unpublished, id: 'a_1', titulo: 'Caneca Azul' },
  { ...unpublished, id: 'a_2', titulo: 'caneca azul' }
];
const synced = matchMlItems(twins, [mlItem('MLB900', 'Bola nova'), mlItem('MLB901', 'Caneca azul'), mlItem('MLB902', 'Caneca azul')]);
assert.equal(synced.length, 3);
assert.equal(new Set(synced.map((record) => record.id)).size, 3);
const owner = Object.fromEntries(synced.map((record) => [record.ml_item_id, record.id]));
assert.deepEqual([owner.MLB901, owner.MLB902].sort(), ['a_1', 'a_2']);
assert.ok(!['a_1', 'a_2'].includes(owner.MLB900));

const single = matchMlItems([twins[0]], [mlItem('MLB901', 'Caneca azul'), mlItem('MLB902', 'Caneca azul')]);
assert.equal(single.length, 2);
assert.notEqual(single[0].id, single[1].id);
assert.equal(single.find((record) => record.id === 'a_1').ml_item_id, 'MLB901');
