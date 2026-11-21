/**
 * Infraestrutura · Serviço HTTP exclusivo da QuickStore (/api/anuncios/... e /api/marketplaces/quickstore/...)
 */
import { requestJson } from '../http/httpClient.js';
import { photosForm, toAnuncioPayload } from '../ai/iaService.js';

/** Lista os produtos publicados na conta da QuickStore do vendedor. */
export async function fetchQuickStoreProducts() {
  return await requestJson('/marketplaces/quickstore/products');
}

/** Publica na QuickStore com o anúncio montado no back. */
export async function publishToQuickStore(listing, photoBlobs = []) {
  const form = photosForm('fotos', photoBlobs);
  form.append('anuncio', JSON.stringify(toAnuncioPayload(listing)));
  const data = await requestJson('/anuncios/publicar/quickstore', { method: 'POST', body: form });
  return {
    id: data.id,
    permalink: data.permalink ?? null,
    status: data.status ?? null,
    categoryId: data.categoria_id ?? null,
    notices: (data.avisos ?? []).map((a) => ({ code: a.codigo, message: a.mensagem }))
  };
}

/** Obtém os dados mais recentes de um anúncio publicado na QuickStore. */
export async function fetchQuickStoreItem(itemId) {
  return await requestJson(`/anuncios/quickstore/${encodeURIComponent(itemId)}`);
}

/** Pausa ('paused') ou reativa ('published') um anúncio diretamente na QuickStore. */
export async function updateQuickStoreStatus(itemId, nextStatus) {
  const status = nextStatus === 'paused' ? 'pausado' : 'publicado';
  return await requestJson(`/anuncios/quickstore/${encodeURIComponent(itemId)}/status`, {
    method: 'PATCH',
    body: { status }
  });
}

/** Atualiza preço, estoque, fotos, atributos, título e descrição de um anúncio na QuickStore. */
export async function updateQuickStoreItem(itemId, listing, photoBlobs = []) {
  const form = photosForm('fotos', photoBlobs);
  form.append('anuncio', JSON.stringify(toAnuncioPayload(listing)));
  return await requestJson(`/anuncios/quickstore/${encodeURIComponent(itemId)}`, {
    method: 'PUT',
    body: form
  });
}

/** Fecha e exclui definitivamente o anúncio na QuickStore. */
export async function deleteQuickStoreItem(itemId) {
  return await requestJson(`/anuncios/quickstore/${encodeURIComponent(itemId)}`, {
    method: 'DELETE'
  });
}
