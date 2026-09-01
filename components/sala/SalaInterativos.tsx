"use client";

import { useEffect, useMemo, useRef, useState, type ReactNode } from "react";
import { useFrame, type ThreeEvent } from "@react-three/fiber";
import { useGLTF } from "@react-three/drei";
import { useXR } from "@react-three/xr";
import * as THREE from "three";
import { Text3D, Panel, Button3D, ARENA_COLORS } from "@/components/arena/ui3d";
import { proximaEstacao, pararRadio, estadoRadio } from "@/lib/lofi";
import { streamChatResponse } from "@/lib/chat-client";

/**
 * Os quatro itens interativos da mesa: rádio, computador (hub), flashcards e
 * livro (tutor de IA). Interação por clique/gatilho — funciona igual com
 * mouse (desktop) e laser (VR), seguindo o padrão da Arena.
 */

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

function Radio() {
  const [nome, setNome] = useState<string>("");
  const tocando = estadoRadio().tocando;

  // Desligar ao sair da página (o áudio não pode vazar para outras rotas).
  useEffect(() => () => pararRadio(), []);

  return (
    <group position={[0.68, 0.765, -1.95]}>
      <Interativo
        rotulo={nome ? `♪ ${nome}` : "Rádio lo-fi — clique para ligar"}
        posRotulo={[0, 0.24, 0.05]}
        onClick={() => {
          void proximaEstacao().then((estado) =>
            setNome(estado.tocando ? estado.nome : ""),
          );
        }}
      >
        {/* Corpo */}
        <mesh position={[0, 0.07, 0]}>
          <boxGeometry args={[0.3, 0.14, 0.12]} />
          <meshStandardMaterial color="#b3572f" roughness={0.6} />
        </mesh>
        {/* Alto-falante */}
        <mesh position={[-0.07, 0.07, 0.062]}>
          <circleGeometry args={[0.045, 20]} />
          <meshStandardMaterial color="#31241c" roughness={1} />
        </mesh>
        {/* Botões */}
        {[0.04, 0.1].map((x) => (
          <mesh key={x} position={[x, 0.07, 0.062]} rotation={[Math.PI / 2, 0, 0]}>
            <cylinderGeometry args={[0.016, 0.016, 0.015, 12]} />
            <meshStandardMaterial color="#e8d9c3" roughness={0.4} />
          </mesh>
        ))}
        {/* Antena */}
        <mesh position={[0.12, 0.2, -0.03]} rotation={[0, 0, -0.35]}>
          <cylinderGeometry args={[0.003, 0.003, 0.14, 6]} />
          <meshStandardMaterial color="#888" metalness={0.6} roughness={0.4} />
        </mesh>
        {/* LED de ligado */}
        <mesh position={[0.07, 0.115, 0.062]}>
          <circleGeometry args={[0.006, 8]} />
          <meshStandardMaterial
            color={tocando || nome ? "#7CFC9B" : "#333"}
            emissive={tocando || nome ? "#4fae89" : "#000"}
            emissiveIntensity={2}
          />
        </mesh>
      </Interativo>
    </group>
  );
}

/* ------------------------------------------------------- COMPUTADOR (HUB) */

// "Office Monitor / Workstation Monitor" por DatSketch (Sketchfab), CC-BY-4.0
// — atribuição em public/models/props/CREDITS.md. Substituiu o monitor
// procedural a pedido do grupo.
const MONITOR_GLB = "/models/props/monitor.glb";

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

const MODOS_HUB = [
  { rotulo: "Estudo 3D", href: "/viewer" },
  { rotulo: "Arena VR", href: "/arena" },
  { rotulo: "Clínica", href: "/clinica" },
  { rotulo: "Quiz", href: "/quiz" },
];

function Computador() {
  const [aberto, setAberto] = useState(false);
  const inSession = useXR((state) => Boolean(state.session));

  return (
    <group position={[0, 0.765, -2.08]}>
      <Interativo
        rotulo={aberto ? "Fechar hub" : "Computador — hub do VRmed"}
        posRotulo={[0, 0.5, 0.08]}
        onClick={() => setAberto((v) => !v)}
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

      {/* Painel-hub flutuante acima do monitor */}
      {aberto && (
        <group position={[0, 0.85, 0.3]}>
          <Panel width={1.15} height={0.78}>
            <Text3D position={[0, 0.28, 0.01]} size={0.06}>
              Portal de estudo
            </Text3D>
            {MODOS_HUB.map((modo, i) => (
              <Button3D
                key={modo.href}
                label={modo.rotulo}
                width={0.9}
                height={0.13}
                position={[0, 0.12 - i * 0.16, 0.01]}
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
    .slice(0, 6);
}

function Flashcards() {
  const [temas, setTemas] = useState<Tema[]>([]);
  const [tema, setTema] = useState<Tema | null>(null);
  const [fila, setFila] = useState<Carta[]>([]);
  const [indice, setIndice] = useState(0);
  const [virada, setVirada] = useState(false);
  const [painel, setPainel] = useState(false);
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
      <group position={[-0.42, 0.769, -1.72]}>
        <Interativo
          rotulo="Flashcards — clique para estudar"
          posRotulo={[0, 0.16, 0]}
          onClick={() => setPainel((v) => !v)}
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

      {/* Painel de temas */}
      {painel && !tema && (
        <group position={[-0.55, 1.5, -1.45]} rotation={[0, 0.18, 0]}>
          <Panel width={1.0} height={1.15}>
            <Text3D position={[0, 0.47, 0.01]} size={0.055}>
              Escolha o tema
            </Text3D>
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

      {/* Carta flutuante */}
      {painel && tema && atual && (
        <group position={[-0.45, 1.48, -1.3]} rotation={[0, 0.15, 0]}>
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
                {virada ? "clique para voltar à pergunta" : "clique na carta para virar"}
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
function TutorVR() {
  const [aberto, setAberto] = useState(false);
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
      .catch(() => setResposta("Tutor indisponível — sem conexão com a IA."))
      .finally(() => setOcupado(false));
  };

  return (
    <group position={[0.62, 1.5, -1.45]} rotation={[0, -0.2, 0]}>
      {!aberto ? (
        <Button3D label="Abrir tutor" width={0.6} height={0.14} onClick={() => setAberto(true)} />
      ) : (
        <>
          <Panel width={1.25} height={1.15}>
            <Text3D position={[0, 0.48, 0.01]} size={0.05}>
              Tutor de IA
            </Text3D>
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
            <Text3D position={[0, -0.28, 0.01]} size={0.036} maxWidth={1.1}>
              {resposta || "Escolha uma pergunta — ou use o teclado no desktop."}
            </Text3D>
          </Panel>
          <Button3D
            label="Fechar"
            width={0.34}
            height={0.1}
            position={[0, -0.68, 0]}
            color="#5c6b7a"
            onClick={() => setAberto(false)}
          />
        </>
      )}
    </group>
  );
}

function Livro({ onAbrirTutorDom }: { onAbrirTutorDom: () => void }) {
  const inSession = useXR((state) => Boolean(state.session));
  const [tutorVR, setTutorVR] = useState(false);

  return (
    <>
      <group position={[-0.72, 0.765, -1.95]} rotation={[0, 0.25, 0]}>
        <Interativo
          rotulo="Livro — pergunte ao tutor de IA"
          posRotulo={[0, 0.16, 0]}
          onClick={() => {
            if (inSession) setTutorVR((v) => !v);
            else onAbrirTutorDom();
          }}
        >
          <mesh position={[0, 0.02, 0]}>
            <boxGeometry args={[0.22, 0.04, 0.3]} />
            <meshStandardMaterial color="#7a2e2e" roughness={0.7} />
          </mesh>
          <mesh position={[0.005, 0.042, 0]}>
            <boxGeometry args={[0.2, 0.006, 0.28]} />
            <meshStandardMaterial color="#efe8da" roughness={0.9} />
          </mesh>
          <Text3D position={[0, 0.06, 0.09]} size={0.024} color="#e8d9c3">
            ANATOMIA
          </Text3D>
        </Interativo>
      </group>
      {inSession && tutorVR && <TutorVR />}
    </>
  );
}

/* ------------------------------------------------------------------ RAIZ */

export function SalaInterativos({
  onAbrirTutorDom,
}: {
  onAbrirTutorDom: () => void;
}) {
  return (
    <group>
      <Radio />
      <Computador />
      <Flashcards />
      <Livro onAbrirTutorDom={onAbrirTutorDom} />
    </group>
  );
}
