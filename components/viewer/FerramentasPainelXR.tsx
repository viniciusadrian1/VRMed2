"use client";

import { useEffect, useState } from "react";
import { Text3D } from "@/components/arena/ui3d";
import { useVRMedStore } from "@/lib/store";
import { getOrganById } from "@/lib/organs";
import { CORES_XR, limitar, paginasXR, PAINEIS_XR } from "@/lib/painel-estudo-xr";
import { ouvirNarracao, pausarNarracao, pararNarracao, useNarracaoEstudo, velocidadeNarracao } from "@/lib/narracao-estudo";
import type { Annotation, ClipAxis } from "@/types";
import { BotaoXR, PainelXRBase, PaginacaoXR, TecladoXR } from "./PainelXRBase";

const ABAS = ["Camadas", "Cortes", "Notas", "Áudio"] as const;
const SEM_NOTAS: Annotation[] = [];

function CamadasXR() {
  const layers = useVRMedStore((s) => s.layers);
  const xray = useVRMedStore((s) => s.xray);
  const [pagina, setPagina] = useState(0);
  const [selecionada, setSelecionada] = useState<string | null>(null);
  const total = Math.max(1, Math.ceil(layers.length / PAINEIS_XR.camadasPorPagina));
  const atual = Math.min(pagina, total - 1);
  const fatia = layers.slice(atual * PAINEIS_XR.camadasPorPagina, (atual + 1) * PAINEIS_XR.camadasPorPagina);
  const camada = fatia.find((l) => l.name === selecionada) ?? fatia[0];
  const loja = useVRMedStore.getState;
  return <group>
    <BotaoXR label={xray ? "Raio-X: ligado" : "Raio-X"} x={-0.32} y={0.27} largura={0.29} ativo={xray} onClick={() => loja().applyXray(!xray)} />
    <BotaoXR label="Mostrar tudo" y={0.27} largura={0.30} onClick={() => loja().showAllLayers()} />
    <BotaoXR label="Isolar seleção" x={0.32} y={0.27} largura={0.29} desabilitado={!camada} onClick={() => camada && loja().isolateLayer(camada.name)} />
    {fatia.map((layer, i) => <group key={layer.name}>
      <BotaoXR label={layer.label} x={-0.105} y={0.17 - i * 0.095} largura={0.72} ativo={camada?.name === layer.name} onClick={() => setSelecionada(layer.name)} />
      <BotaoXR label={layer.visible ? "Visível" : "Oculta"} x={0.38} y={0.17 - i * 0.095} largura={0.2} ativo={layer.visible} onClick={() => loja().setLayerVisibility(layer.name, !layer.visible)} />
    </group>)}
    {!layers.length && <Text3D position={[0, 0.08, 0.025]} size={0.027} maxWidth={0.9}>Aguardando as camadas do modelo.</Text3D>}
    <PaginacaoXR pagina={atual} total={total} aoMudar={setPagina} y={-0.13} />
    {camada && <>
      <Text3D position={[0, -0.22, 0.025]} size={0.024} maxWidth={0.92}>{camada.label}</Text3D>
      <BotaoXR label="Menos opaca" x={-0.31} y={-0.31} largura={0.29} desabilitado={camada.opacity === 0} onClick={() => loja().setLayerOpacity(camada.name, limitar(camada.opacity - 0.1, 0, 1))} />
      <Text3D position={[0, -0.31, 0.025]} size={0.027}>{`${Math.round(camada.opacity * 100)}%`}</Text3D>
      <BotaoXR label="Mais opaca" x={0.31} y={-0.31} largura={0.29} desabilitado={camada.opacity === 1} onClick={() => loja().setLayerOpacity(camada.name, limitar(camada.opacity + 0.1, 0, 1))} />
      {CORES_XR.map((c, i) => <BotaoXR key={c.nome} label={c.nome} x={(i - 2) * 0.19} y={-0.42} largura={0.174} ativo={camada.color === c.cor} onClick={() => loja().setLayerColor(camada.name, c.cor)} />)}
    </>}
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
    <Text3D position={[0, 0.18, 0.025]} size={0.023} maxWidth={0.92} color="#a7d4df">
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
    <Text3D position={[0, -0.245, 0.025]} size={0.024} maxWidth={0.92} color={erro ? "#ffb4a4" : "#a7d4df"}>
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
  const [aberto, setAberto] = useState(true);
  const [aba, setAba] = useState<typeof ABAS[number]>("Camadas");
  const [editando, setEditando] = useState(false);
  return <PainelXRBase titulo="Ferramentas do modelo" aberto={aberto} aoAlternar={() => {
    setAberto(!aberto); setEditando(false); useVRMedStore.getState().setAnnotationMode(false);
  }}>
    <group key={organId ?? "sem-modelo"}>
      {!editando && ABAS.map((nome, i) => <BotaoXR key={nome} label={nome} x={(i - 1.5) * 0.245} y={0.375} largura={0.225} ativo={aba === nome} onClick={() => { setAba(nome); useVRMedStore.getState().setAnnotationMode(false); }} />)}
      {aba === "Camadas" && <CamadasXR />}
      {aba === "Cortes" && <CortesXR />}
      {aba === "Notas" && <NotasXR organId={organId} aoEditar={setEditando} />}
      {aba === "Áudio" && <AudioXR />}
    </group>
  </PainelXRBase>;
}
