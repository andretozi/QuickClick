/**
 * Domínio · Regra de escrita do título e da descrição (a mesma do back, em backend/domain/ia/escrita.py)
 *
 * Sem emojis, sem barra, sem travessão, sem meia risca e sem hífen como pontuação.
 * Hífen dentro de nome técnico (USB-C, Wi-Fi, NF-e) pode. Nenhuma linha começa com marcador.
 */

const EMOJI = /[\u{1F000}-\u{1FAFF}\u{2600}-\u{27BF}\u{2B00}-\u{2BFF}\u{2300}-\u{23FF}\u{FE0F}\u{200D}\u{20E3}\u{1F1E6}-\u{1F1FF}]/u;
const DASHES = /[‒–—―−]/;
const LETTER_OR_DIGIT = /[0-9A-Za-zÀ-ÿ]/;
const MARKER = /^\s*(?:[-*•·▪►✓✔○●]|\d{1,2}[.)])\s+/;

/** Hífen sem letra ou número dos dois lados é pontuação. */
function hasLooseHyphen(text) {
  for (let i = 0; i < text.length; i += 1) {
    if (text[i] !== '-') continue;
    const before = text[i - 1] ?? '';
    const after = text[i + 1] ?? '';
    if (!LETTER_OR_DIGIT.test(before) || !LETTER_OR_DIGIT.test(after)) return true;
  }
  return false;
}

/** Os problemas do texto pela regra: 'emoji', 'slash', 'dash', 'hyphen' e 'marker' (vazio = está certo). */
export function writingProblems(text) {
  const value = String(text ?? '');
  const problems = [];
  if (EMOJI.test(value)) problems.push('emoji');
  if (value.includes('/')) problems.push('slash');
  if (DASHES.test(value)) problems.push('dash');
  if (hasLooseHyphen(value)) problems.push('hyphen');
  if (value.split('\n').some((line) => MARKER.test(line))) problems.push('marker');
  return problems;
}
