import { frameLoop } from './frameLoop.js';
import { between } from './physics.js';

/**
 * Campo de partículas num único <canvas>: a explosão do clique que depois vira palavra.
 * Usado na vitrine da landing, no publicar anúncio e no conectar marketplace.
 *
 * Três movimentos:
 *   burst(x, y)    explosão: velocidade inicial, gravidade, resistência do ar e giro;
 *   formWord(text) molas puxam cada partícula para um ponto da palavra (desenhada em
 *                  Fraunces num canvas fora da tela, de onde sorteamos pontos dos pixels);
 *                  quando elas chegam, a palavra acende por baixo, nítida;
 *   scatter()      a palavra se desfaz: as partículas se soltam e somem.
 *
 * Performance: o canvas respeita o devicePixelRatio e o laço de quadros só roda enquanto
 * há algo para desenhar. Quem usa chama pause() e resume() quando a cena sai e volta da tela.
 */

const GRAVITY = 1150; // px/s²
const AIR_DRAG = 2.1; // quanto da velocidade o ar come por segundo
const SPRING_K = 95; // rigidez da mola até a palavra
const SPRING_C = 13; // amortecimento (um pouco de balanço antes de parar)
const SCATTER_GRAVITY = 260;
const SCATTER_FADE = 1.5; // opacidade perdida por segundo ao desfazer
const TEXT_FADE_IN = 3.2; // por segundo
const TEXT_FADE_OUT = 5;
const FORM_STAGGER_S = 0.28; // atraso máximo entre a primeira e a última partícula a partir

const SHAPES = ['dot', 'dot', 'spark', 'chip'];

/** Lê uma cor dos tokens (tokens.css), para o canvas usar a mesma paleta do CSS. */
function token(name, fallback) {
  const value = getComputedStyle(document.documentElement).getPropertyValue(name).trim();
  return value || fallback;
}

function shuffle(list) {
  for (let i = list.length - 1; i > 0; i -= 1) {
    const j = Math.floor(Math.random() * (i + 1));
    [list[i], list[j]] = [list[j], list[i]];
  }
  return list;
}

/**
 * @param animator  dono do laço (o dispose para tudo)
 * @param canvas    o <canvas> que cobre a cena (o CSS dá o tamanho; aqui só ajustamos o DPR)
 */
export function createParticleField(animator, canvas) {
  const context = canvas.getContext('2d');
  const palette = {
    coral: token('--color-coral', '#ff6a3d'),
    honey: token('--color-honey', '#f2a93b'),
    cream: token('--color-cream', '#fbf3e7'),
    glow: token('--color-coral-glow', '#ffb27a'),
    shadow: `rgb(${token('--rgb-black', '0 0 0')} / 0.5)`
  };
  const tones = [palette.coral, palette.honey, palette.coral, palette.honey, palette.cream];

  let particles = [];
  let word = null; // { text, font, x, y, alpha, target: 0 | 1, leaving }
  let width = 0;
  let height = 0;
  let suspended = false;
  let revealTimer = null;

  function resize() {
    const dpr = Math.min(window.devicePixelRatio || 1, 2);
    width = canvas.clientWidth;
    height = canvas.clientHeight;
    canvas.width = Math.round(width * dpr);
    canvas.height = Math.round(height * dpr);
    context.setTransform(dpr, 0, 0, dpr, 0, 0);
  }

  // ---------- Simulação ----------
  function stepParticle(p, dt) {
    if (p.mode === 'form') {
      p.delay -= dt;
      if (p.delay <= 0) {
        p.vx += (SPRING_K * (p.tx - p.x) - SPRING_C * p.vx) * dt;
        p.vy += (SPRING_K * (p.ty - p.y) - SPRING_C * p.vy) * dt;
        p.size += (p.formSize - p.size) * Math.min(1, dt * 6);
        p.spin *= Math.exp(-3 * dt);
      } else {
        // ainda esperando a vez: continua caindo devagar
        p.vy += GRAVITY * 0.35 * dt;
        p.vx *= Math.exp(-AIR_DRAG * dt);
        p.vy *= Math.exp(-AIR_DRAG * dt);
      }
    } else {
      const gravity = p.mode === 'scatter' ? SCATTER_GRAVITY : GRAVITY;
      p.vy += gravity * dt;
      p.vx *= Math.exp(-AIR_DRAG * dt);
      p.vy *= Math.exp(-AIR_DRAG * dt);
      if (p.mode === 'scatter') p.alpha -= SCATTER_FADE * dt;
      // caiu muito longe da tela: some (as que caíram só um pouco ainda podem formar a palavra)
      else if (p.y > height + 600) p.alpha = 0;
    }
    p.x += p.vx * dt;
    p.y += p.vy * dt;
    p.angle += p.spin * dt;
  }

  // ---------- Desenho ----------
  function drawParticle(p) {
    context.globalAlpha = Math.max(0, Math.min(1, p.alpha));
    context.fillStyle = p.color;
    context.save();
    context.translate(p.x, p.y);
    context.rotate(p.angle);
    const s = p.size;
    if (p.shape === 'spark') {
      // estrela de quatro pontas
      context.beginPath();
      context.moveTo(0, -s * 1.5);
      context.quadraticCurveTo(s * 0.18, -s * 0.18, s * 1.5, 0);
      context.quadraticCurveTo(s * 0.18, s * 0.18, 0, s * 1.5);
      context.quadraticCurveTo(-s * 0.18, s * 0.18, -s * 1.5, 0);
      context.quadraticCurveTo(-s * 0.18, -s * 0.18, 0, -s * 1.5);
      context.fill();
    } else if (p.shape === 'chip') {
      context.fillRect(-s * 0.9, -s * 0.45, s * 1.8, s * 0.9);
    } else {
      context.beginPath();
      context.arc(0, 0, s * 0.75, 0, Math.PI * 2);
      context.fill();
    }
    context.restore();
  }

  function drawWord() {
    if (!word || word.alpha <= 0.01) return;
    context.save();
    context.globalAlpha = Math.min(1, word.alpha);
    context.font = word.font;
    context.textAlign = 'center';
    context.textBaseline = 'middle';
    // sombra escura bem difusa: a palavra lê sobre qualquer fundo de marca
    context.shadowColor = palette.shadow;
    context.shadowBlur = word.size * 0.5;
    context.fillStyle = palette.shadow;
    context.fillText(word.text, word.x, word.y);
    // a palavra em si, com um brilho quente
    const gradient = context.createLinearGradient(word.x - word.width / 2, 0, word.x + word.width / 2, 0);
    gradient.addColorStop(0, palette.coral);
    gradient.addColorStop(1, palette.honey);
    context.shadowColor = palette.glow;
    context.shadowBlur = word.size * 0.35;
    context.fillStyle = gradient;
    context.fillText(word.text, word.x, word.y);
    // contorno creme fino: a palavra fica nítida mesmo sobre fundos quentes
    context.shadowBlur = 0;
    context.globalAlpha = Math.min(1, word.alpha) * 0.7;
    context.strokeStyle = palette.cream;
    context.lineWidth = Math.max(1, word.size * 0.014);
    context.strokeText(word.text, word.x, word.y);
    context.restore();
  }

  function frame(dtMs) {
    if (suspended) return;
    const dt = dtMs / 1000;
    context.clearRect(0, 0, width, height);

    if (word) {
      const speed = word.target ? TEXT_FADE_IN : TEXT_FADE_OUT;
      word.alpha += (word.target - word.alpha) * Math.min(1, dt * speed);
      if (word.leaving && word.alpha < 0.01) word = null;
    }
    drawWord();

    particles.forEach((p) => {
      stepParticle(p, dt);
      drawParticle(p);
    });
    context.globalAlpha = 1;
    particles = particles.filter((p) => p.alpha > 0);

    if (!particles.length && !word) loop.pause();
  }

  resize();
  const loop = frameLoop(animator, frame);
  loop.pause();
  const observer = new ResizeObserver(resize);
  observer.observe(canvas);
  animator.onDispose(() => {
    observer.disconnect();
    window.clearTimeout(revealTimer);
  });

  const wake = () => {
    if (!suspended) loop.resume();
  };

  // ---------- Pontos da palavra ----------
  /** Desenha a palavra fora da tela e sorteia pontos dos pixels pintados. */
  function sampleWord(text, { x, y, size, maxWidth }) {
    let fontSize = size;
    const probe = document.createElement('canvas').getContext('2d');
    const fontFor = (px) => `700 ${px}px Fraunces, Georgia, serif`;
    probe.font = fontFor(fontSize);
    const measured = probe.measureText(text).width;
    if (measured > maxWidth) fontSize = Math.floor((fontSize * maxWidth) / measured);

    const font = fontFor(fontSize);
    const pad = Math.ceil(fontSize * 0.4);
    probe.font = font;
    const textWidth = Math.ceil(probe.measureText(text).width);
    const off = document.createElement('canvas');
    off.width = textWidth + pad * 2;
    off.height = Math.ceil(fontSize * 1.5);
    const offContext = off.getContext('2d', { willReadFrequently: true });
    offContext.font = font;
    offContext.textAlign = 'center';
    offContext.textBaseline = 'middle';
    offContext.fillStyle = '#000';
    offContext.fillText(text, off.width / 2, off.height / 2);

    const { data } = offContext.getImageData(0, 0, off.width, off.height);
    const step = Math.max(2, Math.round(fontSize / 18));
    const points = [];
    for (let py = 0; py < off.height; py += step) {
      for (let px = 0; px < off.width; px += step) {
        if (data[(py * off.width + px) * 4 + 3] > 140) {
          points.push({ x: x - off.width / 2 + px, y: y - off.height / 2 + py });
        }
      }
    }
    return { points: shuffle(points), font, fontSize, textWidth };
  }

  return {
    /** Explosão saindo de (x, y), em px dentro do canvas. */
    burst(x, y, { count = 80, power = 1 } = {}) {
      for (let i = 0; i < count; i += 1) {
        const angle = between(-Math.PI * 0.95, -Math.PI * 0.05) + between(-0.5, 0.5);
        const speed = between(320, 980) * power;
        particles.push({
          x,
          y,
          vx: Math.cos(angle) * speed,
          vy: Math.sin(angle) * speed,
          angle: between(0, Math.PI * 2),
          spin: between(-14, 14),
          size: between(3, 7.5) * Math.max(0.8, power),
          formSize: 2.6,
          shape: SHAPES[i % SHAPES.length],
          color: tones[i % tones.length],
          alpha: 1,
          mode: 'free',
          delay: 0,
          tx: x,
          ty: y
        });
      }
      wake();
    },

    /**
     * Molas levam as partículas até a palavra, centrada em (x, y).
     * size: tamanho de fonte desejado; maxWidth: a palavra encolhe para caber.
     */
    formWord(text, { x = width / 2, y = height / 2, size = 96, maxWidth = width * 0.9 } = {}) {
      const sample = sampleWord(text, { x, y, size, maxWidth });
      const { points } = sample;
      if (!points.length) return;
      particles.forEach((p, i) => {
        const target = points[Math.floor((i * points.length) / particles.length)];
        p.mode = 'form';
        p.tx = target.x;
        p.ty = target.y;
        p.alpha = 1;
        p.delay = (i / particles.length) * FORM_STAGGER_S;
        p.formSize = Math.max(2, sample.fontSize / 26);
      });
      word = {
        text,
        font: sample.font,
        size: sample.fontSize,
        width: sample.textWidth,
        x,
        y,
        alpha: 0,
        target: 0,
        leaving: false
      };
      // a palavra nítida acende quando a maior parte das partículas já chegou
      window.clearTimeout(revealTimer);
      revealTimer = window.setTimeout(() => {
        if (word && word.text === text) word.target = 1;
      }, 520);
      wake();
    },

    /** A palavra se desfaz: as partículas se soltam para cima e para os lados e somem. */
    scatter() {
      particles.forEach((p) => {
        p.mode = 'scatter';
        const angle = between(-Math.PI, 0);
        const speed = between(80, 340);
        p.vx = Math.cos(angle) * speed;
        p.vy = Math.sin(angle) * speed;
        p.spin = between(-8, 8);
      });
      window.clearTimeout(revealTimer);
      if (word) {
        word.target = 0;
        word.leaving = true;
      }
      wake();
    },

    /** Limpa tudo na hora. */
    clear() {
      particles = [];
      word = null;
      context.clearRect(0, 0, width, height);
      loop.pause();
    },

    /** Para o desenho (cena fora da tela ou aba oculta). */
    pause() {
      suspended = true;
      loop.pause();
    },

    resume() {
      suspended = false;
      if (particles.length || word) loop.resume();
    },

    /** Avisa que as fontes chegaram (a palavra é medida em Fraunces). */
    ready: document.fonts ? document.fonts.load('700 96px Fraunces').catch(() => null) : Promise.resolve()
  };
}
