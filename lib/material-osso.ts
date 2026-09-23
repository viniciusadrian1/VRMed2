import * as THREE from "three";

/** Acabamento visual de osso seco. Não inventa suturas nem altera geometria/UV. */
export function aplicarMaterialOsso(raiz: THREE.Object3D) {
  raiz.traverse((obj) => {
    if (!(obj instanceof THREE.Mesh)) return;
    const dentes = /teeth|tooth/i.test(`${obj.name} ${obj.parent?.name ?? ""}`);
    const materiais = Array.isArray(obj.material) ? obj.material : [obj.material];
    for (const mat of materiais) {
      if (!(mat instanceof THREE.MeshStandardMaterial)) continue;
      mat.color.set(dentes ? "#e5dcc7" : "#cbbfaa");
      mat.metalness = 0;
      mat.roughness = dentes ? 0.38 : 0.72;
      mat.envMapIntensity = 0.32;
      // Camadas e inspeção restauram este acabamento, não o branco estourado.
      mat.userData.originalColor = mat.color.clone();
    }
  });
}
