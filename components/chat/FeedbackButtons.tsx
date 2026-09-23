"use client";

import { useContext, useState, type ReactNode } from "react";
import { createPortal } from "react-dom";
import { ContextoPortalDOMXR, useDOMImersivo } from "@/components/viewer/ContextoDOMXR";
import { MessageSquarePlus, ThumbsDown, ThumbsUp } from "lucide-react";
import { track } from "@/lib/analytics";
import { useVRMedStore } from "@/lib/store";
import { Button } from "@/components/ui/button";
import { Checkbox } from "@/components/ui/checkbox";
import {
  Popover,
  PopoverAnchor,
  PopoverContent,
} from "@/components/ui/popover";
import { Textarea } from "@/components/ui/textarea";
import type { ChatMessage, FeedbackPayload, FeedbackTag } from "@/types";

const TAG_OPTIONS: { id: FeedbackTag; label: string }[] = [
  { id: "incorreta", label: "Informação incorreta" },
  { id: "fonte_nao_confiavel", label: "Fonte não confiável" },
  { id: "incompleta", label: "Resposta incompleta" },
  { id: "fora_escopo", label: "Fora do escopo" },
];

function ConteudoAvaliacao({ aberto, children }: { aberto: boolean; children: ReactNode }) {
  const imersivo = useDOMImersivo();
  const portal = useContext(ContextoPortalDOMXR);
  if (!imersivo) return <PopoverContent align="start" className="w-80">{children}</PopoverContent>;
  // Portais fora do painel não entram na textura. Mantém o mesmo formulário dentro da janela.
  const formulario = aberto ? <div data-xr-modal role="dialog" aria-label="Avaliar esta resposta"
    className="absolute inset-x-3 bottom-3 z-50 max-h-[90%] overflow-y-auto rounded-lg border bg-popover p-4 text-popover-foreground shadow-lg" data-xr-scroll>{children}</div> : null;
  // Irmão da conversa: não é recortado ou deslocado pela rolagem das mensagens.
  return portal ? createPortal(formulario, portal) : formulario;
}

/** Botões de avaliação (👍/👎) e formulário de feedback de uma resposta. */
export function FeedbackButtons({ message }: { message: ChatMessage }) {
  const chat = useVRMedStore((s) => s.chat);
  const setChatFeedback = useVRMedStore((s) => s.setChatFeedback);
  const organId = useVRMedStore((s) => s.currentOrganId);

  const [open, setOpen] = useState(false);
  const [tags, setTags] = useState<FeedbackTag[]>([]);
  const [comment, setComment] = useState("");
  const [submitted, setSubmitted] = useState(false);
  const [erro, setErro] = useState(false);
  // Nota que o formulário vai enviar: o 👎 abre como "down", mas o "Comentar"
  // depois de um 👍 não pode transformar o elogio em avaliação negativa.
  const [nota, setNota] = useState<"up" | "down">("down");

  const messageIndex = chat.findIndex((item) => item.id === message.id);
  const userPrompt = messageIndex > 0 ? chat[messageIndex - 1].content : "";

  // Rejeita em qualquer resposta não-ok (429 do limite, 400, 500): antes só a
  // falha de rede era tratada e a avaliação sumia enquanto a UI agradecia.
  const sendFeedback = (
    rating: "up" | "down",
    selectedTags: FeedbackTag[],
    commentText: string,
  ) => {
    const payload: Omit<FeedbackPayload, "timestamp"> = {
      messageId: message.id,
      // Mesmo teto de /api/feedback: o store guarda a pergunta inteira, que o
      // chat-client só corta para o tutor, e acima disso a avaliação dava 400.
      userPrompt: userPrompt.slice(0, 8000),
      aiResponse: message.content,
      rating,
      tags: selectedTags,
      comment: commentText,
      currentOrgan: organId ?? "",
    };
    setErro(false);
    track("chat_response_rated", { rating, organ: organId });
    return fetch("/api/feedback", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(payload),
    }).then((response) => {
      if (!response.ok) throw new Error();
    });
  };

  const handlePositive = () => {
    // Clique repetido no 👍 não vira outro registro nem gasta o limite do IP.
    if (message.feedback === "up") return;
    const anterior = message.feedback ?? null;
    setChatFeedback(message.id, "up");
    sendFeedback("up", [], "").catch(() => {
      setChatFeedback(message.id, anterior);
      setErro(true);
    });
  };

  const handleSubmitDetailed = () => {
    sendFeedback(nota, tags, comment.trim())
      .then(() => {
        setChatFeedback(message.id, nota);
        setSubmitted(true);
        setOpen(false);
      })
      .catch(() => setErro(true));
  };

  const toggleTag = (tag: FeedbackTag) => {
    setTags((previous) =>
      previous.includes(tag)
        ? previous.filter((item) => item !== tag)
        : [...previous, tag],
    );
  };

  if (submitted) {
    return (
      <p className="mt-2 text-xs text-muted-foreground">
        Obrigado pelo feedback — ele ajuda a aprimorar o tutor.
      </p>
    );
  }

  return (
    <Popover open={open} onOpenChange={setOpen}>
      <PopoverAnchor asChild>
        <div className="mt-2 flex flex-wrap items-center gap-1">
          <span className="mr-1 text-xs text-muted-foreground">
            Esta resposta foi útil?
          </span>
          <Button
            variant={message.feedback === "up" ? "default" : "ghost"}
            size="icon-sm"
            onClick={handlePositive}
            aria-label="Resposta útil"
          >
            <ThumbsUp />
          </Button>
          <Button
            variant={message.feedback === "down" ? "default" : "ghost"}
            size="icon-sm"
            onClick={() => {
              setNota("down");
              setOpen(true);
            }}
            aria-label="Resposta com problemas"
          >
            <ThumbsDown />
          </Button>
          <Button
            variant="ghost"
            size="sm"
            onClick={() => {
              setNota(message.feedback ?? "down");
              setOpen(true);
            }}
          >
            <MessageSquarePlus />
            Comentar
          </Button>
          {erro && (
            <p role="alert" className="w-full text-xs text-destructive">
              Não foi possível enviar a avaliação. Tente de novo.
            </p>
          )}
        </div>
      </PopoverAnchor>
      <ConteudoAvaliacao aberto={open}>
        <p className="text-sm font-medium">Avaliar esta resposta</p>
        <p className="mt-0.5 text-xs text-muted-foreground">
          Sua avaliação apoia a validação do tutor por especialistas.
        </p>
        <div className="mt-3 flex flex-col gap-2">
          {TAG_OPTIONS.map((option) => (
            <label
              key={option.id}
              className="flex cursor-pointer items-center gap-2 text-sm"
            >
              <Checkbox
                checked={tags.includes(option.id)}
                onCheckedChange={() => toggleTag(option.id)}
              />
              {option.label}
            </label>
          ))}
        </div>
        <Textarea
          value={comment}
          onChange={(event) => setComment(event.target.value)}
          // Mesmo teto do schema em /api/feedback: acima disso a rota dá 400.
          maxLength={2000}
          placeholder="Comentário (opcional)"
          className="mt-3 min-h-20 text-sm"
        />
        <div className="mt-3 flex justify-end gap-2">
          <Button variant="ghost" size="sm" onClick={() => setOpen(false)}>
            Cancelar
          </Button>
          <Button size="sm" onClick={handleSubmitDetailed}>
            Enviar avaliação
          </Button>
        </div>
      </ConteudoAvaliacao>
    </Popover>
  );
}
