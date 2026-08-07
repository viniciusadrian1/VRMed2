import type * as THREE from "three";

/**
 * Estrutura jogável da Arena.
 *
 * `local` é a posição no espaço do grupo que sofre a manipulação (pegar,
 * girar, escalar) — e não no mundo. Guardar coordenada de mundo faria a dica
 * ficar para trás no instante em que o jogador movesse o órgão.
 */
export interface ArenaStructure {
  id: string;
  label: string;
  local: THREE.Vector3;
}

/** Fases da partida. */
export type ArenaPhase = "ocioso" | "contagem" | "jogando" | "resultado";

/** Registro de um alvo já jogado, usado no laudo final. */
export interface ArenaAttempt {
  label: string;
  acertou: boolean;
}
