/**
 * Tipos centrais do VRmed.
 * Reúne os contratos de dados usados pelo visualizador 3D, chat, quiz,
 * sessões de estudo e instrumentação de pesquisa.
 */

/** Vetor 3D serializável (usado para câmera, posições de anotação etc.). */
export type Vec3 = [number, number, number];

/** Bounding box normalizado de um modelo carregado. */
export interface ModelBounds {
  center: Vec3;
  size: Vec3;
}

/* -------------------------------------------------------------------------- */
/* Catálogo de órgãos                                                          */
/* -------------------------------------------------------------------------- */

export type OrganCategory =
  | "cardiovascular"
  | "respiratorio"
  | "digestorio"
  | "nervoso"
  | "urinario"
  | "musculoesqueletico";

/** Tipo de modelo: órgão individual ou sistema anatômico de corpo inteiro. */
export type ModelKind = "organ" | "system";

/** Estratégia de detecção de camadas anatômicas. */
export type LayerStrategy = "mesh" | "material";

export interface OrganDefinition {
  /** Identificador em slug, ex.: "coracao". */
  id: string;
  /** Nome de exibição, ex.: "Coração". */
  name: string;
  /** "organ" (padrão) ou "system" (modelo de corpo inteiro por sistema). */
  kind?: ModelKind;
  /**
   * Como agrupar as camadas: "mesh" (padrão — uma camada por malha nomeada,
   * ideal para órgãos) ou "material" (uma camada por tecido, ideal para os
   * modelos de sistema cujas malhas não têm nomes anatômicos).
   */
  layerBy?: LayerStrategy;
  /** Sistema anatômico — usado no agrupamento do catálogo de órgãos. */
  category?: OrganCategory;
  /** Caminho do modelo saudável, relativo a /public. */
  modelPath: string;
  /** Caminho do modelo patológico equivalente (se existir). */
  pathologicalPath?: string;
  /** Nome da condição patológica representada. */
  pathologyName?: string;
  /** Frase curta exibida no seletor. */
  blurb: string;
}

/* -------------------------------------------------------------------------- */
/* Camadas anatômicas                                                          */
/* -------------------------------------------------------------------------- */

/** Profundidade anatômica estimada — base para o modo raio-x. */
export type MeshDepth = "external" | "intermediate" | "internal";

export interface LayerState {
  /** Nome original do mesh no arquivo GLB. */
  name: string;
  /** Rótulo traduzido para exibição. */
  label: string;
  visible: boolean;
  /** Opacidade de 0 a 1. */
  opacity: number;
  /** Cor de destaque em hex, ou null para a cor original do material. */
  color: string | null;
  depth: MeshDepth;
}

/* -------------------------------------------------------------------------- */
/* Pontos de estrutura (marcadores numerados)                                  */
/* -------------------------------------------------------------------------- */

/**
 * Ponto numerado e clicável posicionado sobre uma estrutura do modelo.
 * Gerado automaticamente ao carregar o modelo — um marcador por malha
 * relevante — para orientar o estudante sobre onde clicar.
 */
export interface StructurePoint {
  id: string;
  /** Rótulo identificado da estrutura/tecido. */
  label: string;
  /** Centro da estrutura, em coordenadas do mundo. */
  position: Vec3;
}

/* -------------------------------------------------------------------------- */
/* Cortes anatômicos (clipping planes)                                         */
/* -------------------------------------------------------------------------- */

export type ClipAxis = "axial" | "sagital" | "coronal";

export interface ClipPlaneState {
  enabled: boolean;
  /** Posição normalizada de -1 a 1 dentro do bounding box do modelo. */
  position: number;
  /** Inverte o lado do corte. */
  flipped: boolean;
}

export type ClippingState = Record<ClipAxis, ClipPlaneState>;

/* -------------------------------------------------------------------------- */
/* Anotações / hotspots                                                        */
/* -------------------------------------------------------------------------- */

export interface Annotation {
  id: string;
  /** Posição na superfície da malha, em coordenadas do modelo. */
  position: Vec3;
  text: string;
  color: string;
  /** Oculta o texto, mantendo apenas o ponto numerado (usado no quiz). */
  hideLabel: boolean;
}

/* -------------------------------------------------------------------------- */
/* Chat com IA                                                                 */
/* -------------------------------------------------------------------------- */

export type ChatRole = "user" | "assistant";

export interface ChatMessage {
  id: string;
  role: ChatRole;
  content: string;
  createdAt: number;
  /** Órgão em foco no momento da mensagem. */
  organContext?: string;
  /** Avaliação do usuário/especialista para respostas da IA. */
  feedback?: "up" | "down" | null;
}

/* -------------------------------------------------------------------------- */
/* Quiz                                                                        */
/* -------------------------------------------------------------------------- */

/** Modalidade de cronometragem do quiz. */
export type QuizTimingMode = "free" | "timed";

export interface QuizAnswer {
  questionId: string;
  /** Alternativa escolhida (string vazia se o tempo se esgotou). */
  selected: string;
  correct: boolean;
}

export interface QuizQuestion {
  id: string;
  annotationId: string;
  prompt: string;
  correctAnswer: string;
  /** 4 alternativas já embaralhadas (1 correta + 3 distratores). */
  options: string[];
}

export interface QuizResult {
  id: string;
  organId: string;
  organName: string;
  score: number;
  total: number;
  mode: QuizTimingMode;
  durationMs: number;
  createdAt: number;
}

/* -------------------------------------------------------------------------- */
/* Sessão de estudo                                                            */
/* -------------------------------------------------------------------------- */

/** Captura do estado de visualização para retomar/exportar uma sessão. */
export interface ViewerSnapshot {
  layers: LayerState[];
  clipping: ClippingState;
  xray: boolean;
}

export interface StudySession {
  id: string;
  name: string;
  organId: string;
  organName: string;
  createdAt: number;
  updatedAt: number;
  chat: ChatMessage[];
  annotations: Annotation[];
  viewer?: ViewerSnapshot;
  /** Screenshot do modelo em dataURL (PNG). */
  screenshot?: string;
  quizResult?: QuizResult;
}

/* -------------------------------------------------------------------------- */
/* Descrições de órgãos (JSON em /public/descriptions)                          */
/* -------------------------------------------------------------------------- */

export interface OrganDescription {
  name: string;
  shortDescription: string;
  fullDescription: string;
  sources: string[];
}

/* -------------------------------------------------------------------------- */
/* Feedback de respostas                                                       */
/* -------------------------------------------------------------------------- */

export type FeedbackTag =
  | "incorreta"
  | "fonte_nao_confiavel"
  | "incompleta"
  | "fora_escopo";

export interface FeedbackPayload {
  messageId: string;
  userPrompt: string;
  aiResponse: string;
  rating: "up" | "down";
  tags: FeedbackTag[];
  comment: string;
  currentOrgan: string;
  timestamp: string;
}

/* -------------------------------------------------------------------------- */
/* Consentimento e analytics                                                   */
/* -------------------------------------------------------------------------- */

export type ConsentState = "granted" | "denied" | null;

export type AnalyticsEvent =
  | "organ_viewed"
  | "clipping_plane_used"
  | "xray_mode_toggled"
  | "layer_visibility_changed"
  | "annotation_created"
  | "annotation_clicked"
  | "structure_inspected"
  | "audio_narration_played"
  | "quiz_started"
  | "quiz_completed"
  | "chat_message_sent"
  | "chat_response_rated"
  | "compare_mode_used"
  | "vr_entered"
  | "vr_exited"
  | "pdf_exported";

/* -------------------------------------------------------------------------- */
/* Contrato da API de chat                                                     */
/* -------------------------------------------------------------------------- */

export interface ChatApiMessage {
  role: ChatRole;
  content: string;
}

export interface ChatApiRequest {
  messages: ChatApiMessage[];
  currentOrgan?: string;
}
