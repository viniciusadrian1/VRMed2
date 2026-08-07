"use client";

import { Suspense, useCallback, useEffect, useRef, useState } from "react";
import { useFrame } from "@react-three/fiber";
import { useXR, useXRStore } from "@react-three/xr";
import {
  playEnd,
  playHit,
  playMiss,
  playStart,
  playTick,
} from "@/lib/arena-audio";
import { ErrorBoundary } from "@/components/ErrorBoundary";
import { ArenaModel } from "./ArenaModel";
import { ARENA_COLORS, Button3D, Panel, Text3D } from "./ui3d";
import type { ArenaAttempt, ArenaPhase, ArenaStructure } from "./types";

/** Duração da partida, em segundos. Curta o bastante para a fila andar. */
const ROUND_SECONDS = 60;
/** Segundos sem acerto até a dica aparecer (o público é leigo em anatomia). */
const HINT_AFTER = 6;
/** Penalidade por erro, em segundos. */
const MISS_PENALTY = 2;
/** Volta sozinho ao modo ocioso depois deste tempo na tela de resultado. */
const RESULT_TIMEOUT = 20;
/** Modelo principal do jogo (18k triângulos, ~20 estruturas nomeadas). */
const MODEL_PATH = "/models/organs/larynx.glb";

/**
 * Vigia de entrada: se após alguns segundos de sessão nenhum controle ou mão
 * foi detectado, avisa DENTRO do VR. A falha de carregamento de perfil de
 * controle é silenciosa (console.error que ninguém vê no headset) — sem este
 * aviso, o jogador fica parado num mundo bonito em que nada responde.
 */
function VigiaDeControles() {
  const inputs = useXR((state) => state.inputSourceStates.length);
  const [alerta, setAlerta] = useState(false);
  const semInput = useRef(0);

  useFrame((_, delta) => {
    if (inputs > 0) {
      semInput.current = 0;
      if (alerta) setAlerta(false);
      return;
    }
    semInput.current += Math.min(delta, 1 / 30);
    if (!alerta && semInput.current > 5) setAlerta(true);
  });

  if (!alerta) return null;
  return (
    <Text3D
      position={[0, 0.85, 1.0]}
      size={0.09}
      color={ARENA_COLORS.danger}
      maxWidth={2.2}
    >
      Controles não detectados — segure os controles e aperte qualquer botão
    </Text3D>
  );
}

/** Mostrado enquanto o modelo baixa e decodifica, no lugar dele. */
function CarregandoModelo() {
  return (
    <group position={[0, 0.2, 0]}>
      <Text3D size={0.13} color={ARENA_COLORS.muted}>
        Carregando o modelo…
      </Text3D>
    </group>
  );
}

/** Sorteia o próximo alvo, evitando repetir o atual. */
function pickTarget(
  structures: ArenaStructure[],
  current: ArenaStructure | null,
): ArenaStructure | null {
  if (structures.length === 0) return null;
  const pool =
    structures.length > 1 && current
      ? structures.filter((s) => s.label !== current.label)
      : structures;
  return pool[Math.floor(Math.random() * pool.length)] ?? null;
}

/**
 * Partida da Arena: sorteia alvos, conta o tempo, pontua e mostra o resultado.
 *
 * O cronômetro corre em `useFrame` acumulando `delta` num ref e só empurra
 * para o React quando o segundo inteiro muda — a 90 Hz, atualizar estado a
 * cada quadro derrubaria o headset sozinho.
 */
export function ArenaGame() {
  const store = useXRStore();
  // Só para decidir o que renderizar — a UI 3D existe apenas dentro do VR
  // (fora dela, a página DOM cuida da apresentação).
  const inSession = useXR((state) => Boolean(state.session));

  const [phase, setPhase] = useState<ArenaPhase>("ocioso");
  const [structures, setStructures] = useState<ArenaStructure[]>([]);
  const [target, setTarget] = useState<ArenaStructure | null>(null);
  const [seconds, setSeconds] = useState(ROUND_SECONDS);
  const [countdown, setCountdown] = useState(3);
  const [score, setScore] = useState(0);
  const [combo, setCombo] = useState(0);
  const [hits, setHits] = useState(0);
  const [showHint, setShowHint] = useState(false);
  const [attempts, setAttempts] = useState<ArenaAttempt[]>([]);
  const [best, setBest] = useState(0);
  const [feedback, setFeedback] = useState<"acerto" | "erro" | null>(null);
  /** Incrementa a cada rodada; devolve o modelo à pose original. */
  const [roundId, setRoundId] = useState(0);

  // Tempo em ponto flutuante; o estado guarda só o segundo exibido.
  const remaining = useRef(ROUND_SECONDS);
  const sinceTarget = useRef(0);
  const sinceResult = useRef(0);
  const countdownTimer = useRef(0);
  const feedbackTimer = useRef(0);

  const [modelReady, setModelReady] = useState(false);

  const handleStructures = useCallback((list: ArenaStructure[]) => {
    setStructures(list);
    setModelReady(true);
    // Já deixa um alvo pronto: derivar aqui evita um efeito extra e o
    // render em cascata que ele causaria.
    setTarget(pickTarget(list, null));
  }, []);

  const startRound = useCallback(() => {
    if (structures.length === 0) return;
    remaining.current = ROUND_SECONDS;
    countdownTimer.current = 0;
    setSeconds(ROUND_SECONDS);
    setCountdown(3);
    setScore(0);
    setCombo(0);
    setHits(0);
    setAttempts([]);
    // Sorteia o PRIMEIRO alvo da rodada aqui. A versão anterior fazia
    // setTarget(null) — e nada voltava a sortear: a partida começava com
    // "ENCONTRE ..." sem nome e todo clique era ignorado (handleHit exige
    // alvo). Era o jogo inteiro nascendo morto.
    setTarget(pickTarget(structures, null));
    setShowHint(false);
    setRoundId((id) => id + 1);
    setPhase("contagem");
    playTick();
  }, [structures]);

  const endRound = useCallback(() => {
    setPhase("resultado");
    setShowHint(false);
    sinceResult.current = 0;
    setBest((previous) => Math.max(previous, score));
    playEnd();
  }, [score]);

  /** Clique numa estrutura durante a partida. */
  const handleHit = useCallback(
    (label: string) => {
      if (phase !== "jogando" || !target) return;

      const acertou = label === target.label;
      setAttempts((list) => [...list, { label: target.label, acertou }]);
      feedbackTimer.current = 0;
      setFeedback(acertou ? "acerto" : "erro");

      if (acertou) {
        const nextCombo = combo + 1;
        setCombo(nextCombo);
        setScore((value) => value + 100 * nextCombo);
        setHits((value) => value + 1);
        playHit(nextCombo);
        setTarget((current) => pickTarget(structures, current));
        sinceTarget.current = 0;
        setShowHint(false);
      } else {
        setCombo(0);
        remaining.current = Math.max(0, remaining.current - MISS_PENALTY);
        playMiss();
      }
    },
    [phase, target, combo, structures],
  );

  /**
   * Sair do VR devolve tudo ao ocioso — a próxima pessoa da fila nunca herda
   * a partida da anterior.
   *
   * Assina a store do XR em vez de reagir a um estado derivado: a sessão é um
   * sistema externo, e atualizar o estado dentro do callback dela evita a
   * cascata de renders que um efeito sobre `useXR(...)` provocaria.
   */
  useEffect(
    () =>
      store.subscribe((state) => {
        if (!state.session) {
          setPhase("ocioso");
          setShowHint(false);
        }
      }),
    [store],
  );

  useFrame((_, delta) => {
    if (feedback) {
      feedbackTimer.current += delta;
      if (feedbackTimer.current > 0.35) setFeedback(null);
    }

    if (phase === "contagem") {
      countdownTimer.current += delta;
      const step = 3 - Math.floor(countdownTimer.current);
      if (step !== countdown) {
        if (step > 0) playTick();
        setCountdown(step);
      }
      if (countdownTimer.current >= 3) {
        sinceTarget.current = 0;
        setPhase("jogando");
        playStart();
      }
      return;
    }

    if (phase === "jogando") {
      remaining.current -= delta;
      const shown = Math.max(0, Math.ceil(remaining.current));
      if (shown !== seconds) setSeconds(shown);

      sinceTarget.current += delta;
      if (!showHint && sinceTarget.current > HINT_AFTER) setShowHint(true);

      if (remaining.current <= 0) endRound();
      return;
    }

    if (phase === "resultado") {
      sinceResult.current += delta;
      if (sinceResult.current > RESULT_TIMEOUT) setPhase("ocioso");
    }
  });

  const erros = attempts.filter((a) => !a.acertou).map((a) => a.label);
  const errosUnicos = [...new Set(erros)].slice(0, 3);

  return (
    <>
      {/*
        O `useGLTF` do modelo SUSPENDE enquanto carrega. Sem esta fronteira,
        a suspensão sobe e leva junto toda a interface — painel, botão e alvo
        desaparecem enquanto o modelo baixa, e somem para sempre se ele falhar.
        Isolando aqui, a interface aparece na hora e o modelo chega depois.
      */}
      <ErrorBoundary
        fallback={
          <Text3D position={[0, 0.2, 0]} size={0.11} color={ARENA_COLORS.danger}>
            Falha ao carregar o modelo — recarregue a página
          </Text3D>
        }
      >
        <Suspense fallback={<CarregandoModelo />}>
          <ArenaModel
            path={MODEL_PATH}
            scale={1.3}
            roundId={roundId}
            onStructuresReady={handleStructures}
            onHit={handleHit}
            hintPosition={showHint && target ? target.local : null}
            interactive={phase === "jogando"}
            spinning={phase === "ocioso"}
          />
        </Suspense>
      </ErrorBoundary>

      {inSession && <VigiaDeControles />}

      {/* ---------------- Ocioso: convite para começar ---------------- */}
      {inSession && phase === "ocioso" && (
        <group position={[0, 0.35, 1.4]}>
          <Panel width={2.2} height={0.95}>
            <Text3D position={[0, 0.28, 0.01]} size={0.16}>
              VRmed · Arena
            </Text3D>
            <Text3D
              position={[0, 0.04, 0.01]}
              size={0.085}
              color={ARENA_COLORS.muted}
              maxWidth={1.9}
            >
              Encontre as estruturas da laringe em 60 segundos
            </Text3D>
            {/* Instrução explícita: quem nunca usou VR não sabe que o gatilho
                fica embaixo do dedo indicador, e tenta apertar o grip. */}
            <Text3D
              position={[0, -0.2, 0.01]}
              size={0.065}
              color={ARENA_COLORS.primary}
              maxWidth={2.0}
            >
              Gatilho: selecionar · Analógico: girar e aproximar o órgão
            </Text3D>
            {/* Diagnóstico visível: quantos alvos o modelo rendeu. Se o
                carregamento falhar em produzir estruturas, o problema fica
                LEGÍVEL dentro do headset em vez de virar um botão morto. */}
            <Text3D
              position={[0, -0.36, 0.01]}
              size={0.05}
              color={
                modelReady && structures.length === 0
                  ? ARENA_COLORS.danger
                  : ARENA_COLORS.muted
              }
            >
              {!modelReady
                ? "Preparando o modelo…"
                : structures.length === 0
                  ? "ERRO: nenhuma estrutura nomeada no modelo"
                  : `${structures.length} estruturas prontas`}
            </Text3D>
          </Panel>
          <Button3D
            label={structures.length > 0 ? "Começar" : "Carregando…"}
            position={[0, -0.45, 0.02]}
            width={1.4}
            height={0.36}
            onClick={startRound}
          />
        </group>
      )}

      {/* ---------------- Contagem regressiva ---------------- */}
      {phase === "contagem" && (
        <Text3D position={[0, 0.9, 1.0]} size={0.55}>
          {countdown > 0 ? String(countdown) : "JÁ!"}
        </Text3D>
      )}

      {/*
        Painel da partida — na LINHA DO OLHAR, não no teto.
        A cabeça do jogador fica a ~0,35 de altura no mundo, olhando para o
        modelo; a versão anterior (y=1,55, atrás) exigia olhar para cima, e
        em VR ninguém olha para cima sem motivo — o alvo "não aparecia".
        Aqui o painel surge no MESMO lugar da contagem regressiva, onde o
        olhar já está.
      */}
      {phase === "jogando" && (
        <group position={[0, 1.02, 0.9]}>
          <Panel width={2.1} height={0.5}>
            <Text3D
              position={[0, 0.14, 0.01]}
              size={0.055}
              color={ARENA_COLORS.muted}
            >
              ENCONTRE
            </Text3D>
            <Text3D
              position={[0, -0.04, 0.01]}
              size={0.12}
              maxWidth={1.9}
              color={
                feedback === "acerto"
                  ? ARENA_COLORS.success
                  : feedback === "erro"
                    ? ARENA_COLORS.danger
                    : ARENA_COLORS.text
              }
            >
              {target?.label ?? "..."}
            </Text3D>
          </Panel>

          {/* Tempo à esquerda, pontos à direita — leitura periférica. */}
          <Panel width={0.42} height={0.34} position={[-1.35, -0.05, 0]}>
            <Text3D
              position={[0, 0.09, 0.01]}
              size={0.045}
              color={ARENA_COLORS.muted}
            >
              TEMPO
            </Text3D>
            <Text3D
              position={[0, -0.05, 0.01]}
              size={0.15}
              color={seconds <= 10 ? ARENA_COLORS.danger : ARENA_COLORS.text}
            >
              {String(seconds)}
            </Text3D>
          </Panel>
          <Panel width={0.52} height={0.34} position={[1.35, -0.05, 0]}>
            <Text3D
              position={[0, 0.09, 0.01]}
              size={0.045}
              color={ARENA_COLORS.muted}
            >
              PONTOS
            </Text3D>
            <Text3D position={[0, -0.05, 0.01]} size={0.13}>
              {String(score)}
            </Text3D>
            {combo > 1 && (
              <Text3D
                position={[0, -0.22, 0.01]}
                size={0.06}
                color={ARENA_COLORS.success}
              >
                {`combo x${combo}`}
              </Text3D>
            )}
          </Panel>
        </group>
      )}

      {/* ---------------- Resultado ---------------- */}
      {phase === "resultado" && (
        <group position={[0, 0.55, 1.2]}>
          <Panel width={2.4} height={1.5}>
            <Text3D position={[0, 0.55, 0.01]} size={0.13}>
              Fim de jogo
            </Text3D>
            <Text3D position={[0, 0.28, 0.01]} size={0.3}>
              {String(score)}
            </Text3D>
            <Text3D
              position={[0, 0.02, 0.01]}
              size={0.08}
              color={ARENA_COLORS.muted}
            >
              {`${hits} estruturas · recorde ${Math.max(best, score)}`}
            </Text3D>
            {errosUnicos.length > 0 && (
              <Text3D
                position={[0, -0.3, 0.01]}
                size={0.07}
                color={ARENA_COLORS.muted}
                maxWidth={2.1}
              >
                {`Revisar: ${errosUnicos.join(", ")}`}
              </Text3D>
            )}
          </Panel>
          <Button3D
            label="Jogar de novo"
            position={[0, -0.95, 0.02]}
            onClick={startRound}
          />
        </group>
      )}
    </>
  );
}
