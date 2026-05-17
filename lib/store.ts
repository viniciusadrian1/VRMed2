import { create } from "zustand";
import { persist, createJSONStorage, type StateStorage } from "zustand/middleware";
import { XRAY_OPACITY } from "@/lib/anatomy-labels";
import { genId } from "@/lib/format";
import type {
  Annotation,
  ChatMessage,
  ClipAxis,
  ClippingState,
  ClipPlaneState,
  ConsentState,
  LayerState,
  ModelBounds,
  QuizResult,
  StructurePoint,
  StudySession,
  ViewerSnapshot,
} from "@/types";

/** Modo do gizmo de manipulação direta. */
export type TransformMode = "none" | "translate" | "rotate" | "scale";

const DEFAULT_CLIP_PLANE: ClipPlaneState = {
  enabled: false,
  position: 0,
  flipped: false,
};

function defaultClipping(): ClippingState {
  return {
    axial: { ...DEFAULT_CLIP_PLANE },
    sagital: { ...DEFAULT_CLIP_PLANE },
    coronal: { ...DEFAULT_CLIP_PLANE },
  };
}

/** Storage seguro para SSR: sem janela, vira um armazenamento inerte. */
const ssrSafeStorage: StateStorage = {
  getItem: () => null,
  setItem: () => {},
  removeItem: () => {},
};

interface VRMedState {
  /* --- hidratação (persist) --- */
  hasHydrated: boolean;
  setHasHydrated: (value: boolean) => void;

  /* --- consentimento de telemetria (LGPD) --- */
  analyticsConsent: ConsentState;
  setConsent: (value: ConsentState) => void;

  /* --- órgão em foco --- */
  currentOrganId: string | null;
  setCurrentOrgan: (id: string | null) => void;
  /** Origem do modelo exibido: arquivo .glb real ou demonstração procedural. */
  modelKind: "real" | "placeholder" | null;
  setModelKind: (kind: "real" | "placeholder" | null) => void;
  /** Bounding box do modelo (após normalização) — base dos cortes e helpers. */
  modelBounds: ModelBounds | null;
  setModelBounds: (bounds: ModelBounds | null) => void;
  /** Estrutura identificada pelo último clique ("clique para identificar"). */
  inspectedLabel: string | null;
  setInspectedLabel: (label: string | null) => void;

  /* --- camadas anatômicas (transiente, populado ao carregar o modelo) --- */
  layers: LayerState[];
  preXrayLayers: LayerState[] | null;
  setLayers: (layers: LayerState[]) => void;
  setLayerVisibility: (name: string, visible: boolean) => void;
  setLayerOpacity: (name: string, opacity: number) => void;
  setLayerColor: (name: string, color: string | null) => void;
  isolateLayer: (name: string) => void;
  showAllLayers: () => void;

  /* --- pontos de estrutura (numerados, transiente) --- */
  structures: StructurePoint[];
  setStructures: (structures: StructurePoint[]) => void;
  /** Controla a exibição dos marcadores numerados sobre o modelo. */
  showStructurePoints: boolean;
  toggleStructurePoints: () => void;

  /* --- cortes anatômicos --- */
  clipping: ClippingState;
  /** Marca temporal da última alteração de corte (para o helper visual). */
  clipTouchedAt: number;
  setClipPlane: (axis: ClipAxis, patch: Partial<ClipPlaneState>) => void;
  resetClipping: () => void;

  /* --- modo raio-x --- */
  xray: boolean;
  applyXray: (enabled: boolean) => void;

  /* --- modo aramado (wireframe) --- */
  wireframe: boolean;
  toggleWireframe: () => void;

  /* --- gizmo de manipulação --- */
  transformMode: TransformMode;
  setTransformMode: (mode: TransformMode) => void;

  /* --- anotações por órgão (persistido) --- */
  /** Modo de adição: quando ativo, clicar no modelo cria um hotspot. */
  annotationMode: boolean;
  setAnnotationMode: (on: boolean) => void;
  annotationsByOrgan: Record<string, Annotation[]>;
  addAnnotation: (organId: string, annotation: Annotation) => void;
  updateAnnotation: (
    organId: string,
    id: string,
    patch: Partial<Annotation>,
  ) => void;
  removeAnnotation: (organId: string, id: string) => void;
  setAnnotations: (organId: string, list: Annotation[]) => void;

  /* --- chat (persistido) --- */
  chat: ChatMessage[];
  isChatOpen: boolean;
  setChatOpen: (open: boolean) => void;
  addChatMessage: (message: ChatMessage) => void;
  appendToChatMessage: (id: string, chunk: string) => void;
  setChatFeedback: (id: string, feedback: "up" | "down" | null) => void;
  clearChat: () => void;
  setChat: (messages: ChatMessage[]) => void;

  /* --- sessões de estudo salvas (persistido) --- */
  sessions: StudySession[];
  saveSession: (input: {
    name: string;
    organId: string;
    organName: string;
    viewer?: ViewerSnapshot;
    screenshot?: string;
    quizResult?: QuizResult;
  }) => StudySession;
  renameSession: (id: string, name: string) => void;
  deleteSession: (id: string) => void;
  /** Restaura uma sessão salva (órgão, chat, anotações e cortes). */
  resumeSession: (session: StudySession) => void;

  /* --- resultados de quiz (persistido) --- */
  quizResults: QuizResult[];
  addQuizResult: (result: QuizResult) => void;
}

export const useVRMedStore = create<VRMedState>()(
  persist(
    (set, get) => ({
      hasHydrated: false,
      setHasHydrated: (value) => set({ hasHydrated: value }),

      analyticsConsent: null,
      setConsent: (value) => set({ analyticsConsent: value }),

      currentOrganId: null,
      setCurrentOrgan: (id) =>
        set({
          currentOrganId: id,
          modelKind: null,
          modelBounds: null,
          layers: [],
          preXrayLayers: null,
          structures: [],
          clipping: defaultClipping(),
          xray: false,
          wireframe: false,
          transformMode: "none",
          annotationMode: false,
          inspectedLabel: null,
        }),
      modelKind: null,
      setModelKind: (kind) => set({ modelKind: kind }),
      modelBounds: null,
      setModelBounds: (bounds) => set({ modelBounds: bounds }),
      inspectedLabel: null,
      setInspectedLabel: (label) => set({ inspectedLabel: label }),

      layers: [],
      preXrayLayers: null,
      setLayers: (layers) =>
        set({ layers, preXrayLayers: null, xray: false }),
      setLayerVisibility: (name, visible) =>
        set((s) => ({
          layers: s.layers.map((l) =>
            l.name === name ? { ...l, visible } : l,
          ),
        })),
      setLayerOpacity: (name, opacity) =>
        set((s) => ({
          layers: s.layers.map((l) =>
            l.name === name ? { ...l, opacity } : l,
          ),
        })),
      setLayerColor: (name, color) =>
        set((s) => ({
          layers: s.layers.map((l) =>
            l.name === name ? { ...l, color } : l,
          ),
        })),
      isolateLayer: (name) =>
        set((s) => ({
          layers: s.layers.map((l) => ({ ...l, visible: l.name === name })),
        })),
      showAllLayers: () =>
        set((s) => ({
          layers: s.layers.map((l) => ({ ...l, visible: true })),
        })),

      structures: [],
      setStructures: (structures) => set({ structures }),
      showStructurePoints: true,
      toggleStructurePoints: () =>
        set((s) => ({ showStructurePoints: !s.showStructurePoints })),

      clipping: defaultClipping(),
      clipTouchedAt: 0,
      setClipPlane: (axis, patch) =>
        set((s) => ({
          clipping: {
            ...s.clipping,
            [axis]: { ...s.clipping[axis], ...patch },
          },
          clipTouchedAt: Date.now(),
        })),
      resetClipping: () =>
        set({ clipping: defaultClipping(), clipTouchedAt: Date.now() }),

      xray: false,
      applyXray: (enabled) => {
        const { layers, preXrayLayers } = get();
        if (enabled) {
          // Guarda o estado manual e aplica o preset de opacidades por profundidade.
          set({
            xray: true,
            preXrayLayers: layers.map((l) => ({ ...l })),
            layers: layers.map((l) => ({
              ...l,
              visible: true,
              opacity: XRAY_OPACITY[l.depth],
            })),
          });
        } else {
          // Restaura as configurações manuais anteriores ao raio-x.
          set({
            xray: false,
            layers: preXrayLayers ? preXrayLayers.map((l) => ({ ...l })) : layers,
            preXrayLayers: null,
          });
        }
      },

      wireframe: false,
      toggleWireframe: () => set((s) => ({ wireframe: !s.wireframe })),

      transformMode: "none",
      setTransformMode: (mode) => set({ transformMode: mode }),

      annotationMode: false,
      setAnnotationMode: (on) => set({ annotationMode: on }),
      annotationsByOrgan: {},
      addAnnotation: (organId, annotation) =>
        set((s) => ({
          annotationsByOrgan: {
            ...s.annotationsByOrgan,
            [organId]: [...(s.annotationsByOrgan[organId] ?? []), annotation],
          },
        })),
      updateAnnotation: (organId, id, patch) =>
        set((s) => ({
          annotationsByOrgan: {
            ...s.annotationsByOrgan,
            [organId]: (s.annotationsByOrgan[organId] ?? []).map((a) =>
              a.id === id ? { ...a, ...patch } : a,
            ),
          },
        })),
      removeAnnotation: (organId, id) =>
        set((s) => ({
          annotationsByOrgan: {
            ...s.annotationsByOrgan,
            [organId]: (s.annotationsByOrgan[organId] ?? []).filter(
              (a) => a.id !== id,
            ),
          },
        })),
      setAnnotations: (organId, list) =>
        set((s) => ({
          annotationsByOrgan: { ...s.annotationsByOrgan, [organId]: list },
        })),

      chat: [],
      isChatOpen: false,
      setChatOpen: (open) => set({ isChatOpen: open }),
      addChatMessage: (message) =>
        set((s) => ({ chat: [...s.chat, message] })),
      appendToChatMessage: (id, chunk) =>
        set((s) => ({
          chat: s.chat.map((m) =>
            m.id === id ? { ...m, content: m.content + chunk } : m,
          ),
        })),
      setChatFeedback: (id, feedback) =>
        set((s) => ({
          chat: s.chat.map((m) => (m.id === id ? { ...m, feedback } : m)),
        })),
      clearChat: () => set({ chat: [] }),
      setChat: (messages) => set({ chat: messages }),

      sessions: [],
      saveSession: (input) => {
        const now = Date.now();
        const { chat, annotationsByOrgan } = get();
        const session: StudySession = {
          id: genId(),
          name: input.name,
          organId: input.organId,
          organName: input.organName,
          createdAt: now,
          updatedAt: now,
          chat: chat.map((m) => ({ ...m })),
          annotations: (annotationsByOrgan[input.organId] ?? []).map((a) => ({
            ...a,
          })),
          viewer: input.viewer,
          screenshot: input.screenshot,
          quizResult: input.quizResult,
        };
        set((s) => ({ sessions: [session, ...s.sessions] }));
        return session;
      },
      renameSession: (id, name) =>
        set((s) => ({
          sessions: s.sessions.map((sess) =>
            sess.id === id ? { ...sess, name, updatedAt: Date.now() } : sess,
          ),
        })),
      deleteSession: (id) =>
        set((s) => ({ sessions: s.sessions.filter((sess) => sess.id !== id) })),
      resumeSession: (session) =>
        set((s) => ({
          currentOrganId: session.organId,
          modelKind: null,
          modelBounds: null,
          layers: [],
          preXrayLayers: null,
          structures: [],
          // As camadas são recriadas ao carregar o modelo; os cortes são
          // restaurados do snapshot por não dependerem das malhas.
          clipping: session.viewer?.clipping ?? defaultClipping(),
          xray: false,
          wireframe: false,
          transformMode: "none",
          annotationMode: false,
          chat: session.chat.map((m) => ({ ...m })),
          annotationsByOrgan: {
            ...s.annotationsByOrgan,
            [session.organId]: session.annotations.map((a) => ({ ...a })),
          },
        })),

      quizResults: [],
      addQuizResult: (result) =>
        set((s) => ({ quizResults: [result, ...s.quizResults] })),
    }),
    {
      name: "vrmed-store",
      version: 1,
      storage: createJSONStorage(() =>
        typeof window !== "undefined" ? window.localStorage : ssrSafeStorage,
      ),
      // Apenas dados duráveis são persistidos; o estado vivo do 3D é recriado.
      partialize: (state) => ({
        analyticsConsent: state.analyticsConsent,
        currentOrganId: state.currentOrganId,
        annotationsByOrgan: state.annotationsByOrgan,
        chat: state.chat,
        sessions: state.sessions,
        quizResults: state.quizResults,
      }),
      onRehydrateStorage: () => (state) => state?.setHasHydrated(true),
    },
  ),
);
