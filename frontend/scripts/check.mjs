/**
 * Conferência do front, sem dependências (npm run check). O equivalente no back é o
 * backend/tests/test_arquitetura.py.
 *
 * - Todo import relativo ou com "@/" (e todo @import e url() local do CSS) aponta para um
 *   arquivo que existe, com as mesmas maiúsculas e minúsculas (o Windows aceita a grafia
 *   errada, o Linux não).
 * - Cada camada só importa o que pode:
 *     domain          só o próprio domain, sem pacotes (JavaScript puro)
 *     infrastructure  só a própria infrastructure
 *     application     nunca presentation nem app
 *     presentation    nunca infrastructure nem app
 * - O único fetch do front fica no cliente HTTP (infrastructure/http/httpClient.js).
 * - A regra pura das exigências dos canais passa na conferência de scripts/exigencias.check.mjs.
 * - As conversões puras dos anúncios passam na conferência de scripts/listings.check.mjs.
 *
 * Sem problemas, sai com 0. Com problemas, lista um por linha e sai com 1.
 */
import fs from 'node:fs';
import path from 'node:path';
import { fileURLToPath } from 'node:url';

const SRC = fileURLToPath(new URL('../src/', import.meta.url));
const CODE = /\.(jsx?|css)$/;
const RESOLVE_SUFFIXES = ['', '.js', '.jsx', '/index.js', '/index.jsx'];
const ONLY_FETCH = 'infrastructure/http/httpClient.js';

/** Camadas que cada camada não pode importar. */
const FORBIDDEN = {
  domain: ['app', 'presentation', 'application', 'infrastructure'],
  infrastructure: ['app', 'presentation', 'application', 'domain'],
  application: ['app', 'presentation'],
  presentation: ['app', 'infrastructure']
};

/** JS: import ... from '...', import '...', export ... from '...', import('...') e import.meta.glob('...'). */
const IMPORT = /\b(?:import|export)\s+(?:[^'"`;]*?\sfrom\s+)?['"]([^'"]+)['"]|\bimport\(\s*['"]([^'"]+)['"]\s*\)|import\.meta\.glob\(\s*['"]([^'"]+)['"]/g;
/** CSS: @import '...' e url(...), com ou sem aspas. */
const CSS_REF = /@import\s+(?:url\(\s*)?(['"])(.*?)\1|url\(\s*(?:(['"])(.*?)\3|([^'"\s)]+))\s*\)/g;
/** No CSS, fica de fora o que não é arquivo do projeto: data:, http:, "//...", "#..." e caminho absoluto. */
const NOT_A_FILE = /^(?:[a-z]+:|\/|#)/i;
const FETCH = /\bfetch\s*\(/;
/** Depois disto, uma "/" abre uma expressão regular (e não uma divisão). */
const REGEX_CAN_START = /(?:=>|[(,=:[!&|?{;~^+\-*%]|\b(?:return|typeof|case|do|else|in|of|new|delete|void|throw|yield|await))\s*$/;

const walk = (dir) =>
  fs.readdirSync(dir, { withFileTypes: true }).flatMap((entry) => {
    const full = path.join(dir, entry.name);
    return entry.isDirectory() ? walk(full) : [full];
  });

const relative = (file) => path.relative(SRC, file).split(path.sep).join('/');
const layerOf = (rel) => (rel.includes('/') ? rel.split('/')[0] : null);

/**
 * Tira os comentários, para não confundir texto com código. Respeita as strings e as
 * expressões regulares: um "/*" num glob ('fundos/*.webp'), um "//" numa URL ou uma aspa
 * numa regex (/['"]/) não abrem nada. No CSS só existe o comentário de bloco.
 */
function withoutComments(text, { css = false } = {}) {
  let out = '';
  let quote = null;
  for (let i = 0; i < text.length; i += 1) {
    const char = text[i];
    const next = text[i + 1];
    if (quote) {
      out += char;
      if (char === '\\') out += text[++i] ?? '';
      else if (char === quote) quote = null;
    } else if (char === '/' && next === '*') {
      const end = text.indexOf('*/', i + 2);
      i = end === -1 ? text.length : end + 1;
    } else if (!css && char === '/' && next === '/') {
      const end = text.indexOf('\n', i);
      i = end === -1 ? text.length : end - 1;
    } else if (!css && char === '/' && REGEX_CAN_START.test(out.slice(-16))) {
      // regex: copia até a "/" que fecha (fora de [...]), sem passar da linha
      let inClass = false;
      out += char;
      for (i += 1; i < text.length && text[i] !== '\n'; i += 1) {
        out += text[i];
        if (text[i] === '\\') out += text[++i] ?? '';
        else if (inClass) inClass = text[i] !== ']';
        else if (text[i] === '[') inClass = true;
        else if (text[i] === '/') break;
      }
    } else {
      if (char === "'" || char === '"' || (!css && char === '`')) quote = char;
      out += char;
    }
  }
  return out;
}

/** Entradas de cada pasta, para conferir a grafia exata dos nomes. */
const folders = new Map();
function entriesOf(dir) {
  if (!folders.has(dir)) {
    try {
      folders.set(dir, fs.readdirSync(dir, { withFileTypes: true }));
    } catch {
      folders.set(dir, []);
    }
  }
  return folders.get(dir);
}

/** O arquivo existe dentro de src/, com exatamente essas letras em cada parte do caminho? */
function existsExactly(rel) {
  const parts = rel.split('/');
  let dir = SRC;
  for (const [index, part] of parts.entries()) {
    const entry = entriesOf(dir).find((item) => item.name === part);
    if (!entry) return false;
    if (index === parts.length - 1) return entry.isFile();
    if (!entry.isDirectory()) return false;
    dir = path.join(dir, part);
  }
  return false;
}

function resolve(fromRel, spec) {
  const base = spec.startsWith('@/') ? spec.slice(2) : path.posix.normalize(path.posix.join(path.posix.dirname(fromRel), spec));
  const found = RESOLVE_SUFFIXES.map((suffix) => base + suffix).find(existsExactly);
  return { target: found ?? base, exists: Boolean(found) };
}

const problems = [];
const files = walk(SRC).filter((file) => CODE.test(file));

/** Confere um caminho local: se existe (menos glob, que pode não achar nada) e se a camada pode. */
function checkReference(rel, layer, spec, { glob = false, kind = 'import' } = {}) {
  const { target, exists } = resolve(rel, glob ? spec.replace(/\/[^/]*\*.*$/, '') : spec);
  if (!glob && !exists) problems.push(`${rel}: ${kind} para um arquivo que não existe (${spec})`);
  const targetLayer = layerOf(target);
  if (layer && FORBIDDEN[layer]?.includes(targetLayer)) {
    problems.push(`${rel}: ${layer} não pode importar ${targetLayer} (${spec})`);
  }
}

for (const file of files) {
  const rel = relative(file);
  const layer = layerOf(rel);
  const css = rel.endsWith('.css');
  const code = withoutComments(fs.readFileSync(file, 'utf8'), { css });

  if (css) {
    for (const match of code.matchAll(CSS_REF)) {
      const spec = (match[2] ?? match[4] ?? match[5]).split(/[?#]/)[0];
      if (!spec || NOT_A_FILE.test(spec)) continue;
      const local = spec.startsWith('.') || spec.startsWith('@/') ? spec : `./${spec}`;
      checkReference(rel, layer, local, { kind: 'url' });
    }
    continue;
  }

  for (const match of code.matchAll(IMPORT)) {
    const [, fromSpec, dynamicSpec, globSpec] = match;
    const spec = fromSpec ?? dynamicSpec ?? globSpec;
    if (spec.startsWith('.') || spec.startsWith('@/')) {
      // Glob pode não achar nada (pasta opcional): só a camada é conferida.
      checkReference(rel, layer, spec, { glob: Boolean(globSpec) });
    } else if (layer === 'domain') {
      problems.push(`${rel}: o domain não importa pacotes (${spec})`);
    }
  }

  if (rel !== ONLY_FETCH && FETCH.test(code)) {
    problems.push(`${rel}: fetch fora do cliente HTTP (${ONLY_FETCH})`);
  }
}

// Regras puras com conferência própria (node:assert), sem pacote de teste.
try {
  await import('./exigencias.check.mjs');
} catch (error) {
  problems.push(`regra das exigências (scripts/exigencias.check.mjs): ${error.message}`);
}
try {
  await import('./listings.check.mjs');
} catch (error) {
  problems.push(`conversões dos anúncios (scripts/listings.check.mjs): ${error.message}`);
}

if (problems.length) {
  console.error(`check: ${problems.length} problema(s)`);
  problems.forEach((problem) => console.error(`  ${problem}`));
  process.exit(1);
}
console.log(`check: ${files.length} arquivos conferidos, nenhum problema.`);
