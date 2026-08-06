"use client";

import { memo } from "react";
import { Sparkles } from "lucide-react";
import type { ChatMessage } from "@/types";
import { FeedbackButtons } from "./FeedbackButtons";
import { MarkdownContent } from "./MarkdownContent";

/** Indicador de "digitando" exibido enquanto a resposta ainda não chegou. */
function TypingDots() {
  return (
    <div
      className="flex items-center gap-1 py-1"
      role="status"
      aria-label="O tutor está digitando"
    >
      {[0, 1, 2].map((index) => (
        <span
          key={index}
          className="size-1.5 animate-bounce rounded-full bg-muted-foreground"
          style={{ animationDelay: `${index * 0.15}s` }}
        />
      ))}
    </div>
  );
}

interface MessageProps {
  message: ChatMessage;
  /** Verdadeiro quando esta é a mensagem da IA recebendo o streaming. */
  isStreaming?: boolean;
}

/** Renderiza uma mensagem do chat (usuário ou tutor de IA). */
function MessageComponent({ message, isStreaming }: MessageProps) {
  if (message.role === "user") {
    return (
      <div className="flex justify-end">
        <div className="max-w-[85%] whitespace-pre-wrap rounded-2xl rounded-br-md bg-primary px-3.5 py-2 text-sm text-primary-foreground">
          {message.content}
        </div>
      </div>
    );
  }

  return (
    <div className="flex gap-2.5">
      <span className="mt-0.5 grid size-7 shrink-0 place-items-center rounded-lg bg-accent text-accent-foreground">
        <Sparkles className="size-4" />
      </span>
      {/* Região viva: a resposta do tutor é anunciada a leitores de tela. */}
      <div
        className="min-w-0 flex-1"
        aria-live={isStreaming ? "polite" : undefined}
        aria-busy={isStreaming || undefined}
      >
        {message.content ? (
          <MarkdownContent content={message.content} />
        ) : isStreaming ? (
          <TypingDots />
        ) : null}
        {message.content && !isStreaming && <FeedbackButtons message={message} />}
      </div>
    </div>
  );
}

/**
 * Memoizado: durante o streaming, apenas a mensagem que recebe os tokens
 * é re-renderizada — as demais permanecem estáticas (evita custo O(n²)).
 */
export const Message = memo(MessageComponent);
