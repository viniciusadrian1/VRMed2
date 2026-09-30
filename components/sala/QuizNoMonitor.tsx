"use client";

import { useCallback, useEffect, useReducer, useRef, useState, type ReactNode } from "react";
import { useXR } from "@react-three/xr";
import { Text3D } from "@/components/arena/ui3d";
import { ALL_MODELS } from "@/lib/organs";
import { anotacoesQuizaveis, buildQuiz } from "@/lib/quiz";
import { useVRMedStore } from "@/lib/store";
import { formatDate, formatDuration, genId } from "@/lib/format";
import { track } from "@/lib/analytics";
import { ajustarVistaMonitor, type ComandoVista } from "@/lib/monitor-comparacao";
import { ALTERNATIVAS_MONITOR, iniciarQuizMonitor, modeloPermitidoNoMonitor, paginasTextoMonitor, reduzirQuizMonitor, vistaParaPonto } from "@/lib/monitor-quiz";
import type { Annotation, OrganDefinition, QuizQuestion, QuizResult, QuizTimingMode } from "@/types";
import { BotaoMonitor } from "./BotaoMonitor";
import { ModeloNoMonitor, type EstadoModeloMonitor } from "./ModeloNoMonitor";
import { useTextoMonitor } from "./MonitorAcessivel";

type InicioQuiz = { id: string; orgao: OrganDefinition; notas: Annotation[]; questoes: QuizQuestion[]; modo: QuizTimingMode };
const CONTROLES: [string, string, ComandoVista][] = [
  ["←", "Girar modelo à esquerda", "esquerda"], ["→", "Girar modelo à direita", "direita"],
  ["↑", "Inclinar modelo para cima", "cima"], ["↓", "Inclinar modelo para baixo", "baixo"],
  ["+", "Aproximar modelo", "aproximar"], ["−", "Afastar modelo", "afastar"],
];
const notasValidas = (notas: Annotation[]) => anotacoesQuizaveis(notas).filter((n) =>
  n.position.length === 3 && n.position.every(Number.isFinite));

function Configuracao({ texto, children }: { texto: string; children: ReactNode }) {
  useTextoMonitor(texto);
  return <>{children}</>;
}

/** Texto integral paginado: anotações longas não vazam da tela nem perdem conteúdo. */
function Leitura({ texto, x = 0, largura = .92, limite = 170 }: { texto: string; x?: number; largura?: number; limite?: number }) {
  const [pagina, setPagina] = useState(0);
  const paginas = paginasTextoMonitor(texto, limite);
  return <>
    <Text3D tratamento="tela" position={[x - largura / 2, .077, .004]} anchorX="left" anchorY="top" align="left"
      size={.025} maxWidth={largura}>{paginas[pagina]}</Text3D>
    {paginas.length > 1 && <>
      <BotaoMonitor titulo="←" rotuloAcessivel="Texto anterior" largura={.085} altura={.05} position={[x - largura / 2 + .043, -.139, .004]}
        desabilitado={pagina === 0} onClick={() => setPagina((p) => p - 1)} />
      <Text3D tratamento="tela" position={[x, -.139, .004]} size={.022}>{`${pagina + 1}/${paginas.length}`}</Text3D>
      <BotaoMonitor titulo="→" rotuloAcessivel="Próximo texto" largura={.085} altura={.05} position={[x + largura / 2 - .043, -.139, .004]}
        desabilitado={pagina === paginas.length - 1} onClick={() => setPagina((p) => p + 1)} />
    </>}
  </>;
}

function VistaQuestao({ dados, questao, onEstado }: { dados: InicioQuiz; questao: QuizQuestion; onEstado: (estado: EstadoModeloMonitor) => void }) {
  const ponto = dados.notas.find((n) => n.id === questao.annotationId)!.position;
  const [vista, setVista] = useState(() => vistaParaPonto(ponto));
  return <>
    <ModeloNoMonitor caminho={dados.orgao.modelPath} vista={vista} x={-.247} ponto={ponto} onEstado={onEstado} />
    {CONTROLES.map(([titulo, rotulo, comando], i) => <BotaoMonitor key={comando} titulo={titulo} rotuloAcessivel={rotulo}
      largura={.069} altura={.048} tamanho={.025} position={[-.445 + i * .079, -.135, .004]}
      onClick={() => setVista((v) => ajustarVistaMonitor(v, comando))} />)}
    <BotaoMonitor titulo="Voltar ao ponto marcado" tamanho={.023} largura={.458} altura={.06} position={[-.247, -.208, .004]}
      onClick={() => setVista(vistaParaPonto(ponto))} />
  </>;
}

function PartidaQuiz({ dados, configurar, refazer }: { dados: InicioQuiz; configurar: () => void; refazer: () => void }) {
  const [estado, enviar] = useReducer(reduzirQuizMonitor, dados.questoes, iniciarQuizMonitor);
  const [inicio] = useState(Date.now);
  const [modelo, setModelo] = useState({ id: "", estado: "verificando" as EstadoModeloMonitor });
  const [resultado, setResultado] = useState<QuizResult | null>(null);
  const [aviso, setAviso] = useState("");
  const [revisao, setRevisao] = useState<number | null>(null);
  const salvou = useRef(false);
  const session = useXR((s) => s.session);
  const [visivel, setVisivel] = useState(true);
  const adicionar = useVRMedStore((s) => s.addQuizResult), salvar = useVRMedStore((s) => s.saveSession);
  const questao = estado.questoes[estado.indice];
  const resposta = estado.respostas.find((r) => r.questionId === questao.id);
  const pronto = modelo.id === questao.id && modelo.estado === "pronto";
  const carregou = useCallback((valor: EstadoModeloMonitor) => setModelo({ id: questao.id, estado: valor }), [questao.id]);
  const pontos = estado.respostas.filter((r) => r.correct).length;
  const feedback = resposta ? `${resposta.correct ? "Você acertou!" : resposta.selected ? "Vamos revisar." : "Tempo esgotado."} Resposta correta: ${questao.correctAnswer}.` : "";
  const revisada = revisao === null ? null : estado.questoes[revisao];
  const revisadaResposta = revisada && estado.respostas.find((r) => r.questionId === revisada.id);
  const textoRevisao = revisada ? `Sua resposta: ${revisadaResposta?.selected || "Sem resposta"}. Correta: ${revisada.correctAnswer}.` : "";
  useTextoMonitor(resultado
    ? `Quiz concluído: ${pontos} de ${estado.questoes.length} acertos. ${textoRevisao} ${aviso}`
    : `Questão ${estado.indice + 1} de ${estado.questoes.length}. ${questao.prompt} ${feedback || (pronto ? "Identifique o ponto amarelo." : "Aguardando o modelo. Tempo pausado.")}`);

  useEffect(() => {
    const atualizar = () => setVisivel(!document.hidden && (!session || session.visibilityState === "visible"));
    atualizar(); document.addEventListener("visibilitychange", atualizar); session?.addEventListener("visibilitychange", atualizar);
    return () => { document.removeEventListener("visibilitychange", atualizar); session?.removeEventListener("visibilitychange", atualizar); };
  }, [session]);
  useEffect(() => {
    if (dados.modo !== "timed" || !pronto || !visivel || resposta || resultado) return;
    const timer = setTimeout(() => enviar({ tipo: "tempo", questao: questao.id }), 1000);
    return () => clearTimeout(timer);
  }, [dados.modo, pronto, visivel, resposta, resultado, estado.restante, questao.id]);

  const proxima = () => {
    if (!resposta || salvou.current) return;
    if (estado.indice === estado.questoes.length - 1) {
      // Guarda uma vez, inclusive se os dois controles forem acionados juntos.
      salvou.current = true;
      const registro: QuizResult = { id: genId(), organId: dados.orgao.id, organName: dados.orgao.name,
        score: pontos, total: estado.questoes.length, mode: dados.modo, durationMs: Date.now() - inicio, createdAt: Date.now() };
      try {
        adicionar(registro);
        salvar({ name: `Quiz — ${dados.orgao.name} — ${formatDate(registro.createdAt)}`, organId: dados.orgao.id, organName: dados.orgao.name, quizResult: registro });
      } catch { setAviso("Resultado exibido, mas o histórico não pôde ser salvo por completo."); }
      track("quiz_completed", { organ: dados.orgao.id, score: pontos, total: estado.questoes.length, mode: dados.modo });
      setResultado(registro);
    }
    enviar({ tipo: "proxima", questao: questao.id });
  };

  if (resultado) return <>
    <Text3D tratamento="tela" position={[0, .163, .004]} size={.038}>{revisada ? `Revisão ${revisao! + 1}/${estado.questoes.length}` : `${pontos} de ${estado.questoes.length} acertos`}</Text3D>
    {revisada ? <Leitura key={revisada.id} texto={textoRevisao} /> : <>
      <Text3D tratamento="tela" position={[0, .066, .004]} size={.028} maxWidth={.92}>{`${dados.orgao.name} · ${formatDuration(resultado.durationMs)}\n${pontos === estado.questoes.length ? "Muito bem! Continue explorando." : "Reveja as respostas e tente de novo."}`}</Text3D>
      <Text3D tratamento="tela" position={[0, -.06, .004]} size={.022} color="#c1d5d4" maxWidth={.92}>{aviso || "Resultado guardado no histórico deste navegador."}</Text3D>
    </>}
    <BotaoMonitor titulo={revisao === null ? "Rever respostas" : revisao + 1 === estado.questoes.length ? "Voltar ao resumo" : "Próxima revisão"}
      largura={.31} altura={.065} tamanho={.023} position={[-.32, -.22, .004]}
      onClick={() => setRevisao((i) => i === null ? 0 : i + 1 === estado.questoes.length ? null : i + 1)} />
    <BotaoMonitor titulo="Refazer quiz" largura={.27} altura={.065} tamanho={.023} position={[.005, -.22, .004]} onClick={refazer} />
    <BotaoMonitor titulo="Novo quiz" largura={.28} altura={.065} tamanho={.023} position={[.335, -.22, .004]} onClick={configurar} />
  </>;

  return <>
    <Text3D tratamento="tela" position={[-.477, .176, .004]} anchorX="left" size={.022} maxWidth={.97}>
      {`Questão ${estado.indice + 1}/${estado.questoes.length} · Identifique o ponto amarelo · ${dados.modo === "timed" ? pronto && visivel ? `${estado.restante}s` : "Tempo pausado" : "Tempo livre"}`}
    </Text3D>
    <VistaQuestao key={questao.id} dados={dados} questao={questao} onEstado={carregou} />
    {!resposta ? <>
      {questao.options.map((opcao, i) => {
        const b = ALTERNATIVAS_MONITOR[i];
        return <BotaoMonitor key={opcao} titulo={`${"ABCD"[i]}. ${opcao.length > 54 ? `${opcao.slice(0, 51)}…` : opcao}`} rotuloAcessivel={`${"ABCD"[i]}. ${opcao}`}
          largura={b.w} altura={b.h} position={[b.x, b.y, .004]} tamanho={opcao.length > 30 ? .019 : .024} desabilitado={!pronto || !visivel}
          onClick={() => { if (pronto && visivel) enviar({ tipo: "responder", questao: questao.id, opcao }); }} />;
      })}
      <Text3D tratamento="tela" position={[.244, -.211, .004]} size={.02} maxWidth={.46} color="#c1d5d4">{`${pontos} acerto(s) · Gire para explorar.\nMenu encerra este quiz.`}</Text3D>
    </> : <>
      <Text3D tratamento="tela" position={[.244, .116, .004]} size={.029} color={resposta.correct ? "#a4ebba" : "#ffd08b"}>{resposta.correct ? "Correto!" : "Resposta registrada"}</Text3D>
      <Leitura key={questao.id} texto={feedback} x={.244} largura={.446} limite={100} />
      <BotaoMonitor titulo={estado.indice + 1 === estado.questoes.length ? "Ver resultado" : "Próxima questão"} largura={.46} altura={.065} tamanho={.026}
        position={[.244, -.22, .004]} onClick={proxima} />
    </>}
  </>;
}

/** Reutiliza as anotações, gerador, tempo e histórico do Quiz do site; não cria outro Canvas. */
export function QuizNoMonitor({ abrirEstudo }: { abrirEstudo: () => void }) {
  const hidratado = useVRMedStore((s) => s.hasHydrated);
  const anotacoes = useVRMedStore((s) => s.annotationsByOrgan);
  const [orgaoId, setOrgaoId] = useState<string | null>(null), [pagina, setPagina] = useState(0);
  const [quantidade, setQuantidade] = useState(5), [modo, setModo] = useState<QuizTimingMode>("free");
  const [partida, setPartida] = useState<InicioQuiz | null>(null);
  const orgaos = ALL_MODELS.filter((o) => modeloPermitidoNoMonitor(o.id) && notasValidas(anotacoes[o.id] ?? []).length > 0);
  const escolhido = orgaos.find((o) => o.id === orgaoId);
  const iniciar = () => {
    if (!escolhido) return;
    const notas = notasValidas(anotacoes[escolhido.id] ?? []), questoes = buildQuiz(notas, quantidade);
    if (!questoes.length) return;
    setPartida({ id: genId(), orgao: escolhido, notas, questoes, modo });
    track("quiz_started", { organ: escolhido.id, count: questoes.length, mode: modo });
  };
  // O filho anuncia as perguntas; a configuração só anuncia quando está ativa.
  if (partida) return <PartidaQuiz key={partida.id} dados={partida} configurar={() => setPartida(null)} refazer={iniciar} />;
  const texto = !hidratado ? "Carregando anotações…" : orgaos.length ? "Configure o quiz das suas anotações, sem sair da sala." : "O Quiz usa suas anotações salvas neste navegador. Abra Estudo 3D, marque estruturas e nomeie os pontos. Miologia não está disponível no monitor por segurança no Quest.";
  return <Configuracao texto={texto}>
    {!hidratado || orgaos.length === 0 ? <>
      <Text3D tratamento="tela" position={[0, .131, .004]} size={.037}>{hidratado ? "Prepare suas perguntas" : "Carregando…"}</Text3D>
      <Text3D tratamento="tela" position={[0, -.015, .004]} size={.027} maxWidth={.9}>{texto}</Text3D>
      {hidratado && <BotaoMonitor titulo="Ir para Estudo 3D…" largura={.53} altura={.075} position={[0, -.21, .004]} onClick={abrirEstudo} />}
    </> : <>
      <Text3D tratamento="tela" position={[-.26, .17, .004]} size={.026}>Escolha o modelo</Text3D>
      {orgaos.slice(pagina * 3, pagina * 3 + 3).map((o, i) => <BotaoMonitor key={o.id} titulo={o.name}
        largura={.45} altura={.069} tamanho={.023} position={[-.25, .098 - i * .083, .004]}
        selecionado={o.id === orgaoId} onClick={() => setOrgaoId(o.id)} />)}
      {orgaos.length > 3 && <>
        <BotaoMonitor titulo="←" rotuloAcessivel="Modelos anteriores" largura={.09} altura={.048} position={[-.425, -.144, .004]} desabilitado={pagina === 0} onClick={() => setPagina((p) => p - 1)} />
        <Text3D tratamento="tela" position={[-.25, -.144, .004]} size={.022}>{`${pagina + 1}/${Math.ceil(orgaos.length / 3)}`}</Text3D>
        <BotaoMonitor titulo="→" rotuloAcessivel="Próximos modelos" largura={.09} altura={.048} position={[-.075, -.144, .004]} desabilitado={(pagina + 1) * 3 >= orgaos.length} onClick={() => setPagina((p) => p + 1)} />
      </>}
      <Text3D tratamento="tela" position={[.254, .17, .004]} size={.026}>Até quantas questões?</Text3D>
      {[3, 5, 10].map((n, i) => <BotaoMonitor key={n} titulo={`${n}`} rotuloAcessivel={`Até ${n} questões`} selecionado={quantidade === n}
        largura={.126} altura={.063} position={[.1 + i * .149, .098, .004]} onClick={() => setQuantidade(n)} />)}
      <BotaoMonitor titulo="Tempo livre" largura={.436} altura={.061} selecionado={modo === "free"} tamanho={.025} position={[.25, .008, .004]} onClick={() => setModo("free")} />
      <BotaoMonitor titulo="25s por questão" largura={.436} altura={.061} selecionado={modo === "timed"} tamanho={.025} position={[.25, -.068, .004]} onClick={() => setModo("timed")} />
      <Text3D tratamento="tela" position={[.25, -.144, .004]} size={.02} maxWidth={.44}>{escolhido ? `${Math.min(quantidade, notasValidas(anotacoes[escolhido.id] ?? []).length)} questão(ões) disponível(is)` : "Selecione um modelo anotado."}</Text3D>
      <BotaoMonitor titulo="Iniciar quiz no monitor" largura={.73} altura={.077} position={[0, -.222, .004]} desabilitado={!escolhido} onClick={iniciar} />
    </>}
  </Configuracao>;
}
