import assert from "node:assert/strict";
import { readFileSync } from "node:fs";
import type OpenAI from "openai";
import * as THREE from "three";
import { applyModelState, detectStructures, identifyStructure, prepareModel, NOME_DO_ROOT } from "../lib/model-utils.ts";
import { camadasComFoco, contextoTutorSchema, validarComandoTutor, lerEventosTutor, type EventoTutor } from "../lib/tutor-3d.ts";
import { useTutor3D } from "../lib/tutor-3d-store.ts";
import { responderComGuia } from "../lib/tutor-3d-servidor.ts";

const loja = useTutor3D.getState;
const raiz = new THREE.Group(); raiz.name = NOME_DO_ROOT;
const conteudo = new THREE.Group(); raiz.add(conteudo);
const anonima = new THREE.Mesh(new THREE.BoxGeometry(), new THREE.MeshStandardMaterial());
anonima.name = "Object_1"; conteudo.add(anonima);
prepareModel(conteudo);
assert.deepEqual(detectStructures(conteudo), [], "root da aplicação não vira estrutura anatômica");
assert.equal(identifyStructure(anonima, "Coração"), "Coração");
const epiglote = new THREE.Mesh(new THREE.BoxGeometry(), new THREE.MeshStandardMaterial());
epiglote.name = "Epiglottis"; conteudo.add(epiglote);
assert.deepEqual(detectStructures(conteudo).map((e) => e.label), ["Epiglote"]);
const camadas = prepareModel(conteudo);
const camadaEpiglote = camadas.find((l) => l.label === "Epiglote")!;
camadaEpiglote.visible = false;
camadaEpiglote.opacity = 0.4;
const antesDoFoco = structuredClone(camadas);
applyModelState(conteudo, camadasComFoco(camadas, { id: "e0", label: "Epiglote" }), [], false);
assert.equal(epiglote.visible, true);
assert.equal(epiglote.material.opacity, 1);
assert.equal(anonima.material.opacity, 0.16);
assert.deepEqual(camadas, antesDoFoco, "foco não altera as configurações do aluno");
applyModelState(conteudo, camadasComFoco(camadas, null), [], false);
assert.equal(epiglote.visible, false);
assert.equal(epiglote.material.opacity, 0.4);
assert.equal(anonima.material.opacity, 1);
loja().registrar("larynx", "Laringe", ["Epiglote", "Epiglote", "Cartilagem tireóidea"]);
const contexto = loja().contexto!;
assert.equal(contexto.alvos.length, 3, "rótulos duplicados são agrupados");
assert.ok(contextoTutorSchema.safeParse(contexto).success);
assert.equal(validarComandoTutor({ acao: "focar", alvo: "e99" }, contexto), null);
assert.equal(validarComandoTutor({ acao: "focar", alvo: "e0", camera: [0, 0, 0] }, contexto), null);
assert.equal(validarComandoTutor({ acao: "executar", alvo: "modelo" }, contexto), null);
assert.ok(loja().aplicar({ acao: "focar", alvo: "e0" }, contexto));
assert.equal(loja().foco?.label, "Epiglote");
loja().habilitar(false);
assert.equal(loja().foco, null);
assert.equal(loja().aplicar({ acao: "focar", alvo: "e0" }, contexto), false);
loja().habilitar(true);
assert.equal(loja().aplicar({ acao: "focar", alvo: "e0" }, contexto), false, "desligar e religar não reaproveita pedido antigo");
loja().registrar("coracao", "Coração", []);
assert.equal(loja().aplicar({ acao: "focar", alvo: "e0" }, contexto), false, "resposta atrasada é descartada");
const coracao = loja().contexto!;
assert.equal(validarComandoTutor({ acao: "focar", alvo: "ventriculo" }, coracao), null);
assert.ok(loja().aplicar({ acao: "focar", alvo: "modelo" }, coracao));
assert.ok(loja().aplicar({ acao: "restaurar", alvo: "modelo" }, coracao));
assert.equal(loja().foco, null);
loja().limparContexto();
assert.equal(loja().aplicar({ acao: "focar", alvo: "modelo" }, coracao), false);

const encoder = new TextEncoder();
function corpo(texto: string, umByte = false) {
  const bytes = encoder.encode(texto);
  return new ReadableStream<Uint8Array>({ start(c) {
    if (umByte) for (const byte of bytes) c.enqueue(Uint8Array.of(byte));
    else c.enqueue(bytes);
    c.close();
  } });
}
const eventos: EventoTutor[] = [];
await lerEventosTutor(corpo('{"tipo":"texto","texto":"Coração, ação"}\n{"tipo":"fim"}\n', true), (e) => eventos.push(e));
assert.deepEqual(eventos, [{ tipo: "texto", texto: "Coração, ação" }]);
await assert.rejects(lerEventosTutor(corpo('{"tipo":"texto","texto":"parcial"}\n'), () => {}), /interrompida/);
await assert.rejects(lerEventosTutor(corpo('{"tipo":"erro","erro":"Teste de falha"}\n'), () => {}), /Teste de falha/);
await assert.rejects(lerEventosTutor(corpo('{"tipo":"fim"}\n{"tipo":"texto","texto":"tardio"}\n'), () => {}), /inválida/);
const cancelado = new AbortController(); cancelado.abort();
await assert.rejects(lerEventosTutor(corpo('{"tipo":"comando","comando":{"acao":"focar","alvo":"modelo"}}\n'), () => assert.fail("não executar"), cancelado.signal), /Cancelado/);

type Chunk = { choices: { delta: Record<string, unknown>; finish_reason?: string }[] };
function clienteFalso(argumentos: string, falharDepois = false) {
  let chamadas = 0;
  const params: unknown[] = [];
  return {
    get chamadas() { return chamadas; }, params,
    client: { chat: { completions: { create: async (p: unknown) => {
      params.push(p); chamadas++;
      if (chamadas === 2 && falharDepois) throw new Error("falha simulada");
      const chunks: Chunk[] = chamadas === 1 ? [
        { choices: [{ delta: { tool_calls: [{ index: 0, id: "call_teste", function: { name: "guiar_modelo", arguments: argumentos.slice(0, 12) } }] } }] },
        { choices: [{ delta: { tool_calls: [{ index: 0, function: { arguments: argumentos.slice(12) } }] }, finish_reason: "tool_calls" }] },
      ] : [{ choices: [{ delta: { content: "A epiglote participa da proteção da via aérea." }, finish_reason: "stop" }] }];
      return { controller: new AbortController(), async *[Symbol.asyncIterator]() { yield* chunks; } };
    } } } } as unknown as OpenAI,
  };
}
const mock = clienteFalso('{"acao":"focar","alvo":"e0"}');
const resposta = await responderComGuia(mock.client, "teste", "Teste", [{ role: "user", content: "Explique a epiglote" }], contexto, new AbortController().signal);
const recebidos: EventoTutor[] = [];
await lerEventosTutor(resposta.body!, (e) => recebidos.push(e));
assert.equal(mock.chamadas, 2);
assert.equal(recebidos[0].tipo, "comando", "destaque precede a explicação");
assert.equal(recebidos[1].tipo, "texto");
for (const parametros of ["{}", '{"acao":"focar","alvo":"inventado"}', "JSON quebrado"]) {
  const invalido = clienteFalso(parametros);
  const r = await responderComGuia(invalido.client, "teste", "Teste", [], contexto, new AbortController().signal);
  await assert.rejects(lerEventosTutor(r.body!, () => assert.fail("não emitir comando inválido")), /concluir/);
  assert.equal(invalido.chamadas, 1);
}
const falho = clienteFalso('{"acao":"focar","alvo":"e0"}', true);
const r = await responderComGuia(falho.client, "teste", "Teste", [], contexto, new AbortController().signal);
await assert.rejects(lerEventosTutor(r.body!, () => {}), /concluir/);

const scene = readFileSync("components/viewer/Scene.tsx", "utf8");
assert.ok(scene.includes("if (gl.xr.isPresenting) return;"));
assert.ok(scene.includes('controls.addEventListener("start", cancelar)'));
const foco = readFileSync("components/viewer/FocoTutor3D.tsx", "utf8");
assert.ok(foco.includes("novo && !inSession && !reduzido"));
assert.ok(foco.includes("viewerBridge.cancelCamera()"));
assert.ok(!foco.includes("camera.position"), "destaque não escreve na câmera");
console.log("ok: inventário, alvos válidos, troca de modelo, restauração, UTF-8 fragmentado, falhas, limites de ferramentas e guardas XR");
