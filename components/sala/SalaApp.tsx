"use client";

import {
  useCallback,
  useEffect,
  useRef,
  useState,
  type FormEvent,
} from "react";
import Link from "next/link";
import { ArrowLeft, BookOpen, Send, X } from "lucide-react";
import { Canvas } from "@react-three/fiber";
import { XR } from "@react-three/xr";
import { obterXRStore } from "@/lib/xr-store";
import { useMounted } from "@/hooks/use-mounted";
import { ErrorBoundary } from "@/components/ErrorBoundary";
import { Text3D } from "@/components/arena/ui3d";
import { streamChatResponse } from "@/lib/chat-client";
import * as spotify from "@/lib/spotify";
import { CenaSala } from "./SalaScene";

interface Mensagem {
  role: "user" | "assistant";
  content: string;
}

/**
 * Sala de Estudos Individual (Modo 1 do plano multi-modo).
 *
 * Estado 100%% local (regra do projeto: modos novos não tocam a store
 * global). O tutor DOM (gaveta) existe só fora do VR; dentro do headset o
 * livro abre o TutorVR em texto 3D.
 */
export function SalaApp() {
  const mounted = useMounted();
  const [inSession, setInSession] = useState(false);
  const [xrError, setXrError] = useState<string | null>(null);
  const [tutorAberto, setTutorAberto] = useState(false);
  const [mensagens, setMensagens] = useState<Mensagem[]>([]);
  const [pergunta, setPergunta] = useState("");
  const [ocupado, setOcupado] = useState(false);
  const abortRef = useRef<AbortController | null>(null);
  // Spotify (opcional; docs/SALA-SPOTIFY.md). O login é um redirect, então
  // acontece aqui, na tela 2D, nunca dentro da sessão XR.
  const [spotifyEstado, setSpotifyEstado] = useState<"desconectado" | "conectado" | "erro">(
    "desconectado",
  );
  useEffect(() => {
    if (!spotify.spotifyConfigurado()) return;
    const sincronizar = () => setSpotifyEstado(spotify.conectado() ? "conectado" : "desconectado");
    void spotify.concluirLogin().then((resultado) => {
      if (resultado === "erro") setSpotifyEstado("erro");
      else sincronizar();
    });
    window.addEventListener(spotify.EVENTO_SPOTIFY, sincronizar);
    return () => window.removeEventListener(spotify.EVENTO_SPOTIFY, sincronizar);
  }, []);

  const store = obterXRStore();

  useEffect(
    () => store.subscribe((state) => setInSession(Boolean(state.session))),
    [store],
  );
  useEffect(() => () => abortRef.current?.abort(), []);

  const enterVR = useCallback(() => {
    setXrError(null);
    store.enterVR().catch((error: unknown) => {
      setXrError(error instanceof Error ? error.message : String(error));
    });
  }, [store]);

  const enviar = (event: FormEvent) => {
    event.preventDefault();
    const texto = pergunta.trim();
    if (!texto || ocupado) return;
    setPergunta("");
    setOcupado(true);
    const historico: Mensagem[] = [...mensagens, { role: "user", content: texto }];
    setMensagens([...historico, { role: "assistant", content: "" }]);

    abortRef.current = new AbortController();
    // O servidor aceita até 40 mensagens não vazias: uma sessão longa ou
    // uma resposta vazia (recusa do modelo) deixavam o tutor em 400 para
    // sempre.
    streamChatResponse(
      { messages: historico.filter((m) => m.content.trim()).slice(-20) },
      (chunk) => {
        setMensagens((atual) => {
          const copia = [...atual];
          const ultima = copia[copia.length - 1];
          copia[copia.length - 1] = {
            ...ultima,
            content: ultima.content + chunk,
          };
          return copia;
        });
      },
      abortRef.current.signal,
    )
      .catch((error: unknown) => {
        setMensagens((atual) => {
          const copia = [...atual];
          copia[copia.length - 1] = {
            role: "assistant",
            content:
              error instanceof Error ? error.message : "Tutor indisponível.",
          };
          return copia;
        });
      })
      .finally(() => setOcupado(false));
  };

  if (!mounted) return null;

  return (
    <main className="relative h-dvh w-full overflow-hidden bg-[#1a140d]">
      {!inSession && (
        <>
          <Link
            href="/"
            className="absolute left-4 top-4 z-20 flex items-center gap-1.5 rounded-full border border-white/15 bg-black/50 px-4 py-2 text-sm font-medium text-white backdrop-blur hover:bg-black/70"
          >
            <ArrowLeft className="size-4" />
            VRmed
          </Link>

          <div className="pointer-events-none absolute inset-x-0 bottom-6 z-10 flex flex-col items-center gap-3">
            <button
              type="button"
              onClick={enterVR}
              className="pointer-events-auto rounded-full bg-[#c8935a] px-8 py-3 font-semibold text-[#221507] shadow-lg transition-transform hover:scale-105"
            >
              Entrar em VR
            </button>
            {xrError && (
              <p className="pointer-events-auto max-w-md rounded-lg border border-red-400/40 bg-red-950/70 px-4 py-2 text-xs text-red-200">
                Não foi possível iniciar o VR: {xrError}
              </p>
            )}
            {spotify.spotifyConfigurado() && (
              <div className="pointer-events-auto flex flex-col items-center gap-1">
                <button
                  type="button"
                  onClick={() =>
                    spotifyEstado === "conectado"
                      ? spotify.desconectar()
                      : void spotify.iniciarLogin()
                  }
                  className="rounded-full border border-[#1DB954]/60 bg-black/50 px-5 py-2 text-sm font-medium text-[#1DB954] backdrop-blur hover:bg-black/70"
                >
                  {spotifyEstado === "conectado" ? "Desconectar Spotify" : "Conectar Spotify"}
                </button>
                <p className="max-w-md px-4 text-center text-[10px] leading-snug text-white/40">
                  {spotifyEstado === "erro"
                    ? "O login não terminou — tente de novo."
                    : spotifyEstado === "conectado"
                      ? "O rádio da sala controla o que toca no seu celular, computador ou no Spotify do Quest (Premium para controlar)."
                      : "Usa só o estado de reprodução e suas playlists, guardados neste navegador; nada vai para o servidor do VRmed. Conecte antes de entrar em VR."}
                </p>
              </div>
            )}
            <p className="max-w-lg px-4 text-center text-[11px] text-white/45">
              Sala de estudos — clique no rádio, no computador, nos flashcards
              ou no livro. Conteúdo educacional; o tutor de IA responde com base
              nos tratados de anatomia da graduação.
            </p>
          </div>

          {/* Gaveta do tutor (desktop) */}
          {tutorAberto && (
            <aside className="absolute bottom-0 right-0 top-0 z-20 flex w-full max-w-md flex-col border-l border-white/10 bg-[#10151c]/95 backdrop-blur">
              <header className="flex items-center justify-between border-b border-white/10 px-4 py-3">
                <span className="flex items-center gap-2 text-sm font-semibold text-white">
                  <BookOpen className="size-4 text-[#c8935a]" />
                  Tutor de IA
                </span>
                <button
                  type="button"
                  onClick={() => setTutorAberto(false)}
                  className="rounded p-1 text-white/60 hover:text-white"
                  aria-label="Fechar tutor"
                >
                  <X className="size-4" />
                </button>
              </header>
              <div className="flex-1 space-y-3 overflow-y-auto p-4">
                {mensagens.length === 0 && (
                  <p className="text-sm text-white/50">
                    Pergunte qualquer coisa de anatomia, fisiologia ou
                    patologia. Respostas curtas, com base nos tratados da
                    graduação (Moore, Gray, Netter, Sobotta, Guyton, Robbins).
                  </p>
                )}
                {mensagens.map((m, i) => (
                  <div
                    key={i}
                    className={
                      m.role === "user"
                        ? "ml-8 rounded-xl bg-[#c8935a]/20 px-3 py-2 text-sm text-white"
                        : "mr-8 rounded-xl bg-white/5 px-3 py-2 text-sm text-white/90"
                    }
                  >
                    {m.content || "…"}
                  </div>
                ))}
              </div>
              <form onSubmit={enviar} className="flex gap-2 border-t border-white/10 p-3">
                <input
                  value={pergunta}
                  onChange={(event) => setPergunta(event.target.value)}
                  placeholder="Sua dúvida de estudo…"
                  className="flex-1 rounded-lg border border-white/15 bg-black/40 px-3 py-2 text-sm text-white outline-none placeholder:text-white/35 focus:border-[#c8935a]/60"
                />
                <button
                  type="submit"
                  disabled={ocupado}
                  className="rounded-lg bg-[#c8935a] px-3 text-[#221507] disabled:opacity-50"
                  aria-label="Enviar pergunta"
                >
                  <Send className="size-4" />
                </button>
              </form>
            </aside>
          )}
        </>
      )}

      <Canvas
        shadows={false}
        dpr={1}
        frameloop="always"
        // No ponto de vista do VR sentado (olhos ~1,2m sobre o XROrigin):
        // a câmera antiga, 1m atrás e 40cm acima, escondia painéis altos.
        camera={{ position: [0, 1.2, -1.15], fov: 55 }}
        gl={{ antialias: true, alpha: false }}
        onCreated={({ gl }) => gl.setClearColor("#1a140d")}
      >
        <XR store={store}>
          {/* Sem o boundary, qualquer erro na árvore 3D (ex.: carta de IA
              malformada) subia até o error.tsx e derrubava a rota inteira. */}
          <ErrorBoundary
            fallback={
              <Text3D position={[0, 1.3, -1.5]} size={0.08} color="#e06a5c">
                Algo quebrou na sala — recarregue a página
              </Text3D>
            }
          >
            <CenaSala onAbrirTutorDom={() => setTutorAberto(true)} />
          </ErrorBoundary>
        </XR>
      </Canvas>
    </main>
  );
}
