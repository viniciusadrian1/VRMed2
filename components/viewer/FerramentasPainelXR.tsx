"use client";

import { useEffect, useState } from "react";
import { TextoPainelXR as Text3D, SuperficieXR, OpacidadeXR, CaixaSelecaoXR, useTemaPainelXR } from "./EstiloPainelXR";
import { useJanelasEstudoXR } from "@/lib/janelas-estudo-xr";
import { useVRMedStore } from "@/lib/store";
import { getOrganById } from "@/lib/organs";
import { CORES_XR, limitar, paginasXR, PAINEIS_XR } from "@/lib/painel-estudo-xr";
import { ouvirNarracao, pausarNarracao, pararNarracao, useNarracaoEstudo, velocidadeNarracao } from "@/lib/narracao-estudo";
import type { Annotation, ClipAxis } from "@/types";
import { BotaoXR, PainelXRBase, PaginacaoXR, TecladoXR } from "./PainelXRBase";

const ABAS = ["Camadas", "Cortes", "Notas", "Áudio"] as const;
const SEM_NOTAS: Annotation[] = [];

function CamadasXR() {
  const layers = useVRMedStore((s) => s.layers), xray = useVRMedStore((s) => s.xray), tema = useTemaPainelXR();
  const [pagina, setPagina] = useState(0), [colorindo, setColorindo] = useState<string | null>(null);
  const total = Math.max(1, Math.ceil(layers.length / PAINEIS_XR.camadasPorPagina)), atual = Math.min(pagina, total - 1);
  const fatia = layers.slice(atual * PAINEIS_XR.camadasPorPagina, (atual + 1) * PAINEIS_XR.camadasPorPagina);
  const camada = layers.find((l) => l.name === colorindo), loja = useVRMedStore.getState;
  const profundidades = { external: "EXTERNA", intermediate: "INTERMEDIÁRIA", internal: "INTERNA" };
  return <group>
    <SuperficieXR largura={0.97} altura={0.085} y={0.267} cor={tema.muted} />
    <CaixaSelecaoXR x={-0.425} y={0.267} ativo={xray} onClick={() => loja().applyXray(!xray)} />
    <Text3D position={[-0.369, 0.267, 0.025]} anchorX="left" size={0.025}>Modo raio-X</Text3D>
    <BotaoXR label="Mostrar tudo" x={0.29} y={0.267} largura={0.33} variante="ghost" onClick={() => loja().showAllLayers()} />
    {fatia.map((layer, i) => {
      const y = 0.11 - i * 0.195;
      return <group key={layer.name}>
        <SuperficieXR largura={0.97} altura={0.177} y={y} borda />
        <CaixaSelecaoXR x={-0.425} y={y + 0.034} ativo={layer.visible} onClick={() => loja().setLayerVisibility(layer.name, !layer.visible)} />
        <Text3D position={[-0.365, y + 0.043, 0.025]} size={0.025} maxWidth={0.62} anchorX="left">{layer.label.length > 38 ? layer.label.slice(0, 35) + "..." : layer.label}</Text3D>
        <Text3D position={[-0.365, y + 0.008, 0.025]} size={0.017} color="muted" anchorX="left">{profundidades[layer.depth]}</Text3D>
        <BotaoXR label="Isolar" x={0.395} y={y + 0.035} largura={0.142} tamanho={0.022} variante="ghost" onClick={() => loja().isolateLayer(layer.name)} />
        <OpacidadeXR x={-0.13} y={y - 0.049} largura={0.60} valor={layer.opacity} aoMudar={(v) => loja().setLayerOpacity(layer.name, v)} />
        <Text3D position={[0.241, y - 0.049, 0.03]} size={0.022} color="muted">{Math.round(layer.opacity * 100) + "%"}</Text3D>
        <BotaoXR label="Cor" x={0.395} y={y - 0.049} largura={0.142} tamanho={0.022} ativo={colorindo === layer.name} onClick={() => setColorindo(colorindo === layer.name ? null : layer.name)} />
      </group>;
    })}
    {!layers.length && <Text3D position={[0, 0.08, 0.025]} size={0.027} maxWidth={0.9}>Aguardando as camadas do modelo.</Text3D>}
    {camada && <group>
      {CORES_XR.map((c, i) => <BotaoXR key={c.nome} label={c.nome} x={(i - 2) * 0.19} y={-0.42} largura={0.174} ativo={camada.color === c.cor} onClick={() => loja().setLayerColor(camada.name, c.cor)} />)}
    </group>}
    <PaginacaoXR pagina={atual} total={total} aoMudar={(p) => { setPagina(p); setColorindo(null); }} y={-0.507} />
  </group>;
}

function CortesXR() {
  const clipping = useVRMedStore((s) => s.clipping);
  const wireframe = useVRMedStore((s) => s.wireframe);
  const abertura = useVRMedStore((s) => s.explosao);
  const explodivel = useVRMedStore((s) => getOrganById(s.currentOrganId)?.explosao);
  const eixos: [ClipAxis, string][] = [["axial", "Axial"], ["sagital", "Sagital"], ["coronal", "Coronal"]];
  const loja = useVRMedStore.getState;
  return <group>
    <Text3D position={[0, 0.275, 0.025]} size={0.024} maxWidth={0.93}>Ative um plano e ajuste a posição. O corte acompanha o órgão.</Text3D>
    {eixos.map(([eixo, nome], i) => {
      const plano = clipping[eixo], y = 0.16 - i * 0.135;
      return <group key={eixo}>
        <BotaoXR label={nome} x={-0.34} y={y} largura={0.25} ativo={plano.enabled} onClick={() => loja().setClipPlane(eixo, { enabled: !plano.enabled })} />
        <BotaoXR label="−" x={-0.12} y={y} largura={0.12} desabilitado={!plano.enabled || plano.position <= -1} onClick={() => loja().setClipPlane(eixo, { position: limitar(plano.position - 0.1, -1, 1) })} />
        <Text3D position={[0.035, y, 0.025]} size={0.023}>{plano.position.toFixed(1)}</Text3D>
        <BotaoXR label="+" x={0.18} y={y} largura={0.12} desabilitado={!plano.enabled || plano.position >= 1} onClick={() => loja().setClipPlane(eixo, { position: limitar(plano.position + 0.1, -1, 1) })} />
        <BotaoXR label="Inverter" x={0.37} y={y} largura={0.2} ativo={plano.flipped} desabilitado={!plano.enabled} onClick={() => loja().setClipPlane(eixo, { flipped: !plano.flipped })} />
      </group>;
    })}
    <BotaoXR label="Remover cortes" x={-0.245} y={-0.24} largura={0.43} onClick={() => loja().resetClipping()} />
    <BotaoXR label={wireframe ? "Malha: ligada" : "Ver malha"} x={0.245} y={-0.24} largura={0.43} ativo={wireframe} onClick={() => loja().toggleWireframe()} />
    {explodivel && <>
      <Text3D position={[0, -0.34, 0.025]} size={0.024}>{`${explodivel.rotulo}: ${Math.round(abertura * 100)}%`}</Text3D>
      <BotaoXR label="Fechar ossos" x={-0.245} y={-0.44} largura={0.43} desabilitado={abertura === 0} onClick={() => loja().setExplosao(abertura - 0.1)} />
      <BotaoXR label="Abrir ossos" x={0.245} y={-0.44} largura={0.43} desabilitado={abertura === 1} onClick={() => loja().setExplosao(abertura + 0.1)} />
    </>}
  </group>;
}

function NotasXR({ organId, aoEditar }: { organId: string | null; aoEditar: (ativo: boolean) => void }) {
  const notas = useVRMedStore((s) => organId ? s.annotationsByOrgan[organId] ?? SEM_NOTAS : SEM_NOTAS);
  const criando = useVRMedStore((s) => s.annotationMode);
  const abertura = useVRMedStore((s) => s.explosao);
  const [id, setId] = useState<string | null>(null);
  const [edicao, setEdicao] = useState<{ id: string; texto: string } | null>(null);
  const [excluir, setExcluir] = useState(false);
  const [pagina, setPagina] = useState(0);
  const nota = notas.find((n) => n.id === id) ?? notas.at(-1);
  const indice = nota ? notas.indexOf(nota) : 0;
  const texto = paginasXR(nota?.text ?? "Crie uma nota e marque um ponto na superfície do órgão.", 30, 4);
  const loja = useVRMedStore.getState;
  const localizar = () => {
    if (!nota || abertura > 0.001) return;
    loja().setInspectedLabel(`Nota ${indice + 1}`);
    loja().setInspectedPoint(nota.position);
  };
  useEffect(() => () => useVRMedStore.getState().setAnnotationMode(false), []);
  if (edicao) return <TecladoXR texto={edicao.texto} limite={Math.max(500, nota?.text.length ?? 0)} aoMudar={(texto) => setEdicao({ ...edicao, texto })} confirmar="Salvar" aoCancelar={() => { setEdicao(null); aoEditar(false); }} aoConfirmar={() => {
    if (organId) loja().updateAnnotation(organId, edicao.id, { text: edicao.texto.trim() });
    loja().setInspectedLabel(null); loja().setInspectedPoint(null); setEdicao(null); aoEditar(false);
  }} />;
  return <group>
    <BotaoXR label={criando ? "Cancelar marcação" : "Nova nota no órgão"} y={0.265} largura={0.8} ativo={criando} desabilitado={!organId || abertura > 0.001} onClick={() => { loja().setAnnotationMode(!criando); setId(null); setPagina(0); setExcluir(false); }} />
    <Text3D position={[0, 0.18, 0.025]} size={0.023} maxWidth={0.92} color="muted">
      {abertura > 0.001 ? "Feche os ossos para marcar ou localizar notas." : criando ? "Aponte para o órgão e pressione o gatilho." : nota ? `Nota ${indice + 1} de ${notas.length} · salva neste modelo` : "Suas notas também aparecem na tela"}
    </Text3D>
    <Text3D position={[0, 0.115, 0.025]} anchorY="top" size={0.027} maxWidth={0.92}>{texto[Math.min(pagina, texto.length - 1)]}</Text3D>
    <PaginacaoXR pagina={Math.min(pagina, texto.length - 1)} total={texto.length} aoMudar={setPagina} y={-0.105} />
    <BotaoXR label="Editar texto" x={-0.245} y={-0.205} largura={0.43} desabilitado={!nota || criando} onClick={() => {
      if (nota) { setEdicao({ id: nota.id, texto: nota.text }); aoEditar(true); }
    }} />
    <BotaoXR label="Localizar ponto" x={0.245} y={-0.205} largura={0.43} desabilitado={!nota || criando || abertura > 0.001} onClick={localizar} />
    <BotaoXR label={nota?.hideLabel ? "Exibir rótulo" : "Ocultar rótulo"} x={-0.245} y={-0.305} largura={0.43} desabilitado={!nota} onClick={() => {
      if (nota && organId) loja().updateAnnotation(organId, nota.id, { hideLabel: !nota.hideLabel });
      loja().setInspectedLabel(null); loja().setInspectedPoint(null);
    }} />
    <BotaoXR label={excluir ? "Confirmar exclusão" : "Excluir nota"} x={0.245} y={-0.305} largura={0.43} desabilitado={!nota} onClick={() => {
      if (excluir && nota && organId) {
        loja().removeAnnotation(organId, nota.id); loja().setInspectedLabel(null); loja().setInspectedPoint(null); setId(null);
      }
      setExcluir(!excluir);
    }} />
    <BotaoXR label="Nota anterior" x={-0.245} y={-0.42} largura={0.43} desabilitado={!nota || indice === 0} onClick={() => { setId(notas[indice - 1].id); setPagina(0); setExcluir(false); }} />
    <BotaoXR label="Próxima nota" x={0.245} y={-0.42} largura={0.43} desabilitado={!nota || indice === notas.length - 1} onClick={() => { setId(notas[indice + 1].id); setPagina(0); setExcluir(false); }} />
  </group>;
}

function AudioXR() {
  const { description, status, rate, loading, erro } = useNarracaoEstudo();
  const [pagina, setPagina] = useState(0);
  const paginas = paginasXR(description ? `${description.fullDescription} Fontes: ${description.sources.join("; ")}` : loading ? "Carregando descrição..." : "Este modelo ainda não tem descrição narrada.");
  return <group>
    <BotaoXR label={status === "playing" ? "Pausar" : status === "paused" ? "Retomar" : "Ouvir descrição"} x={-0.245} y={0.27} largura={0.43} desabilitado={!description} onClick={status === "playing" ? pausarNarracao : ouvirNarracao} />
    <BotaoXR label="Parar áudio" x={0.245} y={0.27} largura={0.43} desabilitado={status === "idle"} onClick={pararNarracao} />
    <Text3D position={[0, 0.18, 0.025]} anchorY="top" size={0.028} maxWidth={0.92}>{paginas[Math.min(pagina, paginas.length - 1)]}</Text3D>
    <BotaoXR label="Mais lenta" x={-0.31} y={-0.12} largura={0.29} desabilitado={rate === 0.5} onClick={() => velocidadeNarracao(rate - 0.25)} />
    <Text3D position={[0, -0.12, 0.025]} size={0.025}>{`${rate.toFixed(2)}×`}</Text3D>
    <BotaoXR label="Mais rápida" x={0.31} y={-0.12} largura={0.29} desabilitado={rate === 2} onClick={() => velocidadeNarracao(rate + 0.25)} />
    <Text3D position={[0, -0.245, 0.025]} size={0.024} maxWidth={0.92} color={erro ? "danger" : "muted"}>
      {erro ? "Áudio indisponível neste navegador. A descrição continua disponível para leitura." : "A velocidade da voz vale na próxima reprodução. Use Parar e Ouvir para reiniciar."}
    </Text3D>
    <PaginacaoXR pagina={Math.min(pagina, paginas.length - 1)} total={paginas.length} aoMudar={setPagina} y={-0.42} />
  </group>;
}

export function FerramentasPainelXR() {
  const organId = useVRMedStore((s) => s.currentOrganId);
  return <ConteudoFerramentasXR key={organId ?? "sem-modelo"} organId={organId} />;
}

function ConteudoFerramentasXR({ organId }: { organId: string | null }) {
  const aberto = useJanelasEstudoXR((s) => s.abertas.ferramentas);
  const tema = useTemaPainelXR();
  const [aba, setAba] = useState<typeof ABAS[number]>("Camadas");
  const [editando, setEditando] = useState(false);
  return <PainelXRBase titulo="Ferramentas do modelo" aberto={aberto} aoAlternar={() => {
    useJanelasEstudoXR.getState().abrir("ferramentas", !aberto); useVRMedStore.getState().setAnnotationMode(false);
  }}>
    <group key={organId ?? "sem-modelo"}>
      {!editando && <SuperficieXR largura={0.985} altura={0.085} y={0.365} cor={tema.muted} />}
      {!editando && ABAS.map((nome, i) => <BotaoXR key={nome} label={nome} x={(i - 1.5) * 0.245} y={0.365} largura={0.235} variante="tab" ativo={aba === nome} onClick={() => { setAba(nome); useVRMedStore.getState().setAnnotationMode(false); }} />)}
      {aba === "Camadas" && <CamadasXR />}
      {aba === "Cortes" && <CortesXR />}
      {aba === "Notas" && <NotasXR organId={organId} aoEditar={setEditando} />}
      {aba === "Áudio" && <AudioXR />}
    </group>
  </PainelXRBase>;
}
