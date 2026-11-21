/**
 * Infraestrutura · Serviço HTTP exclusivo do Mercado Livre (/api/anuncios/... e /api/marketplaces/mercado-livre/...)
 */
import { requestJson } from '../http/httpClient.js';
import { photosForm, toAnuncioPayload } from '../ai/iaService.js';

/** Lista os produtos publicados na conta do Mercado Livre do vendedor. */
export async function fetchMercadoLivreProducts() {
  return await requestJson('/marketplaces/mercado-livre/products');
}

/**
 * Publica no Mercado Livre com o anúncio montado no back.
 * listing: { title, description, priceCents, stock, condition ('new' ou 'used'), attributes: [{ key, value }],
 *            analysisId, mlCategoryId, keptPhotos }
 */
export async function publishToMercadoLivre(listing, photoBlobs = []) {
  const form = photosForm('fotos', photoBlobs);
  form.append('anuncio', JSON.stringify(toAnuncioPayload(listing)));
  const data = await requestJson('/anuncios/publicar/mercado-livre', { method: 'POST', body: form });
  return {
    id: data.id,
    permalink: data.permalink ?? null,
    status: data.status ?? null,
    categoryId: data.categoria_id ?? null,
    notices: (data.avisos ?? []).map((a) => ({ code: a.codigo, message: a.mensagem }))
  };
}

/** Obtém os dados mais recentes de um anúncio publicado no Mercado Livre. */
export async function fetchMercadoLivreItem(itemId) {
  return await requestJson(`/anuncios/mercado-livre/${encodeURIComponent(itemId)}`);
}

/** Pausa ('paused') ou reativa ('published') um anúncio diretamente no Mercado Livre. */
export async function updateMercadoLivreStatus(itemId, nextStatus) {
  const status = nextStatus === 'paused' ? 'pausado' : 'publicado';
  return await requestJson(`/anuncios/mercado-livre/${encodeURIComponent(itemId)}/status`, {
    method: 'PATCH',
    body: { status }
  });
}

/** Atualiza preço, estoque, fotos, atributos, título e descrição de um anúncio no Mercado Livre. */
export async function updateMercadoLivreItem(itemId, listing, photoBlobs = []) {
  const form = photosForm('fotos', photoBlobs);
  form.append('anuncio', JSON.stringify(toAnuncioPayload(listing)));
  return await requestJson(`/anuncios/mercado-livre/${encodeURIComponent(itemId)}`, {
    method: 'PUT',
    body: form
  });
}

/** Fecha e exclui definitivamente o anúncio no Mercado Livre. */
export async function deleteMercadoLivreItem(itemId) {
  return await requestJson(`/anuncios/mercado-livre/${encodeURIComponent(itemId)}`, {
    method: 'DELETE'
  });
}
