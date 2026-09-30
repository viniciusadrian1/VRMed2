/** Centro do assento original; a mesa fica na direção local -Z. */
export const ASSENTO_SALA: [number, number, number] = [0, 0, -1.15];

interface Ponto3D { x: number; y: number; z: number }

/** Alinha a sala à cabeça sem alterar altura, escala, inclinação ou câmera. */
export function calcularRecentralizacaoSala(cabeca: Ponto3D, frente: Ponto3D, chaoY: number) {
  if (![cabeca.x, cabeca.y, cabeca.z, frente.x, frente.y, frente.z, chaoY].every(Number.isFinite)) return null;
  // Olhar vertical não define uma frente estável: aguardar um novo quadro.
  if (frente.x ** 2 + frente.z ** 2 < 1e-4) return null;
  const rotacaoY = Math.atan2(-frente.x, -frente.z);
  return {
    rotacaoY,
    posicao: [
      cabeca.x - Math.sin(rotacaoY) * ASSENTO_SALA[2],
      chaoY,
      cabeca.z - Math.cos(rotacaoY) * ASSENTO_SALA[2],
    ] as [number, number, number],
    // Só a faixa de botões acompanha a altura. O piso e os móveis não sobem.
    alturaControles: Math.max(0.5, cabeca.y - chaoY - 0.38),
  };
}

export interface EstadoAtalhoSala {
  fonte: object | undefined;
  pressionado: boolean;
}

/** Um disparo por aperto; conectar um controle com botão segurado não dispara. */
export function apertouRecentralizarSala(estado: EstadoAtalhoSala, fonte: object | undefined, pressionado: boolean) {
  const apertou = fonte !== undefined && estado.fonte === fonte && pressionado && !estado.pressionado;
  estado.fonte = fonte;
  estado.pressionado = pressionado;
  return apertou;
}
