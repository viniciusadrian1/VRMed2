"use client";

import {
  Suspense,
  useEffect,
  useLayoutEffect,
  useMemo,
  useRef,
  useState,
  type RefObject,
} from "react";
import { useFrame, useThree } from "@react-three/fiber";
import { useXR, useXRInputSourceState } from "@react-three/xr";
import { useGLTF } from "@react-three/drei";
import * as THREE from "three";
import { ErrorBoundary } from "@/components/ErrorBoundary";
import {
  Text3D,
  Panel,
  Button3D,
  BarraTempo,
  Entrada,
  Floater,
  ARENA_COLORS,
} from "@/components/arena/ui3d";
import {
  detectStructures,
  normalizeContent,
  prepareModel,
} from "@/lib/model-utils";
import type { StructurePoint } from "@/types";
import { ORGANS } from "@/lib/organs";
import {
  desbloquearAudio,
  playClique,
  playEnd,
  playEnviado,
  playHit,
  playHover,
  playMiss,
  playOponentePontuou,
  playStart,
  playTempoEsgotado,
  playTensao,
  playTick,
  playTransicao,
} from "@/lib/arena-audio";
import { pulsar } from "@/lib/xr-haptica";
import { Oponente, type HumorOponente } from "./Oponente";
import { PITCH_SPEED, SPIN_SPEED, shapedAxis } from "@/components/viewer/XRManipulation";
import {
  CONTAGEM_MS,
  RODADA_MS,
  TOTAL_RODADAS,
  type RodadaOnline,
  type VisaoSala,
} from "@/lib/duelo-salas";
import type { DueloOnline } from "./useDueloOnline";

/**
 * Duelo 1x1 (Modo 2 do plano multi-modo): contra BOT ou contra outra pessoa.
 *
 * 8 rodadas alternando: órgão inteiro (100 pts) e estrutura da laringe
 * marcada (200 pts). Quem responde certo primeiro pontua.
 *
 *  - Contra bot, tudo roda aqui: o bot "responde" após um atraso sorteado.
 *  - Online, cada pessoa no seu óculos: o servidor (`app/api/duelo`) é o
 *    árbitro de relógio, placar e acertos, e esta tela só espelha a sala nos
 *    mesmos estados que a partida contra bot usa. O pareamento é por um código
 *    de 4 dígitos que um cria e o outro digita num teclado 3D.
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

// Mesmas regras nos dois modos: vêm das salas online.
const TEMPO_RODADA = RODADA_MS / 1000;

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

/**
 * Papéis de cor do duelo — os mesmos nos dois ambientes.
 *
 * Antes eram 11 hexadecimais soltos pelo arquivo (três brancos diferentes na
 * mesma tela, "errado" em quatro tons). Aqui cada cor tem um significado, e o
 * jogador aprende sem ler: verde-água é sempre você, coral é sempre o
 * adversário, âmbar é sempre ponto (a mesma cor do marcador da estrutura).
 */
const CORES = {
  /** Você — placar, pontos ganhos, resposta certa. */
  meu: "#4fd1a5",
  /** O adversário. NÃO é vermelho de erro: ele é um oponente, não um defeito. */
  dele: "#ff6b57",
  tempo: "#7dd3fc",
  alerta: "#ffb020",
  /** Ponto: o mesmo amarelo do marcador da estrutura. */
  ouro: "#ffd166",
  giz: "#f2f5ec",
  gizFraco: "#cfe0cd",
  apagado: "#5c6b7a",
} as const;

/** Quantas rodadas cabem na fita do placar (uma marca por rodada). */
const MARCA = 0.035;

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

/**
 * "sala": criou a sala e espera o amigo. "codigo": digitando o código.
 * "encerrada": o adversário saiu ou a conexão com a partida caiu.
 */
type Fase =
  | "menu"
  | "contagem"
  | "rodada"
  | "feedback"
  | "fim"
  | "sala"
  | "codigo"
  | "encerrada";

/**
 * Mesma forma nos dois modos: online, quem cria a sala sorteia as rodadas e o
 * servidor as repassa ao outro. `alvo` é a resposta correta como aparece nos
 * botões; `modelo` só no tipo "orgao"; `marcador` só no tipo "estrutura", no
 * espaço local do spinner.
 */
type Rodada = RodadaOnline;

const TECLAS = ["1", "2", "3", "4", "5", "6", "7", "8", "9", "Apagar", "0", "Voltar"];

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
  // Sem repetidos: a laringe tem malhas diferentes com o mesmo rótulo, e duas
  // alternativas iguais na mesma pergunta não têm resposta certa.
  const nomesEstruturas = [...new Set(estruturas.map((p) => p.label))];
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

/**
 * Opção clicável escrita em giz na lousa (sem pop-up): texto + plano
 * invisível para o raycast + crescimento suave no hover.
 *
 * `altura` existe porque o alvo de clique acompanhava o tamanho da fonte
 * (`size * 1.9`) e ignorava o passo entre as linhas: no teclado do código
 * online, dígitos de `size 0.075` viravam alvos de 14 cm com passo de 11 cm —
 * **as teclas se sobrepunham 3 cm**, coplanares. Com o laser tremendo a 2 m,
 * a pessoa clicava na tecla de baixo achando que clicou na de cima, e errar
 * uma alternativa custa 1,6 s de trava. Quem empilha botões passa a altura
 * do passo, e o alvo nunca invade o vizinho.
 */
function BotaoLousa({
  texto,
  position,
  onClick,
  cor = CORES.giz,
  size = 0.14,
  width = 2.3,
  altura,
  destaque = null,
  desabilitado = false,
}: {
  texto: string;
  position: [number, number, number];
  onClick: () => void;
  cor?: string;
  size?: number;
  width?: number;
  /** Altura do alvo de clique (padrão: o tamanho do texto). */
  altura?: number;
  /** Revelação da resposta: verde na certa, coral na que a pessoa errou. */
  destaque?: "certo" | "errado" | null;
  /** Fora da rodada as alternativas continuam na tela, mas não respondem. */
  desabilitado?: boolean;
}) {
  const grupo = useRef<THREE.Group>(null);
  const hovered = useRef(false);
  const escala = useRef(1);
  const risco = useRef<THREE.Mesh>(null);
  const esquerdo = useXRInputSourceState("controller", "left");
  const direito = useXRInputSourceState("controller", "right");
  useFrame((_, delta) => {
    if (!grupo.current) return;
    const ativo = hovered.current && !desabilitado;
    const alvo = destaque === "certo" ? 1.06 : ativo ? 1.09 : 1;
    escala.current += (alvo - escala.current) * Math.min(1, delta * 12);
    grupo.current.scale.setScalar(escala.current);
    // Sublinhado de giz: a 2 m, crescer 9% quase não se vê.
    if (risco.current) risco.current.visible = ativo;
  });
  const corFinal =
    destaque === "certo" ? CORES.meu : destaque === "errado" ? CORES.dele : cor;
  return (
    <group
      ref={grupo}
      position={position}
      onClick={(e) => {
        e.stopPropagation();
        if (desabilitado) return;
        playClique();
        pulsar(direito?.inputSource ?? esquerdo?.inputSource, 0.4, 35);
        onClick();
      }}
      onPointerOver={(e) => {
        e.stopPropagation();
        if (desabilitado || hovered.current) return;
        hovered.current = true;
        playHover();
        pulsar(direito?.inputSource ?? esquerdo?.inputSource, 0.15, 15);
      }}
      onPointerOut={() => {
        hovered.current = false;
      }}
    >
      {/* Panel/Text3D têm raycast desligado — o plano invisível recebe o clique */}
      <mesh>
        <planeGeometry args={[width, altura ?? size * 1.9]} />
        <meshBasicMaterial transparent opacity={0} depthWrite={false} />
      </mesh>
      <Text3D size={size} color={corFinal} maxWidth={width}>
        {texto}
      </Text3D>
      <mesh ref={risco} position={[0, -size * 0.78, 0]} visible={false} raycast={() => null}>
        <planeGeometry args={[width * 0.92, 0.004]} />
        <meshBasicMaterial color={corFinal} toneMapped={false} depthTest={false} transparent opacity={0.8} />
      </mesh>
    </group>
  );
}

/**
 * Placar do duelo: VOCÊ 300 × 200 NOME, com uma fita de uma marca por rodada.
 *
 * Antes os meus pontos eram um texto pequeno num canto e os do adversário
 * flutuavam sobre o avatar — na escola, 1,7 m ATRÁS de mim. Para saber quem
 * estava ganhando era preciso virar a cabeça e fazer a conta. A string
 * "Você 500 × 300 Adversário" só existia na tela de fim.
 */
function Placar({
  meus,
  dele,
  nomeDele,
  historico,
  escala = 1,
  position,
}: {
  meus: number;
  dele: number;
  nomeDele: string;
  /** Uma entrada por rodada já resolvida: quem pontuou (ou ninguém). */
  historico: ("eu" | "outro" | null)[];
  escala?: number;
  position?: [number, number, number];
}) {
  const s = escala;
  return (
    <group position={position}>
      <Text3D position={[-0.42 * s, 0, 0.002]} size={0.042 * s} color={CORES.meu}>
        VOCÊ
      </Text3D>
      <Text3D position={[-0.17 * s, 0, 0.002]} size={0.082 * s} color={CORES.meu}>
        {String(meus)}
      </Text3D>
      <Text3D position={[0, 0, 0.002]} size={0.05 * s} color={CORES.gizFraco}>
        ×
      </Text3D>
      <Text3D position={[0.17 * s, 0, 0.002]} size={0.082 * s} color={CORES.dele}>
        {String(dele)}
      </Text3D>
      <Text3D
        position={[0.42 * s, 0, 0.002]}
        size={0.042 * s}
        color={CORES.dele}
        maxWidth={0.42 * s}
      >
        {nomeDele.toUpperCase()}
      </Text3D>
      {/* Fita das rodadas: o andamento da partida lido de relance, sem texto. */}
      {Array.from({ length: TOTAL_RODADAS }, (_, i) => (
        <mesh
          key={i}
          position={[(i - (TOTAL_RODADAS - 1) / 2) * 0.05 * s, -0.062 * s, 0.002]}
          // O Panel desenha em 998 com depthTest desligado: sem ordem própria,
          // a fita ficava pintada POR BAIXO do painel do hospital.
          renderOrder={999}
          raycast={() => null}
        >
          <planeGeometry args={[MARCA * s, MARCA * s * 0.55]} />
          <meshBasicMaterial
            color={
              historico[i] === "eu"
                ? CORES.meu
                : historico[i] === "outro"
                  ? CORES.dele
                  : historico.length === i
                    ? CORES.gizFraco
                    : CORES.apagado
            }
            toneMapped={false}
            depthTest={false}
            transparent
            opacity={historico[i] || historico.length === i ? 0.95 : 0.35}
          />
        </mesh>
      ))}
    </group>
  );
}

/** Dígito da contagem regressiva, com um pulso a cada troca. */
function DigitoContagem({
  valor,
  size,
  color = CORES.tempo,
  position,
}: {
  valor: number;
  size: number;
  color?: string;
  position?: [number, number, number];
}) {
  const grupo = useRef<THREE.Group>(null);
  const visto = useRef(valor);
  const t = useRef(0);
  useFrame((_, delta) => {
    if (!grupo.current) return;
    if (visto.current !== valor) {
      visto.current = valor;
      t.current = 0;
    }
    t.current += delta;
    // Decaimento exponencial: cresce 45% e volta em ~0,3 s. Sem piscar.
    grupo.current.scale.setScalar(1 + 0.45 * Math.exp(-9 * t.current));
  });
  return (
    <group ref={grupo} position={position}>
      <Text3D size={size} color={color}>
        {String(valor)}
      </Text3D>
    </group>
  );
}

/**
 * Telas do online (sala criada, partida encerrada). Mesma estrutura nos dois
 * ambientes: `linhas` são textos de cima para baixo e `botoes` os alvos
 * clicáveis. Na escola vai em giz na lousa; no hospital, no painel à direita.
 */
function TelaOnline({
  hosp,
  linhas,
  botoes,
}: {
  hosp: boolean;
  linhas: { texto: string; tamanho?: number; cor?: string }[];
  botoes: { texto: string; onClick: () => void }[];
}) {
  return hosp ? (
    <group position={HOSP_UI} rotation={HOSP_ROT}>
      <Panel width={1.7} height={1.4} />
      {linhas.map((l, i) => (
        <Text3D
          key={i}
          position={[0, 0.5 - i * 0.2, 0.01]}
          size={(l.tamanho ?? 1) * 0.07}
          color={l.cor}
          maxWidth={1.5}
        >
          {l.texto}
        </Text3D>
      ))}
      {botoes.map((b, i) => (
        <Button3D
          key={b.texto}
          label={b.texto}
          width={1.2}
          height={0.2}
          position={[0, -0.3 - i * 0.26, 0.01]}
          onClick={b.onClick}
        />
      ))}
    </group>
  ) : (
    <group>
      {linhas.map((l, i) => (
        <Text3D
          key={i}
          position={[LOUSA_X, 0.17 - i * 0.1, LOUSA_Z]}
          size={(l.tamanho ?? 1) * 0.042}
          color={l.cor ?? "#f2f5ec"}
          maxWidth={1.05}
        >
          {l.texto}
        </Text3D>
      ))}
      {botoes.map((b, i) => (
        <BotaoLousa
          key={b.texto}
          texto={b.texto}
          position={[LOUSA_X, -0.3 - i * 0.1, LOUSA_Z]}
          size={0.05}
          width={0.8}
          onClick={b.onClick}
        />
      ))}
    </group>
  );
}

/** Velocidade do giro automático (rad/s): uma volta a cada ~18 s. */
const GIRO_AUTOMATICO = 0.35;
/**
 * Depois de soltar o analógico, quanto tempo o giro automático espera para
 * voltar (s). Sem a pausa ele retomaria no mesmo instante e tiraria de vista a
 * estrutura que a pessoa acabou de trazer para a frente.
 */
const PAUSA_DO_GIRO_AUTOMATICO = 1.5;
/** Limite do tombamento (rad, ~69°): além disso o órgão vira de cabeça para baixo. */
const TOMBO_MAXIMO = 1.2;

/**
 * Modelo da rodada girando devagar; estrutura-alvo ganha um marcador pulsante.
 *
 * O analógico gira o órgão, igual ao visualizador. Motivo: nas rodadas da
 * laringe o marcador pode estar do lado de trás, e o giro automático leva até
 * ~9 s para trazê-lo — metade da rodada esperando o modelo virar. Com o
 * analógico a pessoa traz a estrutura para a frente na hora:
 *
 *  - qualquer analógico ⇄ gira o órgão como um torno;
 *  - qualquer analógico ↕ tomba o órgão para mostrar o topo ou a base.
 *
 * Enquanto o analógico está em uso o giro automático pausa. No computador,
 * sem controle, nada muda.
 */
function ModeloRodada({
  rodada,
  prontoRef,
  revelado = false,
}: {
  rodada: Rodada;
  /** Vira true quando o modelo desta rodada aparece (o relógio do bot espera). */
  prontoRef: RefObject<boolean>;
  /**
   * Rodada resolvida: o giro para por um instante e o marcador cresce — o
   * "hit stop" dos jogos de ação, que dá peso ao acerto. Congela o MODELO,
   * nunca a câmera: parar o mundo em VR embrulha o estômago.
   */
  revelado?: boolean;
}) {
  const caminho = rodada.tipo === "orgao" ? rodada.modelo! : LARINGE;
  const gltf = useGLTF(caminho, "/draco/");
  const scene = useMemo(() => gltf.scene.clone(true), [gltf.scene]);
  // Três grupos aninhados (padrão do ArenaModel): o de fora carrega a escala
  // de projeto, o do meio gira, e o de dentro recebe normalizeContent — que
  // sobrescreve scale/position do grupo em que roda. Num grupo só, a
  // normalização engolia o scale={0.85} e a rotação orbitava o pivô cru do
  // GLB em vez do centro do modelo.
  const spinner = useRef<THREE.Group>(null);
  /**
   * Tombamento fica num grupo POR FORA do giro. Assim o giro continua sendo um
   * torno em volta do eixo do próprio órgão, e o tombo acontece no eixo da sala
   * — empurrar para a frente sempre afasta o topo, qualquer que seja o lado
   * virado para a pessoa. No mesmo grupo, depois de meia volta o comando
   * inverteria.
   */
  const tombo = useRef<THREE.Group>(null);
  const content = useRef<THREE.Group>(null);
  const marcador = useRef<THREE.Mesh>(null);
  const esquerdo = useXRInputSourceState("controller", "left");
  const direito = useXRInputSourceState("controller", "right");
  /** Instante do último uso do analógico, para pausar o giro automático. */
  const ultimoToque = useRef(-Infinity);

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
    if (tombo.current) tombo.current.rotation.x = 0;
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
    // Só roda depois que o GLB chegou (se ainda baixa, o Suspense segura).
    prontoRef.current = true;
  }, [scene, rodada, prontoRef]);

  useFrame((state, delta) => {
    // Mesmo teto de passo do visualizador: ao recolocar o headset, o primeiro
    // delta vem com segundos acumulados e o órgão daria voltas sozinho.
    const dt = Math.min(delta, 1 / 30);
    const agora = state.clock.elapsedTime;

    // Por analógico vale só o eixo DOMINANTE, como no visualizador: ninguém
    // empurra perfeitamente para o lado, e o resto de "frente" tombaria o
    // órgão sem querer.
    let giro = 0;
    let inclinacao = 0;
    for (const lado of [direito, esquerdo]) {
      const pad = lado?.gamepad?.["xr-standard-thumbstick"];
      const x = pad?.xAxis ?? 0;
      const y = pad?.yAxis ?? 0;
      if (Math.abs(x) >= Math.abs(y)) {
        const g = shapedAxis(x);
        if (Math.abs(g) > Math.abs(giro)) giro = g;
      } else {
        const t = shapedAxis(y);
        if (Math.abs(t) > Math.abs(inclinacao)) inclinacao = t;
      }
    }

    if (revelado) {
      // Marcador cresce e o giro descansa enquanto a resposta é revelada.
      if (marcador.current) {
        const s = marcador.current.scale.x;
        marcador.current.scale.setScalar(s + (1.6 - s) * Math.min(1, dt * 10));
      }
      return;
    }

    if (giro !== 0 || inclinacao !== 0) {
      ultimoToque.current = agora;
      // Mesmo sentido do visualizador: analógico para a direita traz para a
      // frente o lado que estava à direita de quem joga.
      if (spinner.current) spinner.current.rotation.y -= giro * dt * SPIN_SPEED;
      // yAxis é negativo com o analógico para a frente: somar afasta o topo.
      // O visualizador responde igual (o sinal dele foi corrigido junto).
      if (tombo.current) {
        tombo.current.rotation.x = THREE.MathUtils.clamp(
          tombo.current.rotation.x + inclinacao * dt * PITCH_SPEED,
          -TOMBO_MAXIMO,
          TOMBO_MAXIMO,
        );
      }
    } else if (
      spinner.current &&
      agora - ultimoToque.current > PAUSA_DO_GIRO_AUTOMATICO
    ) {
      spinner.current.rotation.y += dt * GIRO_AUTOMATICO;
    }

    if (marcador.current) {
      const s = 1 + 0.25 * Math.sin(state.clock.elapsedTime * 5);
      marcador.current.scale.setScalar(s);
    }
  });

  return (
    <group scale={0.85}>
      <group ref={tombo}>
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
    </group>
  );
}

export function DueloGame({
  ambiente = "escola",
  online,
}: {
  ambiente?: Ambiente;
  online: DueloOnline;
}) {
  const hosp = ambiente === "hospital";
  // Tela em pé fora do VR: ao lado da lousa/painel o modelo da rodada cai fora
  // da largura da tela, então ele sobe para cima deles. No óculos nada muda.
  const retrato = useThree((s) => s.size.width < s.size.height);
  const naSessao = useXR((s) => Boolean(s.session));
  // Vibração do controle nos momentos do jogo (acerto, erro, ponto do
  // adversário). Fora do headset não existe atuador e `pulsar` não faz nada.
  const esquerdo = useXRInputSourceState("controller", "left");
  const direito = useXRInputSourceState("controller", "right");
  // Num ref: `vibrar` também é chamada de dentro da assinatura da sala
  // online, que é criada uma vez e guardaria para sempre os controles do
  // render em que a sala foi criada — no Quest, a pessoa cria a sala no 2D e
  // só depois entra no VR, e a partida inteira ficaria sem vibração.
  const fonteRef = useRef<XRInputSource | undefined>(undefined);
  useEffect(() => {
    fonteRef.current = direito?.inputSource ?? esquerdo?.inputSource;
  }, [direito, esquerdo]);
  const vibrar = (forca: number, ms: number) => pulsar(fonteRef.current, forca, ms);
  const empilhar = retrato && !naSessao;
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
  /** Uma entrada por rodada resolvida: alimenta a fita do placar. */
  const [historico, setHistorico] = useState<("eu" | "outro" | null)[]>([]);
  /** "+200" que sobe do órgão quando eu pontuo; a chave reinicia a animação. */
  const [ganho, setGanho] = useState<{ pontos: number; chave: number } | null>(null);

  /** Acertos seguidos: sobem a nota do som do acerto (playHit). */
  const sequencia = useRef(0);
  /**
   * Retrospecto: medido NESTA partida e descartado com ela — nada é somado
   * entre partidas nem estimado. Estado (não ref) porque a tela de fim lê.
   */
  const [reacoes, setReacoes] = useState<number[]>([]);
  const [perdidas, setPerdidas] = useState<string[]>([]);
  /** Fração do tempo restante (1 → 0), lida pela barra dentro do useFrame. */
  const fracaoTempoRef = useRef(1);
  /** Espelho síncrono do histórico (a assinatura online lê num closure antigo). */
  const historicoRef = useRef<("eu" | "outro" | null)[]>([]);
  /** Reação medida no clique, para o ramo online não contar a espera do servidor. */
  const reacaoDoClique = useRef<number | null>(null);
  /**
   * Espelhos síncronos do relógio. O useFrame roda entre o setState e o
   * commit, então comparar com o estado do render anterior fazia o tique da
   * contagem e a batida de tensão saírem duas vezes no mesmo segundo.
   */
  const tempoRestanteRef = useRef(TEMPO_RODADA);
  const contagemRef = useRef(3);

  const relogio = useRef(0); // acumulador da fase atual (s)
  const travadoAte = useRef(0); // lockout após erro do jogador
  // Trava SÍNCRONA da rodada: o clique do jogador pode chegar na janela entre
  // o frame em que o bot/timeout encerrou e o commit do React (fase ainda lê
  // "rodada" no closure) — sem o ref, os dois pontuavam na mesma rodada.
  const rodadaEncerrada = useRef(false);
  const botPlano = useRef({ em: 99, acerta: false, respondeu: false });
  // Contra o bot, cronômetro e bot só andam com o modelo da rodada na tela: em
  // wifi lento o especialista pontuava antes de o órgão terminar de baixar.
  const modeloPronto = useRef(false);
  const rodada = rodadas[indice];

  /* ---- duelo online ---- */
  const [codigoDigitado, setCodigoDigitadoState] = useState("");
  // Espelho síncrono, como `faseRef`: dois toques antes do re-render liam o
  // código velho e o primeiro dígito sumia.
  const codigoRef = useRef("");
  const setCodigoDigitado = (novo: string) => {
    codigoRef.current = novo;
    setCodigoDigitadoState(novo);
  };
  /** Alternativa certa já enviada, esperando o veredito do servidor. */
  const [enviado, setEnviado] = useState<string | null>(null);
  const [outroConectado, setOutroConectado] = useState(true);
  const [revanche, setRevanche] = useState({ eu: false, outro: false });
  const [adversarioSaiu, setAdversarioSaiu] = useState(false);
  /** Última sala recebida e o instante local em que chegou. */
  const visaoRef = useRef<{ v: VisaoSala; recebidoEm: number } | null>(null);
  const partidaVista = useRef(-1);
  const indiceVisto = useRef(-1);
  const eventoVisto = useRef(-1);
  /** Quando a pergunta apareceu NESTE óculos: base do tempo de reação. */
  const inicioLocal = useRef(0);
  const emSala = online.sala !== null;
  const nomeOponente = emSala ? "Adversário" : BOTS[dificuldade].nome.split(" (")[0];

  /** Zera o que é medido por partida (placar, fita, retrospecto). */
  const zerarPartida = () => {
    setHistorico([]);
    historicoRef.current = [];
    setGanho(null);
    setReacoes([]);
    setPerdidas([]);
    sequencia.current = 0;
    reacaoDoClique.current = null;
  };

  const comecar = (nivel: Dificuldade) => {
    // O AudioContext só destrava dentro de um gesto real. Online, o primeiro
    // som da partida vem do servidor (a contagem), sem clique nenhum antes:
    // sem isto o duelo inteiro corria mudo.
    desbloquearAudio();
    setDificuldade(nivel);
    setRodadas(montarRodadas(estruturas));
    setIndice(0);
    setPontosJogador(0);
    setPontosBot(0);
    setHumorBot("idle");
    zerarPartida();
    relogio.current = 0;
    setContagem(3);
    contagemRef.current = 3;
    setFase("contagem");
    playTransicao();
    playTick(0);
  };

  const iniciarRodada = () => {
    relogio.current = 0;
    travadoAte.current = 0;
    rodadaEncerrada.current = false;
    // O layout effect do novo modelo só roda no commit seguinte.
    modeloPronto.current = false;
    fracaoTempoRef.current = 1;
    inicioLocal.current = performance.now();
    setGanho(null);
    setTempoRestante(TEMPO_RODADA);
    tempoRestanteRef.current = TEMPO_RODADA;
    setErroJogador(false);
    setErrados([]);
    setEnviado(null);
    botPlano.current = planejarBot(BOTS[dificuldade]);
    setFase("rodada");
  };

  const criarSala = () => {
    desbloquearAudio();
    online.limparErro();
    zerarPartida();
    setFase("sala");
    playTransicao();
    online.criar(montarRodadas(estruturas));
  };

  const abrirTeclado = () => {
    desbloquearAudio();
    online.limparErro();
    zerarPartida();
    setCodigoDigitado("");
    setFase("codigo");
    playTransicao();
  };

  const tecla = (valor: string) => {
    if (valor === "Voltar") return voltarAoMenu();
    const tinhaErro = online.erro !== null;
    online.limparErro();
    const atual = codigoRef.current;
    if (valor === "Apagar") return setCodigoDigitado(atual.slice(0, -1));
    if (online.conexao === "conectando") return;
    if (atual.length >= 4) {
      // Código recusado ainda no visor: um dígito novo começa outro código,
      // em vez de só apagar o aviso e não fazer nada.
      if (tinhaErro) setCodigoDigitado(valor);
      return;
    }
    const novo = atual + valor;
    setCodigoDigitado(novo);
    // Entra sozinho no quarto dígito: no VR, cada clique a menos conta.
    if (novo.length === 4) online.entrar(novo);
  };

  const voltarAoMenu = () => {
    online.sair();
    setCodigoDigitado("");
    setAdversarioSaiu(false);
    setFase("menu");
  };

  const pedirRevanche = () => {
    if (revanche.eu) return;
    setRevanche((r) => ({ ...r, eu: true }));
    online.revanche(montarRodadas(estruturas));
  };

  /**
   * Registra a rodada na fita do placar e no retrospecto do fim. O índice vem
   * por parâmetro porque a assinatura da sala online roda num closure antigo
   * (deps [online.sala, online.assinar]) e leria `indice` velho.
   */
  const anotar = (quem: "eu" | "outro" | null, alvo: string, idx: number) => {
    // A rejeição de duplicata decide a anotação INTEIRA. Estando só dentro do
    // updater do histórico, uma anotação repetida ainda subia a sequência e
    // empurrava uma reação falsa no retrospecto.
    if (historicoRef.current.length > idx) return;
    const novo = [...historicoRef.current];
    while (novo.length < idx) novo.push(null);
    novo[idx] = quem;
    historicoRef.current = novo;
    setHistorico(novo);
    if (quem === "eu") {
      sequencia.current += 1;
      // Online, esta função roda quando o VEREDITO do servidor chega — depois
      // da janela de 600 ms e do ida-e-volta. A reação boa é a que o clique
      // mediu e mandou para o servidor.
      const ms = reacaoDoClique.current ?? performance.now() - inicioLocal.current;
      setReacoes((r) => [...r, ms / 1000]);
    } else {
      sequencia.current = 0;
      setPerdidas((p) => (p.includes(alvo) ? p : [...p, alvo]));
    }
    reacaoDoClique.current = null;
  };

  // Online: cada atualização da sala vira os estados que a tela já usa na
  // partida contra bot. Sons e humor do avatar só disparam quando o evento é
  // novo (`seq`), para não repetir a cada atualização da mesma rodada.
  useEffect(() => {
    if (!online.sala) return;
    partidaVista.current = -1;
    indiceVisto.current = -1;
    eventoVisto.current = -1;

    return online.assinar((v, recebidoEm) => {
      visaoRef.current = { v, recebidoEm };
      if (v.partida !== partidaVista.current) {
        // Amarrado à partida, não à fase: numa revanche em que o SSE reconecta
        // por cima da contagem, a fita e o retrospecto ficavam congelados na
        // partida anterior — e o guard de duplicata impedia qualquer correção.
        partidaVista.current = v.partida;
        setRodadas(v.rodadas);
        zerarPartida();
      }
      setPontosJogador(v.eu.pontos);
      setPontosBot(v.outro?.pontos ?? 0);
      setOutroConectado(v.outro?.conectado ?? true);
      setRevanche({ eu: v.eu.querRevanche, outro: v.outro?.querRevanche ?? false });
      setAdversarioSaiu(v.saiu === "outro");

      const nova: Fase = v.fase === "aguardando" ? "sala" : v.fase;
      const anterior = faseRef.current;
      const rodadaNova =
        nova === "rodada" && (anterior !== "rodada" || v.indice !== indiceVisto.current);
      indiceVisto.current = v.indice;
      setIndice(v.indice);

      if (nova === "contagem" && anterior !== "contagem") {
        setContagem(Math.max(1, Math.ceil(v.restanteMs / 1000)));
        contagemRef.current = Math.max(1, Math.ceil(v.restanteMs / 1000));
        setHumorBot("idle");
        playTransicao();
        playTick(0);
      }
      if (rodadaNova) {
        if (anterior === "contagem") playStart();
        rodadaEncerrada.current = false;
        travadoAte.current = 0;
        inicioLocal.current = recebidoEm;
        fracaoTempoRef.current = 1;
        setGanho(null);
        setTempoRestante(Math.ceil(v.restanteMs / 1000));
        tempoRestanteRef.current = Math.ceil(v.restanteMs / 1000);
        setErroJogador(false);
        setErrados([]);
        setEnviado(null);
        setHumorBot("idle");
      }
      if (nova !== "rodada") rodadaEncerrada.current = true;

      const ultimo = v.ultimo;
      if (nova === "feedback" && ultimo && ultimo.seq !== eventoVisto.current) {
        eventoVisto.current = ultimo.seq;
        if (ultimo.tipo === "tempo") {
          playTempoEsgotado();
          anotar(null, ultimo.alvo, v.indice);
          setFeedback(`Tempo esgotado — era: ${ultimo.alvo}`);
          setHumorBot("idle");
        } else if (ultimo.quem === "eu") {
          playHit(sequencia.current + 1);
          vibrar(0.7, 80);
          anotar("eu", ultimo.alvo, v.indice);
          setGanho({ pontos: ultimo.pontos, chave: v.indice });
          setFeedback(`Você pontuou! +${ultimo.pontos}`);
          setHumorBot("erra");
        } else {
          // Som PRÓPRIO: antes o ponto do adversário tocava o mesmo som do
          // meu erro — dois eventos opostos com o mesmo significado sonoro.
          playOponentePontuou();
          vibrar(0.2, 40);
          anotar("outro", ultimo.alvo, v.indice);
          setFeedback(`Adversário pontuou: ${ultimo.alvo}`);
          setHumorBot("comemora");
        }
      }
      if (nova === "fim" && anterior !== "fim") {
        const meus = v.eu.pontos;
        const dele = v.outro?.pontos ?? 0;
        // Vitória, derrota e empate tocavam exatamente o mesmo som: a pessoa
        // descobria o resultado lendo.
        playEnd(meus > dele ? "vitoria" : meus === dele ? "empate" : "derrota");
      }
      setFase(nova);
    });
    // `setFase` escreve no ref antes do estado; recriá-la a cada render não
    // muda nada para a assinatura.
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [online.sala, online.assinar]);

  const encerrarRodada = (
    texto: string,
    humor: HumorOponente,
    quem: "eu" | "outro" | null,
  ) => {
    rodadaEncerrada.current = true;
    anotar(quem, rodada.alvo, indice);
    setFeedback(texto);
    setHumorBot(humor);
    relogio.current = 0;
    setFase("feedback");
  };

  const responder = (opcao: string) => {
    // Duas fases, de propósito: `faseRef` já volta para "rodada" quando o
    // feedback acaba, mas a CENA ainda desenha as alternativas reveladas da
    // rodada anterior por alguns quadros (o React só commita depois). Um
    // clique nessa janela pontuava a rodada passada de novo e pulava a
    // seguinte. `fase` é o instantâneo da tela que recebeu o clique.
    if (fase !== "rodada" || faseRef.current !== "rodada") return;
    if (rodadaEncerrada.current) return;
    if (relogio.current < travadoAte.current) return;
    if (errados.includes(opcao)) return;
    if (emSala && opcao === rodada.alvo) {
      // Online o ponto é do servidor: aqui só trava as alternativas e envia
      // o tempo de reação medido neste óculos. O "Você pontuou!" vem com o
      // veredito, porque o adversário pode ter reagido antes.
      rodadaEncerrada.current = true;
      setEnviado(opcao);
      reacaoDoClique.current = performance.now() - inicioLocal.current;
      // Som próprio de "enviei": antes era o tique da contagem regressiva,
      // que significa outra coisa.
      playEnviado();
      const indiceDoClique = indice;
      void online
        .responder(indice, opcao, performance.now() - inicioLocal.current)
        .then((resultado) => {
          if (
            resultado !== "certo" &&
            faseRef.current === "rodada" &&
            indiceVisto.current === indiceDoClique
          ) {
            // Falhou o envio: destrava para tentar de novo.
            rodadaEncerrada.current = false;
            setEnviado(null);
          }
        });
      return;
    }
    if (opcao === rodada.alvo) {
      // A sequência de acertos sobe a nota: o combo vira melodia.
      playHit(sequencia.current + 1);
      vibrar(0.7, 80);
      setPontosJogador((p) => p + rodada.pontos);
      setGanho({ pontos: rodada.pontos, chave: indice });
      encerrarRodada(`Você pontuou! +${rodada.pontos}`, "erra", "eu");
    } else {
      playMiss();
      vibrar(0.3, 50);
      setErroJogador(true);
      setErrados((e) => [...e, opcao]);
      travadoAte.current = relogio.current + 1.6;
    }
  };

  // Atalho de teclado para DESKTOP (no headset não há teclado — lá joga-se com
  // laser/olhar). Sem array de deps de propósito: re-registra a cada render e
  // enxerga fase/rodada/dificuldade atuais (comecar/responder já são recriadas
  // por render). `"123".indexOf("")` retorna 0 — daí o `&& k`. Escape volta ao
  // menu só FORA da sessão XR (no VR ele encerra a sessão): sem ele, as telas
  // abertas pelas teclas 4/5 não tinham saída pelo teclado. Reaproveita
  // responder(), que já trava rodada encerrada/lockout, então não duplica
  // pontuação.
  useEffect(() => {
    const onKey = (e: KeyboardEvent) => {
      if (e.repeat || e.ctrlKey || e.metaKey || e.altKey) return;
      const k = e.key.toLowerCase();
      if (
        k === "escape" &&
        !naSessao &&
        (fase === "sala" ||
          fase === "codigo" ||
          fase === "encerrada" ||
          fase === "fim" ||
          (emSala && online.conexao === "perdida"))
      ) {
        // Contra o bot, sala nula: sair() só limpa o estado — equivale a
        // "Trocar dificuldade". Online, sai da sala como "Cancelar"/"Sair do duelo".
        voltarAoMenu();
        return;
      }
      if (fase === "menu") {
        const i = "123".indexOf(k);
        if (i >= 0 && k) comecar(NIVEIS[i]);
        else if (k === "4") criarSala();
        else if (k === "5") abrirTeclado();
        return;
      }
      if (fase === "codigo") {
        if (/^\d$/.test(k)) tecla(k);
        else if (k === "backspace") tecla("Apagar");
        return;
      }
      if (fase === "fim" && k === "enter" && emSala) {
        pedirRevanche();
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
    if (emSala) {
      // Online o relógio é o do servidor: recalculado a cada quadro a partir
      // do prazo recebido, não acumula erro nem congela com o óculos fora da
      // cabeça. Nenhuma transição acontece aqui — quem muda a fase é a sala.
      // Conexão perdida = partida acabada: sem isto o relógio continuava
      // correndo por trás do "Partida encerrada" — o telão contava 5,4,3,2,1
      // e a batida de tensão tocava sobre uma tela que diz que acabou.
      if (online.conexao === "perdida" || faseRef.current === "encerrada") return;
      const atual = visaoRef.current;
      const faseAgora = faseRef.current;
      const duracaoMs =
        faseAgora === "contagem" ? CONTAGEM_MS : faseAgora === "rodada" ? RODADA_MS : 0;
      if (!atual || !duracaoMs) return;
      relogio.current =
        (duracaoMs - atual.v.restanteMs + (performance.now() - atual.recebidoEm)) / 1000;
      if (faseAgora === "contagem") {
        const restante = 3 - Math.floor(relogio.current);
        if (restante !== contagemRef.current && restante > 0) {
          contagemRef.current = restante;
          setContagem(restante);
          // Cada passo da contagem sobe um grau da tríade: o ouvido antecipa
          // a largada em vez de ouvir a mesma nota três vezes.
          playTick(3 - restante);
        }
        return;
      }
      const restante = Math.max(0, Math.ceil(TEMPO_RODADA - relogio.current));
      // A barra lê este ref no próprio useFrame dela: nada de setState por quadro.
      fracaoTempoRef.current = Math.max(0, 1 - relogio.current / TEMPO_RODADA);
      if (restante !== tempoRestanteRef.current) {
        tempoRestanteRef.current = restante;
        setTempoRestante(restante);
        playTensao(restante);
      }
      if (erroJogador && relogio.current >= travadoAte.current) setErroJogador(false);
      return;
    }

    const faseAgora = faseRef.current;
    if (faseAgora === "rodada" && !modeloPronto.current) return;
    // A rodada só começa a contar quando o modelo aparece — e a reação junto.
    // Marcando no agendamento, o download do GLB (3,3 MB no crânio) entrava na
    // "reação média" do retrospecto e a estourava.
    if (faseAgora === "rodada" && relogio.current === 0) {
      inicioLocal.current = performance.now();
    }
    relogio.current += delta;

    if (faseAgora === "contagem") {
      const restante = 3 - Math.floor(relogio.current);
      if (restante !== contagemRef.current && restante > 0) {
        contagemRef.current = restante;
        setContagem(restante);
        playTick(3 - restante);
      }
      if (relogio.current >= 3) {
        playStart();
        vibrar(0.3, 60);
        iniciarRodada();
      }
      return;
    }

    if (faseAgora === "rodada") {
      if (rodadaEncerrada.current) return;
      const restante = Math.max(0, Math.ceil(TEMPO_RODADA - relogio.current));
      fracaoTempoRef.current = Math.max(0, 1 - relogio.current / TEMPO_RODADA);
      if (restante !== tempoRestanteRef.current) {
        tempoRestanteRef.current = restante;
        setTempoRestante(restante);
        // Últimos 5 s: tique subindo. Em VR a pessoa está olhando o órgão,
        // não o número no canto do painel — a cor sozinha chega tarde.
        playTensao(restante);
      }

      if (erroJogador && relogio.current >= travadoAte.current) {
        setErroJogador(false);
      }

      const bot = botPlano.current;
      if (!bot.respondeu && relogio.current >= bot.em) {
        bot.respondeu = true;
        if (bot.acerta) {
          playOponentePontuou();
          vibrar(0.2, 40);
          setPontosBot((p) => p + rodada.pontos);
          encerrarRodada(
            `${BOTS[dificuldade].nome.split(" (")[0]} pontuou: ${rodada.alvo}`,
            "comemora",
            "outro",
          );
          return;
        }
        // Bot errou: fica de fora da rodada (jogador segue tentando).
      }

      if (relogio.current >= TEMPO_RODADA) {
        // O tempo esgotar era o único desfecho MUDO da rodada.
        playTempoEsgotado();
        encerrarRodada(`Tempo esgotado — era: ${rodada.alvo}`, "idle", null);
      }
      return;
    }

    if (faseAgora === "feedback" && relogio.current >= 2.4) {
      setHumorBot("idle");
      if (indice + 1 >= TOTAL_RODADAS) {
        playEnd(
          pontosJogador > pontosBot
            ? "vitoria"
            : pontosJogador === pontosBot
              ? "empate"
              : "derrota",
        );
        setFase("fim");
      } else {
        setIndice((i) => i + 1);
        iniciarRodada();
      }
    }
  });

  /* ----------------------------------------------------------- render */

  const avisoConexao =
    online.conexao === "reconectando"
      ? "Reconectando…"
      : emSala && !outroConectado
        ? "Adversário desconectado…"
        : null;

  /**
   * Retrospecto da partida. Tudo sai do que aconteceu NESTA partida e some
   * com ela: nada é somado entre partidas nem estimado.
   */
  const acertos = historico.filter((h) => h === "eu").length;
  const maiorSequencia = historico.reduce(
    (acc, h) => {
      const atual = h === "eu" ? acc.atual + 1 : 0;
      return { atual, melhor: Math.max(acc.melhor, atual) };
    },
    { atual: 0, melhor: 0 },
  ).melhor;
  const reacaoMedia = reacoes.length
    ? reacoes.reduce((s, r) => s + r, 0) / reacoes.length
    : null;
  const retrospecto = [
    `Acertos ${acertos} de ${TOTAL_RODADAS}`,
    maiorSequencia > 1 ? `Maior sequência ${maiorSequencia}` : null,
    reacaoMedia ? `Reação média ${reacaoMedia.toFixed(1).replace(".", ",")} s` : null,
  ]
    .filter(Boolean)
    .join(" · ");

  /** O analógico gira o órgão — ninguém descobre isso sozinho no headset. */
  const DICA = "Gatilho responde · Analógico gira o órgão";

  /** Na revelação as alternativas ficam na tela: a certa acende onde estava. */
  const revelar = fase === "feedback";
  const destaqueDe = (opcao: string): "certo" | "errado" | null => {
    if (!revelar || !rodada) return null;
    if (opcao === rodada.alvo) return "certo";
    return errados.includes(opcao) || enviado === opcao ? "errado" : null;
  };

  /**
   * Telão do hospital: nunca mais apagado. Ele está a 5,76 m com texto de
   * 0,34 — é o elemento mais legível da cena e ficava preto fora da rodada.
   */
  const partidaViva = !(emSala && (online.conexao === "perdida" || fase === "encerrada"));
  const led =
    !partidaViva
      ? { texto: `${pontosJogador} × ${pontosBot}`, cor: CORES.giz }
      : fase === "contagem"
        ? { texto: String(contagem), cor: CORES.tempo }
        : fase === "rodada"
          ? {
              texto: String(tempoRestante),
              cor: tempoRestante <= 5 ? CORES.dele : CORES.tempo,
            }
          : fase === "feedback" || fase === "fim"
            ? { texto: `${pontosJogador} × ${pontosBot}`, cor: CORES.giz }
            : { texto: "DUELO 1×1", cor: CORES.tempo };
  /**
   * A tela acesa do telão tem 1,38 m (AmbienteHospital, TelaoLed) e o texto
   * não quebra linha — "1200 × 1000" a 0,34 saía 26 cm para fora da moldura
   * de cada lado. O corpo encolhe conforme o texto cresce.
   */
  const ledSize = led.texto.length <= 3 ? 0.34 : led.texto.length <= 7 ? 0.24 : 0.19;

  /**
   * O oponente fica em cena o tempo todo. Antes ele só existia em 2 das 7
   * telas: na contagem o adversário ainda não existia, e na tela de vitória —
   * o momento em que se quer ver a cara dele — ele evaporava. Manter montado
   * é de graça; remontar é que custa.
   */
  const oponente = hosp ? (
    <Oponente
      humor={humorBot}
      nome={nomeOponente}
      position={[-0.45, -1.3, -1.9]}
      // O corpo é modelado de frente para +z; o jogador está em +z.
      rotationY={0}
    />
  ) : (
    <Oponente
      humor={humorBot}
      nome={nomeOponente}
      position={[-0.81, -1.54, 1.07]}
      rotationY={Math.PI}
      sentado
    />
  );

  const tela = () => {
    if (emSala && (online.conexao === "perdida" || fase === "encerrada")) {
      return (
        <TelaOnline
          hosp={hosp}
          linhas={[
            { texto: "Partida encerrada", tamanho: 1.8 },
            {
              texto: adversarioSaiu
                ? "O adversário saiu da partida."
                : "A conexão com a partida caiu.",
              cor: "#ffc9bd",
            },
          ]}
          botoes={[{ texto: "Voltar ao menu", onClick: voltarAoMenu }]}
        />
      );
    }

    if (fase === "sala") {
      const status = !online.sala
        ? (online.erro ?? "Criando sala…")
        : online.conexao === "conectado"
          ? "Aguardando o adversário…"
          : online.conexao === "reconectando"
            ? "Reconectando…"
            : "Conectando…";
      return (
        <TelaOnline
          hosp={hosp}
          linhas={
            online.sala
              ? [
                  { texto: "Código da sala" },
                  { texto: online.sala.split("").join(" "), tamanho: 3 },
                  {
                    texto: "No outro óculos, toque em Entrar numa sala e digite este código",
                    tamanho: 0.8,
                    cor: CORES.gizFraco,
                  },
                  { texto: status },
                ]
              : [{ texto: status, cor: online.erro ? "#ffc9bd" : undefined }]
          }
          botoes={[{ texto: online.erro ? "Voltar" : "Cancelar", onClick: voltarAoMenu }]}
        />
      );
    }

    if (fase === "codigo") {
      const visor = (codigoDigitado + "____").slice(0, 4).split("").join(" ");
      const aviso =
        online.erro ?? (online.conexao === "conectando" ? "Entrando na sala…" : " ");
      if (hosp) {
        return (
          <group position={HOSP_UI} rotation={HOSP_ROT}>
            <Panel width={1.7} height={1.85} position={[0, -0.2, 0]} />
            <Text3D position={[0, 0.6, 0.01]} size={0.065}>
              Digite o código da sala
            </Text3D>
            <Text3D position={[0, 0.43, 0.01]} size={0.14} color={CORES.tempo}>
              {visor}
            </Text3D>
            <Text3D
              position={[0, 0.28, 0.01]}
              size={0.05}
              color={online.erro ? CORES.dele : ARENA_COLORS.muted}
              maxWidth={1.5}
            >
              {aviso}
            </Text3D>
            {TECLAS.map((t, i) => (
              <Button3D
                key={t}
                label={t}
                width={t.length > 1 ? 0.46 : 0.4}
                height={0.2}
                position={[((i % 3) - 1) * 0.5, 0.1 - Math.floor(i / 3) * 0.26, 0.01]}
                color={t === "Voltar" ? ARENA_COLORS.muted : ARENA_COLORS.primary}
                onClick={() => tecla(t)}
              />
            ))}
          </group>
        );
      }
      return (
        <group>
          <Text3D position={[LOUSA_X, 0.2, LOUSA_Z]} size={0.04} color={CORES.gizFraco}>
            Digite o código da sala
          </Text3D>
          <Text3D position={[LOUSA_X, 0.11, LOUSA_Z]} size={0.09} color={CORES.giz}>
            {visor}
          </Text3D>
          <Text3D
            position={[LOUSA_X, 0.035, LOUSA_Z]}
            size={0.03}
            color={online.erro ? "#ffc9bd" : CORES.gizFraco}
            maxWidth={1.05}
          >
            {aviso}
          </Text3D>
          {/* Passo 0,13 com alvo de 0,10: as teclas se sobrepunham 3 cm e o
              laser registrava a tecla de baixo. */}
          {TECLAS.map((t, i) => (
            <BotaoLousa
              key={t}
              texto={t}
              position={[
                LOUSA_X + ((i % 3) - 1) * 0.24,
                -0.06 - Math.floor(i / 3) * 0.13,
                LOUSA_Z,
              ]}
              size={t.length > 1 ? 0.042 : 0.075}
              altura={0.106}
              width={0.22}
              cor={t === "Voltar" ? CORES.gizFraco : CORES.giz}
              onClick={() => tecla(t)}
            />
          ))}
        </group>
      );
    }

    if (fase === "menu") {
      if (hosp) {
        return (
          <group position={HOSP_UI} rotation={HOSP_ROT}>
            <Panel width={1.7} height={1.85} position={[0, -0.2, 0]} />
            <Text3D position={[0, 0.55, 0.01]} size={0.14}>
              Duelo 1×1
            </Text3D>
            <Text3D position={[0, 0.36, 0.01]} size={0.055} color={ARENA_COLORS.muted} maxWidth={1.5}>
              Identifique órgãos (100 pts) e estruturas (200 pts) antes do oponente
            </Text3D>
            <Text3D position={[0, 0.24, 0.01]} size={0.042} color={CORES.tempo} maxWidth={1.5}>
              {DICA}
            </Text3D>
            {(Object.keys(BOTS) as Dificuldade[]).map((nivel, i) => (
              <Button3D
                key={nivel}
                label={BOTS[nivel].nome}
                width={1.4}
                height={0.22}
                position={[0, -0.02 - i * 0.28, 0.01]}
                color={nivel === "especialista" ? ARENA_COLORS.danger : ARENA_COLORS.primary}
                icone
                onClick={() => comecar(nivel)}
              />
            ))}
            <Text3D position={[0, -0.77, 0.01]} size={0.05} color={ARENA_COLORS.muted}>
              Contra um amigo, cada um no seu óculos:
            </Text3D>
            <Button3D
              label="Criar sala"
              width={0.82}
              height={0.2}
              position={[-0.43, -0.97, 0.01]}
              color={ARENA_COLORS.success}
              onClick={criarSala}
            />
            <Button3D
              label="Entrar numa sala"
              width={0.82}
              height={0.2}
              position={[0.43, -0.97, 0.01]}
              color={ARENA_COLORS.success}
              onClick={abrirTeclado}
            />
          </group>
        );
      }
      return (
        <group>
          <Text3D position={[LOUSA_X, 0.2, LOUSA_Z]} size={0.1} color={CORES.giz}>
            Duelo 1×1
          </Text3D>
          <Text3D
            position={[LOUSA_X, 0.115, LOUSA_Z]}
            size={0.034}
            color={CORES.gizFraco}
            maxWidth={1.05}
          >
            Órgãos valem 100 · estruturas valem 200
          </Text3D>
          <Text3D position={[LOUSA_X, 0.06, LOUSA_Z]} size={0.028} color={CORES.tempo} maxWidth={1.05}>
            {DICA}
          </Text3D>
          {(Object.keys(BOTS) as Dificuldade[]).map((nivel, i) => (
            <BotaoLousa
              key={nivel}
              texto={BOTS[nivel].nome}
              position={[LOUSA_X, -0.05 - i * 0.115, LOUSA_Z]}
              cor={nivel === "especialista" ? "#ffc9bd" : CORES.giz}
              size={0.06}
              altura={0.094}
              width={1.1}
              onClick={() => comecar(nivel)}
            />
          ))}
          <Text3D position={[LOUSA_X, -0.355, LOUSA_Z]} size={0.028} color={CORES.gizFraco}>
            Contra um amigo, cada um no seu óculos:
          </Text3D>
          <BotaoLousa
            texto="Criar sala"
            position={[LOUSA_X - 0.27, -0.435, LOUSA_Z]}
            cor="#bfe8cf"
            size={0.05}
            altura={0.08}
            width={0.5}
            onClick={criarSala}
          />
          <BotaoLousa
            texto="Entrar numa sala"
            position={[LOUSA_X + 0.27, -0.435, LOUSA_Z]}
            cor="#bfe8cf"
            size={0.05}
            altura={0.08}
            width={0.5}
            onClick={abrirTeclado}
          />
        </group>
      );
    }

    /**
     * Contagem regressiva = apresentação da partida. Antes era só o dígito
     * numa tela vazia; agora é o cartão de quem joga contra quem, o placar já
     * no formato definitivo e as regras em uma linha.
     */
    if (fase === "contagem") {
      if (hosp) {
        return (
          <group position={HOSP_UI} rotation={HOSP_ROT}>
            <Panel width={1.7} height={1.0} position={[0, 0.05, 0]} />
            <Placar
              meus={pontosJogador}
              dele={pontosBot}
              nomeDele={nomeOponente}
              historico={historico}
              position={[0, 0.4, 0.01]}
            />
            <DigitoContagem valor={contagem} size={0.42} position={[0, 0.02, 0.01]} />
            <Text3D
              position={[0, -0.28, 0.01]}
              size={0.05}
              color={ARENA_COLORS.muted}
              maxWidth={1.5}
            >
              {`${TOTAL_RODADAS} rodadas · órgãos 100 pts · estruturas 200 pts`}
            </Text3D>
            <Text3D position={[0, -0.38, 0.01]} size={0.042} color={CORES.tempo} maxWidth={1.5}>
              {DICA}
            </Text3D>
          </group>
        );
      }
      return (
        <group>
          <Placar
            meus={pontosJogador}
            dele={pontosBot}
            nomeDele={nomeOponente}
            historico={historico}
            escala={0.7}
            position={[LOUSA_X, 0.2, LOUSA_Z]}
          />
          <DigitoContagem valor={contagem} size={0.26} position={[LOUSA_X, -0.05, LOUSA_Z]} />
          <Text3D
            position={[LOUSA_X, -0.3, LOUSA_Z]}
            size={0.032}
            color={CORES.gizFraco}
            maxWidth={1.05}
          >
            {`${TOTAL_RODADAS} rodadas · órgãos 100 pts · estruturas 200 pts`}
          </Text3D>
          <Text3D position={[LOUSA_X, -0.38, LOUSA_Z]} size={0.028} color={CORES.tempo} maxWidth={1.05}>
            {DICA}
          </Text3D>
        </group>
      );
    }

    if (fase === "fim") {
      const venceu = pontosJogador > pontosBot;
      const empate = pontosJogador === pontosBot;
      const titulo = venceu
        ? "Você venceu!"
        : empate
          ? "Empate!"
          : emSala
            ? "Adversário venceu"
            : "O bot venceu";
      // Online: "de novo" é revanche (só começa quando os dois pedem) e o
      // segundo botão sai da sala. Contra bot, fica como era.
      const rotuloDeNovo = !emSala
        ? "Jogar de novo"
        : revanche.eu
          ? "Aguardando o adversário…"
          : revanche.outro
            ? "Aceitar revanche"
            : "Revanche";
      const deNovo = emSala ? pedirRevanche : () => comecar(dificuldade);
      const rotuloSegundo = emSala ? "Sair do duelo" : "Trocar dificuldade";
      const segundo = emSala ? voltarAoMenu : () => setFase("menu");
      const revisar = perdidas.length ? `Revisar: ${perdidas.slice(0, 2).join(", ")}` : null;
      if (hosp) {
        return (
          <group position={HOSP_UI} rotation={HOSP_ROT}>
            <Panel width={1.7} height={1.35}>
              {avisoConexao && (
                <Text3D position={[0, 0.58, 0.01]} size={0.05} color={CORES.dele}>
                  {avisoConexao}
                </Text3D>
              )}
              <Text3D
                position={[0, 0.44, 0.01]}
                size={0.14}
                color={venceu ? CORES.meu : empate ? ARENA_COLORS.primary : CORES.dele}
              >
                {titulo}
              </Text3D>
              <Placar
                meus={pontosJogador}
                dele={pontosBot}
                nomeDele={nomeOponente}
                historico={historico}
                escala={1.15}
                position={[0, 0.2, 0.01]}
              />
              <Text3D
                position={[0, -0.02, 0.01]}
                size={0.048}
                color={ARENA_COLORS.muted}
                maxWidth={1.55}
              >
                {retrospecto}
              </Text3D>
              {revisar && (
                <Text3D
                  position={[0, -0.1, 0.01]}
                  size={0.045}
                  color={CORES.ouro}
                  maxWidth={1.55}
                >
                  {revisar}
                </Text3D>
              )}
              <Button3D
                label={rotuloDeNovo}
                width={1.45}
                height={0.22}
                position={[0, -0.3, 0.01]}
                color={ARENA_COLORS.success}
                icone
                onClick={deNovo}
              />
              <Button3D
                label={rotuloSegundo}
                width={1.3}
                height={0.2}
                position={[0, -0.56, 0.01]}
                onClick={segundo}
              />
            </Panel>
          </group>
        );
      }
      return (
        <group>
          {avisoConexao && (
            <Text3D position={[LOUSA_X, 0.25, LOUSA_Z]} size={0.028} color="#ffc9bd">
              {avisoConexao}
            </Text3D>
          )}
          <Text3D
            position={[LOUSA_X, 0.17, LOUSA_Z]}
            size={0.09}
            color={venceu ? CORES.meu : empate ? CORES.giz : CORES.dele}
          >
            {titulo}
          </Text3D>
          <Placar
            meus={pontosJogador}
            dele={pontosBot}
            nomeDele={nomeOponente}
            historico={historico}
            escala={0.75}
            position={[LOUSA_X, 0.05, LOUSA_Z]}
          />
          <Text3D
            position={[LOUSA_X, -0.075, LOUSA_Z]}
            size={0.029}
            color={CORES.gizFraco}
            maxWidth={1.05}
          >
            {retrospecto}
          </Text3D>
          {revisar && (
            <Text3D
              position={[LOUSA_X, -0.135, LOUSA_Z]}
              size={0.026}
              color={CORES.ouro}
              maxWidth={1.05}
            >
              {revisar}
            </Text3D>
          )}
          <BotaoLousa
            texto={rotuloDeNovo}
            position={[LOUSA_X, -0.255, LOUSA_Z]}
            cor="#bfe8cf"
            size={0.062}
            altura={0.1}
            width={1.1}
            onClick={deNovo}
          />
          <BotaoLousa
            texto={rotuloSegundo}
            position={[LOUSA_X, -0.385, LOUSA_Z]}
            size={0.052}
            altura={0.1}
            width={1.1}
            onClick={segundo}
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
            painel, na altura do peito (1,5m do chão). Tela em pé fora do VR:
            acima da lousa/do painel (a câmera da escola sobe e a do hospital
            recua, ver DueloApp). */}
        <group
          position={
            hosp
              ? empilhar
                ? [0.72, 1.2, -0.5]
                : [-1.05, 0.2, -0.5]
              : empilhar
                ? // 0.42 punha a base do órgão em cima do placar (a laringe é
                  // mais alta que larga); 0.56 deixa o placar livre.
                  [LOUSA_X, 0.56, -0.95]
                : [-0.78, -0.15, -0.95]
          }
          scale={hosp ? (empilhar ? 0.4 : 0.6) : empilhar ? 0.26 : 0.36}
        >
          {/* Boundary LOCAL, novo a cada rodada: um GLB que falha tira só o
              modelo — pergunta, alternativas e placar seguem, e a partida não
              acaba. Libera o relógio do bot, que esperava o modelo. */}
          <ErrorBoundary
            key={indice}
            onError={() => {
              modeloPronto.current = true;
            }}
            fallback={
              <Text3D position={[0, 0, 0]} size={0.11} color={ARENA_COLORS.muted}>
                Modelo indisponível
              </Text3D>
            }
          >
            <Suspense
              fallback={
                <Text3D position={[0, 0, 0]} size={0.11} color={ARENA_COLORS.muted}>
                  Carregando…
                </Text3D>
              }
            >
              <ModeloRodada rodada={rodada} prontoRef={modeloPronto} revelado={revelar} />
            </Suspense>
          </ErrorBoundary>
          {/* "+200" subindo do próprio órgão, no instante do acerto. */}
          {ganho && <Floater key={ganho.chave} value={ganho.pontos} position={[0, 1.15, 0]} />}
        </group>

        {/* Placar, cronômetro, pergunta, alternativas e feedback */}
        {hosp ? (
          <group position={HOSP_UI} rotation={HOSP_ROT}>
            <Panel width={1.7} height={1.55} position={[0, -0.05, 0]}>
              {avisoConexao && (
                <Text3D position={[0, 0.66, 0.01]} size={0.042} color={CORES.dele}>
                  {avisoConexao}
                </Text3D>
              )}
              <Placar
                meus={pontosJogador}
                dele={pontosBot}
                nomeDele={nomeOponente}
                historico={historico}
                position={[0, 0.55, 0.01]}
              />
              {/* A barra drena por 18 s; o número sozinho ficava idêntico
                  durante 13 deles. Fora da rodada os dois saem: o tempo
                  parado em 0 não diz nada. */}
              {!revelar && (
                <>
                  <BarraTempo
                    width={1.5}
                    position={[0, 0.4, 0.01]}
                    fracaoRef={fracaoTempoRef}
                  />
                  <Text3D
                    position={[-0.66, 0.31, 0.01]}
                    size={0.055}
                    color={tempoRestante <= 5 ? CORES.dele : CORES.tempo}
                  >
                    {String(tempoRestante)}
                  </Text3D>
                </>
              )}
              <Text3D position={[0.12, 0.31, 0.01]} size={0.042} color={ARENA_COLORS.muted}>
                {`Rodada ${indice + 1}/${TOTAL_RODADAS} · vale ${rodada.pontos}`}
              </Text3D>
              <Text3D position={[0, 0.17, 0.01]} size={0.075} maxWidth={1.5}>
                {revelar
                  ? feedback
                  : rodada.tipo === "orgao"
                    ? "Qual órgão é este?"
                    : "Qual estrutura está marcada em amarelo?"}
              </Text3D>
              {/* As alternativas NÃO saem da tela no feedback: a certa acende
                  verde no lugar onde estava, e quem errou finalmente vê qual
                  era. Antes elas viravam uma frase. */}
              {rodada.opcoes.map((opcao, i) => (
                <Button3D
                  key={opcao}
                  label={opcao}
                  selo={["A", "B", "C", "D"][i]}
                  width={1.55}
                  height={0.18}
                  position={[0, -0.02 - i * 0.21, 0.01]}
                  color={
                    revelar
                      ? ARENA_COLORS.muted
                      : enviado === opcao
                        ? ARENA_COLORS.success
                        : errados.includes(opcao)
                          ? ARENA_COLORS.muted
                          : ARENA_COLORS.primary
                  }
                  // Na revelação o botão fica mudo e imóvel (sem clique, som,
                  // vibração ou hover) — o destaque tem precedência sobre o
                  // cinza de desabilitado dentro do Button3D, então a certa
                  // continua acesa.
                  destaque={destaqueDe(opcao)}
                  desabilitado={revelar || erroJogador || errados.includes(opcao)}
                  onClick={() => responder(opcao)}
                />
              ))}
              {/* Ao lado do cronômetro: em y=-0.72 o aviso caía DENTRO da
                  placa da alternativa D e, com depthTest desligado, era
                  desenhado por cima dela. */}
              {erroJogador && !revelar && (
                <Text3D position={[-0.4, 0.31, 0.01]} size={0.045} color={CORES.dele}>
                  Errado!
                </Text3D>
              )}
            </Panel>
          </group>
        ) : (
          <>
            {avisoConexao && (
              <Text3D position={[LOUSA_X, 0.245, LOUSA_Z]} size={0.028} color="#ffc9bd">
                {avisoConexao}
              </Text3D>
            )}
            <Placar
              meus={pontosJogador}
              dele={pontosBot}
              nomeDele={nomeOponente}
              historico={historico}
              escala={0.75}
              position={[LOUSA_X, 0.205, LOUSA_Z]}
            />
            {!revelar && (
              <>
                <BarraTempo
                  width={0.95}
                  height={0.016}
                  position={[LOUSA_X, 0.118, LOUSA_Z]}
                  fracaoRef={fracaoTempoRef}
                />
                <Text3D
                  position={[LOUSA_X - 0.53, 0.118, LOUSA_Z]}
                  size={0.045}
                  color={tempoRestante <= 5 ? CORES.dele : CORES.tempo}
                >
                  {String(tempoRestante)}
                </Text3D>
              </>
            )}
            <Text3D
              position={[LOUSA_X, 0.022, LOUSA_Z]}
              size={0.048}
              maxWidth={1.08}
              color={CORES.giz}
            >
              {revelar
                ? feedback
                : rodada.tipo === "orgao"
                  ? "Qual órgão é este?"
                  : "Qual estrutura está marcada em amarelo?"}
            </Text3D>
            <Text3D
              position={[LOUSA_X + 0.33, 0.082, LOUSA_Z]}
              size={0.025}
              color={CORES.gizFraco}
            >
              {`Rodada ${indice + 1}/${TOTAL_RODADAS} · vale ${rodada.pontos}`}
            </Text3D>
            {/* Passo 0,115 com alvo de 0,094: antes sobravam 1,2 mm entre uma
                alternativa e a seguinte. */}
            {rodada.opcoes.map((opcao, i) => (
              <BotaoLousa
                key={opcao}
                texto={`${["A", "B", "C", "D"][i]})  ${opcao}`}
                position={[LOUSA_X, -0.055 - i * 0.115, LOUSA_Z]}
                cor={
                  revelar
                    ? "#8fae94"
                    : enviado === opcao
                      ? "#bfe8cf"
                      : errados.includes(opcao)
                        ? "#8fae94"
                        : "#f8fbef"
                }
                destaque={destaqueDe(opcao)}
                desabilitado={revelar || erroJogador || errados.includes(opcao)}
                size={0.05}
                altura={0.094}
                width={1.1}
                onClick={() => responder(opcao)}
              />
            ))}
            {erroJogador && !revelar && (
              <Text3D position={[LOUSA_X - 0.53, 0.022, LOUSA_Z]} size={0.03} color="#ffb0a0">
                Errado!
              </Text3D>
            )}
          </>
        )}
      </group>
    );
  };

  return (
    <group>
      {/*
        Cada tela entra crescendo de 0,92 e vindo 4 cm de trás em 180 ms: o
        corte seco entre telas era metade da sensação de protótipo. A chave
        junta "rodada" e "feedback" de propósito — trocá-la ali remontaria o
        modelo 3D no meio da revelação.
      */}
      <Entrada key={fase === "feedback" ? "rodada" : fase}>{tela()}</Entrada>
      {oponente}
      {hosp && (
        <Text3D position={HOSP_LED} size={ledSize} color={led.cor}>
          {led.texto}
        </Text3D>
      )}
    </group>
  );
}

useGLTF.preload(LARINGE, "/draco/");
for (const organ of ORGAOS_DUELO) useGLTF.preload(organ.modelPath, "/draco/");
