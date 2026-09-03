"use client";

import { useEffect, useMemo, useRef, useState, type ReactNode } from "react";
import { useFrame, type ThreeEvent } from "@react-three/fiber";
import { useGLTF } from "@react-three/drei";
import { useXR } from "@react-three/xr";
import * as THREE from "three";
import { Text3D, Panel, Button3D, ARENA_COLORS } from "@/components/arena/ui3d";
import { proximaEstacao, pararRadio } from "@/lib/lofi";
import * as spotify from "@/lib/spotify";
import { streamChatResponse } from "@/lib/chat-client";

/**
 * Os quatro itens interativos da mesa: rádio, computador (hub), flashcards e
 * livro (tutor de IA). Interação por clique/gatilho — funciona igual com
 * mouse (desktop) e laser (VR), seguindo o padrão da Arena.
 */

/** Qual pop-up está aberto — só um por vez (abrir outro fecha o anterior). */
type PainelAberto = "hub" | "flashcards" | "tutor" | null;
interface PropsPainel {
  aberto: boolean;
  onAbrir: () => void;
  onFechar: () => void;
}

/** "×" no canto do painel: segundo jeito de fechar, além de clicar no item. */
function BotaoFechar({ position, onClick }: { position: [number, number, number]; onClick: () => void }) {
  return <Button3D label="×" width={0.11} height={0.1} position={position} color="#5c6b7a" onClick={onClick} />;
}

/** Wrapper de item clicável: cresce um pouco sob o ponteiro + rótulo. */
function Interativo({
  rotulo,
  posRotulo = [0, 0.28, 0],
  onClick,
  children,
}: {
  rotulo: string;
  posRotulo?: [number, number, number];
  onClick: () => void;
  children: ReactNode;
}) {
  const group = useRef<THREE.Group>(null);
  const hovered = useRef(false);
  const [mostrarRotulo, setMostrarRotulo] = useState(false);
  const escala = useRef(1);

  useFrame((_, delta) => {
    if (!group.current) return;
    const alvo = hovered.current ? 1.06 : 1;
    escala.current += (alvo - escala.current) * Math.min(1, delta * 12);
    group.current.scale.setScalar(escala.current);
  });

  return (
    <group
      ref={group}
      onClick={(event: ThreeEvent<MouseEvent>) => {
        event.stopPropagation();
        onClick();
      }}
      onPointerOver={(event) => {
        event.stopPropagation();
        hovered.current = true;
        setMostrarRotulo(true);
      }}
      onPointerOut={() => {
        hovered.current = false;
        setMostrarRotulo(false);
      }}
    >
      {children}
      {mostrarRotulo && (
        <Text3D position={posRotulo} size={0.045} color={ARENA_COLORS.muted}>
          {rotulo}
        </Text3D>
      )}
    </group>
  );
}

/* ------------------------------------------------------------------ RÁDIO */

// "Philips Radio" por Lassi Kaukonen (Sketchfab, CC-BY-4.0). Simplificado de
// 228k para 18k tris (regra "nunca simplificar" vale para ANATOMIA; prop
// decorativo pode) + texturas 1024/webp: 29MB -> 321KB.
const RADIO_GLB = "/models/props/radio.glb";

function Radio() {
  const [nome, setNome] = useState<string>("");
  // Spotify como controle remoto (docs/SALA-SPOTIFY.md): conectado = o rádio
  // mostra e controla o que toca no dispositivo do usuário; o lo-fi desliga
  // (Policy III.7 do Spotify: nada de mixar com outro áudio).
  const [viaSpotify, setViaSpotify] = useState(false);
  const [reproducao, setReproducao] = useState<spotify.Reproducao | null>(null);
  const [aviso, setAviso] = useState<string>("");
  const gltf = useGLTF(RADIO_GLB, "/draco/");
  const scene = useMemo(() => gltf.scene.clone(true), [gltf.scene]);

  // Desligar ao sair da página (o áudio não pode vazar para outras rotas).
  useEffect(() => () => pararRadio(), []);

  // Conectado? (o login acontece no DOM, antes de entrar em VR; o evento
  // cobre conectar/desconectar sem recarregar a cena)
  useEffect(() => {
    const sincronizar = () => {
      const ativo = spotify.conectado();
      setViaSpotify(ativo);
      if (ativo) {
        pararRadio();
        setNome("");
      } else {
        setReproducao(null);
      }
    };
    sincronizar();
    window.addEventListener(spotify.EVENTO_SPOTIFY, sincronizar);
    return () => window.removeEventListener(spotify.EVENTO_SPOTIFY, sincronizar);
  }, []);

  // Sonda o estado a cada 5 s (a janela de rate limit do Spotify é de 30 s;
  // 6 chamadas por janela é conservador).
  useEffect(() => {
    if (!viaSpotify) return;
    let cancelado = false;
    const ler = () =>
      spotify
        .estadoReproducao()
        .then((estado) => {
          if (!cancelado) setReproducao(estado);
        })
        .catch((erro: unknown) => {
          if (!cancelado && erro instanceof spotify.ErroSpotify) setAviso(erro.message);
        });
    void ler();
    const timer = setInterval(ler, 5000);
    return () => {
      cancelado = true;
      clearInterval(timer);
    };
  }, [viaSpotify]);

  // Avisos somem sozinhos
  useEffect(() => {
    if (!aviso) return;
    const timer = setTimeout(() => setAviso(""), 5000);
    return () => clearTimeout(timer);
  }, [aviso]);

  const comando = (acao: () => Promise<void>) => {
    acao()
      .then(() => spotify.estadoReproducao())
      .then((estado) => setReproducao(estado))
      .catch((erro: unknown) => {
        setAviso(erro instanceof spotify.ErroSpotify ? erro.message : "Spotify não respondeu");
      });
  };

  const rotulo = aviso
    ? aviso
    : viaSpotify
      ? reproducao
        ? `${reproducao.tocando ? "Tocando:" : "Pausado:"} ${reproducao.faixa} — ${reproducao.artista}`
        : "Spotify conectado — dê play no celular ou no Quest"
      : nome
        ? `Tocando: ${nome}`
        : "Rádio lo-fi — clique para ligar";

  return (
    <group position={[0.68, 0.765, -2.1]}>
      {viaSpotify && (
        <group position={[0, 0.46, 0.05]}>
          {/* Atribuição exigida pelo Spotify (Design Guidelines); o logo
              oficial como textura é pendência em docs/SALA-SPOTIFY.md */}
          <Text3D position={[0, 0.1, 0]} size={0.03} color="#1DB954">
            Spotify
          </Text3D>
          <Button3D
            label="<<"
            width={0.13}
            height={0.06}
            position={[-0.17, 0, 0]}
            onClick={() => comando(spotify.faixaAnterior)}
          />
          <Button3D
            label={reproducao?.tocando ? "II" : ">"}
            width={0.13}
            height={0.06}
            position={[0, 0, 0]}
            onClick={() => comando(() => spotify.alternar(Boolean(reproducao?.tocando)))}
          />
          <Button3D
            label=">>"
            width={0.13}
            height={0.06}
            position={[0.17, 0, 0]}
            onClick={() => comando(spotify.proximaFaixa)}
          />
        </group>
      )}
      <Interativo
        rotulo={rotulo}
        posRotulo={[0, 0.3, 0.05]}
        onClick={() => {
          if (viaSpotify) {
            comando(() => spotify.alternar(Boolean(reproducao?.tocando)));
            return;
          }
          void proximaEstacao().then((estado) =>
            setNome(estado.tocando ? estado.nome : ""),
          );
        }}
      >
        {/* Rádio Philips vintage (~40cm): arquivo com base em y=0.158 e
            centro deslocado — offsets internos assentam e centram. */}
        <group scale={0.0493}>
          <group position={[0.156, -0.158, -0.3635]}>
            <primitive object={scene} />
          </group>
        </group>
        {/* Luz de "ligado" flutuando discreta sobre o rádio */}
        {(nome || reproducao?.tocando) && (
          <mesh position={[0, 0.26, 0]}>
            <sphereGeometry args={[0.008, 8, 6]} />
            <meshBasicMaterial color="#7CFC9B" toneMapped={false} />
          </mesh>
        )}
      </Interativo>
    </group>
  );
}
useGLTF.preload(RADIO_GLB, "/draco/");

/* ------------------------------------------------------- COMPUTADOR (HUB) */

// "Office Monitor / Workstation Monitor" por DatSketch (Sketchfab), CC-BY-4.0
// — atribuição em public/models/props/CREDITS.md. Substituiu o monitor
// procedural a pedido do grupo.
const MONITOR_GLB = "/models/props/monitor.glb";
// "Book - Encyclopedia" por Maxence Rouillet (Sketchfab, CC-BY-4.0).
const LIVRO_GLB = "/models/props/livro.glb";

/** Monitor GLB medido e fixado à mão: tela (815×418 un.) vira para +Z,
 *  base no y=0 do grupo. Escala 0.00076 → ~0,42m de altura na mesa. */
function MonitorGLB() {
  const gltf = useGLTF(MONITOR_GLB, "/draco/");
  const scene = useMemo(() => gltf.scene.clone(true), [gltf.scene]);
  return (
    <group rotation={[0, -Math.PI / 2, 0]} scale={0.00076}>
      <group position={[-24.7, 50.7, 25.1]}>
        <primitive object={scene} />
      </group>
    </group>
  );
}
useGLTF.preload(MONITOR_GLB, "/draco/");

// Modos do hub da Sala. Segue a ordem do NAV_ITEMS de
// components/layout/Sidebar.tsx, mas não é cópia literal: aqui o rótulo é
// "Estudo 3D" (lá "Visualizador") e há "Arena VR" (ausente na Sidebar).
// Manter em sincronia com as rotas de app/ ao adicionar/remover um modo.
const MODOS_HUB = [
  { rotulo: "Estudo 3D", href: "/viewer" },
  { rotulo: "Comparar", href: "/compare" },
  { rotulo: "Quiz", href: "/quiz" },
  { rotulo: "Clínica", href: "/clinica" },
  { rotulo: "Arena VR", href: "/arena" },
  { rotulo: "Duelo 1×1", href: "/duelo" },
];

function Computador({ aberto, onAbrir, onFechar }: PropsPainel) {
  const inSession = useXR((state) => Boolean(state.session));

  return (
    <group position={[0, 0.765, -2.08]}>
      <Interativo
        rotulo={aberto ? "Fechar hub" : "Computador — hub do VRmed"}
        posRotulo={[0, 0.5, 0.08]}
        onClick={() => (aberto ? onFechar() : onAbrir())}
      >
        <MonitorGLB />
        {/* Tela ligada por cima do vidro preto do GLB (a tela fica em z≈0.058) */}
        <mesh position={[0, 0.253, 0.062]}>
          <planeGeometry args={[0.58, 0.29]} />
          <meshStandardMaterial
            color="#122336"
            emissive="#16324a"
            emissiveIntensity={0.9}
          />
        </mesh>
        <Text3D position={[0, 0.3, 0.066]} size={0.05} color="#7fb2d9">
          VRmed
        </Text3D>
        <Text3D position={[0, 0.21, 0.066]} size={0.024} color={ARENA_COLORS.muted}>
          {aberto ? "escolha um modo ↓" : "clique para abrir o hub"}
        </Text3D>
        {/* "Wifi" — três arcos, indicando conexão */}
        {[0.012, 0.022, 0.032].map((r, i) => (
          <mesh key={r} position={[0.24, 0.155, 0.066]}>
            <ringGeometry args={[r, r + 0.004, 16, 1, Math.PI * 0.25, Math.PI * 0.5]} />
            <meshBasicMaterial color="#4fae89" toneMapped={false} transparent opacity={0.9 - i * 0.2} />
          </mesh>
        ))}
      </Interativo>

      {/* Painel-hub flutuante acima do monitor, a ~1 m dos olhos (origem no
          assento em z −1,15; com o painel a 0,3 m do monitor ele ficava colado
          no rosto). */}
      {aberto && (
        <group position={[0, 0.62, -0.35]} scale={0.8}>
          <Panel width={1.15} height={0.78}>
            <Text3D position={[0, 0.28, 0.01]} size={0.06}>
              Modos do VRmed
            </Text3D>
            <BotaoFechar position={[0.5, 0.31, 0.01]} onClick={onFechar} />
            {/* Duas colunas para os 6 modos caberem no painel (0.78 de altura):
                colunas em x ±0.28, linhas a cada 0.16 em y. */}
            {MODOS_HUB.map((modo, i) => (
              <Button3D
                key={modo.href}
                label={modo.rotulo}
                width={0.52}
                height={0.13}
                position={[i % 2 === 0 ? -0.28 : 0.28, 0.12 - Math.floor(i / 2) * 0.16, 0.01]}
                onClick={() => {
                  // Navegar derruba a sessão VR (comportamento do navegador);
                  // no headset o aviso abaixo explica isso antes do clique.
                  window.location.href = modo.href;
                }}
              />
            ))}
          </Panel>
          {inSession && (
            <Text3D position={[0, -0.5, 0]} size={0.03} color={ARENA_COLORS.muted}>
              Navegar encerra a sessão VR — recoloque o headset na nova página
            </Text3D>
          )}
        </group>
      )}
    </group>
  );
}

/* ----------------------------------------------------------- FLASHCARDS */

interface Carta {
  pergunta: string;
  resposta: string;
  /** true quando veio do /api/chat, não da base curada */
  ia?: true;
}
interface Tema {
  id: string;
  nome: string;
  cartas: Carta[];
}

function embaralhar<T>(lista: T[]): T[] {
  const r = [...lista];
  for (let i = r.length - 1; i > 0; i -= 1) {
    const j = Math.floor(Math.random() * (i + 1));
    [r[i], r[j]] = [r[j], r[i]];
  }
  return r;
}

/** Pede ao tutor (mesmo /api/chat, com as fontes controladas) cartas novas. */
async function gerarCartasIA(tema: Tema): Promise<Carta[]> {
  let texto = "";
  await streamChatResponse(
    {
      messages: [
        {
          role: "user",
          content:
            `Gere exatamente 4 flashcards de anatomia sobre "${tema.nome}", nível estudante de medicina. ` +
            `Responda APENAS um array JSON válido, sem markdown: ` +
            `[{"pergunta":"...","resposta":"..."}] — respostas de no máximo 2 frases, baseadas em livros-texto reconhecidos.`,
        },
      ],
    },
    (chunk) => {
      texto += chunk;
    },
  );
  const inicio = texto.indexOf("[");
  const fim = texto.lastIndexOf("]");
  if (inicio === -1 || fim === -1) throw new Error("resposta sem JSON");
  const cartas = JSON.parse(texto.slice(inicio, fim + 1)) as Carta[];
  // Só strings entram: um campo objeto ("resposta": {…}) renderizado como
  // filho de <Text> derruba o React — e a rota inteira junto.
  return cartas
    .filter(
      (c) => typeof c.pergunta === "string" && typeof c.resposta === "string",
    )
    // Teto de tamanho: a carta (0.95×0.6, maxWidth 0.8) comporta ~7 linhas de
    // ~35 chars; texto maior invade o rodapé.
    .filter((c) => c.pergunta.length <= 140 && c.resposta.length <= 220)
    .slice(0, 6)
    .map((c) => ({ pergunta: c.pergunta, resposta: c.resposta, ia: true as const }));
}

function Flashcards({ aberto: painel, onAbrir, onFechar }: PropsPainel) {
  const [temas, setTemas] = useState<Tema[]>([]);
  const [tema, setTema] = useState<Tema | null>(null);
  const [fila, setFila] = useState<Carta[]>([]);
  const [indice, setIndice] = useState(0);
  const [virada, setVirada] = useState(false);
  const [statusIA, setStatusIA] = useState<string | null>(null);
  // Id do tema vigente, lido na RESOLUÇÃO da geração por IA: se o usuário
  // trocou de tema durante o streaming, as cartas antigas são descartadas
  // (senão cartas de Coração caíam no baralho de Nervoso).
  const temaVigente = useRef<string | null>(null);
  const pop = useRef(1);
  const carta = useRef<THREE.Group>(null);

  useEffect(() => {
    fetch("/flashcards/base.json")
      .then((res) => res.json())
      .then((data: { temas: Tema[] }) => setTemas(data.temas))
      .catch(() => setTemas([]));
  }, []);

  // "Virada" da carta: os painéis usam depthTest desligado (UI sempre à
  // frente), então uma rotação física de duas faces não funciona — o verso
  // sempre desenharia por cima. Em vez disso, o conteúdo troca e a carta dá
  // um "pop" horizontal, que lê como virada.
  useFrame((_, delta) => {
    if (!carta.current) return;
    pop.current = Math.min(1, pop.current + delta * 6);
    carta.current.scale.x = 0.05 + 0.95 * pop.current;
  });

  const escolherTema = (t: Tema) => {
    temaVigente.current = t.id;
    setTema(t);
    setFila(embaralhar(t.cartas));
    setIndice(0);
    setVirada(false);
    setStatusIA(null);
  };

  const atual = fila[indice % Math.max(fila.length, 1)];

  return (
    <group>
      {/* Baralho sobre a mesa */}
      <group position={[-0.56, 0.769, -1.6]}>
        <Interativo
          rotulo="Flashcards — clique para estudar"
          posRotulo={[0, 0.16, 0]}
          onClick={() => (painel ? onFechar() : onAbrir())}
        >
          {[0, 1, 2].map((i) => (
            <mesh key={i} position={[i * 0.004, i * 0.008, -i * 0.003]} rotation={[0, i * 0.08, 0]}>
              <boxGeometry args={[0.14, 0.008, 0.09]} />
              <meshStandardMaterial color={i === 2 ? "#f3f0e8" : "#ded9cc"} roughness={0.8} />
            </mesh>
          ))}
          <mesh position={[0.01, 0.026, 0]} rotation={[-Math.PI / 2, 0, 0.16]}>
            <planeGeometry args={[0.12, 0.07]} />
            <meshStandardMaterial color="#5896c8" roughness={0.7} />
          </mesh>
        </Interativo>
      </group>

      {/* Painel de temas: à esquerda, sobre a mesa, ~1,1 m dos olhos e virado
          para quem está sentado no assento (z −1,15). */}
      {painel && !tema && (
        <group position={[-0.8, 1.35, -2.0]} rotation={[0, 0.55, 0]}>
          <Panel width={1.0} height={1.15}>
            <Text3D position={[0, 0.47, 0.01]} size={0.055}>
              Escolha o tema
            </Text3D>
            <BotaoFechar position={[0.43, 0.5, 0.01]} onClick={onFechar} />
            {temas.map((t, i) => (
              <Button3D
                key={t.id}
                label={t.nome}
                width={0.8}
                height={0.12}
                position={[0, 0.3 - i * 0.15, 0.01]}
                onClick={() => escolherTema(t)}
              />
            ))}
          </Panel>
        </group>
      )}

      {/* Carta flutuante (mesmo lugar do painel de temas) */}
      {painel && tema && atual && (
        <group position={[-0.8, 1.35, -2.0]} rotation={[0, 0.55, 0]}>
          <BotaoFechar position={[0.42, 0.36, 0.02]} onClick={onFechar} />
          <group
            ref={carta}
            onClick={(event) => {
              event.stopPropagation();
              pop.current = 0;
              setVirada((v) => !v);
            }}
          >
            {/* Plano invisível MAS raycastável: Panel e Text3D desligam o
                raycast (são pano de fundo), então sem isto a carta não
                receberia clique nenhum. */}
            <mesh position={[0, 0, 0.006]}>
              <planeGeometry args={[0.95, 0.6]} />
              <meshBasicMaterial transparent opacity={0} depthWrite={false} />
            </mesh>
            <Panel width={0.95} height={0.6} color={virada ? "#16281e" : "#13202e"}>
              <Text3D
                position={[0, 0.21, 0.01]}
                size={0.032}
                color={virada ? ARENA_COLORS.success : ARENA_COLORS.muted}
              >
                {virada
                  ? "Resposta"
                  : `${tema.nome} · pergunta ${(indice % fila.length) + 1}/${fila.length}`}
              </Text3D>
              <Text3D position={[0, -0.02, 0.01]} size={virada ? 0.042 : 0.048} maxWidth={0.8}>
                {virada ? atual.resposta : atual.pergunta}
              </Text3D>
              <Text3D position={[0, -0.24, 0.01]} size={0.026} color={ARENA_COLORS.muted}>
                {virada
                  ? atual.ia
                    ? "gerada por IA — confira no tratado"
                    : "clique para voltar à pergunta"
                  : atual.ia
                    ? "gerada por IA — clique para virar"
                    : "clique na carta para virar"}
              </Text3D>
            </Panel>
          </group>

          <Button3D
            label="Próxima"
            width={0.42}
            height={0.11}
            position={[-0.26, -0.45, 0]}
            color={ARENA_COLORS.success}
            onClick={() => {
              setVirada(false);
              setIndice((i) => i + 1);
            }}
          />
          <Button3D
            label="Temas"
            width={0.34}
            height={0.11}
            position={[0.2, -0.45, 0]}
            onClick={() => {
              temaVigente.current = null;
              setTema(null);
            }}
          />
          <Button3D
            label={statusIA === "gerando" ? "Gerando…" : "+4 com IA"}
            width={0.4}
            height={0.1}
            position={[0, -0.6, 0]}
            color="#7c5cbf"
            onClick={() => {
              if (statusIA === "gerando") return;
              setStatusIA("gerando");
              const pedidoPara = tema.id;
              gerarCartasIA(tema)
                .then((novas) => {
                  if (temaVigente.current !== pedidoPara) return;
                  setFila((f) => [...f, ...novas]);
                  setStatusIA(`+${novas.length} cartas geradas`);
                })
                .catch(() => {
                  if (temaVigente.current === pedidoPara)
                    setStatusIA("IA indisponível (offline?)");
                });
            }}
          />
          {statusIA && statusIA !== "gerando" && (
            <Text3D position={[0, -0.72, 0]} size={0.028} color={ARENA_COLORS.muted}>
              {statusIA}
            </Text3D>
          )}
        </group>
      )}
    </group>
  );
}

/* ------------------------------------------------------- LIVRO (TUTOR IA) */

const PERGUNTAS_RAPIDAS = [
  "Explique o ciclo cardíaco em 3 frases.",
  "Qual a diferença entre artéria e veia?",
  "O que é a hematose e onde ocorre?",
];

/** Painel de tutor DENTRO do VR: perguntas prontas + resposta em texto 3D. */
function TutorVR({ onFechar }: { onFechar: () => void }) {
  const [resposta, setResposta] = useState("");
  const [ocupado, setOcupado] = useState(false);
  const buffer = useRef("");
  const ultimaAtualizacao = useRef(0);

  // Streaming com atualização limitada (re-layout do troika a cada chunk
  // engasgaria o headset — atualiza a cada ~300ms).
  useFrame(({ clock }) => {
    if (!ocupado) return;
    // Sem o guard, o primeiro tick sobrescrevia o "…" com string vazia e o
    // painel voltava ao texto ocioso durante a latência inicial da IA — a
    // pergunta parecia ignorada.
    if (!buffer.current) return;
    if (clock.elapsedTime - ultimaAtualizacao.current > 0.3) {
      ultimaAtualizacao.current = clock.elapsedTime;
      setResposta(buffer.current);
    }
  });

  const perguntar = (texto: string) => {
    if (ocupado) return;
    buffer.current = "";
    setResposta("…");
    setOcupado(true);
    streamChatResponse(
      { messages: [{ role: "user", content: texto + " Responda em até 4 frases." }] },
      (chunk) => {
        buffer.current += chunk;
      },
    )
      .then(() => setResposta(buffer.current))
      .catch((error: unknown) =>
        setResposta(
          error instanceof Error
            ? error.message
            : "Não foi possível contatar o tutor de IA.",
        ),
      )
      .finally(() => setOcupado(false));
  };

  return (
    // À direita, sobre a mesa, ~1,1 m dos olhos de quem está no assento.
    <group position={[0.85, 1.35, -2.0]} rotation={[0, -0.55, 0]}>
      <Panel width={1.25} height={1.15}>
        <Text3D position={[0, 0.48, 0.01]} size={0.05}>
          Tutor de IA
        </Text3D>
        <BotaoFechar position={[0.55, 0.5, 0.01]} onClick={onFechar} />
        {PERGUNTAS_RAPIDAS.map((p, i) => (
          <Button3D
            key={p}
            label={p.length > 34 ? `${p.slice(0, 33)}…` : p}
            width={1.05}
            height={0.11}
            position={[0, 0.31 - i * 0.14, 0.01]}
            onClick={() => perguntar(p)}
          />
        ))}
        {/* Ancorado no topo, abaixo do último chip; teto de 572
            caracteres (~11 linhas) para caber no painel. */}
        <Text3D
          position={[0, -0.065, 0.01]}
          size={0.036}
          maxWidth={1.1}
          anchorY="top"
        >
          {resposta.length > 572
            ? `${resposta.slice(0, 572)}…`
            : resposta || "Escolha uma pergunta — ou use o teclado no desktop."}
        </Text3D>
      </Panel>
    </group>
  );
}

function Livro({
  onAbrirTutorDom,
  aberto,
  onAbrir,
  onFechar,
}: PropsPainel & { onAbrirTutorDom: () => void }) {
  const inSession = useXR((state) => Boolean(state.session));
  const gltf = useGLTF(LIVRO_GLB, "/draco/");
  const scene = useMemo(() => gltf.scene.clone(true), [gltf.scene]);

  return (
    <>
      <group position={[-0.72, 0.765, -1.95]} rotation={[0, 0.25, 0]}>
        <Interativo
          rotulo="Livro — pergunte ao tutor de IA"
          posRotulo={[0, 0.16, 0]}
          onClick={() => {
            if (!inSession) onAbrirTutorDom();
            else if (aberto) onFechar();
            else onAbrir();
          }}
        >
          {/* Enciclopédia deitada: arquivo centrado na origem, base em
              y=-0.145 (bruto); escala 0.15 → lombada de 30cm. */}
          <group scale={0.15}>
            <group position={[0, 0.145, 0]}>
              <primitive object={scene} />
            </group>
          </group>
        </Interativo>
      </group>
      {inSession && aberto && <TutorVR onFechar={onFechar} />}
    </>
  );
}
useGLTF.preload(LIVRO_GLB, "/draco/");

/* ------------------------------------------------------------------ RAIZ */

export function SalaInterativos({
  onAbrirTutorDom,
}: {
  onAbrirTutorDom: () => void;
}) {
  // Um pop-up por vez: abrir um fecha o outro (pedido do teste no Quest).
  const [aberto, setAberto] = useState<PainelAberto>(null);
  const props = (nome: Exclude<PainelAberto, null>): PropsPainel => ({
    aberto: aberto === nome,
    onAbrir: () => setAberto(nome),
    onFechar: () => setAberto((atual) => (atual === nome ? null : atual)),
  });
  return (
    <group>
      <Radio />
      <Computador {...props("hub")} />
      <Flashcards {...props("flashcards")} />
      <Livro onAbrirTutorDom={onAbrirTutorDom} {...props("tutor")} />
    </group>
  );
}
