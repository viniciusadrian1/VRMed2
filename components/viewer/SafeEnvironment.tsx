"use client";

import { useEffect, useMemo } from "react";
import { useThree } from "@react-three/fiber";
import * as THREE from "three";
import { RoomEnvironment } from "three/examples/jsm/environments/RoomEnvironment.js";

/**
 * Mapa de ambiente local (RoomEnvironment + PMREM), sem rede; não passa pelo
 * DefaultLoadingManager, então não dispara o ViewerLoader.
 * Declarativo (attach) porque o React Compiler proíbe mutar `scene`.
 */
export function SafeEnvironment() {
  const gl = useThree((state) => state.gl);
  const ambiente = useMemo(() => {
    const pmrem = new THREE.PMREMGenerator(gl);
    const textura = pmrem.fromScene(new RoomEnvironment(), 0.04).texture;
    pmrem.dispose();
    return textura;
  }, [gl]);
  useEffect(() => () => ambiente.dispose(), [ambiente]);
  return <primitive object={ambiente} attach="environment" />;
}
