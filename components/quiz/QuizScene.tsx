"use client";

import { Suspense, useEffect, useMemo, useRef, useState } from "react";
import { Canvas } from "@react-three/fiber";
import { ContactShadows, Html, OrbitControls, useGLTF } from "@react-three/drei";
import * as THREE from "three";
import { normalizeContent } from "@/lib/model-utils";
import { getOrganById } from "@/lib/organs";
import { cn } from "@/lib/utils";
import { useMounted } from "@/hooks/use-mounted";
import { Skeleton } from "@/components/ui/skeleton";
import { PlaceholderOrgan } from "@/components/viewer/PlaceholderOrgan";
import { SafeEnvironment } from "@/components/viewer/SafeEnvironment";
import type { Annotation } from "@/types";

function QuizGLB({ path }: { path: string }) {
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

function QuizModel({ path }: { path: string }) {
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
        <QuizGLB path={path} />
      </Suspense>
    );
  }
  return <PlaceholderOrgan />;
}

interface QuizSceneProps {
  organId: string;
  annotations: Annotation[];
  activeAnnotationId: string | null;
}

/** Canvas 3D do quiz: o modelo com pontos numerados; o ponto da questão atual é destacado. */
export function QuizScene({
  organId,
  annotations,
  activeAnnotationId,
}: QuizSceneProps) {
  const mounted = useMounted();
  const organ = getOrganById(organId);

  if (!mounted || !organ) {
    return <Skeleton className="size-full rounded-none" />;
  }

  return (
    <Canvas
      shadows="percentage"
      dpr={[1, 2]}
      camera={{ position: [3, 2.2, 4.6], fov: 45 }}
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
      <QuizModel path={organ.modelPath} />

      {annotations.map((annotation, index) => {
        const active = annotation.id === activeAnnotationId;
        return (
          <Html
            key={annotation.id}
            position={annotation.position}
            center
            occlude
            zIndexRange={[20, 0]}
          >
            <div
              className={cn(
                "grid place-items-center rounded-full font-bold transition-all",
                active
                  ? "size-9 animate-pulse bg-primary text-sm text-primary-foreground ring-4 ring-primary/30"
                  : "size-5 border border-border bg-card text-[10px] text-muted-foreground",
              )}
            >
              {index + 1}
            </div>
          </Html>
        );
      })}

      <ContactShadows
        position={[0, -1.2, 0]}
        opacity={0.38}
        scale={8}
        blur={2.6}
        far={3.5}
      />
      <OrbitControls
        makeDefault
        enableDamping
        dampingFactor={0.08}
        minDistance={1.8}
        maxDistance={12}
      />
    </Canvas>
  );
}
