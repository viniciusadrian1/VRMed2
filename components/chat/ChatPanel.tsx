"use client";

import { useEffect, useRef, useState } from "react";
import { Eraser, Send, Sparkles, X } from "lucide-react";
import { track } from "@/lib/analytics";
import { detectQuestionCategory, streamChatResponse } from "@/lib/chat-client";
import { genId, stableHash } from "@/lib/format";
import { getOrganById } from "@/lib/organs";
import { useVRMedStore } from "@/lib/store";
import { useMediaQuery } from "@/hooks/use-media-query";
import { Button } from "@/components/ui/button";
import { Sheet, SheetContent, SheetTitle } from "@/components/ui/sheet";
import { Textarea } from "@/components/ui/textarea";
import type { ChatMessage } from "@/types";
import { Message } from "./Message";

const EXAMPLE_QUESTIONS = [
  "O que é a valva mitral e qual a sua função?",
  "Explique a circulação pulmonar passo a passo.",
  "Quais são as camadas da parede do estômago?",
];

/** Conteúdo do chat — cabeçalho, histórico e campo de entrada. */
function ChatPanelContent() {
  const chat = useVRMedStore((s) => s.chat);
  const addChatMessage = useVRMedStore((s) => s.addChatMessage);
  const appendToChatMessage = useVRMedStore((s) => s.appendToChatMessage);
  const clearChat = useVRMedStore((s) => s.clearChat);
  const setChatOpen = useVRMedStore((s) => s.setChatOpen);
  const organId = useVRMedStore((s) => s.currentOrganId);
  const organ = getOrganById(organId);

  const [input, setInput] = useState("");
  const [isStreaming, setIsStreaming] = useState(false);
  const scrollRef = useRef<HTMLDivElement>(null);
  const textareaRef = useRef<HTMLTextAreaElement>(null);

  // Mantém a conversa rolada para a mensagem mais recente.
  useEffect(() => {
    scrollRef.current?.scrollTo({ top: scrollRef.current.scrollHeight });
  }, [chat]);

  const sendMessage = async (text: string) => {
    const trimmed = text.trim();
    if (!trimmed || isStreaming) return;

    const userMessage: ChatMessage = {
      id: genId(),
      role: "user",
      content: trimmed,
      createdAt: Date.now(),
      organContext: organ?.name,
    };
    addChatMessage(userMessage);
    setInput("");
    if (textareaRef.current) textareaRef.current.style.height = "auto";

    const history = [...chat, userMessage]
      .filter((message) => message.content.trim().length > 0)
      .map((message) => ({ role: message.role, content: message.content }));

    const assistantId = genId();
    addChatMessage({
      id: assistantId,
      role: "assistant",
      content: "",
      createdAt: Date.now(),
      feedback: null,
    });
    setIsStreaming(true);

    // Telemetria anônima: hash + categoria da pergunta, nunca o texto.
    track("chat_message_sent", {
      organ: organId,
      questionHash: stableHash(trimmed),
      category: detectQuestionCategory(trimmed),
    });

    try {
      await streamChatResponse(
        { messages: history, currentOrgan: organ?.name },
        (chunk) => appendToChatMessage(assistantId, chunk),
      );
    } catch (error) {
      const message =
        error instanceof Error ? error.message : "Erro ao falar com o tutor.";
      appendToChatMessage(
        assistantId,
        `_Não foi possível obter a resposta: ${message}_`,
      );
    } finally {
      setIsStreaming(false);
    }
  };

  return (
    <div className="flex h-full flex-col">
      <div className="flex h-14 shrink-0 items-center gap-2 border-b border-border px-3">
        <span className="grid size-8 place-items-center rounded-lg bg-accent text-accent-foreground">
          <Sparkles className="size-4" />
        </span>
        <div className="flex-1">
          <h2 className="text-sm font-semibold leading-tight">Tutor de IA</h2>
          <p className="text-[11px] text-muted-foreground">
            Respostas com fontes médicas
          </p>
        </div>
        <Button
          variant="ghost"
          size="icon-sm"
          onClick={clearChat}
          disabled={chat.length === 0 || isStreaming}
          aria-label="Limpar conversa"
          title="Limpar conversa"
        >
          <Eraser />
        </Button>
        <Button
          variant="ghost"
          size="icon-sm"
          onClick={() => setChatOpen(false)}
          aria-label="Fechar chat"
        >
          <X />
        </Button>
      </div>

      <div ref={scrollRef} className="min-h-0 flex-1 overflow-y-auto p-3">
        {chat.length === 0 ? (
          <div className="flex h-full flex-col items-center justify-center gap-4 px-2 text-center">
            <span className="grid size-12 place-items-center rounded-xl bg-accent text-accent-foreground">
              <Sparkles className="size-6" />
            </span>
            <div>
              <h3 className="font-serif text-lg font-medium">
                Pergunte ao tutor
              </h3>
              <p className="mt-1 text-sm text-muted-foreground">
                Tire dúvidas de anatomia e fisiologia. As respostas citam apenas
                fontes médicas reconhecidas.
              </p>
            </div>
            <div className="flex w-full flex-col gap-2">
              {EXAMPLE_QUESTIONS.map((question) => (
                <button
                  key={question}
                  type="button"
                  onClick={() => sendMessage(question)}
                  className="rounded-lg border border-border px-3 py-2 text-left text-sm transition-colors hover:bg-muted"
                >
                  {question}
                </button>
              ))}
            </div>
          </div>
        ) : (
          <div className="flex flex-col gap-4">
            {chat.map((message, index) => (
              <Message
                key={message.id}
                message={message}
                isStreaming={
                  isStreaming &&
                  index === chat.length - 1 &&
                  message.role === "assistant"
                }
              />
            ))}
          </div>
        )}
      </div>

      <div className="shrink-0 border-t border-border p-3">
        <div className="flex items-end gap-2">
          <Textarea
            ref={textareaRef}
            value={input}
            rows={1}
            placeholder="Escreva sua dúvida…"
            className="max-h-40 min-h-9 resize-none"
            onChange={(event) => {
              setInput(event.target.value);
              const element = event.target;
              element.style.height = "auto";
              element.style.height = `${Math.min(element.scrollHeight, 160)}px`;
            }}
            onKeyDown={(event) => {
              if (event.key === "Enter" && !event.shiftKey) {
                event.preventDefault();
                void sendMessage(input);
              }
            }}
            disabled={isStreaming}
          />
          <Button
            size="icon"
            onClick={() => void sendMessage(input)}
            disabled={isStreaming || input.trim().length === 0}
            aria-label="Enviar mensagem"
          >
            <Send />
          </Button>
        </div>
        <p className="mt-1.5 text-[11px] text-muted-foreground">
          Ferramenta de estudo — não substitui avaliação clínica profissional.
        </p>
      </div>
    </div>
  );
}

/** Painel do chat tutor — coluna fixa no desktop, drawer inferior no mobile. */
export function ChatPanel() {
  const isChatOpen = useVRMedStore((s) => s.isChatOpen);
  const setChatOpen = useVRMedStore((s) => s.setChatOpen);
  const isDesktop = useMediaQuery("(min-width: 768px)");

  if (isDesktop) {
    if (!isChatOpen) return null;
    return (
      <aside className="hidden w-[400px] shrink-0 border-l border-border bg-card md:block">
        <ChatPanelContent />
      </aside>
    );
  }

  return (
    <Sheet open={isChatOpen} onOpenChange={(value) => !value && setChatOpen(false)}>
      <SheetContent side="bottom" className="h-[86dvh] gap-0 p-0">
        <SheetTitle className="sr-only">Tutor de IA do VRmed</SheetTitle>
        <ChatPanelContent />
      </SheetContent>
    </Sheet>
  );
}
