"use client";

import { create } from "zustand";
import { useVRMedStore } from "@/lib/store";
import { useTutor3D } from "@/lib/tutor-3d-store";
import { detectQuestionCategory, streamChatResponse } from "@/lib/chat-client";
import { getOrganById } from "@/lib/organs";
import { genId, stableHash } from "@/lib/format";
import { track } from "@/lib/analytics";

/** Um pedido compartilhado entre o chat DOM e o chat imersivo. Não é persistido. */
export const useConversaTutor = create<{ ocupado: boolean; erro: string | null }>(() => ({ ocupado: false, erro: null }));
let pedido: AbortController | null = null;
let respostaId: string | null = null;

export function cancelarConversaTutor() {
  const anterior = pedido, id = respostaId;
  pedido = null; respostaId = null;
  anterior?.abort();
  const loja = useVRMedStore.getState();
  if (id && loja.chat.some((m) => m.id === id && !m.content.trim())) {
    loja.setChat(loja.chat.filter((m) => m.id !== id));
  }
  useConversaTutor.setState({ ocupado: false });
  useTutor3D.getState().limparFoco();
}

export function limparConversaTutor() {
  cancelarConversaTutor();
  useVRMedStore.getState().clearChat();
  useConversaTutor.setState({ erro: null });
}

export async function enviarPerguntaTutor(texto: string) {
  const pergunta = texto.trim().slice(0, 8000);
  if (!pergunta || pedido) return;
  const controller = new AbortController(); pedido = controller;
  const loja = useVRMedStore.getState();
  const organId = loja.currentOrganId, organ = getOrganById(organId);
  const guia = useTutor3D.getState();
  const contexto = guia.ativo && guia.contexto?.organId === organId ? guia.contexto : undefined;
  const id = genId(); respostaId = id;
  guia.limparFoco();
  useConversaTutor.setState({ ocupado: true, erro: null });
  loja.addChatMessage({ id: genId(), role: "user", content: pergunta, createdAt: Date.now(), organContext: organ?.name });
  const historico = useVRMedStore.getState().chat.map((m) => ({ role: m.role, content: m.content }));
  loja.addChatMessage({ id, role: "assistant", content: "", createdAt: Date.now(), feedback: null });
  track("chat_message_sent", { organ: organId, questionHash: stableHash(pergunta), category: detectQuestionCategory(pergunta) });
  // A troca de órgão vale mesmo se nenhum dos painéis estiver visível.
  const desinscrever = useVRMedStore.subscribe((s) => {
    if (s.currentOrganId !== organId && pedido === controller) cancelarConversaTutor();
  });
  try {
    await streamChatResponse({ messages: historico, currentOrgan: organ?.name, contexto3d: contexto },
      (parte) => { if (pedido === controller && !controller.signal.aborted) useVRMedStore.getState().appendToChatMessage(id, parte); },
      controller.signal,
      (comando) => { if (pedido === controller && !controller.signal.aborted && contexto) useTutor3D.getState().aplicar(comando, contexto); });
  } catch (falha) {
    if (pedido !== controller || controller.signal.aborted) return;
    useTutor3D.getState().limparFoco();
    const atual = useVRMedStore.getState();
    atual.setChat(atual.chat.filter((m) => m.id !== id));
    useConversaTutor.setState({ erro: falha instanceof Error ? falha.message : "Não foi possível contatar o tutor de IA." });
  } finally {
    desinscrever();
    if (pedido === controller) {
      pedido = null; respostaId = null;
      useConversaTutor.setState({ ocupado: false });
    }
  }
}

export function repetirPerguntaTutor() {
  if (pedido) return;
  const loja = useVRMedStore.getState(), ultima = loja.chat.at(-1);
  if (ultima?.role !== "user") return;
  loja.setChat(loja.chat.slice(0, -1));
  void enviarPerguntaTutor(ultima.content);
}
