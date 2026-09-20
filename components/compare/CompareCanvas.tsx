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
import { ContactShadows, Text, useGLTF } from "@react-three/drei";
import * as THREE from "three";
import { normalizeContent } from "@/lib/model-utils";
import { useMounted } from "@/hooks/use-mounted";
import { Skeleton } from "@/components/ui/skeleton";
import { ErrorBoundary } from "@/components/ErrorBoundary";
import { SafeEnvironment } from "@/components/viewer/SafeEnvironment";
import { ComparePlaceholder } from "./ComparePlaceholder";
import { SyncedCameras, type CameraSyncState } from "./SyncedCameras";

function CompareLoading({ variant }: { variant: "healthy" | "pathological" }) {
  return (
    <group position={[0, 0, 0.1]}>
      <mesh rotation={[0, 0, Math.PI / 4]}>
        <torusGeometry args={[0.12, 0.025, 8, 24]} />
        <meshBasicMaterial color="#c8935a" />
      </mesh>
      <Text
        position={[0, -0.24, 0]}
        font="/fonts/inter-600.woff"
        fontSize={0.085}
        color="#f3eee6"
        anchorX="center"
        anchorY="middle"
      >
        Preparando modelo
      </Text>
      <Text
        position={[0, -0.36, 0]}
        font="/fonts/inter-600.woff"
        fontSize={0.055}
        color="#9aa6b2"
        anchorX="center"
        anchorY="middle"
      >
        {variant === "healthy" ? "Anatomia saudável" : "Anatomia patológica"}
      </Text>
    </group>
  );
}

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
  onResolved,
}: {
  path: string;
  variant: "healthy" | "pathological";
  onResolved?: (kind: "real" | "placeholder") => void;
}) {
  const [state, setState] = useState<"checking" | "real" | "missing">(
    "checking",
  );

  useEffect(() => {
    let cancelled = false;
    // O estado precisa voltar a "checking" quando o path muda, antes do HEAD
    // assíncrono decidir se o GLB real está disponível.
    // eslint-disable-next-line react-hooks/set-state-in-effect -- reset de recurso assíncrono
    setState("checking");
    fetch(path, { method: "HEAD" })
      .then((res) => {
        if (cancelled) return;
        setState(res.ok ? "real" : "missing");
        onResolved?.(res.ok ? "real" : "placeholder");
      })
      .catch(() => {
        if (cancelled) return;
        setState("missing");
        onResolved?.("placeholder");
      });
    return () => {
      cancelled = true;
    };
  }, [path, onResolved]);

  if (state === "real") {
    // Se o download cair depois do HEAD ou o Draco falhar, recai no modelo de
    // demonstração (com o selo honesto) em vez de derrubar a página. O clear
    // tira o erro do cache do useGLTF para a próxima montagem tentar de novo.
    return (
      <ErrorBoundary
        key={path}
        fallback={<ComparePlaceholder variant={variant} />}
        onError={() => {
          useGLTF.clear(path);
          onResolved?.("placeholder");
        }}
      >
        <Suspense fallback={<CompareLoading variant={variant} />}>
          <CompareGLB path={path} />
        </Suspense>
      </ErrorBoundary>
    );
  }
  return <ComparePlaceholder variant={variant} />;
}

interface CompareCanvasProps {
  path: string;
  variant: "healthy" | "pathological";
  synced: boolean;
  syncRef: RefObject<CameraSyncState>;
  onResolved?: (kind: "real" | "placeholder") => void;
}

/** Um dos dois canvas 3D do modo de comparação. */
export function CompareCanvas({
  path,
  variant,
  synced,
  syncRef,
  onResolved,
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
      <CompareModel path={path} variant={variant} onResolved={onResolved} />

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
