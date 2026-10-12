/**
 * Configuração geral das animações (um único lugar para ajustar).
 *
 * respectReducedMotion:
 *   false → as animações rodam SEMPRE, como no projeto original. Esse é o padrão porque,
 *           no Windows com "Efeitos de animação" desligado, o navegador pede "menos movimento"
 *           e a landing ficaria parada.
 *   true  → quem ativou "reduzir movimento" no sistema vê a página já no estado final.
 *
 * intensity: 'sutil' | 'equilibrada' | 'cinematografica'
 * loopScenes: as cenas animadas se repetem (foto, IA, brilho do preço, clique do hero)
 * parallax:   as luzes do topo andam mais devagar que a rolagem
 */
export const MOTION_CONFIG = {
  respectReducedMotion: false,
  intensity: 'cinematografica',
  loopScenes: true,
  parallax: true
};

/**
 * Vitrine de marketplaces da landing: quanto dura a cena de cada marketplace, da entrada
 * até a saída (5 s: nem rápido, nem devagar). A coreografia inteira escala com esse tempo.
 */
export const MARKETPLACE_SHOWCASE_SCENE_MS = 5000;

/** Partículas da explosão do clique na vitrine: desktop e celular. */
export const SHOWCASE_PARTICLES = { desktop: 80, mobile: 40 };
