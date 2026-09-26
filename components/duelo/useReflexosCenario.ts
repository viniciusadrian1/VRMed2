"use client";

import { useLayoutEffect } from "react";
import { useThree } from "@react-three/fiber";
import * as THREE from "three";

type Entrada = { alvo: THREE.WebGLRenderTarget; usuarios: number };
const ambientes = new WeakMap<THREE.WebGLRenderer, Entrada>();

/** Reflexo de luminárias grandes, gerado uma vez e compartilhado pelo cenário.
 * Não usa scene.environment: os órgãos e a interface mantêm seus materiais/luzes.
 */
function adquirir(gl: THREE.WebGLRenderer): Entrada {
  const existente = ambientes.get(gl);
  if (existente) { existente.usuarios++; return existente; }
  const sala = new THREE.Scene();
  sala.background = new THREE.Color("#34474b");
  const geometria = new THREE.PlaneGeometry();
  const materiais: THREE.MeshBasicMaterial[] = [];
  const painel = (pos: [number, number, number], tam: [number, number], cor: string, intensidade: number) => {
    const mat = new THREE.MeshBasicMaterial({ color: new THREE.Color(cor).multiplyScalar(intensidade), side: THREE.DoubleSide });
    materiais.push(mat);
    const objeto = new THREE.Mesh(geometria, mat);
    objeto.position.set(...pos); objeto.scale.set(tam[0], tam[1], 1);
    objeto.lookAt(0, 0, 0); sala.add(objeto);
  };
  painel([-4, 1, 0], [5, 2], "#e5f4ff", 2.0);
  painel([2.5, 3.5, 0], [1.2, 6], "#fff2d5", 2.5);
  painel([-2.5, 3.5, 0], [1.2, 6], "#fff2d5", 2.5);
  painel([4, 0, -2], [2, 3], "#87b9c1", .65);
  const gerador = new THREE.PMREMGenerator(gl);
  try {
    const alvo = gerador.fromScene(sala, .04, .1, 20, { size: 128 });
    const entrada = { alvo, usuarios: 1 };
    ambientes.set(gl, entrada);
    return entrada;
  } finally {
    gerador.dispose(); geometria.dispose(); materiais.forEach(mat => mat.dispose());
    sala.clear();
  }
}

/** Materiais são cópias locais; a troca de sala restaura e libera cada recurso. */
export function useReflexosCenario(cena: THREE.Object3D) {
  const gl = useThree(s => s.gl);
  useLayoutEffect(() => {
    const entrada = adquirir(gl);
    const originais = new Map<THREE.Mesh, THREE.Material | THREE.Material[]>();
    const copias = new Map<THREE.Material, THREE.Material>();
    const copiar = (mat: THREE.Material) => {
      if (!(mat instanceof THREE.MeshStandardMaterial)) return mat;
      if (!copias.has(mat)) {
        const novo = mat.clone();
        novo.envMap = entrada.alvo.texture;
        novo.envMapIntensity = .55;
        copias.set(mat, novo);
      }
      return copias.get(mat)!;
    };
    cena.traverse(obj => {
      if (!(obj instanceof THREE.Mesh)) return;
      originais.set(obj, obj.material);
      obj.material = Array.isArray(obj.material) ? obj.material.map(copiar) : copiar(obj.material);
    });
    return () => {
      originais.forEach((mat, obj) => { obj.material = mat; });
      copias.forEach(mat => mat.dispose());
      if (--entrada.usuarios === 0) {
        entrada.alvo.dispose(); ambientes.delete(gl);
      }
    };
  }, [cena, gl]);
}
