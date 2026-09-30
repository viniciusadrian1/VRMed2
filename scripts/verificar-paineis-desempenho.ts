import assert from "node:assert/strict";
import { readFileSync } from "node:fs";
import { ESTILOS_CAPTURA, itemForaDaCaptura } from "../lib/painel-captura-xr.ts";
import { ALL_MODELS } from "../lib/organs.ts";
import { PERGUNTAS_POR_MODELO, perguntasDoModelo } from "../lib/tutor-perguntas.ts";
import { createElement as h } from "react";
import { renderToStaticMarkup } from "react-dom/server";
import "./registrar-componentes-teste.mjs";

assert.ok(ESTILOS_CAPTURA.length < 130, "não recopiamos centenas de defaults irrelevantes");
assert.equal(new Set(ESTILOS_CAPTURA).size, ESTILOS_CAPTURA.length);
for (const nome of ["font-family", "border-radius", "color", "fill", "stroke", "transform", "overflow-y", "flex-basis"]) assert.ok(ESTILOS_CAPTURA.includes(nome as typeof ESTILOS_CAPTURA[number]));
const janela = { top: 60, bottom: 620 };
assert.equal(itemForaDaCaptura({ top: 0, bottom: 58 }, janela), false, "folga de borda evita sumiço");
assert.equal(itemForaDaCaptura({ top: 0, bottom: 30 }, janela), true);
assert.equal(itemForaDaCaptura({ top: 580, bottom: 710 }, janela), false, "item parcialmente visível continua completo");
assert.equal(itemForaDaCaptura({ top: 630, bottom: 760 }, janela), true);
assert.equal(itemForaDaCaptura({ top: -900, bottom: 760 }, janela), false, "mensagem longa atravessando a janela não some");
assert.deepEqual(perguntasDoModelo(null), []);
assert.deepEqual(perguntasDoModelo("inexistente"), []);
assert.deepEqual(Object.keys(PERGUNTAS_POR_MODELO).sort(), ALL_MODELS.map((m) => m.id).sort());
const grupos = new Set<string>();
for (const modelo of ALL_MODELS) {
  const perguntas = perguntasDoModelo(modelo.id);
  assert.equal(perguntas.length, 3);
  assert.equal(new Set(perguntas).size, 3);
  assert.ok(perguntas.every((p) => p.endsWith("?") && p.length < 100));
  grupos.add(perguntas.join("|"));
}
assert.equal(grupos.size, ALL_MODELS.length, "nenhum modelo recebe o mesmo trio genérico");
assert.ok(perguntasDoModelo("estomago").some((p) => p.includes("boca ao reto")), "ID legado representa trato completo");
assert.ok(!perguntasDoModelo("larynx").join(" ").includes("valva mitral"));
const { ChatPanelContent } = await import("../components/chat/ChatPanel.tsx");
const { ConteudoSiteXR } = await import("../components/viewer/PainelSiteXR.tsx");
const { useVRMedStore } = await import("../lib/store.ts");
const { TooltipProvider } = await import("../components/ui/tooltip.tsx");
const inicial = useVRMedStore.getInitialState(), antes = { ...inicial };
try {
  for (const modelo of ALL_MODELS) for (const historico of [false, true]) {
    Object.assign(inicial, { currentOrganId: modelo.id, chat: historico ? [{ id: "sintetica", role: "user", content: "Pergunta de teste anterior", createdAt: 0 }] : [] });
    for (const html of [renderToStaticMarkup(h(TooltipProvider, null, h(ChatPanelContent))), renderToStaticMarkup(h(ConteudoSiteXR, { id: "tutor", aoFechar: () => {} }))]) {
      for (const pergunta of perguntasDoModelo(modelo.id)) assert.ok(html.includes(pergunta), `${modelo.name}: sugestões presentes com/sem histórico, desktop e XR`);
      assert.ok(html.includes(`Dúvidas sobre ${modelo.name}`));
    }
  }
} finally { Object.assign(inicial, antes); }

const painel = readFileSync("components/viewer/PainelSiteXR.tsx", "utf8");
const renderer = readFileSync("lib/renderizar-painel-dom.ts", "utf8");
assert.match(painel, /sessao\.visibilityState === "visible"/);
assert.match(painel, /r\.attributeName !== "tabindex"/);
assert.match(painel, /if \(!proximo \|\| !podeCapturar\(\)\) return/);
assert.match(renderer, /if \(!ativo\(\)\) return null/);
assert.match(renderer, /dupla\.verso = dupla\.frente/);
assert.ok(!painel.slice(painel.indexOf("const apontar ="), painel.indexOf("const pressionar =")).includes("alvoAindaValido"), "hover não consulta estilo/layout por frame");
assert.ok(painel.slice(painel.indexOf("const pressionar =")).includes("alvoAindaValido"), "clique não usa alvo obsoleto");
assert.match(renderer, /validarPixelsPainel/);
console.log(`ok: ${ALL_MODELS.length} modelos com sugestões específicas, identidade DOM/XR, recorte conservador, cancelamento de captura e hover sem leitura de layout`);
console.log("limite: desempenho numérico exige o navegador; FPS e conforto exigem Quest físico.");
