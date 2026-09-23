"use client";

import { useEffect, useRef, useState } from "react";
import { Eraser, Send, Sparkles, Square, X } from "lucide-react";
import { cancelarConversaTutor, enviarPerguntaTutor, limparConversaTutor, repetirPerguntaTutor, useConversaTutor } from "@/lib/tutor-conversa";
import { useVRMedStore } from "@/lib/store";
import { useMediaQuery } from "@/hooks/use-media-query";
import { Button } from "@/components/ui/button";
import { Sheet, SheetContent, SheetTitle } from "@/components/ui/sheet";
import { Textarea } from "@/components/ui/textarea";
import { Message } from "./Message";
import { useTutor3D } from "@/lib/tutor-3d-store";

const EXAMPLE_QUESTIONS = [
  "O que é a valva mitral e qual a sua função?",
  "Explique a circulação pulmonar passo a passo.",
  "Quais são as camadas da parede do estômago?",
];

/** O DOM e os painéis XR usam a mesma conversa e o mesmo pedido em andamento. */
export function ChatPanelContent({ onClose }: { onClose?: () => void } = {}) {
  const chat = useVRMedStore((s) => s.chat);
  const setChatOpen = useVRMedStore((s) => s.setChatOpen);
  const guia = useTutor3D((s) => s.ativo);
  const contexto = useTutor3D((s) => s.contexto);
  const foco = useTutor3D((s) => s.foco);
  const [input, setInput] = useState("");
  const isStreaming = useConversaTutor((s) => s.ocupado);
  const erro = useConversaTutor((s) => s.erro);
  const scrollRef = useRef<HTMLDivElement>(null);
  const textareaRef = useRef<HTMLTextAreaElement>(null);

  useEffect(() => {
    scrollRef.current?.scrollTo({ top: scrollRef.current.scrollHeight });
  }, [chat]);

  // Fechar apenas o DOM não cancela o pedido que está sendo lido no XR.
  // A saída do visualizador encerra a conversa através de Scene.
  const handleClearChat = limparConversaTutor;
  const retry = repetirPerguntaTutor;
  const sendMessage = async (text: string) => {
    if (!text.trim() || isStreaming) return;
    setInput("");
    if (textareaRef.current) textareaRef.current.style.height = "auto";
    await enviarPerguntaTutor(text);
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
            Respostas curtas, com base nos tratados de anatomia
          </p>
        </div>
        <Button
          variant="ghost"
          size="icon-sm"
          onClick={handleClearChat}
          disabled={chat.length === 0}
          aria-label="Limpar conversa"
          title="Limpar conversa"
        >
          <Eraser />
        </Button>
        <Button
          variant="ghost"
          size="icon-sm"
          onClick={() => onClose ? onClose() : setChatOpen(false)}
          aria-label="Fechar chat"
        >
          <X />
        </Button>
      </div>

      <div className="border-b border-border px-3 py-2 text-xs">
        <label className="flex items-center gap-2">
          <input type="checkbox" checked={guia} onChange={(e) => useTutor3D.getState().habilitar(e.target.checked)} />
          Guiar no modelo 3D
        </label>
        <p className="mt-1 text-muted-foreground">{contexto?.alvos.length === 1 ? "Este modelo permite foco no conjunto, não em partes isoladas." : "Destaque de estruturas disponíveis; câmera livre no VR."}</p>
        <div role="status" className="mt-1 flex items-center justify-between gap-2">
          <span>{foco ? `Foco: ${foco.label}` : !contexto ? "Aguardando modelo 3D." : "Pergunte sobre o modelo para explorar."}</span>
          {foco && <button type="button" className="underline" onClick={() => useTutor3D.getState().limparFoco()}>Limpar foco</button>}
        </div>
      </div>
      <div ref={scrollRef} data-xr-scroll className="min-h-0 flex-1 overflow-y-auto p-3">
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
                Tire dúvidas de anatomia e fisiologia. Respostas curtas, com base
                nos tratados da graduação (Moore, Gray, Netter, Sobotta, Guyton,
                Robbins).
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
        {erro && (
          <p
            role="alert"
            className="mb-2 flex items-center justify-between gap-2 text-xs text-destructive"
          >
            <span>{erro}</span>
            <Button variant="ghost" size="sm" onClick={retry}>
              Tentar novamente
            </Button>
          </p>
        )}
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
            onClick={() => isStreaming ? cancelarConversaTutor() : void sendMessage(input)}
            disabled={!isStreaming && input.trim().length === 0}
            aria-label={isStreaming ? "Parar resposta" : "Enviar mensagem"}
          >
            {isStreaming ? <Square /> : <Send />}
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
