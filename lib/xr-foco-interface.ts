import { fonteDoPonteiro } from "./botao3d-interacao.ts";

// Dono + ponteiro: sair de um botão não apaga o hover que já entrou em outro.
const alvos = new Map<object, Map<number, XRHandedness>>();

export function ocuparPonteiroUI(dono: object, evento: { pointerId: number }) {
  const fonte = fonteDoPonteiro(evento);
  if (!fonte || fonte.handedness === "none") return;
  let ponteiros = alvos.get(dono);
  if (!ponteiros) alvos.set(dono, ponteiros = new Map());
  ponteiros.set(evento.pointerId, fonte.handedness);
}

export function liberarPonteiroUI(dono: object, pointerId?: number) {
  if (pointerId == null) alvos.delete(dono);
  else {
    const ponteiros = alvos.get(dono);
    ponteiros?.delete(pointerId);
    if (!ponteiros?.size) alvos.delete(dono);
  }
}

export function maoNaInterface(lado: "left" | "right") {
  for (const ponteiros of alvos.values()) {
    for (const mao of ponteiros.values()) if (mao === lado) return true;
  }
  return false;
}

/** Uma pinça iniciada na UI fica reservada à UI até soltar, mesmo fora da placa. */
export function bloquearPincaUI(pressionada: boolean, anterior: boolean, bloqueada: boolean, sobreUI: boolean) {
  return pressionada && (anterior ? bloqueada : sobreUI);
}
