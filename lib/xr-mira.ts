import type { DefaultXRInputSourceRayPointerOptions } from "@react-three/xr";
import type { Pointer } from "@pmndrs/pointer-events";
import { DoubleSide, MeshBasicMaterial, type WebGLProgramParametersWithUniforms, type WebGLRenderer } from "three";

/** A linha é visual; o alcance da seleção continua sendo o do raycast real. */
export const COMPRIMENTO_MIRA_XR = 12;
export const ORDEM_MIRA_XR = 1_000_000;

function temAlvo(ponteiro: Pointer) {
  const hit = ponteiro.getIntersection();
  return hit != null && !hit.object.isVoidObject;
}

function corMira(ponteiro: Pointer) {
  // Âmbar indica gatilho pressionado, não resposta certa nem operação concluída.
  if (ponteiro.getButtonsDown().size > 0) return "#fbbf24";
  return temAlvo(ponteiro) ? "#67e8f9" : "#cbd5e1";
}

/** Sem o fade padrão que apaga justamente a ponta do raio junto ao botão. */
export class MaterialRaioXR extends MeshBasicMaterial {
  constructor() {
    super({ transparent: true, toneMapped: false, depthWrite: false, depthTest: false });
  }
}

/** Ponto preciso + anel com contorno escuro, legível sobre painéis claros/escuros. */
export class MaterialCursorXR extends MeshBasicMaterial {
  constructor() {
    super({ transparent: true, toneMapped: false, depthWrite: false, depthTest: false, side: DoubleSide });
  }

  override onBeforeCompile(shader: WebGLProgramParametersWithUniforms, renderer: WebGLRenderer) {
    super.onBeforeCompile(shader, renderer);
    shader.vertexShader = "varying vec2 vMiraXR;\n" + shader.vertexShader;
    shader.vertexShader = shader.vertexShader.replace("#include <begin_vertex>",
      "#include <begin_vertex>\nvMiraXR = position.xy * 2.0;");
    shader.fragmentShader = "varying vec2 vMiraXR;\n" + shader.fragmentShader;
    shader.fragmentShader = shader.fragmentShader.replace("#include <color_fragment>", `
      #include <color_fragment>
      float rMira = length(vMiraXR);
      float aaMira = max(fwidth(rMira), 0.015);
      float pontoMira = 1.0 - smoothstep(0.16 - aaMira, 0.16 + aaMira, rMira);
      float anelMira = smoothstep(0.60 - aaMira, 0.60 + aaMira, rMira)
        * (1.0 - smoothstep(0.80 - aaMira, 0.80 + aaMira, rMira));
      float mascaraMira = max(
        1.0 - smoothstep(0.29 - aaMira, 0.29 + aaMira, rMira),
        smoothstep(0.47 - aaMira, 0.47 + aaMira, rMira)
          * (1.0 - smoothstep(0.96 - aaMira, 0.96 + aaMira, rMira)));
      diffuseColor.rgb = mix(vec3(0.008, 0.016, 0.025), diffuseColor.rgb, anelMira);
      diffuseColor.rgb = mix(diffuseColor.rgb, vec3(1.0), pontoMira);
      diffuseColor.a *= mascaraMira;
    `);
  }
}

/**
 * Mesma interseção para linha, cursor e gatilho — sem uma segunda mira paralela.
 * A UI já aparece sobre o cenário: desenhar o cursor depois dela evita que
 * painéis transparentes/depthTest=false escondam o ponto de seleção.
 * Sem alvo a biblioteca mantém a linha, mas oculta o cursor (voidObject).
 */
export const MIRA_XR = {
  minDistance: 0.05,
  rayModel: {
    maxLength: COMPRIMENTO_MIRA_XR,
    size: 0.003,
    color: corMira,
    opacity: (ponteiro: Pointer) => temAlvo(ponteiro) ? 0.75 : 0.3,
    renderOrder: ORDEM_MIRA_XR,
    materialClass: MaterialRaioXR,
  },
  cursorModel: {
    size: 0.024,
    color: corMira,
    opacity: 1,
    cursorOffset: 0.001,
    renderOrder: ORDEM_MIRA_XR + 1,
    materialClass: MaterialCursorXR,
  },
} satisfies DefaultXRInputSourceRayPointerOptions;

// O grip continua disponível para XRManipulation (leitura direta do gamepad).
// Remover o ponteiro esférico evita que ele desative o raio perto de um órgão.
export const CONTROLE_XR = { grabPointer: false, teleportPointer: false, rayPointer: MIRA_XR } as const;
