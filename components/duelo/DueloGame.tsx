"use client";

import { Suspense, useEffect, useLayoutEffect, useMemo, useRef, useState } from "react";
import { useFrame } from "@react-three/fiber";
import { useGLTF } from "@react-three/drei";
import * as THREE from "three";
import { Text3D, Panel, Button3D, ARENA_COLORS } from "@/components/arena/ui3d";
import {
  detectStructures,
  normalizeContent,
  prepareModel,
} from "@/lib/model-utils";
import type { StructurePoint } from "@/types";
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

// Layout "sala de aula" em coordenadas de mundo, derivado das medidas do GLB
// na escala humana (ESCOLA_S=0.72, ver DueloApp): face da lousa em z=-1.06,
// centro em x=0.36; o quadro verde ocupa y≈-0.50..0.26 e x≈±0.58 do centro
// (conferido no print da visão sentada — a estimativa anterior cortava 13cm do topo).
// Cadeiras da frente: x=-0.81 (bot) e x=+0.28 (jogador/XROrigin).
const LOUSA_X = 0.36;
const LOUSA_Z = -1.06;

const TOTAL_RODADAS = 8;
const TEMPO_RODADA = 18;

export type Dificuldade = "iniciante" | "residente" | "especialista";
export type Ambiente = "escola" | "hospital";

// Layout do HOSPITAL em coordenadas de mundo (piso em -1.3; jogador de pé no
// XROrigin [0,-1.3,2.55], olhos ≈ +0.3, olhando para -z). Toda a UI vive num
// painel só, 14° à direita e na altura dos olhos; órgão ~18° à esquerda; bot
// entre os dois, ao lado da mesa dele (não pode ficar atrás do painel). O layout antigo foi desenhado para a câmera
// de desktop vista de cima: a pergunta ficava a 3m do chão e 44° à esquerda —
// no Quest ela "não aparecia".
const HOSP_UI: [number, number, number] = [0.75, 0.15, -0.55];
const HOSP_ROT: [number, number, number] = [0, -0.25, 0];
const HOSP_LED: [number, number, number] = [0, 1.27, -3.13];

const BOTS: Record<
  Dificuldade,
  { nome: string; atrasoMin: number; atrasoMax: number; acerto: number }
> = {
  iniciante: { nome: "Dr. Caloni (iniciante)", atrasoMin: 6.5, atrasoMax: 10, acerto: 0.5 },
  residente: { nome: "Dra. Reis (residente)", atrasoMin: 4, atrasoMax: 7, acerto: 0.72 },
  especialista: { nome: "Dr. Chefe (especialista)", atrasoMin: 2.6, atrasoMax: 4.6, acerto: 0.9 },
};

// Ordem iniciante/residente/especialista = teclas 1/2/3 (mesma ordem dos menus 3D).
const NIVEIS = Object.keys(BOTS) as Dificuldade[];

type Fase = "menu" | "contagem" | "rodada" | "feedback" | "fim";

interface Rodada {
  tipo: "orgao" | "estrutura";
  pontos: 100 | 200;
  /** Resposta correta (pt-BR, como aparece nos botões). */
  alvo: string;
  opcoes: string[];
  /** Só para tipo "orgao": caminho do GLB. */
  modelo?: string;
  /** Só para tipo "estrutura": marcador no espaço local do spinner. */
  marcador?: [number, number, number];
}

/** Sorteia quando e se o bot acerta a rodada (fora do componente: o lint de
 *  pureza do React não aceita Math.random no escopo de render). */
function planejarBot(bot: (typeof BOTS)[Dificuldade]) {
  return {
    em: bot.atrasoMin + Math.random() * (bot.atrasoMax - bot.atrasoMin),
    acerta: Math.random() < bot.acerto,
    respondeu: false,
  };
}

function embaralhar<T>(lista: T[]): T[] {
  const r = [...lista];
  for (let i = r.length - 1; i > 0; i -= 1) {
    const j = Math.floor(Math.random() * (i + 1));
    [r[i], r[j]] = [r[j], r[i]];
  }
  return r;
}

function montarRodadas(estruturas: StructurePoint[]): Rodada[] {
  const orgaos = embaralhar(ORGAOS_DUELO).slice(0, TOTAL_RODADAS / 2);
  const nomesOrgaos = ORGANS.map((o) => o.name);
  const nomesEstruturas = estruturas.map((p) => p.label);
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
  const rodadasEstrutura: Rodada[] = alvosEstrutura.map((ponto) => ({
    tipo: "estrutura",
    pontos: 200,
    alvo: ponto.label,
    marcador: ponto.position,
    opcoes: embaralhar([
      ponto.label,
      ...embaralhar(nomesEstruturas.filter((e) => e !== ponto.label)).slice(0, 3),
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

  // Normalização calculada no espaço PRÓPRIO do clone, ainda solto da cena
  // (useMemo roda antes de montar). O normalizeContent media em coordenadas
  // de MUNDO: com o grupo-pai deslocado para o lado da lousa, o centro vinha
  // contaminado e cada órgão voava para um canto aleatório da sala.
  const ajuste = useMemo(() => {
    scene.updateMatrixWorld(true);
    const box = new THREE.Box3().setFromObject(scene);
    const centro = box.getCenter(new THREE.Vector3());
    const tam = box.getSize(new THREE.Vector3());
    const s = 2 / Math.max(tam.x, tam.y, tam.z, 1e-6);
    return {
      escala: s,
      pos: [-centro.x * s, -centro.y * s, -centro.z * s] as [
        number,
        number,
        number,
      ],
    };
  }, [scene]);

  // useLayoutEffect, não useEffect: com frameloop="always" um quadro podia
  // ser desenhado ANTES da normalização — um flash do GLB em unidades cruas
  // dentro do headset a cada troca de rodada.
  useLayoutEffect(() => {
    const g = content.current;
    if (!g) return;
    if (spinner.current) spinner.current.rotation.y = 0;
    g.updateWorldMatrix(true, true);
    prepareModel(g, "mesh");
    // O modelo do Duelo não é clicável (diferente da Arena) — sem isto, as
    // malhas do órgão interceptavam o laser/mouse na frente dos botões de
    // resposta e o clique/hover falhava quando o giro passava por cima.
    g.traverse((obj) => {
      if (obj instanceof THREE.Mesh) obj.raycast = () => null;
    });
    // O marcador vive no SPINNER (fora do content) com posição pré-calculada
    // no clone normalizado da laringe (montarRodadas). Calculá-lo aqui, com o
    // grupo-pai deslocado, puxava o ponto para a origem do MUNDO: o
    // detectStructures escolhe o vértice mais distante da origem e o afasta
    // 3% dela — na sala, o marcador caía sobre a cartilagem vizinha.
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
        <group ref={content} position={ajuste.pos} scale={ajuste.escala}>
          <primitive object={scene} />
        </group>
        {rodada.marcador && (
          <mesh ref={marcador} position={rodada.marcador} raycast={() => null}>
            <sphereGeometry args={[0.09, 16, 12]} />
            <meshBasicMaterial color="#ffd166" toneMapped={false} transparent opacity={0.9} />
          </mesh>
        )}
      </group>
    </group>
  );
}

export function DueloGame({ ambiente = "escola" }: { ambiente?: Ambiente }) {
  const hosp = ambiente === "hospital";
  // A laringe carrega já no menu (Suspense) — as rodadas de 200 pts saem
  // das estruturas nomeadas reais dela.
  const laringe = useGLTF(LARINGE, "/draco/");
  // Pontos medidos no clone normalizado e solto da cena — mesma normalização
  // do ModeloRodada, então a posição já é a do espaço local do spinner.
  const estruturas = useMemo(() => {
    const clone = laringe.scene.clone(true);
    normalizeContent(clone);
    return detectStructures(clone).filter((p) => p.label.length <= 34);
  }, [laringe.scene]);

  const [fase, setFaseState] = useState<Fase>("menu");
  // Espelho síncrono da fase: o useFrame pode rodar entre o setState e o
  // commit (o React cede tempo no re-layout do troika) e ler a fase velha —
  // a contagem disparava um tick fantasma e voltava a "3" já na rodada.
  const faseRef = useRef<Fase>("menu");
  const setFase = (nova: Fase) => {
    faseRef.current = nova;
    setFaseState(nova);
  };
  const [dificuldade, setDificuldade] = useState<Dificuldade>("residente");
  const [rodadas, setRodadas] = useState<Rodada[]>([]);
  const [indice, setIndice] = useState(0);
  const [pontosJogador, setPontosJogador] = useState(0);
  const [pontosBot, setPontosBot] = useState(0);
  const [humorBot, setHumorBot] = useState<HumorOponente>("idle");
  const [feedback, setFeedback] = useState("");
  const [erroJogador, setErroJogador] = useState(false);
  // Alternativas já erradas nesta rodada: ficam cinzas e param de aceitar clique.
  const [errados, setErrados] = useState<string[]>([]);
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
    setErrados([]);
    botPlano.current = planejarBot(BOTS[dificuldade]);
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
    if (faseRef.current !== "rodada" || rodadaEncerrada.current) return;
    if (relogio.current < travadoAte.current) return;
    if (errados.includes(opcao)) return;
    if (opcao === rodada.alvo) {
      playHit();
      setPontosJogador((p) => p + rodada.pontos);
      encerrarRodada(`Você pontuou! +${rodada.pontos}`, "erra");
    } else {
      playMiss();
      setErroJogador(true);
      setErrados((e) => [...e, opcao]);
      travadoAte.current = relogio.current + 1.6;
    }
  };

  // Atalho de teclado para DESKTOP (no headset não há teclado — lá joga-se com
  // laser/olhar). Sem array de deps de propósito: re-registra a cada render e
  // enxerga fase/rodada/dificuldade atuais (comecar/responder já são recriadas
  // por render). `"123".indexOf("")` retorna 0 — daí o `&& k`. Escape NÃO é
  // mapeado (no VR ele encerra a sessão). Reaproveita responder(), que já trava
  // rodada encerrada/lockout, então não duplica pontuação.
  useEffect(() => {
    const onKey = (e: KeyboardEvent) => {
      if (e.repeat || e.ctrlKey || e.metaKey || e.altKey) return;
      const k = e.key.toLowerCase();
      if (fase === "menu") {
        const i = "123".indexOf(k);
        if (i >= 0 && k) comecar(NIVEIS[i]);
        return;
      }
      if (fase === "rodada" && rodada) {
        let i = "1234".indexOf(k);
        if (i < 0) i = "abcd".indexOf(k);
        if (i >= 0 && k && rodada.opcoes[i]) responder(rodada.opcoes[i]);
        return;
      }
      if (fase === "fim" && k === "enter") comecar(dificuldade);
    };
    window.addEventListener("keydown", onKey);
    return () => window.removeEventListener("keydown", onKey);
  });

  // Cronômetro, contagem regressiva e o "raciocínio" do bot — tudo num
  // useFrame, empurrando para o React só quando um valor visível muda.
  useFrame((_, delta) => {
    relogio.current += delta;
    const faseAgora = faseRef.current;

    if (faseAgora === "contagem") {
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

    if (faseAgora === "rodada") {
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

    if (faseAgora === "feedback" && relogio.current >= 2.4) {
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
    if (hosp) {
      return (
        <group position={HOSP_UI} rotation={HOSP_ROT}>
          <Panel width={1.7} height={1.4}>
            <Text3D position={[0, 0.5, 0.01]} size={0.14}>
              Duelo 1×1
            </Text3D>
            <Text3D position={[0, 0.28, 0.01]} size={0.055} color={ARENA_COLORS.muted} maxWidth={1.5}>
              Identifique órgãos (100 pts) e estruturas (200 pts) antes do oponente
            </Text3D>
            {(Object.keys(BOTS) as Dificuldade[]).map((nivel, i) => (
              <Button3D
                key={nivel}
                label={BOTS[nivel].nome}
                width={1.4}
                height={0.22}
                position={[0, -0.02 - i * 0.28, 0.01]}
                color={nivel === "especialista" ? ARENA_COLORS.danger : ARENA_COLORS.primary}
                onClick={() => comecar(nivel)}
              />
            ))}
          </Panel>
        </group>
      );
    }
    return (
      <group>
        <Text3D position={[LOUSA_X, 0.17, LOUSA_Z]} size={0.1} color="#f2f5ec">
          Duelo 1×1
        </Text3D>
        <Text3D
          position={[LOUSA_X, 0.055, LOUSA_Z]}
          size={0.034}
          color="#cfe0cd"
          maxWidth={1.05}
        >
          Identifique órgãos (100 pts) e estruturas (200 pts) antes do oponente
        </Text3D>
        {(Object.keys(BOTS) as Dificuldade[]).map((nivel, i) => (
          <BotaoLousa
            key={nivel}
            texto={BOTS[nivel].nome}
            position={[LOUSA_X, -0.06 - i * 0.11, LOUSA_Z]}
            cor={nivel === "especialista" ? "#ffc9bd" : "#f2f5ec"}
            size={0.06}
            width={1.1}
            onClick={() => comecar(nivel)}
          />
        ))}
        <Text3D position={[LOUSA_X, -0.42, LOUSA_Z]} size={0.042} color="#cfe0cd">
          Online em breve — hoje você joga contra um bot
        </Text3D>
      </group>
    );
  }

  if (fase === "contagem") {
    return hosp ? (
      <>
        <group position={HOSP_UI} rotation={HOSP_ROT}>
          <Text3D size={0.5} color="#7de8ff">
            {String(contagem)}
          </Text3D>
        </group>
        <Text3D position={HOSP_LED} size={0.42} color="#7de8ff">
          {String(contagem)}
        </Text3D>
      </>
    ) : (
      <Text3D position={[LOUSA_X, -0.12, LOUSA_Z]} size={0.4} color="#f2f5ec">
        {String(contagem)}
      </Text3D>
    );
  }

  if (fase === "fim") {
    const venceu = pontosJogador > pontosBot;
    const empate = pontosJogador === pontosBot;
    if (hosp) {
      return (
        <group position={HOSP_UI} rotation={HOSP_ROT}>
          <Panel width={1.7} height={1.2}>
            <Text3D
              position={[0, 0.38, 0.01]}
              size={0.15}
              color={venceu ? ARENA_COLORS.success : empate ? ARENA_COLORS.primary : ARENA_COLORS.danger}
            >
              {venceu ? "Você venceu!" : empate ? "Empate!" : "O bot venceu"}
            </Text3D>
            <Text3D position={[0, 0.12, 0.01]} size={0.085}>
              {`Você ${pontosJogador} × ${pontosBot} ${BOTS[dificuldade].nome.split(" (")[0]}`}
            </Text3D>
            <Button3D
              label="Jogar de novo"
              width={1.3}
              height={0.22}
              position={[0, -0.16, 0.01]}
              color={ARENA_COLORS.success}
              onClick={() => comecar(dificuldade)}
            />
            <Button3D
              label="Trocar dificuldade"
              width={1.3}
              height={0.2}
              position={[0, -0.44, 0.01]}
              onClick={() => setFase("menu")}
            />
          </Panel>
        </group>
      );
    }
    return (
      <group>
        <Text3D
          position={[LOUSA_X, 0.12, LOUSA_Z]}
          size={0.1}
          color={venceu ? "#bfe8cf" : empate ? "#f2f5ec" : "#ffc9bd"}
        >
          {venceu ? "Você venceu!" : empate ? "Empate!" : "O bot venceu"}
        </Text3D>
        <Text3D position={[LOUSA_X, -0.02, LOUSA_Z]} size={0.055} color="#f2f5ec">
          {`Você ${pontosJogador} × ${pontosBot} ${BOTS[dificuldade].nome.split(" (")[0]}`}
        </Text3D>
        <BotaoLousa
          texto="Jogar de novo"
          position={[LOUSA_X, -0.17, LOUSA_Z]}
          cor="#bfe8cf"
          size={0.065}
          width={1.1}
          onClick={() => comecar(dificuldade)}
        />
        <BotaoLousa
          texto="Trocar dificuldade"
          position={[LOUSA_X, -0.31, LOUSA_Z]}
          size={0.055}
          width={1.1}
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
      {/* Escola: órgão ao lado da lousa. Hospital: flutuando à esquerda do
          painel, na altura do peito (1,5m do chão). */}
      <group
        position={hosp ? [-1.05, 0.2, -0.5] : [-0.78, -0.15, -0.95]}
        scale={hosp ? 0.6 : 0.36}
      >
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

      {/* Placar, cronômetro, pergunta, alternativas e feedback */}
      {hosp ? (
        <group position={HOSP_UI} rotation={HOSP_ROT}>
          <Panel width={1.7} height={1.45} position={[0, -0.05, 0]}>
            <Text3D position={[-0.55, 0.55, 0.01]} size={0.06} color="#bfe8cf">
              {`Você: ${pontosJogador}`}
            </Text3D>
            {fase === "rodada" && (
              <Text3D
                position={[0, 0.55, 0.01]}
                size={0.075}
                color={tempoRestante <= 5 ? "#ffb0a0" : "#7de8ff"}
              >
                {String(tempoRestante)}
              </Text3D>
            )}
            <Text3D position={[0.5, 0.55, 0.01]} size={0.05} color="#e8e3c8">
              {`Rodada ${indice + 1}/${TOTAL_RODADAS} · vale ${rodada.pontos}`}
            </Text3D>
            {fase === "rodada" ? (
              <>
                <Text3D position={[0, 0.34, 0.01]} size={0.085} maxWidth={1.5}>
                  {rodada.tipo === "orgao"
                    ? "Qual órgão é este?"
                    : "Qual estrutura está marcada em amarelo?"}
                </Text3D>
                {rodada.opcoes.map((opcao, i) => (
                  <Button3D
                    key={opcao}
                    label={opcao}
                    width={1.55}
                    height={0.18}
                    position={[0, 0.1 - i * 0.22, 0.01]}
                    color={erroJogador || errados.includes(opcao) ? "#5c6b7a" : ARENA_COLORS.primary}
                    onClick={() => responder(opcao)}
                  />
                ))}
                {erroJogador && (
                  <Text3D position={[0, -0.7, 0.01]} size={0.05} color="#ffb0a0">
                    Errado!
                  </Text3D>
                )}
              </>
            ) : (
              <Text3D position={[0, -0.1, 0.01]} size={0.09} maxWidth={1.5}>
                {feedback}
              </Text3D>
            )}
          </Panel>
        </group>
      ) : (
        <>
          <Text3D position={[LOUSA_X - 0.38, 0.2, LOUSA_Z]} size={0.04} color="#bfe8cf">
            {`Você: ${pontosJogador}`}
          </Text3D>
          <Text3D position={[LOUSA_X + 0.28, 0.2, LOUSA_Z]} size={0.036} color="#e8e3c8">
            {`Rodada ${indice + 1}/${TOTAL_RODADAS} · vale ${rodada.pontos}`}
          </Text3D>
          {fase === "rodada" && (
            <>
              {/* Pergunta em giz na lousa */}
              <Text3D
                position={[LOUSA_X, 0.08, LOUSA_Z]}
                size={0.068}
                maxWidth={1.08}
                color="#f2f5ec"
              >
                {rodada.tipo === "orgao"
                  ? "Qual órgão é este?"
                  : "Qual estrutura está marcada em amarelo?"}
              </Text3D>
              {/* Cronômetro no canto da lousa */}
              <Text3D
                position={[LOUSA_X - 0.47, 0.06, LOUSA_Z]}
                size={0.06}
                color={tempoRestante <= 5 ? "#ffb0a0" : "#dfe8db"}
              >
                {String(tempoRestante)}
              </Text3D>
              {/* Alternativas em giz */}
              {rodada.opcoes.map((opcao, i) => (
                <BotaoLousa
                  key={opcao}
                  texto={`${["A", "B", "C", "D"][i]})  ${opcao}`}
                  position={[LOUSA_X, -0.09 - i * 0.1, LOUSA_Z]}
                  cor={erroJogador || errados.includes(opcao) ? "#8fae94" : "#f8fbef"}
                  size={0.052}
                  width={1.1}
                  onClick={() => responder(opcao)}
                />
              ))}
              {erroJogador && (
                <Text3D
                  position={[LOUSA_X - 0.47, -0.03, LOUSA_Z]}
                  size={0.035}
                  color="#ffb0a0"
                >
                  Errado!
                </Text3D>
              )}
            </>
          )}
          {fase === "feedback" && (
            <Text3D
              position={[LOUSA_X, -0.1, LOUSA_Z]}
              size={0.072}
              maxWidth={1.08}
              color="#f2f5ec"
            >
              {feedback}
            </Text3D>
          )}
        </>
      )}

      {/* Telão LED do hospital espelha o cronômetro (ambiente) */}
      {hosp && fase === "rodada" && (
        <Text3D
          position={HOSP_LED}
          size={0.34}
          color={tempoRestante <= 5 ? "#ffb0a0" : "#7de8ff"}
        >
          {String(tempoRestante)}
        </Text3D>
      )}

      {hosp ? (
        <Oponente
          humor={humorBot}
          nome={BOTS[dificuldade].nome.split(" (")[0]}
          pontos={pontosBot}
          position={[-0.45, -1.3, -1.9]}
          // O corpo é modelado de frente para +z; o jogador está em +z.
          rotationY={0}
        />
      ) : (
        <Oponente
          humor={humorBot}
          nome={BOTS[dificuldade].nome.split(" (")[0]}
          pontos={pontosBot}
          position={[-0.81, -1.54, 1.07]}
          rotationY={Math.PI}
          sentado
        />
      )}
    </group>
  );
}

useGLTF.preload(LARINGE, "/draco/");
for (const organ of ORGAOS_DUELO) useGLTF.preload(organ.modelPath, "/draco/");
