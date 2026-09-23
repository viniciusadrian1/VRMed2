import { Matrix4, Plane, Ray, Vector2, Vector3, type Intersection, type Mesh, type PlaneGeometry, type Raycaster } from "three";

const inversa = new Matrix4(), raio = new Ray(), local = new Vector3();
const plano = new Plane(new Vector3(0, 0, 1), 0);

/** Área retangular contínua, sem a emenda numérica dos dois triângulos da placa. */
export function raioPlacaXR(this: Mesh, raycaster: Raycaster, intersecoes: Intersection[]) {
  const { width: largura, height: altura } = (this.geometry as PlaneGeometry).parameters;
  if (!(largura > 0 && altura > 0)) return;
  inversa.copy(this.matrixWorld).invert();
  raio.copy(raycaster.ray).applyMatrix4(inversa);
  if (!raio.intersectPlane(plano, local)) return;
  if (Math.abs(local.x) > largura / 2 || Math.abs(local.y) > altura / 2) return;
  const uv = new Vector2(local.x / largura + 0.5, local.y / altura + 0.5);
  const ponto = local.clone().applyMatrix4(this.matrixWorld), distancia = ponto.distanceTo(raycaster.ray.origin);
  if (distancia < raycaster.near || distancia > raycaster.far) return;
  intersecoes.push({ distance: distancia, point: ponto, object: this, uv, normal: new Vector3(0, 0, 1) });
}
