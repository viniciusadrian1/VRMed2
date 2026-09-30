import { Matrix4, Vector3, type Intersection, type Mesh, type Raycaster } from "three";
import { raioPlacaXR } from "./raio-placa-xr.ts";

const inversa = new Matrix4(), direcao = new Vector3();
/** O menu só pode ser selecionado pela frente da tela física. */
export function raioMonitorEstudos(this: Mesh, raycaster: Raycaster, hits: Intersection[]) {
  inversa.copy(this.matrixWorld).invert();
  direcao.copy(raycaster.ray.direction).transformDirection(inversa);
  if (direcao.z >= 0) return;
  raioPlacaXR.call(this, raycaster, hits);
}
