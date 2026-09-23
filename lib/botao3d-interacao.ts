/** Contrato comum ao botão renderizado e aos testes com o ponteiro XR real. */
export const ORDEM_PONTEIRO_UI = 1000;
export const CAMADAS_UI3D = { painel: 998, botao: 999, contorno: 1000, texto: 1001 } as const;

export function deveAcionarBotao3D(etapa: "pressionar" | "clicar", evento: object) {
  const { pointerType, button } = evento as { pointerType?: string; button?: number };
  if (button != null && button !== 0) return false;
  // O raio XR confirma no selectstart. O click padrão exige soltar em até
  // 300 ms e sobre a mesma malha: apertos mais demorados sumiam silenciosamente.
  // Ignorar o click do raio também impede selecionar de novo ao soltar em outra tela.
  return etapa === (pointerType === "ray" ? "pressionar" : "clicar");
}

export function fonteDoPonteiro(evento: object): XRInputSource | undefined {
  return (evento as { pointerState?: { inputSource?: XRInputSource } }).pointerState?.inputSource;
}
