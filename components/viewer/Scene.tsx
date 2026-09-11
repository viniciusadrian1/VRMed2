"use client";

import { useEffect, useMemo, useRef, useState } from "react";
import { Canvas, useFrame, useThree } from "@react-three/fiber";
import { ContactShadows, OrbitControls } from "@react-three/drei";
import { XR, XROrigin, createXRStore, useXR } from "@react-three/xr";
import { SairDoVR } from "@/components/xr/SairDoVR";
import * as THREE from "three";
import { track } from "@/lib/analytics";
import { clamp } from "@/lib/format";
import { useVRMedStore } from "@/lib/store";
import { viewerBridge } from "@/lib/viewer-bridge";
import { useMounted } from "@/hooks/use-mounted";
import { Skeleton } from "@/components/ui/skeleton";
import { AnnotationHotspots } from "./AnnotationSystem";
import { ClipPlaneHelpers } from "./ClipPlaneHelpers";
import { OrganModel } from "./OrganModel";
import { SafeEnvironment } from "./SafeEnvironment";
import { StructureHotspots } from "./StructureHotspots";

const DEFAULT_CAMERA: [number, number, number] = [3.2, 2.3, 4.6];
const MIN_DISTANCE = 1.7;
const MAX_DISTANCE = 14;
/** Altura do chão da cena (o modelo é normalizado em ~2 unidades no centro). */
const FLOOR_Y = -1.3;

interface OrbitLike {
  target: THREE.Vector3;
  update: () => void;
}

/** Anima a câmera (reset / enquadramento) e registra as ações na ponte. */
function CameraRig() {
  const camera = useThree((s) => s.camera);
  const controls = useThree((s) => s.controls) as unknown as OrbitLike | null;
  const invalidate = useThree((s) => s.invalidate);
  const goal = useRef<{ pos: THREE.Vector3; look: THREE.Vector3 } | null>(null);

  useEffect(() => {
    if (!controls) return;

    viewerBridge.resetCamera = () => {
      goal.current = {
        pos: new THREE.Vector3(...DEFAULT_CAMERA),
        look: new THREE.Vector3(0, 0, 0),
      };
      invalidate();
    };

    viewerBridge.frameTo = (point) => {
      const look = new THREE.Vector3(...point);
      const direction = new THREE.Vector3()
        .subVectors(camera.position, controls.target)
        .normalize();
      goal.current = { pos: look.clone().addScaledVector(direction, 2.6), look };
      invalidate();
    };

    viewerBridge.zoom = (factor) => {
      const offset = camera.position.clone().sub(controls.target);
      const distance = clamp(
        offset.length() * factor,
        MIN_DISTANCE,
        MAX_DISTANCE,
      );
      camera.position.copy(controls.target).add(offset.setLength(distance));
      controls.update();
      invalidate();
    };
  }, [camera, controls, invalidate]);

  useFrame(() => {
    if (!goal.current || !controls) return;
    camera.position.lerp(goal.current.pos, 0.14);
    controls.target.lerp(goal.current.look, 0.14);
    controls.update();
    invalidate();
    if (camera.position.distanceTo(goal.current.pos) < 0.012) {
      goal.current = null;
    }
  });

  return null;
}

/** Solicita um novo frame quando o estado relevante muda (frameloop "demand"). */
function SceneInvalidator() {
  const invalidate = useThree((s) => s.invalidate);
  const organId = useVRMedStore((s) => s.currentOrganId);
  const layers = useVRMedStore((s) => s.layers);
  const clipping = useVRMedStore((s) => s.clipping);
  const wireframe = useVRMedStore((s) => s.wireframe);
  const transformMode = useVRMedStore((s) => s.transformMode);
  const annotations = useVRMedStore((s) => s.annotationsByOrgan);

  useEffect(() => {
    invalidate();
  }, [
    invalidate,
    organId,
    layers,
    clipping,
    wireframe,
    transformMode,
    annotations,
  ]);

  return null;
}

/**
 * Cenário exclusivo da sessão VR: chão em grade e um anel sob o modelo.
 *
 * Resolve o "tudo preto ao redor" — sem nenhuma referência espacial, o headset
 * mostra um vazio preto e fica impossível saber para onde olhar. A grade também
 * prova que a renderização está funcionando, separando "não renderiza" de
 * "o modelo não carregou". Usa geometria pura (nada de rede, nada de fonte).
 */
function XRStage() {
  return (
    <>
      <hemisphereLight args={["#dfe9f2", "#1b2229", 1.1]} />
      {/* Chão: referência espacial imediata ao entrar em VR. */}
      <gridHelper
        args={[24, 24, "#3d7ab0", "#243542"]}
        position={[0, FLOOR_Y, 0]}
      />
      {/* Anel sob o modelo: mostra onde o órgão está, mesmo de costas. */}
      <mesh position={[0, FLOOR_Y + 0.01, 0]} rotation={[-Math.PI / 2, 0, 0]}>
        <ringGeometry args={[1.05, 1.25, 48]} />
        <meshBasicMaterial color="#5896c8" transparent opacity={0.55} />
      </mesh>
    </>
  );
}

/**
 * Conteúdo da cena. Em VR, remove tudo que é DOM, custoso ou que disputa a
 * câmera do headset:
 *  - OrbitControls e CameraRig escrevem em `camera.position` a cada quadro
 *    (o OrbitControls do drei não tem consciência de XR) e, numa sessão, essa
 *    câmera é a do headset — brigando com o rastreamento da cabeça.
 *  - SafeEnvironment agora é local (RoomEnvironment + PMREM), sem rede; fica
 *    fora da sessão VR pelo custo de PMREM no Quest.
 *  - Html (hotspots) é DOM: invisível em VR e ainda faz raycast por quadro.
 */
function SceneContents() {
  const modo = useXR((state) => state.mode);
  const inSession = modo === "immersive-vr" || modo === "immersive-ar";
  const emAR = modo === "immersive-ar";

  return (
    <>
      {/*
       * Em VR o usuário nasce 3 m atrás do modelo, olhando para ele: a sala é
       * nossa e cabe. Em AR a sala é a de verdade — recuar 3 m colocaria a
       * pessoa dentro da parede do estande. Por isso, em AR, a origem fica
       * onde os pés já estão e é o ÓRGÃO que vem para perto (ver OrganModel).
       */}
      <XROrigin position={emAR ? [0, 0, 0] : [0, FLOOR_Y, 3]}>
        <SairDoVR position={[-0.45, 1.25, -0.5]} />
      </XROrigin>

      {/*
       * Em AR a luz da sala real já ilumina o campo de visão; repetir aqui a
       * chave forte do modo 2D deixa o órgão "estourado" e chapado contra o
       * passthrough. Menos intensidade e mais preenchimento.
       */}
      <ambientLight intensity={emAR ? 1.15 : inSession ? 0.85 : 0.5} />
      <directionalLight
        position={[5, 7, 5]}
        intensity={emAR ? 1.1 : 2.1}
        castShadow={!inSession}
        shadow-mapSize={[2048, 2048]}
        shadow-bias={-0.0002}
      >
        <orthographicCamera
          attach="shadow-camera"
          args={[-4, 4, 4, -4, 0.1, 30]}
        />
      </directionalLight>
      <directionalLight
        position={[-6, 3, -5]}
        intensity={emAR ? 0.8 : 0.55}
        color="#9fc3dd"
      />

      <OrganModel />

      {/*
       * O cenário do VR (grade + anel) existe para a pessoa não ficar num vazio
       * preto. Em AR o vazio não existe: o fundo é a sala. Desenhar a grade
       * ali seria plantar um chão falso por cima do chão de verdade.
       */}
      {inSession ? (
        emAR ? null : <XRStage />
      ) : (
        <>
          <SafeEnvironment />
          <ClipPlaneHelpers />
          <StructureHotspots />
          <AnnotationHotspots />
          <ContactShadows
            position={[0, -1.25, 0]}
            opacity={0.4}
            scale={9}
            blur={2.8}
            far={4}
          />
          <OrbitControls
            makeDefault
            enableDamping
            dampingFactor={0.08}
            minDistance={MIN_DISTANCE}
            maxDistance={MAX_DISTANCE}
          />
          <CameraRig />
        </>
      )}

      <SceneInvalidator />
    </>
  );
}

/** Canvas 3D principal do visualizador, com suporte a WebXR. */
export function Scene() {
  const mounted = useMounted();
  // emulate:false desativa o emulador de headset (e o botão "Enter XR" que ele
  // injeta) — o WebXR real continua funcionando em dispositivos compatíveis.
  const xrStore = useMemo(() => createXRStore({ emulate: false }), []);
  // Numa sessão XR a renderização precisa ser contínua ("always"). O modo
  // "demand" (usado no 2D para economizar GPU) não é suportado pelo WebXR
  // e deixaria o headset com a tela preta.
  const [inXR, setInXR] = useState(false);

  // Registra a entrada em VR/AR na ponte e mede a duração das sessões.
  useEffect(() => {
    viewerBridge.enterVR = () => {
      void xrStore.enterVR();
    };
    viewerBridge.enterAR = () => {
      void xrStore.enterAR();
    };
    let enteredAt = 0;
    // Guardado na entrada: ao sair, `state.mode` já voltou a null e não dá
    // mais para saber de qual dos dois modos a sessão era.
    let modoAtivo: "vr" | "ar" = "vr";
    const unsubscribe = xrStore.subscribe((state) => {
      const active = Boolean(state.session);
      setInXR(active);
      if (active && enteredAt === 0) {
        enteredAt = Date.now();
        modoAtivo = state.mode === "immersive-ar" ? "ar" : "vr";
        track(modoAtivo === "ar" ? "ar_entered" : "vr_entered");
      } else if (!active && enteredAt > 0) {
        track(modoAtivo === "ar" ? "ar_exited" : "vr_exited", {
          durationMs: Date.now() - enteredAt,
        });
        enteredAt = 0;
      }
    });
    return () => {
      unsubscribe();
      viewerBridge.enterVR = () => {};
      viewerBridge.enterAR = () => {};
    };
  }, [xrStore]);

  if (!mounted) {
    return <Skeleton className="size-full rounded-none" />;
  }

  return (
    <Canvas
      // Sombras (PCSS + mapa 2048²) são caras demais para o Quest.
      shadows={inXR ? false : "percentage"}
      dpr={inXR ? 1 : [1, 2]}
      frameloop={inXR ? "always" : "demand"}
      camera={{ position: DEFAULT_CAMERA, fov: 45 }}
      gl={{ antialias: true, alpha: true, preserveDrawingBuffer: true }}
      onCreated={(state) => {
        // Habilita os clipping planes por material (cortes anatômicos).
        state.gl.localClippingEnabled = true;
        // Captura de tela: renderiza um frame fresco e exporta como PNG.
        viewerBridge.capture = () => {
          state.gl.render(state.scene, state.camera);
          return state.gl.domElement.toDataURL("image/png");
        };
      }}
    >
      <XR store={xrStore}>
        <SceneContents />
      </XR>
    </Canvas>
  );
}
