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
