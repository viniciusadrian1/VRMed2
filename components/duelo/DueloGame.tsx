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
    normalizeContent(g);
    prepareModel(g, "mesh");
    if (rodada.tipo === "estrutura") {
      // Posições vêm em coordenadas de mundo com os grupos ainda sem rotação —
      // convertidas para locais, o marcador gira junto com o modelo.
      const ponto = detectStructures(g).find((p) => p.label === rodada.alvo);
      if (ponto) {
        const local = g.worldToLocal(new THREE.Vector3(...ponto.position));
        setPosMarcador([local.x, local.y, local.z]);
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
          {posMarcador && (
            <mesh ref={marcador} position={posMarcador}>
              <sphereGeometry args={[0.055, 16, 12]} />
              <meshBasicMaterial color="#ffd166" toneMapped={false} transparent opacity={0.9} />
            </mesh>
          )}
        </group>
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
      <group position={[0, 0.35, 0]}>
        <Panel width={2.3} height={1.5}>
          <Text3D position={[0, 0.55, 0.01]} size={0.14}>
            Duelo 1×1
          </Text3D>
          <Text3D position={[0, 0.32, 0.01]} size={0.055} color={ARENA_COLORS.muted} maxWidth={2}>
            Identifique órgãos (100 pts) e estruturas (200 pts) antes do oponente
          </Text3D>
          {(Object.keys(BOTS) as Dificuldade[]).map((nivel, i) => (
            <Button3D
              key={nivel}
              label={BOTS[nivel].nome}
              width={1.7}
              height={0.24}
              position={[0, 0.02 - i * 0.3, 0.01]}
              color={nivel === "especialista" ? ARENA_COLORS.danger : ARENA_COLORS.primary}
              onClick={() => comecar(nivel)}
            />
          ))}
        </Panel>
        <Text3D position={[0, -0.98, 0]} size={0.045} color={ARENA_COLORS.muted}>
          Online por partida — em breve; hoje o oponente é um bot
        </Text3D>
      </group>
    );
  }

  if (fase === "contagem") {
    return (
      <Text3D position={[0, 0.4, 0]} size={0.65} color={ARENA_COLORS.primary}>
        {String(contagem)}
      </Text3D>
    );
  }

  if (fase === "fim") {
    const venceu = pontosJogador > pontosBot;
    const empate = pontosJogador === pontosBot;
    return (
      <group position={[0, 0.35, 0]}>
        <Panel width={2.2} height={1.3}>
          <Text3D
            position={[0, 0.42, 0.01]}
            size={0.15}
            color={venceu ? ARENA_COLORS.success : empate ? ARENA_COLORS.primary : ARENA_COLORS.danger}
          >
            {venceu ? "Você venceu!" : empate ? "Empate!" : "O bot venceu"}
          </Text3D>
          <Text3D position={[0, 0.16, 0.01]} size={0.085}>
            {`Você ${pontosJogador} × ${pontosBot} ${BOTS[dificuldade].nome.split(" (")[0]}`}
          </Text3D>
          <Button3D
            label="Jogar de novo"
            width={1.3}
            height={0.22}
            position={[0, -0.14, 0.01]}
            color={ARENA_COLORS.success}
            onClick={() => comecar(dificuldade)}
          />
          <Button3D
            label="Trocar dificuldade"
            width={1.3}
            height={0.2}
            position={[0, -0.42, 0.01]}
            onClick={() => setFase("menu")}
          />
        </Panel>
      </group>
    );
  }

  // fase "rodada" ou "feedback"
  return (
    <group>
      {/* Suspense LOCAL: em wifi lento, um GLB de rodada ainda em voo não pode
          apagar placar, cronômetro e botões — só o modelo espera. */}
      <Suspense
        fallback={
          <Text3D position={[0, 0.2, 0]} size={0.07} color={ARENA_COLORS.muted}>
            Carregando o modelo…
          </Text3D>
        }
      >
        <ModeloRodada rodada={rodada} />
      </Suspense>

      {/* Placar e cabeçalho */}
      <Text3D position={[-1.25, 1.5, 0]} size={0.09} color={ARENA_COLORS.success}>
        {`Você: ${pontosJogador}`}
      </Text3D>
      <Text3D position={[1.25, 1.5, 0]} size={0.07} color={ARENA_COLORS.muted}>
        {`Rodada ${indice + 1}/${TOTAL_RODADAS} · vale ${rodada.pontos}`}
      </Text3D>

      {fase === "rodada" && (
        <>
          <Panel width={2.4} height={0.34} position={[0, 1.02, 0]}>
            <Text3D position={[0, 0, 0.01]} size={0.075} maxWidth={2.2}>
              {rodada.tipo === "orgao"
                ? "Qual órgão é este?"
                : "Qual estrutura está marcada em amarelo?"}
            </Text3D>
          </Panel>
          <Text3D
            position={[0, 0.78, 0]}
            size={0.08}
            color={tempoRestante <= 5 ? ARENA_COLORS.danger : ARENA_COLORS.muted}
          >
            {String(tempoRestante)}
          </Text3D>

          {/* Opções em grade 2×2, perto do jogador */}
          {rodada.opcoes.map((opcao, i) => (
            <Button3D
              key={opcao}
              label={opcao}
              width={1.45}
              height={0.24}
              position={[i % 2 === 0 ? -0.8 : 0.8, -0.18 - Math.floor(i / 2) * 0.3, 0.75]}
              color={erroJogador ? "#5c6b7a" : ARENA_COLORS.primary}
              onClick={() => responder(opcao)}
            />
          ))}
          {erroJogador && (
            <Text3D position={[0, 0.08, 0.75]} size={0.06} color={ARENA_COLORS.danger}>
              Errado — aguarde um instante…
            </Text3D>
          )}
        </>
      )}

      {fase === "feedback" && (
        <Panel width={2.2} height={0.4} position={[0, 1.02, 0]}>
          <Text3D position={[0, 0, 0.01]} size={0.08} maxWidth={2}>
            {feedback}
          </Text3D>
        </Panel>
      )}

      <Oponente
        humor={humorBot}
        nome={BOTS[dificuldade].nome.split(" (")[0]}
        pontos={pontosBot}
        position={[0, -1.3, -2.3]}
      />
    </group>
  );
}

useGLTF.preload(LARINGE, "/draco/");
for (const organ of ORGAOS_DUELO) useGLTF.preload(organ.modelPath, "/draco/");
