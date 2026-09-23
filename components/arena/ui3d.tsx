"use client";

import { useRef, type ReactNode, type RefObject } from "react";
import { Text } from "@react-three/drei";
import { useFrame, type ThreeEvent } from "@react-three/fiber";
import { useXRInputSourceState } from "@react-three/xr";
import { preloadFont } from "troika-three-text";
import * as THREE from "three";
import { playClique, playHover } from "@/lib/arena-audio";
import { pulsar } from "@/lib/xr-haptica";
import { CAMADAS_UI3D, deveAcionarBotao3D, fonteDoPonteiro, ORDEM_PONTEIRO_UI } from "@/lib/botao3d-interacao";

/**
 * Primitivas de interface em espaço 3D para a Arena.
 *
 * Toda a UI do app é DOM (React/Tailwind) e **não é renderizada dentro de uma
 * sessão immersive-vr** — por isso nada de texto aparecia no headset. Aqui a
 * interface é geometria de verdade, desenhada na cena.
 *
 * A fonte é **local e explícita**: o `<Text>` do drei (troika) busca a fonte
 * padrão em cdn.jsdelivr.net e, sem rede, não desenha absolutamente nada.
 * No evento a rede pode cair, então a fonte viaja com o projeto.
 */
export const ARENA_FONT = "/fonts/inter-600.woff";

/**
 * Constrói o atlas da fonte antes da partida.
 *
 * Cada glifo novo obriga o troika a reconstruir o atlas SDF — se isso
 * acontecer no meio da rodada (um "ó" que ainda não apareceu, por exemplo),
 * o headset engasga. Pré-carregando dígitos, acentos e pontuação, o custo
 * fica todo no carregamento da página.
 *
 * REGRA: qualquer glifo novo usado em <Text3D> (todos os modos passam por
 * aqui — Arena, Duelo e Sala) precisa (1) existir em inter-600.woff E (2)
 * entrar na string abaixo. Glifo fora da fonte faz o troika buscar um
 * fallback na CDN (jsdelivr) em runtime — proibido no evento sem rede.
 */
// Só no navegador: o troika usa `self` e quebraria a pré-renderização.
if (typeof window !== "undefined") {
  preloadFont(
    {
      font: ARENA_FONT,
      characters:
        "ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789 ·×ÁÂÃÀÇÉÊÍÓÔÕÚáâãàçéêíóôõú.,:!?()-<>↓…—+/_",
    },
    () => {},
  );
}

/**
 * Paleta da Arena — mesma linguagem clínica do resto do app.
 *
 * `panel` é o fundo da cena (clearColor da Arena), não a cor dos painéis: ele
 * passa pelo gerenciamento de cor do three e SEMPRE foi desenhado certo. Com
 * os painéis agora em sRGB de verdade (ver `panelTexture`), eles ficaram no
 * tom autorado — então o fundo desceu um degrau para as placas voltarem a
 * parecer superfícies FLUTUANDO sobre a sala, e não recortes do mesmo cinza.
 */
export const ARENA_COLORS = {
  primary: "#5896c8",
  panel: "#0b1118",
  text: "#f3f6f8",
  muted: "#9fb3c4",
  success: "#4fae89",
  danger: "#e06a5c",
} as const;

/** Iluminação de estudo compartilhada pela Arena e pelo Duelo. */
export function LuzEstudio() {
  return (
    <>
      <directionalLight position={[4, 6, 4]} intensity={2.05} color="#ffeedd" />
      <directionalLight position={[-5, 3, -4]} intensity={0.65} color="#9fc3dd" />
      <hemisphereLight args={["#dfe9f2", "#141a22", 0.42]} />
    </>
  );
}

/** Botão sem resposta: cinza-azulado dessaturado, longe do azul de ação. */
const COLOR_DESABILITADO = "#39454f";
/** Rótulo do botão desabilitado — legível, mas claramente apagado. */
const TEXTO_DESABILITADO = "#7b8894";

/**
 * Material-base do texto. Com `outlineWidth`, o troika expõe `material` como
 * ARRAY [contorno, texto] — então `material-depthTest={false}` caía no array e
 * nunca chegava ao shader: o texto era depth-testado e sumia atrás de qualquer
 * transparência à frente (a divisória de vidro do hospital apagava metade do
 * painel do Duelo). Os derivados herdam depthTest/toneMapped por protótipo; a
 * cor vira propriedade própria de cada texto (o troika cuida disso).
 *
 * É o mesmo array que impede animar OPACIDADE de texto: `material-opacity`
 * também cairia no array. Quem anima entrada de tela usa `Entrada` (escala e
 * profundidade), nunca opacidade.
 */
const TEXT_MATERIAL = new THREE.MeshBasicMaterial({
  transparent: true,
  side: THREE.DoubleSide,
  // A interface nunca pode ser engolida pelo modelo — o jogador pode
  // escalá-lo até 6× e cobrir o painel que ele precisa clicar.
  depthTest: false,
  depthWrite: false,
  // Sem tonemapping o texto mantém o contraste dentro do headset.
  toneMapped: false,
});

interface Text3DProps {
  children: ReactNode;
  position?: [number, number, number];
  size?: number;
  color?: string;
  /** Largura máxima antes de quebrar a linha, em metros. */
  maxWidth?: number;
  anchorY?: "top" | "middle" | "bottom";
}

/** Texto 3D com a fonte local já aplicada. Use sempre este, nunca o <Text> direto. */
export function Text3D({
  children,
  position,
  size = 0.12,
  color = ARENA_COLORS.text,
  maxWidth,
  anchorY = "middle",
}: Text3DProps) {
  return (
    <Text
      font={ARENA_FONT}
      position={position}
      fontSize={size}
      color={color}
      maxWidth={maxWidth}
      anchorX="center"
      anchorY={anchorY}
      textAlign="center"
      // Contorno escuro: o texto passa por cima de um modelo claro.
      outlineWidth={size * 0.05}
      outlineColor="#04070c"
      material={TEXT_MATERIAL}
      renderOrder={CAMADAS_UI3D.texto}
      // Texto não intercepta o laser: o clique atravessa até o modelo.
      raycast={() => null}
    >
      {children}
    </Text>
  );
}

/**
 * Textura de painel desenhada em runtime (canvas): cantos arredondados,
 * preenchimento com leve gradiente e borda de acento. Gerada localmente —
 * zero rede, zero asset — e cacheada por proporção e cor.
 */
const panelTextureCache = new Map<string, THREE.CanvasTexture>();

function panelTexture(
  aspect: number,
  fill: string,
  stroke: string,
  fillBottom = "#0d151d",
  espessura = 3,
): THREE.CanvasTexture {
  const key = `${aspect.toFixed(1)}|${fill}|${stroke}|${fillBottom}|${espessura}`;
  const cached = panelTextureCache.get(key);
  if (cached) return cached;

  const w = 512;
  const h = Math.round(Math.min(512, Math.max(96, 512 / aspect)));
  const canvas = document.createElement("canvas");
  canvas.width = w;
  canvas.height = h;
  const ctx = canvas.getContext("2d")!;
  const r = Math.min(28, h * 0.22);

  ctx.beginPath();
  ctx.roundRect(3, 3, w - 6, h - 6, r);
  const gradient = ctx.createLinearGradient(0, 0, 0, h);
  gradient.addColorStop(0, fill);
  gradient.addColorStop(1, fillBottom);
  ctx.fillStyle = gradient;
  ctx.fill();
  ctx.lineWidth = espessura;
  ctx.strokeStyle = stroke;
  ctx.stroke();

  const texture = new THREE.CanvasTexture(canvas);
  /**
   * O canvas é pintado em sRGB, mas a CanvasTexture nasce em `NoColorSpace`:
   * o renderer tratava esses bytes como LINEARES e aplicava a conversão de
   * saída por cima, clareando tudo (`#101820` chegava à tela como `#45545f`).
   * Cada painel e cada botão do app estavam lavados — o mesmo motivo pelo qual
   * AmbienteHospital e SalaScene já marcam `SRGBColorSpace` nas texturas deles.
   */
  texture.colorSpace = THREE.SRGBColorSpace;
  texture.anisotropy = 4;
  panelTextureCache.set(key, texture);
  return texture;
}

/**
 * Base escura do gradiente, derivada da PRÓPRIA cor do botão.
 *
 * O valor fixo antigo (`#2d5a80`) era um azul: qualquer botão que passasse
 * outra cor (o "×" cinza da Sala, o verde da resposta certa) ganhava um pé
 * azul que não tinha nada a ver com o topo. Multiplicar no espaço linear
 * escurece qualquer matiz mantendo o tom — e o resultado é cacheado, porque
 * ele vira chave da textura.
 */
const sombraCache = new Map<string, string>();
function sombra(cor: string, fator = 0.55): string {
  const chave = `${cor}|${fator}`;
  let hex = sombraCache.get(chave);
  if (!hex) {
    hex = `#${new THREE.Color(cor).multiplyScalar(fator).getHexString()}`;
    sombraCache.set(chave, hex);
  }
  return hex;
}

/** Painel de fundo arredondado, para dar leitura ao texto sobre qualquer cena. */
export function Panel({
  width,
  height,
  // Reautorado junto com a correção de espaço de cor: o `#0d141c` antigo foi
  // escolhido olhando o resultado lavado e, desenhado certo, virava um buraco
  // preto no headset. `#16212c` devolve a placa ao cinza-azulado pretendido.
  color = "#16212c",
  opacity = 0.92,
  position,
  children,
}: {
  width: number;
  height: number;
  color?: string;
  opacity?: number;
  position?: [number, number, number];
  children?: ReactNode;
}) {
  return (
    <group position={position}>
      {/* raycast nulo: o painel é pano de fundo, não alvo do laser — sem
          isso ele bloquearia os cliques no modelo atrás dele. */}
      <mesh renderOrder={CAMADAS_UI3D.painel} raycast={() => null}>
        <planeGeometry args={[width, height]} />
        <meshBasicMaterial
          map={panelTexture(width / height, color, "rgba(88,150,200,0.45)")}
          transparent
          opacity={opacity}
          depthWrite={false}
          side={THREE.DoubleSide}
          toneMapped={false}
          depthTest={false}
        />
      </mesh>
      {children}
    </group>
  );
}

/**
 * Botão 3D: reage ao laser do controle (ou da mão) e ao gatilho.
 * Alvo estável, independente da animação visual. No XR confirma ao apertar
 * o gatilho; mouse/toque continuam usando o clique convencional.
 */
export function Button3D({
  label,
  onClick,
  width = 1.1,
  height = 0.3,
  position,
  color = ARENA_COLORS.primary,
  icone = false,
  selo,
  destaque = null,
  desabilitado = false,
}: {
  label: string;
  onClick: () => void;
  width?: number;
  height?: number;
  position?: [number, number, number];
  color?: string;
  /**
   * Triângulo de "play" à esquerda do rótulo. Era desenhado SEMPRE — inclusive
   * no dígito "7" do teclado 3D e no "Apagar" —, o que ensinava o jogador a
   * ignorar a iconografia. Agora é opt-in, e só onde significa "começa aqui".
   */
  icone?: boolean;
  /** Letra da alternativa (A/B/C/D) num quadradinho à esquerda do rótulo. */
  selo?: string;
  /** Revelação da resposta: verde na certa, coral na que a pessoa errou. */
  destaque?: "certo" | "errado" | null;
  /** Fora da rodada o botão continua na tela, mas não responde. */
  desabilitado?: boolean;
}) {
  const group = useRef<THREE.Group>(null);
  const hovered = useRef(new Set<number>());
  const pressionado = useRef(new Set<number>());
  const contorno = useRef<THREE.Mesh>(null);
  const scale = useRef(1);
  const esquerdo = useXRInputSourceState("controller", "left");
  const direito = useXRInputSourceState("controller", "right");

  useFrame((_, delta) => {
    if (!group.current) return;
    const ativo = hovered.current.size > 0 && !desabilitado;
    if (contorno.current) contorno.current.visible = ativo;
    // Só o desenho comprime; a malha clicável permanece nas dimensões reais.
    // Sem crescer para dentro da alternativa vizinha, mesmo com dois lasers.
    const target = pressionado.current.size > 0 && !desabilitado ? 0.985 : 1;
    scale.current += (target - scale.current) * Math.min(1, delta * 12);
    group.current.scale.setScalar(scale.current);
  });

  const stop = (event: ThreeEvent<PointerEvent>) => event.stopPropagation();
  const acionar = (event: object) => {
    if (desabilitado) return;
    playClique();
    pulsar(fonteDoPonteiro(event) ?? direito?.inputSource ?? esquerdo?.inputSource, 0.4, 35);
    onClick();
  };

  // Verde e coral mais claros que os da paleta: na revelação a placa certa
  // precisa saltar de relance a 3 m, e o `success` normal fica escuro demais
  // ao lado do `danger` (que é bem mais luminoso).
  // O destaque vem ANTES de `desabilitado`: na revelação as alternativas
  // ficam mudas e imóveis (não respondem a clique nem a hover), mas a certa
  // precisa continuar acesa — senão o cinza apagaria justamente a informação
  // pela qual a tela existe.
  const corFundo =
    destaque === "certo"
      ? "#3fd49a"
      : destaque === "errado"
        ? "#f0796a"
        : desabilitado
          ? COLOR_DESABILITADO
          : color;
  const corTexto = desabilitado && !destaque ? TEXTO_DESABILITADO : ARENA_COLORS.text;
  // Ícone e selo ocupam a esquerda da placa; sem eles o rótulo volta ao centro.
  const seloLado = height * 0.52;
  const rotuloX = selo ? height * 0.2 : icone ? height * 0.14 : 0;

  return (
    <group
      position={position}
      pointerEventsOrder={ORDEM_PONTEIRO_UI}
      onClick={(event) => {
        event.stopPropagation();
        if (deveAcionarBotao3D("clicar", event)) acionar(event);
      }}
      onPointerOver={(event) => {
        stop(event);
        // Só na ENTRADA do hover: o R3F dispara onPointerOver a cada quadro em
        // que o laser se move sobre o alvo, e vibrar 90 vezes por segundo
        // esquenta o motor e vira ruído branco na mão.
        if (hovered.current.has(event.pointerId)) return;
        hovered.current.add(event.pointerId);
        if (desabilitado) return;
        playHover();
        pulsar(fonteDoPonteiro(event) ?? direito?.inputSource ?? esquerdo?.inputSource, 0.15, 15);
      }}
      onPointerOut={(event) => {
        hovered.current.delete(event.pointerId);
        pressionado.current.delete(event.pointerId);
      }}
      onPointerDown={(event) => {
        stop(event);
        if (desabilitado || event.button !== 0) return;
        pressionado.current.add(event.pointerId);
        if (deveAcionarBotao3D("pressionar", event)) acionar(event);
      }}
      onPointerUp={(event) => {
        stop(event);
        pressionado.current.delete(event.pointerId);
      }}
      onPointerCancel={(event) => {
        hovered.current.delete(event.pointerId);
        pressionado.current.delete(event.pointerId);
      }}
    >
      {/* Este é o único alvo: nunca encolhe, cresce ou muda de profundidade. */}
      <mesh name={`alvo-botao-${selo ?? label}`}>
        <planeGeometry args={[width, height]} />
        <meshBasicMaterial transparent opacity={0} depthWrite={false} side={THREE.DoubleSide} />
      </mesh>
      <group ref={group} pointerEvents="none">
      {/* Camadas explícitas: o fundo não pode cobrir botões pela distância. */}
      <mesh renderOrder={CAMADAS_UI3D.botao} raycast={() => null}>
        <planeGeometry args={[width, height]} />
        <meshBasicMaterial
          map={panelTexture(
            width / height,
            corFundo,
            // Borda quase branca no destaque: a 3 m, o verde do fundo sozinho
            // se confunde com as placas vizinhas — a moldura é o que separa.
            destaque
              ? "rgba(255,255,255,0.95)"
              : desabilitado
                ? "rgba(255,255,255,0.18)"
                : "rgba(255,255,255,0.55)",
            sombra(corFundo, destaque ? 0.78 : undefined),
          )}
          transparent
          depthWrite={false}
          toneMapped={false}
          depthTest={false}
          side={THREE.DoubleSide}
        />
      </mesh>
      <mesh ref={contorno} visible={false} position={[0, 0, 0.003]} renderOrder={CAMADAS_UI3D.contorno} raycast={() => null}>
        <planeGeometry args={[width, height]} />
        <meshBasicMaterial
          map={panelTexture(width / height, "rgba(0,0,0,0)", "#b6f4ff", "rgba(0,0,0,0)", 6)}
          transparent depthWrite={false} depthTest={false} toneMapped={false}
        />
      </mesh>

      {/* Triângulo "play" em geometria pura: o botão continua reconhecível
          como clicável mesmo se a fonte falhar em carregar (rede ruim). */}
      {icone && (
        <mesh
          position={[-width / 2 + height * 0.42, 0, 0.004]}
          rotation={[0, 0, -Math.PI / 2]}
          renderOrder={CAMADAS_UI3D.contorno}
          raycast={() => null}
        >
          <circleGeometry args={[height * 0.22, 3]} />
          <meshBasicMaterial
            color={corTexto}
            transparent
            depthWrite={false}
            toneMapped={false}
            depthTest={false}
          />
        </mesh>
      )}

      {/* Selo da alternativa: keycap claro com a letra na cor do botão. A 2 m
          a letra é o que a pessoa lê primeiro para decidir onde mirar. */}
      {selo && (
        <group position={[-width / 2 + height * 0.45, 0, 0.004]}>
          <mesh renderOrder={CAMADAS_UI3D.contorno} raycast={() => null}>
            <planeGeometry args={[seloLado, seloLado]} />
            <meshBasicMaterial
              color={corTexto}
              transparent
              opacity={desabilitado ? 0.45 : 0.92}
              depthWrite={false}
              toneMapped={false}
              depthTest={false}
            />
          </mesh>
          <Text3D position={[0, 0, 0.002]} size={seloLado * 0.62} color={corFundo}>
            {selo}
          </Text3D>
        </group>
      )}

      {/* maxWidth: sem ele "Aguardando o adversário…" transbordava a placa e
          escorria para fora do botão. */}
      <Text3D
        position={[rotuloX, 0, 0.005]}
        // Duas linhas medem ~1,02 × a altura da placa: qualquer rótulo que
        // quebre transborda. Quem tem rótulo longo passa uma largura maior.
        size={height * 0.42}
        color={corTexto}
        maxWidth={width * 0.86}
      >
        {label}
      </Text3D>
      </group>
    </group>
  );
}

/** "+100" que sobe e some no ponto do acerto — resposta imediata e local. */
export function Floater({
  value,
  position,
}: {
  value: number;
  position: [number, number, number];
}) {
  const group = useRef<THREE.Group>(null);
  const life = useRef(0);

  useFrame((_, delta) => {
    if (!group.current) return;
    life.current += Math.min(delta, 1 / 30);
    const t = life.current;
    group.current.position.y = position[1] + t * 0.35;
    // Cresce rápido no início, encolhe até sumir no fim.
    const scale = t < 0.12 ? t / 0.12 : Math.max(0, 1 - (t - 0.45) / 0.35);
    group.current.scale.setScalar(Math.max(0.001, scale));
  });

  return (
    <group ref={group} position={position}>
      <Text3D size={0.11} color={ARENA_COLORS.success}>
        {`+${value}`}
      </Text3D>
    </group>
  );
}

/**
 * Chegada de uma tela: a placa vem de um pouco atrás e de um pouco menor até
 * assentar. Troca instantânea de painel dentro do headset parece BUG — o olho
 * não vê uma transição, vê um corte —, e 0,18 s bastam para o cérebro
 * entender que a informação é nova.
 *
 * Anima escala e profundidade, nunca opacidade: com `outlineWidth` o troika
 * expõe `material` como array e `material-opacity` cairia no array sem nunca
 * chegar ao shader (ver o comentário de TEXT_MATERIAL).
 *
 * Use com `key={fase}` para a animação recomeçar a cada tela.
 */
export function Entrada({
  children,
  dur = 0.18,
  atraso = 0,
}: {
  children: ReactNode;
  dur?: number;
  atraso?: number;
}) {
  const group = useRef<THREE.Group>(null);
  const tempo = useRef(0);

  useFrame((_, delta) => {
    const g = group.current;
    // Para de escrever assim que assenta: é uma animação de 0,18 s, não vale
    // um write por quadro pelo resto da partida.
    if (!g || tempo.current > atraso + dur) return;
    tempo.current += Math.min(delta, 1 / 30);
    const p = Math.min(1, Math.max(0, (tempo.current - atraso) / dur));
    const e = 1 - (1 - p) ** 3; // ease-out cúbico: rápido no início, freia no fim
    g.scale.setScalar(0.92 + 0.08 * e);
    g.position.z = -0.04 + 0.04 * e;
  });

  return (
    <group ref={group} scale={0.92} position={[0, 0, -0.04]}>
      {children}
    </group>
  );
}

/**
 * Cores da barra de tempo. Instâncias de módulo porque o `useFrame` copia
 * delas a cada quadro — criar `THREE.Color` a 90 Hz é lixo para o coletor.
 */
const BARRA_OK = new THREE.Color("#7dd3fc");
const BARRA_ALERTA = new THREE.Color("#ffb020");
const BARRA_CRITICO = new THREE.Color("#ff6b57");

/**
 * Barra que drena com o tempo da rodada.
 *
 * O número em segundos exige LER; a barra é periférica — a pessoa sabe que o
 * tempo está acabando sem tirar os olhos do órgão. A fração vem por ref e é
 * lida DENTRO do useFrame: a 90 Hz, um `setState` por quadro derruba o Quest
 * sozinho, então escala e cor vão direto no objeto three.
 *
 * A mudança de cor é gradual (sem piscar): azul até 50%, âmbar em 33%, coral
 * em 15%, interpolando entre as faixas.
 */
export function BarraTempo({
  width,
  height = 0.024,
  position,
  fracaoRef,
}: {
  width: number;
  height?: number;
  position?: [number, number, number];
  /** Fração restante, de 1 a 0. Lida por quadro, nunca durante o render. */
  fracaoRef: RefObject<number>;
}) {
  const preenchimento = useRef<THREE.Group>(null);
  const barra = useRef<THREE.Mesh>(null);

  useFrame(() => {
    const g = preenchimento.current;
    const m = barra.current;
    if (!g || !m) return;
    const f = Math.min(1, Math.max(0, fracaoRef.current));
    // Nunca zero: escala 0 em three deixa a matriz sem inversa e polui o
    // console com avisos de matriz degenerada.
    g.scale.x = Math.max(0.0001, f);

    const cor = (m.material as THREE.MeshBasicMaterial).color;
    if (f >= 0.5) cor.copy(BARRA_OK);
    else if (f >= 0.33) cor.copy(BARRA_ALERTA).lerp(BARRA_OK, (f - 0.33) / 0.17);
    else if (f >= 0.15)
      cor.copy(BARRA_CRITICO).lerp(BARRA_ALERTA, (f - 0.15) / 0.18);
    else cor.copy(BARRA_CRITICO);
  });

  return (
    <group position={position}>
      {/* Trilho: sem ele a barra encurtando não tem contra quê ser medida. */}
      <mesh renderOrder={998} raycast={() => null}>
        <planeGeometry args={[width, height]} />
        <meshBasicMaterial
          color="#0a1119"
          transparent
          opacity={0.85}
          toneMapped={false}
          depthTest={false}
        />
      </mesh>
      {/*
        Ancorada à ESQUERDA: o grupo externo leva a origem para a ponta
        esquerda e normaliza a largura, então o plano unitário em x=0.5 ocupa
        [0, 1] e escalar em x drena a barra da direita para a esquerda —
        escalar o mesh direto encolheria pelos dois lados, para o centro.
      */}
      <group position={[-width / 2, 0, 0.001]} scale={[width, 1, 1]}>
        <group ref={preenchimento}>
          <mesh ref={barra} position={[0.5, 0, 0]} renderOrder={999} raycast={() => null}>
            <planeGeometry args={[1, height]} />
            {/* Mesma fila transparente do painel: renderOrder sozinho não
                coloca uma malha opaca depois de uma placa transparente. */}
            <meshBasicMaterial transparent depthWrite={false} toneMapped={false} depthTest={false} />
          </mesh>
        </group>
      </group>
    </group>
  );
}
