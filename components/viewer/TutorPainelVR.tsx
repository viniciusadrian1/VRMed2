"use client";

import { useEffect, useRef, useState } from "react";
import { Panel, Button3D, Text3D } from "@/components/arena/ui3d";
import { streamChatResponse } from "@/lib/chat-client";
import { useTutor3D } from "@/lib/tutor-3d-store";
import { useVRMedStore } from "@/lib/store";
import type { ContextoTutor } from "@/lib/tutor-3d";

/** Perguntas rápidas sem teclado/microfone. Montado só na sessão imersiva. */
export function TutorPainelVR() {
  const contexto = useTutor3D((s) => s.contexto);
  // Trocar o modelo descarta texto e requisição anteriores, não só o destaque.
  return <ConteudoTutorVR key={contexto?.revisao ?? "carregando"} contexto={contexto} />;
}

function ConteudoTutorVR({ contexto }: { contexto: ContextoTutor | null }) {
  const [aberto, setAberto] = useState(false);
  const [texto, setTexto] = useState("");
  const [erro, setErro] = useState("");
  const [ocupado, setOcupado] = useState(false);
  const [pagina, setPagina] = useState(0);
  const pedido = useRef<AbortController | null>(null);
  const foco = useTutor3D((s) => s.foco);
  const inspecionado = useVRMedStore((s) => s.inspectedLabel);
  const alvo = inspecionado ?? contexto?.alvos[0].label ?? "modelo";
  const paginas = texto.match(/[\s\S]{1,230}(?:\s|$)|[\s\S]{1,230}/g) ?? [""];

  useEffect(() => {
    return () => { pedido.current?.abort(); useTutor3D.getState().limparFoco(); };
  }, [contexto]);

  const perguntar = async (funcao: boolean) => {
    if (!contexto || pedido.current) return;
    const controller = new AbortController();
    useTutor3D.getState().limparFoco();
    pedido.current = controller;
    setTexto(""); setErro(""); setPagina(0); setOcupado(true);
    const pergunta = funcao ? `Qual a função de ${alvo}? Explique de forma simples.` : `Explique ${alvo} e destaque no modelo se estiver disponível.`;
    try {
      await streamChatResponse({
        messages: [{ role: "user", content: pergunta }], currentOrgan: contexto.alvos[0].label,
        contexto3d: useTutor3D.getState().ativo ? contexto : undefined,
      }, (parte) => setTexto((s) => s + parte), controller.signal,
      (comando) => { if (!controller.signal.aborted) useTutor3D.getState().aplicar(comando, contexto); });
    } catch (falha) {
      useTutor3D.getState().limparFoco();
      if (!controller.signal.aborted) { setTexto(""); setErro(falha instanceof Error ? falha.message : "Tutor indisponível."); }
    } finally {
      if (pedido.current === controller) { pedido.current = null; setOcupado(false); }
    }
  };

  return <group position={[0.55, 1.45, -0.95]}>
    {!aberto ? <Button3D label="Tutor 3D" width={0.3} height={0.075} onClick={() => setAberto(true)} /> :
      <Panel width={0.73} height={0.83}>
        <Text3D position={[0, 0.35, 0.01]} size={0.034}>Tutor 3D</Text3D>
        <Text3D position={[0, 0.275, 0.01]} size={0.024} maxWidth={0.65}>{`Selecionado: ${alvo}`}</Text3D>
        <Text3D position={[0, 0.06, 0.01]} size={0.025} maxWidth={0.64}>
          {erro || paginas[pagina] || (ocupado ? "Preparando explicação..." : "Aponte para uma estrutura e puxe o gatilho. Depois escolha uma pergunta abaixo. Sua cabeça continua livre.")}
        </Text3D>
        <Button3D label="Explicar" position={[-0.17, -0.17, 0.01]} width={0.3} height={0.065} desabilitado={ocupado || !contexto} onClick={() => void perguntar(false)} />
        <Button3D label="Qual a função?" position={[0.17, -0.17, 0.01]} width={0.3} height={0.065} desabilitado={ocupado || !contexto} onClick={() => void perguntar(true)} />
        <Button3D label={paginas.length > 1 ? `Texto ${pagina + 1}/${paginas.length}` : "Texto completo"} position={[-0.17, -0.255, 0.01]} width={0.3} height={0.065} desabilitado={paginas.length < 2} onClick={() => setPagina((p) => (p + 1) % paginas.length)} />
        <Button3D label="Limpar foco" position={[0.17, -0.255, 0.01]} width={0.3} height={0.065} desabilitado={!foco} onClick={() => useTutor3D.getState().limparFoco()} />
        <Button3D label="Fechar tutor" position={[0, -0.345, 0.01]} width={0.4} height={0.065} onClick={() => { pedido.current?.abort(); setAberto(false); useTutor3D.getState().limparFoco(); }} />
      </Panel>}
  </group>;
}
