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
}: {
  rodada: Rodada;
  /** Vira true quando o modelo desta rodada aparece (o relógio do bot espera). */
  prontoRef: RefObject<boolean>;
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
    // O layout effect do novo modelo só roda no commit seguinte.
    modeloPronto.current = false;
    setTempoRestante(TEMPO_RODADA);
    setErroJogador(false);
    setErrados([]);
    setEnviado(null);
    botPlano.current = planejarBot(BOTS[dificuldade]);
    setFase("rodada");
  };

  const criarSala = () => {
    online.limparErro();
    setFase("sala");
    online.criar(montarRodadas(estruturas));
  };

  const abrirTeclado = () => {
    online.limparErro();
    setCodigoDigitado("");
    setFase("codigo");
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
        partidaVista.current = v.partida;
        setRodadas(v.rodadas);
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
        setHumorBot("idle");
        playTick();
      }
      if (rodadaNova) {
        if (anterior === "contagem") playStart();
        rodadaEncerrada.current = false;
        travadoAte.current = 0;
        inicioLocal.current = recebidoEm;
        setTempoRestante(Math.ceil(v.restanteMs / 1000));
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
          setFeedback(`Tempo esgotado — era: ${ultimo.alvo}`);
          setHumorBot("idle");
        } else if (ultimo.quem === "eu") {
          playHit();
          setFeedback(`Você pontuou! +${ultimo.pontos}`);
          setHumorBot("erra");
        } else {
          playMiss();
          setFeedback(`Adversário pontuou: ${ultimo.alvo}`);
          setHumorBot("comemora");
        }
      }
      if (nova === "fim" && anterior !== "fim") playEnd();
      setFase(nova);
    });
    // `setFase` escreve no ref antes do estado; recriá-la a cada render não
    // muda nada para a assinatura.
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [online.sala, online.assinar]);

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
    if (emSala && opcao === rodada.alvo) {
      // Online o ponto é do servidor: aqui só trava as alternativas e envia
      // o tempo de reação medido neste óculos. O "Você pontuou!" vem com o
      // veredito, porque o adversário pode ter reagido antes.
      rodadaEncerrada.current = true;
      setEnviado(opcao);
      playTick();
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
      const atual = visaoRef.current;
      const faseAgora = faseRef.current;
      const duracaoMs =
        faseAgora === "contagem" ? CONTAGEM_MS : faseAgora === "rodada" ? RODADA_MS : 0;
      if (!atual || !duracaoMs) return;
      relogio.current =
        (duracaoMs - atual.v.restanteMs + (performance.now() - atual.recebidoEm)) / 1000;
      if (faseAgora === "contagem") {
        const restante = 3 - Math.floor(relogio.current);
        if (restante !== contagem && restante > 0) {
          setContagem(restante);
          playTick();
        }
        return;
      }
      const restante = Math.max(0, Math.ceil(TEMPO_RODADA - relogio.current));
      if (restante !== tempoRestante) setTempoRestante(restante);
      if (erroJogador && relogio.current >= travadoAte.current) setErroJogador(false);
      return;
    }

    const faseAgora = faseRef.current;
    if (faseAgora === "rodada" && !modeloPronto.current) return;
    relogio.current += delta;

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

  const avisoConexao =
    online.conexao === "reconectando"
      ? "Reconectando…"
      : emSala && !outroConectado
        ? "Adversário desconectado…"
        : null;

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
                  cor: "#cfe0cd",
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
          <Text3D position={[0, 0.43, 0.01]} size={0.14} color="#7de8ff">
            {visor}
          </Text3D>
          <Text3D
            position={[0, 0.28, 0.01]}
            size={0.05}
            color={online.erro ? "#ffb0a0" : ARENA_COLORS.muted}
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
              color={t === "Voltar" ? "#5c6b7a" : ARENA_COLORS.primary}
              onClick={() => tecla(t)}
            />
          ))}
        </group>
      );
    }
    return (
      <group>
        <Text3D position={[LOUSA_X, 0.2, LOUSA_Z]} size={0.04} color="#cfe0cd">
          Digite o código da sala
        </Text3D>
        <Text3D position={[LOUSA_X, 0.11, LOUSA_Z]} size={0.09} color="#f2f5ec">
          {visor}
        </Text3D>
        <Text3D
          position={[LOUSA_X, 0.035, LOUSA_Z]}
          size={0.03}
          color={online.erro ? "#ffc9bd" : "#cfe0cd"}
          maxWidth={1.05}
        >
          {aviso}
        </Text3D>
        {TECLAS.map((t, i) => (
          <BotaoLousa
            key={t}
            texto={t}
            position={[
              LOUSA_X + ((i % 3) - 1) * 0.24,
              -0.06 - Math.floor(i / 3) * 0.11,
              LOUSA_Z,
            ]}
            size={t.length > 1 ? 0.042 : 0.075}
            width={0.22}
            cor={t === "Voltar" ? "#cfe0cd" : "#f2f5ec"}
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
          <Text3D position={[0, -0.77, 0.01]} size={0.05} color={ARENA_COLORS.muted}>
            Contra um amigo, cada um no seu óculos:
          </Text3D>
          <Button3D
            label="Criar sala"
            width={0.72}
            height={0.2}
            position={[-0.39, -0.97, 0.01]}
            color={ARENA_COLORS.success}
            onClick={criarSala}
          />
          <Button3D
            label="Entrar numa sala"
            width={0.72}
            height={0.2}
            position={[0.39, -0.97, 0.01]}
            color={ARENA_COLORS.success}
            onClick={abrirTeclado}
          />
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
        <Text3D position={[LOUSA_X, -0.345, LOUSA_Z]} size={0.028} color="#cfe0cd">
          Contra um amigo, cada um no seu óculos:
        </Text3D>
        <BotaoLousa
          texto="Criar sala"
          position={[LOUSA_X - 0.27, -0.425, LOUSA_Z]}
          cor="#bfe8cf"
          size={0.05}
          width={0.5}
          onClick={criarSala}
        />
        <BotaoLousa
          texto="Entrar numa sala"
          position={[LOUSA_X + 0.27, -0.425, LOUSA_Z]}
          cor="#bfe8cf"
          size={0.05}
          width={0.5}
          onClick={abrirTeclado}
        />
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
    if (hosp) {
      return (
        <group position={HOSP_UI} rotation={HOSP_ROT}>
          {avisoConexao && (
            <Text3D position={[0, 0.7, 0.01]} size={0.05} color="#ffb0a0">
              {avisoConexao}
            </Text3D>
          )}
          <Panel width={1.7} height={1.2}>
            <Text3D
              position={[0, 0.38, 0.01]}
              size={0.15}
              color={venceu ? ARENA_COLORS.success : empate ? ARENA_COLORS.primary : ARENA_COLORS.danger}
            >
              {titulo}
            </Text3D>
            <Text3D position={[0, 0.12, 0.01]} size={0.085}>
              {`Você ${pontosJogador} × ${pontosBot} ${nomeOponente}`}
            </Text3D>
            <Button3D
              label={rotuloDeNovo}
              width={1.3}
              height={0.22}
              position={[0, -0.16, 0.01]}
              color={ARENA_COLORS.success}
              onClick={deNovo}
            />
            <Button3D
              label={rotuloSegundo}
              width={1.3}
              height={0.2}
              position={[0, -0.44, 0.01]}
              onClick={segundo}
            />
          </Panel>
        </group>
      );
    }
    return (
      <group>
        {avisoConexao && (
          <Text3D position={[LOUSA_X, 0.235, LOUSA_Z]} size={0.028} color="#ffc9bd">
            {avisoConexao}
          </Text3D>
        )}
        <Text3D
          position={[LOUSA_X, 0.12, LOUSA_Z]}
          size={0.1}
          color={venceu ? "#bfe8cf" : empate ? "#f2f5ec" : "#ffc9bd"}
        >
          {titulo}
        </Text3D>
        <Text3D position={[LOUSA_X, -0.02, LOUSA_Z]} size={0.055} color="#f2f5ec">
          {`Você ${pontosJogador} × ${pontosBot} ${nomeOponente}`}
        </Text3D>
        <BotaoLousa
          texto={rotuloDeNovo}
          position={[LOUSA_X, -0.17, LOUSA_Z]}
          cor="#bfe8cf"
          size={0.065}
          width={1.1}
          onClick={deNovo}
        />
        <BotaoLousa
          texto={rotuloSegundo}
          position={[LOUSA_X, -0.31, LOUSA_Z]}
          size={0.055}
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
              ? [LOUSA_X, 0.42, -0.95]
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
            <ModeloRodada rodada={rodada} prontoRef={modeloPronto} />
          </Suspense>
        </ErrorBoundary>
      </group>

      {/* Placar, cronômetro, pergunta, alternativas e feedback */}
      {hosp ? (
        <group position={HOSP_UI} rotation={HOSP_ROT}>
          <Panel width={1.7} height={1.45} position={[0, -0.05, 0]}>
            {avisoConexao && (
              <Text3D position={[0, 0.8, 0.01]} size={0.05} color="#ffb0a0">
                {avisoConexao}
              </Text3D>
            )}
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
                    color={
                      enviado === opcao
                        ? ARENA_COLORS.success
                        : erroJogador || errados.includes(opcao)
                          ? "#5c6b7a"
                          : ARENA_COLORS.primary
                    }
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
          {avisoConexao && (
            <Text3D position={[LOUSA_X, 0.245, LOUSA_Z]} size={0.028} color="#ffc9bd">
              {avisoConexao}
            </Text3D>
          )}
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
                  cor={
                    enviado === opcao
                      ? "#bfe8cf"
                      : erroJogador || errados.includes(opcao)
                        ? "#8fae94"
                        : "#f8fbef"
                  }
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
          nome={nomeOponente}
          pontos={pontosBot}
          position={[-0.45, -1.3, -1.9]}
          // O corpo é modelado de frente para +z; o jogador está em +z.
          rotationY={0}
        />
      ) : (
        <Oponente
          humor={humorBot}
          nome={nomeOponente}
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
