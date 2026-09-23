"use client";

import { useState } from "react";
import { TextoPainelXR as Text3D, SuperficieXR, CaixaSelecaoXR, useTemaPainelXR } from "./EstiloPainelXR";
import { useJanelasEstudoXR } from "@/lib/janelas-estudo-xr";
import { useTutor3D } from "@/lib/tutor-3d-store";
import { useVRMedStore } from "@/lib/store";
import { paginasXR } from "@/lib/painel-estudo-xr";
import { cancelarConversaTutor, enviarPerguntaTutor, limparConversaTutor, repetirPerguntaTutor, useConversaTutor } from "@/lib/tutor-conversa";
import { BotaoXR, PainelXRBase, PaginacaoXR, TecladoXR } from "./PainelXRBase";

/** Mesma conversa do site, em cartões legíveis e manipuláveis no mundo 3D. */
export function TutorPainelVR() {
  const aberto = useJanelasEstudoXR((s) => s.abertas.tutor), tema = useTemaPainelXR();
  const [escrevendo, setEscrevendo] = useState(false), [rascunho, setRascunho] = useState("");
  const [mensagemId, setMensagemId] = useState<string | null>(null), [pagina, setPagina] = useState(0);
  const [confirmarLimpeza, setConfirmarLimpeza] = useState(false);
  const chat = useVRMedStore((s) => s.chat), inspecionado = useVRMedStore((s) => s.inspectedLabel);
  const contexto = useTutor3D((s) => s.contexto), guia = useTutor3D((s) => s.ativo), foco = useTutor3D((s) => s.foco);
  const ocupado = useConversaTutor((s) => s.ocupado), erro = useConversaTutor((s) => s.erro);
  const alvo = contexto?.alvos.find((a) => a.label === inspecionado)?.label ?? contexto?.alvos[0]?.label ?? "modelo";
  const indice = mensagemId ? chat.findIndex((m) => m.id === mensagemId) : chat.length - 1;
  const atual = Math.max(0, indice < 0 ? chat.length - 1 : indice), mensagem = chat[atual];
  const pergunta = mensagem?.role === "assistant" ? chat.slice(0, atual).findLast((m) => m.role === "user")?.content : null;
  const resumoPergunta = paginasXR(pergunta ?? "", 35, 2);
  const paginas = paginasXR(erro || mensagem?.content || (ocupado ? "Preparando explicação..." : "Pergunte sobre o modelo para explorar. Use as sugestões ou escreva sua dúvida."), 30, 5);
  const paginaAtual = Math.min(pagina, paginas.length - 1), doAluno = !erro && mensagem?.role === "user";
  const enviar = (pergunta: string) => {
    setConfirmarLimpeza(false); setEscrevendo(false); setRascunho(""); setMensagemId(null); setPagina(0);
    void enviarPerguntaTutor(pergunta);
  };
  const escolherMensagem = (i: number) => { setMensagemId(chat[i]?.id ?? null); setPagina(0); };
  return <PainelXRBase titulo="Tutor de IA" aberto={aberto} aoAlternar={() => useJanelasEstudoXR.getState().abrir("tutor", !aberto)}>
    {escrevendo ? <TecladoXR texto={rascunho} aoMudar={setRascunho} aoCancelar={() => setEscrevendo(false)} aoConfirmar={() => enviar(rascunho)} /> : <>
      <Text3D position={[-0.475, 0.44, 0.025]} size={0.018} anchorX="left" color="muted">Respostas curtas, com base nos tratados de anatomia</Text3D>
      <BotaoXR label="Limpar" x={0.30} y={0.482} largura={0.16} tamanho={0.021} variante="ghost" desabilitado={!chat.length || ocupado}
        onClick={() => setConfirmarLimpeza(!confirmarLimpeza)} />
      <CaixaSelecaoXR x={-0.433} y={0.365} ativo={guia} onClick={() => useTutor3D.getState().habilitar(!guia)} />
      <Text3D position={[-0.374, 0.365, 0.03]} size={0.026} anchorX="left">Guiar no modelo 3D</Text3D>
      <BotaoXR label="Limpar foco" x={0.34} y={0.365} largura={0.27} tamanho={0.021} variante="ghost" desabilitado={!foco} onClick={() => useTutor3D.getState().limparFoco()} />
      <Text3D position={[-0.46, 0.305, 0.025]} size={0.022} anchorX="left" maxWidth={0.93} color="muted">
        {foco ? `Foco: ${foco.label}` : "Destaque de estruturas; câmera livre em AR e VR"}
      </Text3D>
      {pergunta && <group>
        <SuperficieXR x={0.075} y={0.218} largura={0.80} altura={0.125} cor={tema.primary} />
        <Text3D position={[0.44, 0.257, 0.025]} anchorX="right" anchorY="top" size={0.022} maxWidth={0.73} color={tema.primaryForeground}>
          {resumoPergunta[0] + (resumoPergunta.length > 1 ? "..." : "")}
        </Text3D>
      </group>}
      {!pergunta && <Text3D position={[-0.46, 0.227, 0.025]} size={0.024} anchorX="left" color="muted">Sua conversa de estudo</Text3D>}
      <SuperficieXR x={-0.434} y={0.104} largura={0.064} altura={0.059} cor={tema.accent} />
      <Text3D position={[-0.434, 0.104, 0.03]} size={0.022} color="primary">{doAluno ? "Eu" : "IA"}</Text3D>
      {doAluno && <SuperficieXR x={0.062} y={0.018} largura={0.82} altura={0.218} cor={tema.primary} />}
      <Text3D position={[-0.335, 0.109, 0.03]} anchorX="left" anchorY="top" size={0.026} maxWidth={0.78}
        color={erro ? "danger" : doAluno ? tema.primaryForeground : undefined}>{paginas[paginaAtual]}</Text3D>
      <PaginacaoXR pagina={paginaAtual} total={paginas.length} aoMudar={setPagina} y={-0.142} />
      <BotaoXR label="Anterior" x={-0.335} y={-0.232} largura={0.25} variante="ghost" desabilitado={atual === 0 || !chat.length} onClick={() => escolherMensagem(atual - 1)} />
      <Text3D position={[0, -0.232, 0.03]} size={0.021} color="muted">{chat.length ? `Mensagem ${atual + 1}/${chat.length}` : "Histórico compartilhado"}</Text3D>
      <BotaoXR label="Seguinte" x={0.335} y={-0.232} largura={0.25} variante="ghost" desabilitado={!chat.length || atual === chat.length - 1} onClick={() => escolherMensagem(atual + 1)} />
      <BotaoXR label="Explicar estrutura" x={-0.245} y={-0.32} largura={0.43} desabilitado={ocupado || !contexto} onClick={() => enviar(`Explique ${alvo} e destaque no modelo se estiver disponível.`)} />
      <BotaoXR label="Qual a função?" x={0.245} y={-0.32} largura={0.43} desabilitado={ocupado || !contexto} onClick={() => enviar(`Qual a função de ${alvo}? Explique de forma simples.`)} />
      {confirmarLimpeza ? <group>
        <BotaoXR label="Apagar conversa" x={-0.21} y={-0.414} largura={0.5} onClick={() => { limparConversaTutor(); setMensagemId(null); setPagina(0); setConfirmarLimpeza(false); }} />
        <BotaoXR label="Cancelar" x={0.3} y={-0.414} largura={0.32} onClick={() => setConfirmarLimpeza(false)} />
      </group> : ocupado ? <BotaoXR label="Parar resposta" y={-0.414} largura={0.94} onClick={cancelarConversaTutor} /> :
        erro ? <BotaoXR label="Tentar novamente" y={-0.414} largura={0.94} onClick={repetirPerguntaTutor} /> : <group>
          <BotaoXR label={rascunho ? rascunho.slice(0, 35) : "Escreva sua dúvida..."} x={-0.092} y={-0.414} largura={0.756} alinhar="left" cor={tema.muted} onClick={() => setEscrevendo(true)} />
          <BotaoXR label={rascunho.trim() ? "Enviar" : "Abrir"} x={0.386} y={-0.414} largura={0.166} tamanho={0.022} variante="primary" onClick={() => rascunho.trim() ? enviar(rascunho) : setEscrevendo(true)} />
        </group>}
      <Text3D position={[-0.46, -0.507, 0.025]} anchorX="left" size={0.019} maxWidth={0.92} color="muted">Ferramenta de estudo. Não substitui avaliação clínica.</Text3D>
    </>}
  </PainelXRBase>;
}
