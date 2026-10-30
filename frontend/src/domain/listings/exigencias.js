/**
 * Domínio · Exigências dos canais no passo Confirmar
 *
 * O que os canais conectados pedem e ainda falta (leitura.exigencias, já convertida pela
 * infraestrutura) vira os campos do formulário. A sugestão da IA entra pré-preenchida, mas só
 * conta depois que o vendedor confirma (Sim) ou escolhe e digita o valor ele mesmo.
 */
// Import relativo, e não "@/": o scripts/exigencias.check.mjs carrega este arquivo direto no Node.
import { MARKETPLACE_CATALOG } from '../content/marketplacesContent.js';

/** Tipos de campo (os mesmos do back). */
export const FIELD_TYPE = { TEXT: 'texto', NUMBER: 'numero', LIST: 'lista', BOOLEAN: 'booleano' };

/** Respostas de um campo booleano, no formato do contrato da confirmação. */
export const BOOLEAN_VALUES = ['Sim', 'Não'];

/** Grupo das exigências que não são campo próprio de um canal. */
export const COMMON_GROUP = 'comum';

const channelName = (slug) => MARKETPLACE_CATALOG.find((channel) => channel.slug === slug)?.name ?? slug;
const channelNames = (slugs) => new Intl.ListFormat('pt-BR', { type: 'conjunction' }).format(slugs.map(channelName));

/** "350 g", "350" ou "1,5" → "350" ou "1.5"; vazio quando a unidade lida não é a do campo. */
function numberFrom(text, unit) {
  const match = String(text ?? '').trim().match(/^(\d+(?:[.,]\d+)?)\s*(.*)$/);
  if (!match) return '';
  const rest = match[2].trim().toLowerCase();
  return !rest || rest === unit.toLowerCase() ? match[1].replace(',', '.') : '';
}

/** O valor que serve para o campo (vazio quando não serve): lista só um dos valores, booleano só Sim ou Não. */
function validValue(field, value) {
  const text = String(value ?? '').trim();
  if (!text) return '';
  if (field.type === FIELD_TYPE.LIST || field.type === FIELD_TYPE.BOOLEAN) return field.options.includes(text) ? text : '';
  if (field.type === FIELD_TYPE.NUMBER) {
    const number = text.replace(',', '.');
    return /^\d+(\.\d+)?$/.test(number) && Number(number) > 0 ? number : '';
  }
  return text;
}

/**
 * leitura.exigencias → campos do formulário, na ordem do back. Cada campo:
 * { id (a chave, ou "canal:id" no campo próprio), key, own, label, type, options, unit, required,
 *   channels ("Mercado Livre e Shopee"), group ('comum' ou o canal), groupName, readKey, suggestion }
 */
export function requirementFields(requirements) {
  return (requirements ?? [])
    .map((item) => {
      const known = Object.values(FIELD_TYPE).includes(item.type) ? item.type : FIELD_TYPE.TEXT;
      // lista sem valores não tem o que escolher: o vendedor digita
      const type = known === FIELD_TYPE.LIST && !item.values?.length ? FIELD_TYPE.TEXT : known;
      const field = {
        id: item.own ? `${item.own.channel}:${item.own.id}` : item.key,
        key: item.own ? '' : item.key,
        own: item.own ?? null,
        label: item.name,
        type,
        options: type === FIELD_TYPE.LIST ? item.values : type === FIELD_TYPE.BOOLEAN ? BOOLEAN_VALUES : [],
        unit: type === FIELD_TYPE.NUMBER ? item.unit ?? '' : '',
        required: Boolean(item.required),
        channels: channelNames(item.channels ?? []),
        group: item.own ? item.own.channel : COMMON_GROUP,
        groupName: item.own ? channelName(item.own.channel) : '',
        readKey: item.suggestion?.readKey ?? '',
        suggestion: null
      };
      const read = item.suggestion?.value;
      const value = validValue(field, type === FIELD_TYPE.NUMBER ? numberFrom(read, field.unit) : read);
      if (value) {
        const { origin, confidence, card } = item.suggestion;
        field.suggestion = { value, origin, confidence, card };
      }
      return field;
    })
    .filter((field) => field.id);
}

/** Campos em grupos, na ordem em que aparecem: o comum e um por canal com campo próprio. */
export function requirementGroups(fields) {
  const groups = new Map();
  for (const field of fields) {
    if (!groups.has(field.group)) groups.set(field.group, { id: field.group, name: field.groupName, fields: [] });
    groups.get(field.group).fields.push(field);
  }
  return [...groups.values()];
}

/**
 * Respostas iniciais por id do campo: { value, confirmed }. A sugestão entra pré-preenchida e não
 * confirmada; o que o vendedor já confirmou (rascunho ou leitura anterior) fica.
 */
export function requirementAnswers(fields, previous = {}) {
  return Object.fromEntries(
    fields.map((field) => {
      const old = previous?.[field.id];
      return [field.id, old?.confirmed ? old : { value: field.suggestion?.value ?? '', confirmed: false }];
    })
  );
}

/** O valor confirmado pelo vendedor (vazio quando não confirmou ou o valor não serve). */
function confirmedValue(field, answer) {
  return answer?.confirmed ? validValue(field, answer.value) : '';
}

/** Ids das obrigatórias ainda sem valor confirmado. */
export function missingRequirements(fields, answers) {
  return fields.filter((field) => field.required && !confirmedValue(field, answers?.[field.id])).map((field) => field.id);
}

/** Dá para continuar: toda obrigatória tem valor confirmado pelo vendedor. */
export function canContinue(fields, answers) {
  return missingRequirements(fields, answers).length === 0;
}

/**
 * O pedaço das exigências na confirmação, com o valor no formato do contrato (número com ponto e a
 * unidade, booleano Sim ou Não): { attributes: [{ key, value }], ownFields: [{ channel, id, value }] }.
 */
export function requirementsConfirmation(fields, answers) {
  const attributes = [];
  const ownFields = [];
  for (const field of fields) {
    const confirmed = confirmedValue(field, answers?.[field.id]);
    if (!confirmed) continue;
    const value = field.type === FIELD_TYPE.NUMBER && field.unit ? `${confirmed} ${field.unit}` : confirmed;
    if (field.own) ownFields.push({ channel: field.own.channel, id: field.own.id, value });
    else attributes.push({ key: field.key, value });
  }
  return { attributes, ownFields };
}

/** Chaves dos cartões da leitura que as exigências cobrem (a chave e a de onde a sugestão veio). */
export function coveredCardKeys(fields) {
  return new Set(fields.flatMap((field) => [field.key, field.readKey]).filter(Boolean));
}
