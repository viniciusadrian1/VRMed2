"use client";

import { useState } from "react";
import { useRouter } from "next/navigation";
import { Layers, MoreVertical, Pencil, Play, Trash2 } from "lucide-react";
import { formatDateTime } from "@/lib/format";
import { useVRMedStore } from "@/lib/store";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Card } from "@/components/ui/card";
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from "@/components/ui/dialog";
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuTrigger,
} from "@/components/ui/dropdown-menu";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import type { StudySession } from "@/types";
import { PDFExportButton } from "./PDFExportButton";

/** Grade de sessões de estudo salvas, com ações de retomar, renomear e excluir. */
export function SessionList({ sessions }: { sessions: StudySession[] }) {
  const router = useRouter();
  const resumeSession = useVRMedStore((s) => s.resumeSession);
  const renameSession = useVRMedStore((s) => s.renameSession);
  const deleteSession = useVRMedStore((s) => s.deleteSession);

  const [renameTarget, setRenameTarget] = useState<StudySession | null>(null);
  const [renameValue, setRenameValue] = useState("");
  const [deleteTarget, setDeleteTarget] = useState<StudySession | null>(null);
  const [resumeTarget, setResumeTarget] = useState<StudySession | null>(null);

  const doResume = (session: StudySession) => {
    resumeSession(session);
    router.push("/viewer");
  };

  // Retomar substitui a conversa (global) e as anotações do órgão pelas do
  // snapshot, e o store persistido é sobrescrito. Só pede confirmação quando
  // algo atual não está na sessão — senão nada se perde. As anotações são
  // comparadas pelo conteúdo, não só pelo id: updateAnnotation mantém o id ao
  // editar texto, cor ou hideLabel, e essa edição também se perderia. A ordem
  // das chaves bate porque o snapshot e o patch usam spread do mesmo objeto.
  const handleResume = (session: StudySession) => {
    const { chat, annotationsByOrgan } = useVRMedStore.getState();
    const snapChat = new Set(session.chat.map((m) => m.id));
    const snapAnn = new Map(
      session.annotations.map((a) => [a.id, JSON.stringify(a)]),
    );
    const perde =
      chat.some((m) => !snapChat.has(m.id)) ||
      (annotationsByOrgan[session.organId] ?? []).some(
        (a) => snapAnn.get(a.id) !== JSON.stringify(a),
      );
    if (perde) setResumeTarget(session);
    else doResume(session);
  };

  const confirmRename = () => {
    if (renameTarget && renameValue.trim()) {
      renameSession(renameTarget.id, renameValue.trim());
    }
    setRenameTarget(null);
  };

  return (
    <>
      <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-3">
        {sessions.map((session) => (
          <Card key={session.id} className="flex flex-col overflow-hidden">
            <div className="aspect-video bg-muted">
              {session.screenshot ? (
                // eslint-disable-next-line @next/next/no-img-element
                <img
                  src={session.screenshot}
                  alt={`Pré-visualização de ${session.name}`}
                  className="size-full object-cover"
                />
              ) : (
                <div className="grid size-full place-items-center text-muted-foreground">
                  <Layers className="size-7" />
                </div>
              )}
            </div>
            <div className="flex flex-1 flex-col gap-2 p-4">
              <div className="flex items-start justify-between gap-2">
                <h3 className="line-clamp-2 font-medium leading-tight">
                  {session.name}
                </h3>
                <DropdownMenu>
                  <DropdownMenuTrigger asChild>
                    <Button
                      variant="ghost"
                      size="icon-sm"
                      aria-label="Mais ações"
                    >
                      <MoreVertical />
                    </Button>
                  </DropdownMenuTrigger>
                  <DropdownMenuContent align="end">
                    <DropdownMenuItem
                      onClick={() => {
                        setRenameValue(session.name);
                        setRenameTarget(session);
                      }}
                    >
                      <Pencil />
                      Renomear
                    </DropdownMenuItem>
                    <DropdownMenuItem onClick={() => setDeleteTarget(session)}>
                      <Trash2 />
                      Excluir
                    </DropdownMenuItem>
                  </DropdownMenuContent>
                </DropdownMenu>
              </div>

              <div className="flex flex-wrap items-center gap-1.5 text-xs text-muted-foreground">
                <Badge variant="secondary">{session.organName}</Badge>
                <span>{formatDateTime(session.createdAt)}</span>
              </div>

              <p className="text-xs text-muted-foreground">
                {session.chat.length} mensagens · {session.annotations.length}{" "}
                anotações
                {session.quizResult
                  ? ` · quiz ${session.quizResult.score}/${session.quizResult.total}`
                  : ""}
              </p>

              <div className="mt-auto flex gap-2 pt-2">
                <Button
                  size="sm"
                  className="flex-1"
                  onClick={() => handleResume(session)}
                >
                  <Play />
                  Retomar
                </Button>
                <PDFExportButton session={session} />
              </div>
            </div>
          </Card>
        ))}
      </div>

      {/* Diálogo de renomear */}
      <Dialog
        open={renameTarget !== null}
        onOpenChange={(open) => !open && setRenameTarget(null)}
      >
        <DialogContent>
          <DialogHeader>
            <DialogTitle>Renomear sessão</DialogTitle>
          </DialogHeader>
          <div className="space-y-1.5">
            <Label htmlFor="rename-input">Nome da sessão</Label>
            <Input
              id="rename-input"
              value={renameValue}
              onChange={(event) => setRenameValue(event.target.value)}
              autoFocus
            />
          </div>
          <DialogFooter>
            <Button variant="ghost" onClick={() => setRenameTarget(null)}>
              Cancelar
            </Button>
            <Button onClick={confirmRename}>Salvar</Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>

      {/* Diálogo de exclusão */}
      <Dialog
        open={deleteTarget !== null}
        onOpenChange={(open) => !open && setDeleteTarget(null)}
      >
        <DialogContent>
          <DialogHeader>
            <DialogTitle>Excluir sessão?</DialogTitle>
            <DialogDescription>
              A sessão &ldquo;{deleteTarget?.name}&rdquo; será removida
              permanentemente. Esta ação não pode ser desfeita.
            </DialogDescription>
          </DialogHeader>
          <DialogFooter>
            <Button variant="ghost" onClick={() => setDeleteTarget(null)}>
              Cancelar
            </Button>
            <Button
              variant="destructive"
              onClick={() => {
                if (deleteTarget) deleteSession(deleteTarget.id);
                setDeleteTarget(null);
              }}
            >
              Excluir
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>

      {/* Diálogo de retomar (quando há conversa ou anotações que se perderiam) */}
      <Dialog
        open={resumeTarget !== null}
        onOpenChange={(open) => !open && setResumeTarget(null)}
      >
        <DialogContent>
          <DialogHeader>
            <DialogTitle>Retomar sessão?</DialogTitle>
            <DialogDescription>
              Retomar substitui a conversa atual com o tutor e as anotações
              atuais de {resumeTarget?.organName}. Salve a sessão atual antes
              se quiser mantê-las.
            </DialogDescription>
          </DialogHeader>
          <DialogFooter>
            <Button variant="ghost" onClick={() => setResumeTarget(null)}>
              Cancelar
            </Button>
            <Button
              onClick={() => {
                if (resumeTarget) doResume(resumeTarget);
                setResumeTarget(null);
              }}
            >
              Retomar
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>
    </>
  );
}
