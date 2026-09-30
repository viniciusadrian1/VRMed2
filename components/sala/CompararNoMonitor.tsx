"use client";

import { useState } from "react";
import { Text3D } from "@/components/arena/ui3d";
import { COMPARISON_NOTES, getComparableOrgans } from "@/lib/organs";
import { ajustarVistaMonitor, VISTA_MONITOR_INICIAL, type ComandoVista } from "@/lib/monitor-comparacao";
import { ModeloNoMonitor } from "./ModeloNoMonitor";
import { BotaoMonitor } from "./BotaoMonitor";

const ORGAOS = getComparableOrgans();
const COMANDOS: { titulo: string; comando: ComandoVista }[] = [
  { titulo: "Girar <", comando: "esquerda" }, { titulo: "Girar >", comando: "direita" },
  { titulo: "Inclinar +", comando: "cima" }, { titulo: "Inclinar −", comando: "baixo" },
  { titulo: "Zoom +", comando: "aproximar" }, { titulo: "Zoom −", comando: "afastar" },
  { titulo: "Restaurar", comando: "restaurar" },
];

/** Comparação no monitor físico; sem navegar ou finalizar a sessão XR. */
export function CompararNoMonitor() {
  const [indice, setIndice] = useState(() => Math.max(0, ORGAOS.findIndex((o) => o.id === "figado")));
  const [vistas, setVistas] = useState([VISTA_MONITOR_INICIAL, VISTA_MONITOR_INICIAL]);
  const [alvo, setAlvo] = useState<"ambos" | "saudavel" | "patologico">("ambos");
  const [notas, setNotas] = useState(false), [pagina, setPagina] = useState(0);
  const orgao = ORGAOS[indice], diferencas = COMPARISON_NOTES[orgao.id] ?? [];
  const comando = (acao: ComandoVista) => setVistas((atuais) => atuais.map((vista, i) => (
    alvo === "ambos" || (alvo === "saudavel" ? i === 0 : i === 1) ? ajustarVistaMonitor(vista, acao) : vista
  )));
  return <>
    {ORGAOS.map((o, i) => <BotaoMonitor key={o.id} titulo={o.name} selecionado={i === indice}
      largura={.184} altura={.06} tamanho={.023} position={[-.388 + i * .204, .172, .003]}
      onClick={() => { setIndice(i); setVistas([VISTA_MONITOR_INICIAL, VISTA_MONITOR_INICIAL]); setPagina(0); }} />)}
    <BotaoMonitor titulo={notas ? "Ver modelos" : "Diferenças"} largura={.29} altura={.06} tamanho={.024}
      position={[.332, .172, .003]} onClick={() => setNotas((v) => !v)} />
    {notas ? <>
      <Text3D tratamento="tela" position={[-.465, .105, .003]} anchorX="left" anchorY="top" align="left" size={.029} maxWidth={.9}>{orgao.pathologyName}</Text3D>
      <Text3D tratamento="tela" position={[-.465, .043, .003]} anchorX="left" anchorY="top" align="left" size={.025} maxWidth={.9}>{diferencas[pagina] ?? "Sem notas cadastradas."}</Text3D>
      <BotaoMonitor titulo="Anterior" largura={.2} altura={.06} position={[-.36, -.13, .003]} desabilitado={pagina === 0} onClick={() => setPagina((v) => v - 1)} />
      <Text3D tratamento="tela" position={[0, -.13, .003]} size={.024}>{`${pagina + 1} / ${diferencas.length}`}</Text3D>
      <BotaoMonitor titulo="Próxima" largura={.2} altura={.06} position={[.36, -.13, .003]} desabilitado={pagina >= diferencas.length - 1} onClick={() => setPagina((v) => v + 1)} />
      <Text3D tratamento="tela" position={[0, -.23, .003]} size={.021} maxWidth={.94} color="#c1d5d4">Conteúdo educacional. As vistas são normalizadas, não estão em escala real.</Text3D>
    </> : <>
      <ModeloNoMonitor key={`${orgao.id}-saudavel`} caminho={orgao.modelPath} vista={vistas[0]} x={-.247} />
      <ModeloNoMonitor key={`${orgao.id}-patologico`} caminho={orgao.pathologicalPath!} vista={vistas[1]} x={.247} />
      <Text3D tratamento="tela" position={[-.247, .107, .003]} size={.02} color="#b1efd2">Saudável</Text3D>
      <Text3D tratamento="tela" position={[.247, .107, .003]} size={.02} maxWidth={.45} color="#ffc6aa">{orgao.pathologyName}</Text3D>
      <BotaoMonitor titulo={alvo === "ambos" ? "Controlando: ambos" : alvo === "saudavel" ? "Controlando: saudável" : "Controlando: patológico"}
        largura={.42} altura={.051} tamanho={.021} position={[-.26, -.119, .003]}
        onClick={() => setAlvo((v) => v === "ambos" ? "saudavel" : v === "saudavel" ? "patologico" : "ambos")} />
      <Text3D tratamento="tela" position={[.24, -.12, .003]} maxWidth={.44} size={.019} color="#c1d5d4">Tamanhos normalizados, sem escala real.</Text3D>
      {COMANDOS.map((c, i) => <BotaoMonitor key={c.comando} titulo={c.titulo} largura={i === 6 ? .174 : .117} altura={.057}
        tamanho={.019} position={[i === 6 ? .389 : -.419 + i * .127, -.192, .003]} onClick={() => comando(c.comando)} />)}
      <Text3D tratamento="tela" position={[0, -.247, .003]} size={.019} color="#c1d5d4">A sala permanece aberta. Use Menu para escolher outra atividade.</Text3D>
    </>}
  </>;
}
