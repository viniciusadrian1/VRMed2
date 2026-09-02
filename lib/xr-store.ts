import { createXRStore } from "@react-three/xr";

let store: ReturnType<typeof createXRStore> | undefined;

/**
 * Uma store XR para o app inteiro, criada no primeiro uso — não uma por
 * montagem. Cada `createXRStore` pendura um <div> de overlay no body, um
 * listener de teclado e outro de `sessiongranted`, e nunca chama `destroy()`
 * (destruir sob o StrictMode quebrava a religada do renderer); cada ida e
 * volta Home → Sala/Duelo vazava tudo isso, e as stores órfãs ainda tentavam
 * abrir sessão num renderer já descartado. Um Canvas novo religa a mesma
 * store via setWebXRManager (que só ignora o MESMO manager).
 *
 * Endurecimento da Arena (lições dos testes no Quest 2): perfis locais em URL
 * absoluta, só o ponteiro de raio, recursos de realidade mista desligados e
 * taxa de quadros intocada.
 */
export function obterXRStore() {
  store ??= createXRStore({
    baseAssetPath:
      typeof window !== "undefined"
        ? `${window.location.origin}/webxr-profiles/`
        : "https://localhost/webxr-profiles/",
    controller: { grabPointer: false, teleportPointer: false },
    hand: { model: false, grabPointer: false, touchPointer: false },
    anchors: false,
    meshDetection: false,
    planeDetection: false,
    hitTest: false,
    depthSensing: false,
    frameRate: false,
    foveation: 0.5,
  });
  return store;
}
