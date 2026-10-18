/**
 * Infraestrutura · IA do criar anúncio, pela API real (/api/ia e /api/anuncios)
 *
 * Fotos vão em FormData (multipart). As respostas do back (em português) viram os objetos
 * do front (em inglês), como no resto da infraestrutura. Erros chegam como ApiError, com o
 * código do back (cota_esgotada, ia_indisponivel, foto_invalida, limite_por_hora...).
 */
import { requestJson } from '../http/httpClient.js';

function toQuota(data) {
  return {
    plan: data.plano,
    level: data.nivel,
    levelNow: data.nivel_agora,
    perMonth: data.analises_por_mes,
    used: data.usadas_no_mes,
    remaining: data.restantes,
    budgetExceeded: Boolean(data.orcamento_do_dia_estourado),
    available: Boolean(data.disponivel),
    unavailableReason: data.motivo_indisponivel ?? null,
    features: {
      marketResearch: Boolean(data.tem?.pesquisa_de_mercado),
      pricingAnalysis: Boolean(data.tem?.preco_com_analise),
      webSearch: Boolean(data.tem?.busca_na_web)
    },
    freeDataNotice: Boolean(data.aviso_de_dados_no_gratis)
  };
}

function toReading(leitura) {
  if (!leitura) return null;
  return {
    recognized: Boolean(leitura.reconhecido),
    reason: leitura.motivo_nao_reconhecido ?? '',
    product: leitura.produto ?? '',
    category: leitura.categoria ?? 'outros',
    searchTerms: leitura.termos_busca ?? [],
    attributes: (leitura.atributos ?? []).map((a) => ({
      key: a.chave,
      value: a.valor ?? '',
      origin: a.origem,
      evidence: a.evidencia ?? '',
      confidence: a.confianca,
      card: a.cartao
    })),
    condition: {
      value: leitura.condicao?.valor ?? 'desconhecido',
      signals: leitura.condicao?.sinais ?? [],
      confidence: leitura.condicao?.confianca ?? 'baixa'
    },
    defects: leitura.defeitos_visiveis ?? [],
    readableText: leitura.texto_legivel ?? [],
    questions: (leitura.perguntas ?? []).map((q) => ({
      key: q.chave,
      question: q.pergunta,
      suggestPhoto: q.sugerir_foto ?? 'nenhuma'
    }))
  };
}

function toPrice(preco) {
  if (!preco) return null;
  if (preco.sem_dados) return { noData: true, reason: preco.motivo ?? null };
  const mercado = preco.mercado ?? {};
  return {
    noData: false,
    source: preco.fonte,
    byAi: Boolean(preco.por_ia),
    suggestedCents: preco.sugerido_centavos,
    range: { min: preco.faixa?.min, max: preco.faixa?.max },
    market: {
      count: mercado.quantidade,
      p25: mercado.p25,
      median: mercado.mediana,
      p75: mercado.p75,
      min: mercado.minimo,
      max: mercado.maximo,
      freeShipping: mercado.com_frete_gratis
    },
    strategy: preco.estrategia ?? null,
    justification: preco.justificativa ?? null,
    alerts: preco.alertas ?? [],
    feeCents: preco.tarifa_centavos ?? null,
    netCents: preco.liquido_centavos ?? null
  };
}

function toAnalysis(data) {
  const pesquisa = data.pesquisa;
  return {
    id: data.id,
    status: data.status,
    stage: data.etapa_atual,
    running: Boolean(data.em_processamento),
    level: data.nivel,
    plan: data.plano,
    photos: (data.fotos ?? []).map((f) => ({ index: f.indice, quality: f.qualidade, width: f.largura, height: f.altura })),
    reading: toReading(data.leitura),
    mercadoLivre: data.mercado_livre
      ? { categoryId: data.mercado_livre.categoria_id, categoryName: data.mercado_livre.categoria_nome }
      : null,
    confirmed: data.atributos_confirmados
      ? {
          product: data.atributos_confirmados.produto,
          category: data.atributos_confirmados.categoria,
          condition: data.atributos_confirmados.condicao,
          attributes: (data.atributos_confirmados.atributos ?? []).map((a) => ({ key: a.chave, value: a.valor })),
          defects: data.atributos_confirmados.defeitos ?? []
        }
      : null,
    research: pesquisa
      ? {
          buyerProfile: pesquisa.perfil_comprador ?? '',
          values: pesquisa.o_que_valoriza ?? [],
          objections: pesquisa.objecoes ?? [],
          terms: pesquisa.termos_que_usam ?? [],
          sources: pesquisa.fontes ?? []
        }
      : null,
    price: toPrice(data.preco),
    text: data.texto
      ? {
          title: data.texto.titulo ?? '',
          description: data.texto.descricao ?? '',
          specs: (data.texto.especificacoes ?? []).map((e) => ({ label: e.rotulo, value: e.valor })),
          corrected: Boolean(data.texto.corrigido)
        }
      : null,
    channels: data.canais ? data.canais.map((c) => ({ slug: c.slug, connected: Boolean(c.conectado), reason: c.motivo ?? null })) : null,
    notices: (data.avisos ?? []).map((a) => ({ code: a.codigo, message: a.mensagem })),
    error: data.erro ? { code: data.erro.codigo, message: data.erro.mensagem } : null,
    canResume: Boolean(data.pode_retomar),
    needsPhotosToResume: Boolean(data.precisa_fotos_para_retomar)
  };
}

function photosForm(field, blobs) {
  const form = new FormData();
  blobs.forEach((blob, index) => form.append(field, blob, `foto${index + 1}.jpg`));
  return form;
}

export async function fetchQuota() {
  return toQuota(await requestJson('/ia/cota'));
}

/** Cria a análise com as fotos de leitura (Blob JPEG). Devolve o id. */
export async function createAnalysis(readingBlobs) {
  const data = await requestJson('/ia/analises', { method: 'POST', body: photosForm('fotos', readingBlobs) });
  return data.id;
}

export async function fetchAnalysis(id) {
  return toAnalysis(await requestJson(`/ia/analises/${encodeURIComponent(id)}`));
}

/** Foto extra (etiqueta, verso ou detalhe): reabre só a leitura dela. */
export async function sendExtraPhoto(id, blob, kind) {
  const form = photosForm('foto', [blob]);
  form.append('tipo', kind);
  return toAnalysis(await requestJson(`/ia/analises/${encodeURIComponent(id)}/fotos`, { method: 'POST', body: form }));
}

/** { product, category, condition ('novo' ou 'usado'), attributes: [{ key, value }], defects: [] } */
export async function confirmAnalysis(id, confirmation) {
  const body = {
    produto: confirmation.product,
    categoria: confirmation.category,
    condicao: confirmation.condition,
    atributos: confirmation.attributes.map((a) => ({ chave: a.key, valor: a.value })),
    defeitos: confirmation.defects
  };
  return toAnalysis(await requestJson(`/ia/analises/${encodeURIComponent(id)}/confirmacao`, { method: 'POST', body }));
}

/** Retoma uma análise interrompida ou com falha (com as fotos de novo, quando a leitura não terminou). */
export async function resumeAnalysis(id, readingBlobs = null) {
  const options = { method: 'POST' };
  if (readingBlobs?.length) options.body = photosForm('fotos', readingBlobs);
  return toAnalysis(await requestJson(`/ia/analises/${encodeURIComponent(id)}/retomar`, options));
}

/**
 * Publica no Mercado Livre com o anúncio montado no back.
 * listing: { title, description, priceCents, stock, condition ('new' ou 'used'), attributes: [{ key, value }],
 *            analysisId, mlCategoryId }
 */
export async function publishToMercadoLivre(listing, photoBlobs) {
  const form = photosForm('fotos', photoBlobs);
  form.append(
    'anuncio',
    JSON.stringify({
      titulo: listing.title,
      descricao: listing.description,
      preco_centavos: listing.priceCents,
      estoque: listing.stock,
      condicao: listing.condition === 'used' ? 'usado' : 'novo',
      atributos: (listing.attributes ?? []).map((a) => ({ chave: a.key, valor: a.value })),
      analise_id: listing.analysisId ?? null,
      ml_categoria_id: listing.mlCategoryId ?? null
    })
  );
  const data = await requestJson('/anuncios/publicar/mercado-livre', { method: 'POST', body: form });
  return {
    id: data.id,
    permalink: data.permalink ?? null,
    status: data.status ?? null,
    notices: (data.avisos ?? []).map((a) => ({ code: a.codigo, message: a.mensagem }))
  };
}
