import { Matrix4, Object3D, Vector3 } from "three";

export function eixoSuaveXR(valor: number) {
  if (!Number.isFinite(valor) || Math.abs(valor) < 0.2) return 0;
  const t = (Math.min(1, Math.abs(valor)) - 0.2) / 0.8;
  return Math.sign(valor) * t * t;
}

/** Esquerdo orienta/abre; direito translada. Diagonal esquerda não abre ossos ao tentar girar. */
export function analogicosEstudoXR(lx: number, ly: number, rx: number, ry: number, bloquearEsquerdo = false, bloquearDireito = false) {
  return {
    giro: bloquearEsquerdo || Math.abs(lx) < Math.abs(ly) ? 0 : eixoSuaveXR(lx),
    aberturaOuTombo: bloquearEsquerdo || Math.abs(ly) <= Math.abs(lx) ? 0 : eixoSuaveXR(ly),
    lateral: bloquearDireito ? 0 : eixoSuaveXR(rx),
    profundidade: bloquearDireito ? 0 : eixoSuaveXR(ry),
  };
}

const cabeca = new Vector3(), direita = new Vector3(), frente = new Vector3(), atual = new Vector3(), seguinte = new Vector3(), local = new Vector3(), cima = new Vector3(0, 1, 0);
const inversa = new Matrix4();
/** Translada só o modelo no plano horizontal do olhar; funciona com pais transformados. */
export function transladarModeloXR(modelo: Object3D, camera: Object3D, lateral: number, profundidade: number, delta: number) {
  if (!lateral && !profundidade) return;
  camera.updateWorldMatrix(true, false); modelo.updateWorldMatrix(true, false);
  camera.getWorldPosition(cabeca); modelo.getWorldPosition(atual);
  camera.getWorldDirection(frente); frente.y = 0;
  if (frente.lengthSq() < 1e-4) return;
  frente.normalize(); direita.crossVectors(frente, cima).normalize();
  const dt = Math.min(Math.max(0, delta), 1 / 30), normalizar = Math.max(1, Math.hypot(lateral, profundidade));
  seguinte.copy(atual).addScaledVector(direita, lateral * 0.7 * dt / normalizar)
    // Empurrar o analógico afasta; puxar aproxima. A altura permanece a mesma.
    .addScaledVector(frente, -profundidade * 0.7 * dt / normalizar);
  const antes = Math.hypot(atual.x - cabeca.x, atual.z - cabeca.z);
  const depois = Math.hypot(seguinte.x - cabeca.x, seguinte.z - cabeca.z);
  if (depois < Math.min(0.28, antes) || depois > Math.max(5, antes)) return;
  local.copy(seguinte);
  if (modelo.parent) { modelo.parent.updateWorldMatrix(true, false); local.applyMatrix4(inversa.copy(modelo.parent.matrixWorld).invert()); }
  modelo.position.copy(local);
}
