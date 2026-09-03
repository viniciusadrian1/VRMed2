"use client";

import { useState } from "react";
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

/** Botões de avaliação (👍/👎) e formulário de feedback de uma resposta. */
export function FeedbackButtons({ message }: { message: ChatMessage }) {
  const chat = useVRMedStore((s) => s.chat);
  const setChatFeedback = useVRMedStore((s) => s.setChatFeedback);
  const organId = useVRMedStore((s) => s.currentOrganId);

  const [open, setOpen] = useState(false);
  const [tags, setTags] = useState<FeedbackTag[]>([]);
  const [comment, setComment] = useState("");
  const [submitted, setSubmitted] = useState(false);

  const messageIndex = chat.findIndex((item) => item.id === message.id);
  const userPrompt = messageIndex > 0 ? chat[messageIndex - 1].content : "";

  const sendFeedback = (
    rating: "up" | "down",
    selectedTags: FeedbackTag[],
    commentText: string,
  ) => {
    const payload: Omit<FeedbackPayload, "timestamp"> = {
      messageId: message.id,
      userPrompt,
      aiResponse: message.content,
      rating,
      tags: selectedTags,
      comment: commentText,
      currentOrgan: organId ?? "",
    };
    void fetch("/api/feedback", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(payload),
    }).catch(() => {
      /* feedback é best-effort — falhas de rede não afetam o estudo */
    });
    track("chat_response_rated", { rating, organ: organId });
  };

  const handlePositive = () => {
    setChatFeedback(message.id, "up");
    sendFeedback("up", [], "");
  };

  const handleSubmitDetailed = () => {
    setChatFeedback(message.id, "down");
    sendFeedback("down", tags, comment.trim());
    setSubmitted(true);
    setOpen(false);
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
            onClick={() => setOpen(true)}
            aria-label="Resposta com problemas"
          >
            <ThumbsDown />
          </Button>
          <Button variant="ghost" size="sm" onClick={() => setOpen(true)}>
            <MessageSquarePlus />
            Comentar
          </Button>
        </div>
      </PopoverAnchor>
      <PopoverContent align="start" className="w-80">
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
      </PopoverContent>
    </Popover>
  );
}
