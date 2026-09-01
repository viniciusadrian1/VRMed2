"use client";

import { Suspense, useLayoutEffect, useMemo, useRef, useState } from "react";
import { useFrame } from "@react-three/fiber";
import { useGLTF } from "@react-three/drei";
import * as THREE from "three";
import { Text3D, Panel, Button3D, ARENA_COLORS } from "@/components/arena/ui3d";
import {
  detectStructures,
  normalizeContent,
  prepareModel,
} from "@/lib/model-utils";
import { ORGANS } from "@/lib/organs";
import { playEnd, playHit, playMiss, playStart, playTick } from "@/lib/arena-audio";
import { Oponente, type HumorOponente } from "./Oponente";

/**
 * Duelo 1x1 (Modo 2 do plano multi-modo) — v1 contra BOT.
 *
 * 8 rodadas alternando: órgão inteiro (100 pts) e estrutura da laringe
 * marcada (200 pts). Quem responde certo primeiro pontua — o bot "responde"
 * após um atraso sorteado pela dificuldade. Online real fica para a fase 2
 * (WebSocket); a máquina de estados já separa "quem pontuou" de "como a
 * resposta chegou", então o oponente remoto entra no lugar do bot.
 */

const LARINGE = "/models/organs/larynx.glb";
// pulmao.glb (3,2MB) fica fora do sorteio para o carregamento não pesar no
// wifi de evento; o nome "Pulmão" ainda aparece como alternativa errada.
const ORGAOS_DUELO = ORGANS.filter((o) => o.id !== "pulmao");

// Layout "sala de aula" (coordenadas de mundo, medidas do GLB do cenário):
// lousa em x=0.8 com face em z=-3.85; cadeiras da frente em x=-1.81 (bot) e
// x=+0.62 (jogador, onde fica o XROrigin — ver DueloApp).
const LOUSA_X = 0.8;
const LOUSA_Z = -3.85;
const MESA_JOGADOR_X = 0.62;

const TOTAL_RODADAS = 8;
const TEMPO_RODADA = 18;

export type Dificuldade = "iniciante" | "residente" | "especialista";

const BOTS: Record<
  Dificuldade,
  { nome: string; atrasoMin: number; atrasoMax: number; acerto: number }
> = {
  iniciante: { nome: "Dr. Caloni (iniciante)", atrasoMin: 6.5, atrasoMax: 10, acerto: 0.5 },
  residente: { nome: "Dra. Reis (residente)", atrasoMin: 4, atrasoMax: 7, acerto: 0.72 },
  especialista: { nome: "Dr. Chefe (especialista)", atrasoMin: 2.6, atrasoMax: 4.6, acerto: 0.9 },
};

type Fase = "menu" | "contagem" | "rodada" | "feedback" | "fim";

interface Rodada {
  tipo: "orgao" | "estrutura";
  pontos: 100 | 200;
  /** Resposta correta (pt-BR, como aparece nos botões). */
  alvo: string;
  opcoes: string[];
  /** Só para tipo "orgao": caminho do GLB. */
  modelo?: string;
}

function embaralhar<T>(lista: T[]): T[] {
  const r = [...lista];
  for (let i = r.length - 1; i > 0; i -= 1) {
    const j = Math.floor(Math.random() * (i + 1));
    [r[i], r[j]] = [r[j], r[i]];
  }
  return r;
}

function montarRodadas(estruturas: string[]): Rodada[] {
  const orgaos = embaralhar(ORGAOS_DUELO).slice(0, TOTAL_RODADAS / 2);
  const nomesOrgaos = ORGANS.map((o) => o.name);
  const alvosEstrutura = embaralhar(estruturas).slice(0, TOTAL_RODADAS / 2);

  const rodadasOrgao: Rodada[] = orgaos.map((organ) => ({
    tipo: "orgao",
    pontos: 100,
    alvo: organ.name,
    modelo: organ.modelPath,
    opcoes: embaralhar([
      organ.name,
      ...embaralhar(nomesOrgaos.filter((n) => n !== organ.name)).slice(0, 3),
    ]),
  }));
  const rodadasEstrutura: Rodada[] = alvosEstrutura.map((alvo) => ({
    tipo: "estrutura",
    pontos: 200,
    alvo,
    opcoes: embaralhar([
      alvo,
      ...embaralhar(estruturas.filter((e) => e !== alvo)).slice(0, 3),
    ]),
  }));

  // Alterna fácil/difícil: 100, 200, 100, 200…
  const rodadas: Rodada[] = [];
  for (let i = 0; i < TOTAL_RODADAS / 2; i += 1) {
    rodadas.push(rodadasOrgao[i], rodadasEstrutura[i]);
  }
  return rodadas;
}

/** Opção clicável escrita em giz na lousa (sem pop-up): texto + plano
 *  invisível para o raycast + crescimento suave no hover. */
function BotaoLousa({
  texto,
  position,
  onClick,
  cor = "#f2f5ec",
  size = 0.14,
  width = 2.3,
}: {
  texto: string;
  position: [number, number, number];
  onClick: () => void;
  cor?: string;
  size?: number;
  width?: number;
}) {
  const grupo = useRef<THREE.Group>(null);
  const hovered = useRef(false);
  const escala = useRef(1);
  useFrame((_, delta) => {
    if (!grupo.current) return;
    const alvo = hovered.current ? 1.09 : 1;
    escala.current += (alvo - escala.current) * Math.min(1, delta * 12);
    grupo.current.scale.setScalar(escala.current);
  });
  return (
    <group
      ref={grupo}
      position={position}
      onClick={(e) => {
        e.stopPropagation();
        onClick();
      }}
      onPointerOver={(e) => {
        e.stopPropagation();
        hovered.current = true;
      }}
      onPointerOut={() => {
        hovered.current = false;
      }}
    >
      {/* Panel/Text3D têm raycast desligado — o plano invisível recebe o clique */}
      <mesh>
        <planeGeometry args={[width, size * 1.9]} />
        <meshBasicMaterial transparent opacity={0} depthWrite={false} />
      </mesh>
      <Text3D size={size} color={cor} maxWidth={width}>
        {texto}
      </Text3D>
    </group>
  );
}

/** Modelo da rodada girando devagar; estrutura-alvo ganha um marcador pulsante. */
function ModeloRodada({ rodada }: { rodada: Rodada }) {
  const caminho = rodada.tipo === "orgao" ? rodada.modelo! : LARINGE;
  const gltf = useGLTF(caminho, "/draco/");
  const scene = useMemo(() => gltf.scene.clone(true), [gltf.scene]);
  // Três grupos aninhados (padrão do ArenaModel): o de fora carrega a escala
  // de projeto, o do meio gira, e o de dentro recebe normalizeContent — que
  // sobrescreve scale/position do grupo em que roda. Num grupo só, a
  // normalização engolia o scale={0.85} e a rotação orbitava o pivô cru do
  // GLB em vez do centro do modelo.
  const spinner = useRef<THREE.Group>(null);
  const content = useRef<THREE.Group>(null);
  const marcador = useRef<THREE.Mesh>(null);
  const [posMarcador, setPosMarcador] = useState<[number, number, number] | null>(null);

  // useLayoutEffect, não useEffect: com frameloop="always" um quadro podia
  // ser desenhado ANTES da normalização — um flash do GLB em unidades cruas
  // dentro do headset a cada troca de rodada.
  useLayoutEffect(() => {
    const g = content.current;
    if (!g) return;
    if (spinner.current) spinner.current.rotation.y = 0;
    // Rodando ANTES do primeiro quadro (useLayoutEffect), as matrizes de
    // mundo ainda carregam a rotação da rodada anterior — medir assim
    // deslocava o modelo para o lado. Recalcula a cadeia inteira primeiro.
    g.updateWorldMatrix(true, true);
    normalizeContent(g);
    prepareModel(g, "mesh");
    // O modelo do Duelo não é clicável (diferente da Arena) — sem isto, as
    // malhas do órgão interceptavam o laser/mouse na frente dos botões de
    // resposta e o clique/hover falhava quando o giro passava por cima.
    g.traverse((obj) => {
      if (obj instanceof THREE.Mesh) obj.raycast = () => null;
    });
    if (rodada.tipo === "estrutura" && spinner.current) {
      // Posições vêm em coordenadas de mundo com os grupos ainda sem rotação.
      // O marcador vive no SPINNER (fora do content): dentro do content ele
      // contaminava a medição da rodada seguinte — o normalizeContent media
      // "órgão novo + marcador velho" e o órgão saía minúsculo/deslocado
      // (era o cérebro invisível e o coração miniatura do teste do grupo).
      const ponto = detectStructures(g).find((p) => p.label === rodada.alvo);
      if (ponto) {
        const local = spinner.current.worldToLocal(
          new THREE.Vector3(...ponto.position),
        );
        setPosMarcador([local.x, local.y, local.z]);
      } else {
        setPosMarcador(null);
      }
    } else {
      setPosMarcador(null);
    }
  }, [scene, rodada]);

  useFrame((state, delta) => {
    if (spinner.current) spinner.current.rotation.y += delta * 0.35;
    if (marcador.current) {
      const s = 1 + 0.25 * Math.sin(state.clock.elapsedTime * 5);
      marcador.current.scale.setScalar(s);
    }
  });

  return (
    <group scale={0.85}>
      <group ref={spinner}>
        <group ref={content}>
          <primitive object={scene} />
        </group>
        {posMarcador && (
          <mesh ref={marcador} position={posMarcador} raycast={() => null}>
            <sphereGeometry args={[0.055, 16, 12]} />
            <meshBasicMaterial color="#ffd166" toneMapped={false} transparent opacity={0.9} />
          </mesh>
        )}
      </group>
    </group>
  );
}

export function DueloGame() {
  // A laringe carrega já no menu (Suspense) — as rodadas de 200 pts saem
  // das estruturas nomeadas reais dela.
  const laringe = useGLTF(LARINGE, "/draco/");
  const estruturas = useMemo(() => {
    const clone = laringe.scene.clone(true);
    normalizeContent(clone);
    return detectStructures(clone)
      .map((p) => p.label)
      .filter((nome) => nome.length <= 34);
  }, [laringe.scene]);

  const [fase, setFase] = useState<Fase>("menu");
  const [dificuldade, setDificuldade] = useState<Dificuldade>("residente");
  const [rodadas, setRodadas] = useState<Rodada[]>([]);
  const [indice, setIndice] = useState(0);
  const [pontosJogador, setPontosJogador] = useState(0);
  const [pontosBot, setPontosBot] = useState(0);
  const [humorBot, setHumorBot] = useState<HumorOponente>("idle");
  const [feedback, setFeedback] = useState("");
  const [erroJogador, setErroJogador] = useState(false);
  const [contagem, setContagem] = useState(3);
  const [tempoRestante, setTempoRestante] = useState(TEMPO_RODADA);

  const relogio = useRef(0); // acumulador da fase atual (s)
  const travadoAte = useRef(0); // lockout após erro do jogador
  // Trava SÍNCRONA da rodada: o clique do jogador pode chegar na janela entre
  // o frame em que o bot/timeout encerrou e o commit do React (fase ainda lê
  // "rodada" no closure) — sem o ref, os dois pontuavam na mesma rodada.
  const rodadaEncerrada = useRef(false);
  const botPlano = useRef({ em: 99, acerta: false, respondeu: false });
  const rodada = rodadas[indice];

  const comecar = (nivel: Dificuldade) => {
    setDificuldade(nivel);
    setRodadas(montarRodadas(estruturas));
    setIndice(0);
    setPontosJogador(0);
    setPontosBot(0);
    setHumorBot("idle");
    relogio.current = 0;
    setContagem(3);
    setFase("contagem");
    playTick();
  };

  const iniciarRodada = () => {
    relogio.current = 0;
    travadoAte.current = 0;
    rodadaEncerrada.current = false;
    setTempoRestante(TEMPO_RODADA);
    setErroJogador(false);
    const bot = BOTS[dificuldade];
    botPlano.current = {
      em: bot.atrasoMin + Math.random() * (bot.atrasoMax - bot.atrasoMin),
      acerta: Math.random() < bot.acerto,
      respondeu: false,
    };
    setFase("rodada");
  };

  const encerrarRodada = (texto: string, humor: HumorOponente) => {
    rodadaEncerrada.current = true;
    setFeedback(texto);
    setHumorBot(humor);
    relogio.current = 0;
    setFase("feedback");
  };

  const responder = (opcao: string) => {
    if (fase !== "rodada" || rodadaEncerrada.current) return;
    if (relogio.current < travadoAte.current) return;
    if (opcao === rodada.alvo) {
      playHit();
      setPontosJogador((p) => p + rodada.pontos);
      encerrarRodada(`Você pontuou! +${rodada.pontos}`, "erra");
    } else {
      playMiss();
      setErroJogador(true);
      travadoAte.current = relogio.current + 1.6;
    }
  };

  // Cronômetro, contagem regressiva e o "raciocínio" do bot — tudo num
  // useFrame, empurrando para o React só quando um valor visível muda.
  useFrame((_, delta) => {
    relogio.current += delta;

    if (fase === "contagem") {
      const restante = 3 - Math.floor(relogio.current);
      if (restante !== contagem && restante > 0) {
        setContagem(restante);
        playTick();
      }
      if (relogio.current >= 3) {
        playStart();
        iniciarRodada();
      }
      return;
    }

    if (fase === "rodada") {
      if (rodadaEncerrada.current) return;
      const restante = Math.max(0, Math.ceil(TEMPO_RODADA - relogio.current));
      if (restante !== tempoRestante) setTempoRestante(restante);

      if (erroJogador && relogio.current >= travadoAte.current) {
        setErroJogador(false);
      }

      const bot = botPlano.current;
      if (!bot.respondeu && relogio.current >= bot.em) {
        bot.respondeu = true;
        if (bot.acerta) {
          playMiss();
          setPontosBot((p) => p + rodada.pontos);
          encerrarRodada(
            `${BOTS[dificuldade].nome.split(" (")[0]} pontuou: ${rodada.alvo}`,
            "comemora",
          );
          return;
        }
        // Bot errou: fica de fora da rodada (jogador segue tentando).
      }

      if (relogio.current >= TEMPO_RODADA) {
        encerrarRodada(`Tempo esgotado — era: ${rodada.alvo}`, "idle");
      }
      return;
    }

    if (fase === "feedback" && relogio.current >= 2.4) {
      setHumorBot("idle");
      if (indice + 1 >= TOTAL_RODADAS) {
        playEnd();
        setFase("fim");
      } else {
        setIndice((i) => i + 1);
        iniciarRodada();
      }
    }
  });

  /* ----------------------------------------------------------- render */

  if (fase === "menu") {
    return (
      <group>
        <Text3D position={[LOUSA_X, 2.05, LOUSA_Z]} size={0.24} color="#f2f5ec">
          Duelo 1×1
        </Text3D>
        <Text3D
          position={[LOUSA_X, 1.76, LOUSA_Z]}
          size={0.07}
          color="#cfe0cd"
          maxWidth={2.3}
        >
          Identifique órgãos (100 pts) e estruturas (200 pts) antes do oponente
        </Text3D>
        {(Object.keys(BOTS) as Dificuldade[]).map((nivel, i) => (
          <BotaoLousa
            key={nivel}
            texto={BOTS[nivel].nome}
            position={[LOUSA_X, 1.47 - i * 0.24, LOUSA_Z]}
            cor={nivel === "especialista" ? "#ffc9bd" : "#f2f5ec"}
            size={0.13}
            onClick={() => comecar(nivel)}
          />
        ))}
        <Text3D position={[LOUSA_X, 0.98, LOUSA_Z]} size={0.055} color="#a9c9ad">
          Online por partida — em breve; hoje o oponente é um bot
        </Text3D>
      </group>
    );
  }

  if (fase === "contagem") {
    return (
      <Text3D position={[LOUSA_X, 1.6, LOUSA_Z]} size={0.85} color="#f2f5ec">
        {String(contagem)}
      </Text3D>
    );
  }

  if (fase === "fim") {
    const venceu = pontosJogador > pontosBot;
    const empate = pontosJogador === pontosBot;
    return (
      <group>
        <Text3D
          position={[LOUSA_X, 2.05, LOUSA_Z]}
          size={0.22}
          color={venceu ? "#bfe8cf" : empate ? "#f2f5ec" : "#ffc9bd"}
        >
          {venceu ? "Você venceu!" : empate ? "Empate!" : "O bot venceu"}
        </Text3D>
        <Text3D position={[LOUSA_X, 1.7, LOUSA_Z]} size={0.12} color="#f2f5ec">
          {`Você ${pontosJogador} × ${pontosBot} ${BOTS[dificuldade].nome.split(" (")[0]}`}
        </Text3D>
        <BotaoLousa
          texto="→ Jogar de novo"
          position={[LOUSA_X, 1.36, LOUSA_Z]}
          cor="#bfe8cf"
          size={0.14}
          onClick={() => comecar(dificuldade)}
        />
        <BotaoLousa
          texto="→ Trocar dificuldade"
          position={[LOUSA_X, 1.08, LOUSA_Z]}
          size={0.12}
          onClick={() => setFase("menu")}
        />
      </group>
    );
  }

  // fase "rodada" ou "feedback"
  return (
    <group>
      {/* Suspense LOCAL: em wifi lento, um GLB de rodada ainda em voo não pode
          apagar placar, cronômetro e botões — só o modelo espera. */}
      {/* Órgão AO LADO da lousa, girando no próprio eixo */}
      <group position={[-1.75, 1.25, -3.4]} scale={0.62}>
        <Suspense
          fallback={
            <Text3D position={[0, 0, 0]} size={0.11} color={ARENA_COLORS.muted}>
              Carregando…
            </Text3D>
          }
        >
          <ModeloRodada rodada={rodada} />
        </Suspense>
      </group>

      {/* Placar e cabeçalho */}
      {/* Cantos internos do quadro verde: placar e info da rodada (giz) */}
      <Text3D position={[LOUSA_X - 0.72, 2.28, LOUSA_Z]} size={0.09} color="#bfe8cf">
        {`Você: ${pontosJogador}`}
      </Text3D>
      <Text3D position={[LOUSA_X + 0.62, 2.28, LOUSA_Z]} size={0.08} color="#e8e3c8">
        {`Rodada ${indice + 1}/${TOTAL_RODADAS} · vale ${rodada.pontos}`}
      </Text3D>

      {fase === "rodada" && (
        <>
          {/* Pergunta escrita na lousa, como giz */}
          <Text3D
            position={[LOUSA_X, 2.0, LOUSA_Z]}
            size={0.15}
            maxWidth={2.35}
            color="#f2f5ec"
          >
            {rodada.tipo === "orgao"
              ? "Qual órgão é este?"
              : "Qual estrutura está marcada em amarelo?"}
          </Text3D>
          {/* Cronômetro no canto inferior direito do quadro */}
          <Text3D
            position={[LOUSA_X - 0.85, 2.02, LOUSA_Z]}
            size={0.13}
            color={tempoRestante <= 5 ? "#ffb0a0" : "#dfe8db"}
          >
            {String(tempoRestante)}
          </Text3D>

          {/* Opções em grade 2×2, perto do jogador */}
          {/* Alternativas escritas na lousa, clicáveis */}
          {rodada.opcoes.map((opcao, i) => (
            <BotaoLousa
              key={opcao}
              texto={`${["A", "B", "C", "D"][i]})  ${opcao}`}
              position={[LOUSA_X, 1.64 - i * 0.23, LOUSA_Z]}
              cor={erroJogador ? "#8fae94" : "#f8fbef"}
              size={0.115}
              onClick={() => responder(opcao)}
            />
          ))}
          {erroJogador && (
            <Text3D position={[LOUSA_X - 0.85, 1.82, LOUSA_Z]} size={0.07} color="#ffb0a0">
              Errado!
            </Text3D>
          )}
        </>
      )}

      {fase === "feedback" && (
        <Text3D
          position={[LOUSA_X, 1.45, LOUSA_Z]}
          size={0.16}
          maxWidth={2.35}
          color="#f2f5ec"
        >
          {feedback}
        </Text3D>
      )}

      <Oponente
        humor={humorBot}
        nome={BOTS[dificuldade].nome.split(" (")[0]}
        pontos={pontosBot}
        position={[-1.81, -0.82, 0.85]}
        rotationY={Math.PI}
        sentado
        escala={1.35}
      />
    </group>
  );
}

useGLTF.preload(LARINGE, "/draco/");
for (const organ of ORGAOS_DUELO) useGLTF.preload(organ.modelPath, "/draco/");
