"use client";

import { useEffect, useMemo, useRef, type RefObject } from "react";
import { useFrame, useThree } from "@react-three/fiber";
import { Billboard } from "@react-three/drei";
import { useXR } from "@react-three/xr";
import * as THREE from "three";
import { Text3D } from "@/components/arena/ui3d";
import { identifyStructure } from "@/lib/model-utils";
import { useTutor3D } from "@/lib/tutor-3d-store";
import { viewerBridge } from "@/lib/viewer-bridge";

/** O marcador acompanha o root, inclusive quando o aluno pega o modelo no VR. */
export function FocoTutor3D({ rootRef, contentRef }: {
  rootRef: RefObject<THREE.Group | null>; contentRef: RefObject<THREE.Group | null>;
}) {
  const foco = useTutor3D((s) => s.foco);
  const inSession = useXR((s) => Boolean(s.session));
  const invalidate = useThree((s) => s.invalidate);
  const anel = useRef<THREE.Mesh>(null);
  const tempo = useRef(0);
  const ultimoFoco = useRef<number | null>(null);
  const reduzido = useMemo(() => window.matchMedia("(prefers-reduced-motion: reduce)").matches, []);
  const medidaRef = useRef({ centro: new THREE.Vector3(), raio: 0.2, valido: false });

  useEffect(() => {
    const medida = medidaRef.current;
    medida.valido = false;
    tempo.current = 0;
    const root = rootRef.current, content = contentRef.current;
    if (!foco || !root || !content) return;
    const novo = ultimoFoco.current !== foco.sequencia;
    ultimoFoco.current = foco.sequencia;
    root.updateWorldMatrix(true, true);
    const caixa = new THREE.Box3();
    content.traverse((obj) => {
      if (!(obj instanceof THREE.Mesh)) return;
      if (foco.id !== "modelo" && identifyStructure(obj) !== foco.label) return;
      caixa.union(new THREE.Box3().setFromObject(obj));
    });
    if (caixa.isEmpty()) return;
    const esfera = caixa.getBoundingSphere(new THREE.Sphere());
    medida.centro.copy(root.worldToLocal(esfera.center.clone()));
    medida.raio = esfera.radius / Math.max(0.001, root.getWorldScale(new THREE.Vector3()).length() / Math.sqrt(3));
    medida.valido = true;
    // A cabeça é sempre do aluno. Entrar/sair do XR não agenda movimentos futuros.
    if (novo && !inSession && !reduzido) viewerBridge.frameTo(medida.centro.toArray(), medida.raio);
    invalidate();
    return () => { viewerBridge.cancelCamera(); invalidate(); };
  }, [foco, rootRef, contentRef, inSession, reduzido, invalidate]);

  useFrame((_, delta) => {
    const medida = medidaRef.current;
    const mesh = anel.current;
    if (!mesh || !foco || !medida.valido) return;
    tempo.current += Math.min(delta, 0.1);
    // Três segundos de respiração lenta; depois repousa (economiza GPU no desktop).
    const pulsando = !reduzido && tempo.current < 3;
    mesh.scale.setScalar(pulsando ? 1 + Math.sin(tempo.current * Math.PI * 1.4) * 0.04 : 1);
    if (pulsando) invalidate();
    mesh.parent?.position.copy(medida.centro);
  });

  if (!foco) return null;
  return <Billboard>
    <mesh ref={anel} raycast={() => null}>
      <ringGeometry args={[0.12, 0.127, 40]} />
      <meshBasicMaterial color="#ffd166" transparent opacity={0.85} depthWrite={false} toneMapped={false} />
    </mesh>
    <Text3D position={[0, 0.19, 0]} size={0.058} maxWidth={1.1} color="#ffd166">
      {`Foco: ${foco.label}`}
    </Text3D>
  </Billboard>;
}
