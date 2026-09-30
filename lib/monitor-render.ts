import type { Camera, Scene, WebGLRenderer, WebGLRenderTarget } from "three";

/** Preserva o framebuffer XR mesmo se a renderização da ferramenta falhar. */
export function renderizarModeloNoMonitor(gl: WebGLRenderer, alvo: WebGLRenderTarget, cena: Scene, camera: Camera) {
  const anterior = gl.getRenderTarget(), xr = gl.xr.enabled, limpar = gl.autoClear;
  const face = gl.getActiveCubeFace(), mip = gl.getActiveMipmapLevel();
  try {
    gl.xr.enabled = false; gl.autoClear = true;
    gl.setRenderTarget(alvo); gl.render(cena, camera);
  } finally {
    gl.setRenderTarget(anterior, face, mip); gl.xr.enabled = xr; gl.autoClear = limpar;
  }
}
