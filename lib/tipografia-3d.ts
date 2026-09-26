import * as THREE from "three";

/** Interface legível e sinalização física não compartilham a mesma profundidade. */
export type TratamentoTexto3D = "sobreposto" | "interface" | "placa" | "tela";

export const TIPOGRAFIA_3D = {
  sobreposto: { contorno: 0.05, entrelinha: undefined, ordem: 1000, profundidade: false },
  interface: { contorno: 0, entrelinha: 1.2, ordem: 1000, profundidade: false },
  placa: { contorno: 0, entrelinha: 1.2, ordem: 1, profundidade: true },
  tela: { contorno: 0, entrelinha: 1.2, ordem: 1, profundidade: true },
} as const;

export function criarMaterialTexto3D(tratamento: TratamentoTexto3D) {
  const opcoes = {
    transparent: true,
    depthWrite: false,
    depthTest: TIPOGRAFIA_3D[tratamento].profundidade,
    side: tratamento === "placa" || tratamento === "tela" ? THREE.FrontSide : THREE.DoubleSide,
    toneMapped: tratamento === "placa",
  };
  // Placa acompanha a luz; tela mantém contraste, mas não atravessa a parede.
  return tratamento === "placa"
    ? new THREE.MeshStandardMaterial({ ...opcoes, roughness: 1, metalness: 0 })
    : new THREE.MeshBasicMaterial(opcoes);
}

/** Recuo só do desenho: não altera dimensões, posição ou prioridade do alvo. */
export function layoutRotuloBotao(largura: number, altura: number, selo: boolean, icone: boolean) {
  const margem = Math.min(largura * 0.08, altura * 0.36);
  const recuo = selo ? altura * 0.94 : icone ? altura * 0.88 : margem;
  return { x: -largura / 2 + recuo, largura: largura - recuo - margem };
}
