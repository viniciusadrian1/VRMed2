/** O acervo ósseo mantém 158.090 triângulos: não disputar GPU com a rodada. */
export function mostrarEsqueleto3D(fase: string, solicitado: boolean) {
  return solicitado && (fase === "menu" || fase === "fim");
}

export const ESCOLA = {
  piso: -1.3,
  lousaX: 0.36,
  lousaZ: -1.06,
  larguraOpcao: 1.1,
  alturaOpcao: 0.094,
  passoOpcao: 0.115,
} as const;
