"use client";

import { useState } from "react";
import Link from "next/link";
import { Check, Save } from "lucide-react";
import { formatDate } from "@/lib/format";
import { downscaleDataUrl } from "@/lib/image";
import { getOrganById } from "@/lib/organs";
import { useVRMedStore } from "@/lib/store";
import { viewerBridge } from "@/lib/viewer-bridge";
import { Button } from "@/components/ui/button";
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
  DialogTrigger,
} from "@/components/ui/dialog";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";

/** Salva a sessão de estudo atual (chat, anotações, cortes e screenshot). */
export function SaveSessionButton() {
  const organId = useVRMedStore((s) => s.currentOrganId);
  const layers = useVRMedStore((s) => s.layers);
  const clipping = useVRMedStore((s) => s.clipping);
  const xray = useVRMedStore((s) => s.xray);
  const saveSession = useVRMedStore((s) => s.saveSession);
  const organ = getOrganById(organId);

  const [open, setOpen] = useState(false);
  const [name, setName] = useState("");
  const [saving, setSaving] = useState(false);
  const [savedName, setSavedName] = useState<string | null>(null);

  if (!organId || !organ) return null;

  const handleOpenChange = (next: boolean) => {
    if (next) {
      setName(`Estudo de ${organ.name} — ${formatDate(Date.now())}`);
      setSavedName(null);
    }
    setOpen(next);
  };

  const handleSave = async () => {
    setSaving(true);
    let screenshot: string | undefined;
    const captured = viewerBridge.capture();
    if (captured) {
      try {
        screenshot = await downscaleDataUrl(captured);
      } catch {
        screenshot = captured;
      }
    }
    const finalName = name.trim() || `Estudo de ${organ.name}`;
    saveSession({
      name: finalName,
      organId,
      organName: organ.name,
      viewer: { layers, clipping, xray },
      screenshot,
    });
    setSaving(false);
    setSavedName(finalName);
  };

  return (
    <Dialog open={open} onOpenChange={handleOpenChange}>
      <DialogTrigger asChild>
        <Button variant="outline" size="sm">
          <Save />
          Salvar sessão
        </Button>
      </DialogTrigger>
      <DialogContent>
        <DialogHeader>
          <DialogTitle>Salvar sessão de estudo</DialogTitle>
          <DialogDescription>
            A sessão guarda a conversa com o tutor, as anotações, os cortes e
            uma imagem do modelo.
          </DialogDescription>
        </DialogHeader>

        {savedName ? (
          <div className="flex flex-col gap-4">
            <div className="flex items-center gap-2 rounded-lg bg-accent px-3 py-2.5 text-sm text-accent-foreground">
              <Check className="size-4 shrink-0" />
              Sessão &ldquo;{savedName}&rdquo; salva.
            </div>
            <DialogFooter>
              <Button variant="ghost" onClick={() => setOpen(false)}>
                Fechar
              </Button>
              <Button asChild>
                <Link href="/history">Ver histórico</Link>
              </Button>
            </DialogFooter>
          </div>
        ) : (
          <>
            <div className="space-y-1.5">
              <Label htmlFor="session-name">Nome da sessão</Label>
              <Input
                id="session-name"
                value={name}
                onChange={(event) => setName(event.target.value)}
              />
            </div>
            <DialogFooter>
              <Button variant="ghost" onClick={() => setOpen(false)}>
                Cancelar
              </Button>
              <Button onClick={handleSave} disabled={saving}>
                {saving ? "Salvando…" : "Salvar sessão"}
              </Button>
            </DialogFooter>
          </>
        )}
      </DialogContent>
    </Dialog>
  );
}
