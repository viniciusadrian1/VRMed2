"use client";

import {
  Suspense,
  useEffect,
  useMemo,
  useRef,
  useState,
  type RefObject,
} from "react";
import { Canvas } from "@react-three/fiber";
import { ContactShadows, useGLTF } from "@react-three/drei";
import * as THREE from "three";
import { normalizeContent } from "@/lib/model-utils";
import { useMounted } from "@/hooks/use-mounted";
import { Skeleton } from "@/components/ui/skeleton";
import { SafeEnvironment } from "@/components/viewer/SafeEnvironment";
import { ComparePlaceholder } from "./ComparePlaceholder";
import { SyncedCameras, type CameraSyncState } from "./SyncedCameras";

/** Carrega um modelo .glb e o normaliza para caber na cena. */
function CompareGLB({ path }: { path: string }) {
  const { scene } = useGLTF(path, "/draco/");
  const cloned = useMemo(() => scene.clone(true), [scene]);
  const ref = useRef<THREE.Group>(null);

  useEffect(() => {
    if (ref.current) normalizeContent(ref.current);
  }, [cloned]);

  return (
    <group ref={ref}>
      <primitive object={cloned} />
    </group>
  );
}

/** Decide entre o modelo .glb real e o de demonstração. */
function CompareModel({
  path,
  variant,
}: {
  path: string;
  variant: "healthy" | "pathological";
}) {
  const [state, setState] = useState<"checking" | "real" | "missing">(
    "checking",
  );

  useEffect(() => {
    let cancelled = false;
    setState("checking");
    fetch(path, { method: "HEAD" })
      .then((res) => !cancelled && setState(res.ok ? "real" : "missing"))
      .catch(() => !cancelled && setState("missing"));
    return () => {
      cancelled = true;
    };
  }, [path]);

  if (state === "real") {
    return (
      <Suspense fallback={null}>
        <CompareGLB path={path} />
      </Suspense>
    );
  }
  return <ComparePlaceholder variant={variant} />;
}

interface CompareCanvasProps {
  path: string;
  variant: "healthy" | "pathological";
  synced: boolean;
  syncRef: RefObject<CameraSyncState>;
}

/** Um dos dois canvas 3D do modo de comparação. */
export function CompareCanvas({
  path,
  variant,
  synced,
  syncRef,
}: CompareCanvasProps) {
  const mounted = useMounted();

  if (!mounted) {
    return <Skeleton className="size-full rounded-none" />;
  }

  return (
    <Canvas
      shadows="percentage"
      dpr={[1, 2]}
      frameloop="demand"
      camera={{ position: [3, 2, 4], fov: 45 }}
      gl={{ antialias: true, alpha: true }}
    >
      <ambientLight intensity={0.55} />
      <directionalLight
        position={[5, 7, 5]}
        intensity={2}
        castShadow
        shadow-mapSize={[1024, 1024]}
      />
      <directionalLight position={[-5, 2, -4]} intensity={0.5} color="#9fc3dd" />

      <SafeEnvironment />
      <CompareModel path={path} variant={variant} />

      <ContactShadows
        position={[0, -1.2, 0]}
        opacity={0.38}
        scale={8}
        blur={2.6}
        far={3.5}
      />
      <SyncedCameras syncRef={syncRef} synced={synced} />
    </Canvas>
  );
}
