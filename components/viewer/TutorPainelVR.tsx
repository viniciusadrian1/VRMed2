"use client";

import { useState } from "react";
import { Text3D } from "@/components/arena/ui3d";
import { useTutor3D } from "@/lib/tutor-3d-store";
import { useVRMedStore } from "@/lib/store";
import { paginasXR } from "@/lib/painel-estudo-xr";
import { cancelarConversaTutor, enviarPerguntaTutor, limparConversaTutor, repetirPerguntaTutor, useConversaTutor } from "@/lib/tutor-conversa";
import { BotaoXR, PainelXRBase, PaginacaoXR, TecladoXR } from "./PainelXRBase";

/** Conversa completa no mundo 3D, compartilhada com o painel da tela. */
export function TutorPainelVR() {
  const [aberto, setAberto] = useState(true);
  const [escrevendo, setEscrevendo] = useState(false);
  const [rascunho, setRascunho] = useState("");
  const [mensagemId, setMensagemId] = useState<string | null>(null);
  const [pagina, setPagina] = useState(0);
  const [confirmarLimpeza, setConfirmarLimpeza] = useState(false);
  const chat = useVRMedStore((s) => s.chat);
  const contexto = useTutor3D((s) => s.contexto);
  const guia = useTutor3D((s) => s.ativo);
  const foco = useTutor3D((s) => s.foco);
  const ocupado = useConversaTutor((s) => s.ocupado);
  const erro = useConversaTutor((s) => s.erro);
  const inspecionado = useVRMedStore((s) => s.inspectedLabel);
  const alvo = contexto?.alvos.find((a) => a.label === inspecionado)?.label ?? contexto?.alvos[0]?.label ?? "modelo";
  const indice = mensagemId ? chat.findIndex((m) => m.id === mensagemId) : chat.length - 1;
  const atual = Math.max(0, indice < 0 ? chat.length - 1 : indice);
  const mensagem = chat[atual];
  const paginas = paginasXR(erro || mensagem?.content || (ocupado
    ? "Preparando explicação..."
    : "Aponte para uma estrutura com o laser. Escolha uma pergunta rápida ou escreva sua dúvida no teclado 3D."));
  const paginaAtual = Math.min(pagina, paginas.length - 1);
  const enviar = (pergunta: string) => {
    setConfirmarLimpeza(false);
    setEscrevendo(false); setRascunho(""); setMensagemId(null); setPagina(0);
    void enviarPerguntaTutor(pergunta);
  };
  const escolherMensagem = (i: number) => { setMensagemId(chat[i]?.id ?? null); setPagina(0); };
  return <PainelXRBase titulo="Tutor de IA" aberto={aberto} aoAlternar={() => {
    if (aberto && ocupado) cancelarConversaTutor();
    setAberto(!aberto); setEscrevendo(false); setConfirmarLimpeza(false);
  }}>
    {escrevendo ? <TecladoXR texto={rascunho} aoMudar={setRascunho} aoCancelar={() => setEscrevendo(false)} aoConfirmar={() => enviar(rascunho)} /> : <>
      <BotaoXR label={guia ? "Guia 3D: ligado" : "Guia 3D: desligado"} x={-0.245} y={0.375} largura={0.45} ativo={guia} onClick={() => useTutor3D.getState().habilitar(!guia)} />
      <BotaoXR label="Limpar foco" x={0.245} y={0.375} largura={0.45} desabilitado={!foco} onClick={() => useTutor3D.getState().limparFoco()} />
      <Text3D position={[0, 0.293, 0.025]} size={0.023} maxWidth={0.91} color="#a7d4df">
        {foco ? `Foco: ${foco.label}` : "A câmera continua livre em AR e VR"}
      </Text3D>
      <BotaoXR label="Mensagem anterior" x={-0.265} y={0.215} largura={0.4} desabilitado={atual === 0 || !chat.length} onClick={() => escolherMensagem(atual - 1)} />
      <BotaoXR label="Mais recente" x={0.265} y={0.215} largura={0.4} desabilitado={!chat.length || atual === chat.length - 1} onClick={() => { setMensagemId(null); setPagina(0); }} />
      <Text3D position={[0, 0.145, 0.025]} size={0.022} color={erro ? "#ffb4a4" : "#a7d4df"}>
        {erro ? "Não foi possível responder" : mensagem ? `${mensagem.role === "user" ? "Você" : "Tutor"} · ${atual + 1}/${chat.length}` : "Sua conversa de estudo"}
      </Text3D>
      <Text3D position={[0, 0.11, 0.025]} anchorY="top" size={0.028} maxWidth={0.92}>{paginas[paginaAtual]}</Text3D>
      <PaginacaoXR pagina={paginaAtual} total={paginas.length} aoMudar={setPagina} y={-0.18} />
      <BotaoXR label="Explicar" x={-0.32} y={-0.275} largura={0.29} desabilitado={ocupado || !contexto} onClick={() => enviar(`Explique ${alvo} e destaque no modelo se estiver disponível.`)} />
      <BotaoXR label="Qual a função?" y={-0.275} largura={0.31} desabilitado={ocupado || !contexto} onClick={() => enviar(`Qual a função de ${alvo}? Explique de forma simples.`)} />
      <BotaoXR label="Escrever" x={0.32} y={-0.275} largura={0.29} desabilitado={ocupado} onClick={() => setEscrevendo(true)} />
      {ocupado ? <BotaoXR label="Parar resposta" y={-0.37} largura={0.6} onClick={cancelarConversaTutor} /> :
        erro ? <BotaoXR label="Tentar novamente" y={-0.37} largura={0.6} onClick={repetirPerguntaTutor} /> :
        <BotaoXR label={confirmarLimpeza ? "Confirmar: apagar conversa" : "Limpar conversa"} y={-0.37} largura={0.65} desabilitado={!chat.length} onClick={() => {
          if (confirmarLimpeza) { limparConversaTutor(); setMensagemId(null); setPagina(0); }
          setConfirmarLimpeza(!confirmarLimpeza);
        }} />}
      <Text3D position={[0, -0.478, 0.025]} size={0.021} maxWidth={0.92} color="#aebecd">
        Ferramenta de estudo. Não substitui avaliação clínica.
      </Text3D>
    </>}
  </PainelXRBase>;
}
