"use client";

import { useRef, type RefObject } from "react";
import { useFrame, useThree } from "@react-three/fiber";
import { OrbitControls } from "@react-three/drei";
import * as THREE from "three";
import type { Vec3 } from "@/types";

/** Estado de câmera compartilhado entre os dois canvas da comparação. */
export interface CameraSyncState {
  pos: Vec3;
  target: Vec3;
  /** Incrementado a cada alteração feita pelo usuário — detecta o canvas ativo. */
  epoch: number;
}

interface OrbitLike {
  target: THREE.Vector3;
  update: () => void;
}

interface SyncedCamerasProps {
  syncRef: RefObject<CameraSyncState>;
  synced: boolean;
  minDistance?: number;
  maxDistance?: number;
}

/**
 * OrbitControls com sincronização opcional entre os dois lados da comparação.
 * O canvas que recebe a interação do usuário grava a câmera no estado
 * compartilhado; o outro acompanha. Uma flag evita laços de realimentação.
 */
export function SyncedCameras({
  syncRef,
  synced,
  minDistance = 1.8,
  maxDistance = 12,
}: SyncedCamerasProps) {
  const camera = useThree((s) => s.camera);
  const controls = useThree((s) => s.controls) as unknown as OrbitLike | null;
  const invalidate = useThree((s) => s.invalidate);
  const localEpoch = useRef(0);
  const applying = useRef(false);

  // Alteração feita pelo usuário neste canvas → publica no estado compartilhado.
  const handleChange = () => {
    if (applying.current || !synced || !controls) return;
    syncRef.current.pos = [
      camera.position.x,
      camera.position.y,
      camera.position.z,
    ];
    syncRef.current.target = [
      controls.target.x,
      controls.target.y,
      controls.target.z,
    ];
    syncRef.current.epoch += 1;
    localEpoch.current = syncRef.current.epoch;
  };

  // Quando o outro canvas avança o epoch, este acompanha a câmera.
  useFrame(() => {
    if (!synced || !controls) return;
    if (syncRef.current.epoch === localEpoch.current) return;
    applying.current = true;
    const { pos, target } = syncRef.current;
    camera.position.set(pos[0], pos[1], pos[2]);
    controls.target.set(target[0], target[1], target[2]);
    controls.update();
    localEpoch.current = syncRef.current.epoch;
    applying.current = false;
    invalidate();
  });

  return (
    <OrbitControls
      makeDefault
      enableDamping
      dampingFactor={0.08}
      enablePan={false}
      minDistance={minDistance}
      maxDistance={maxDistance}
      onChange={handleChange}
    />
  );
}
