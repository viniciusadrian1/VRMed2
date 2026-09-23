import assert from "node:assert/strict";
import { readFileSync } from "node:fs";
import { setImmediate } from "node:timers/promises";
import * as THREE from "three";
import { createRayPointer } from "@pmndrs/pointer-events";
import "./registrar-aliases-teste.mjs";
import { editarTextoXR, limitar, paginasXR, PAINEIS_XR, TECLAS_XR } from "../lib/painel-estudo-xr.ts";
import { deveAcionarBotao3D, ORDEM_PONTEIRO_UI } from "../lib/botao3d-interacao.ts";
import { applyModelState, computeClippingPlanes, prepareModel } from "../lib/model-utils.ts";
import { bloquearPincaUI, liberarPonteiroUI, maoNaInterface, ocuparPonteiroUI } from "../lib/xr-foco-interface.ts";

// O teste importa os módulos reais; fetch, áudio e relógio do navegador são falsos.
// Nenhuma chamada OpenAI, rede externa, chave ou armazenamento do usuário.
const { useVRMedStore } = await import("../lib/store.ts");
const { useTutor3D } = await import("../lib/tutor-3d-store.ts");
const conversa = await import("../lib/tutor-conversa.ts");
const narracao = await import("../lib/narracao-estudo.ts");
const tts = await import("../lib/tts.ts");
const loja = useVRMedStore.getState;
const originalFetch = globalThis.fetch;

const longo = Array.from({ length: 150 }, (_, i) => `palavra${i}`).join(" ");
const paginas = paginasXR(longo);
assert.equal(paginas.join(" ").replace(/\s+/g, " "), longo);
assert.ok(paginas.every((p) => p.split("\n").length <= 6 && p.split("\n").every((l) => l.length <= 42)));
assert.ok(paginasXR("x".repeat(180)).every((p) => p.split("\n").every((l) => l.length <= 42)));
assert.deepEqual(paginasXR(""), [""]);
assert.equal(editarTextoXR("ação", "Apagar"), "açã");
assert.equal(editarTextoXR("a🫀", "Apagar"), "a");
assert.equal(editarTextoXR("oi", "Espaço"), "oi ");
assert.equal(editarTextoXR("oi", "Limpar"), "");
assert.equal(editarTextoXR("abcd", "e", 4), "abcd");
assert.equal(limitar(0.3 - 0.1, 0, 1), 0.2);
assert.equal(limitar(4, -1, 1), 1);
assert.ok(TECLAS_XR.join("").includes("ç") && TECLAS_XR.join("").includes("ã"));
const botaoA = {}, botaoB = {};
const eventoMao = { pointerId: 23, pointerState: { inputSource: { hand: {}, handedness: "left" } } };
ocuparPonteiroUI(botaoA, eventoMao); ocuparPonteiroUI(botaoB, eventoMao);
liberarPonteiroUI(botaoA, 23);
assert.equal(maoNaInterface("left"), true, "sair do botão antigo não libera o novo");
assert.equal(maoNaInterface("right"), false);
assert.equal(bloquearPincaUI(true, false, false, true), true);
assert.equal(bloquearPincaUI(true, true, true, false), true, "pinça da UI não pega o órgão ao sair da placa");
assert.equal(bloquearPincaUI(false, true, true, true), false);
assert.equal(bloquearPincaUI(true, false, false, false), false);
liberarPonteiroUI(botaoB); assert.equal(maoNaInterface("left"), false);

// Raio real da biblioteca instalada: botões têm prioridade sobre o escudo;
// espaços vazios do painel não atingem uma malha anatômica atrás/à frente.
for (const lado of [-1, 1]) {
  const cena = new THREE.Scene(), camera = new THREE.PerspectiveCamera();
  const painel = new THREE.Group();
  painel.position.set(lado * PAINEIS_XR.lateral, -PAINEIS_XR.abaixoDosOlhos, -PAINEIS_XR.distancia);
  painel.rotation.y = -lado * PAINEIS_XR.inclinacao; cena.add(painel);
  const escudo = new THREE.Mesh(new THREE.PlaneGeometry(PAINEIS_XR.largura, PAINEIS_XR.altura), new THREE.MeshBasicMaterial({ side: THREE.DoubleSide }));
  escudo.position.z = 0.005; escudo.pointerEventsOrder = ORDEM_PONTEIRO_UI - 1;
  escudo.addEventListener("pointerdown", (e) => e.stopPropagation()); painel.add(escudo);
  const orgao = new THREE.Mesh(new THREE.PlaneGeometry(8, 8), new THREE.MeshBasicMaterial({ side: THREE.DoubleSide }));
  orgao.position.z = -0.35; orgao.addEventListener("pointerdown", () => assert.fail("órgão recebeu interação do painel")); cena.add(orgao);
  const teclas: THREE.Mesh[] = [];
  let cliques = 0;
  for (let i = 0; i < 10; i++) {
    const tecla = new THREE.Mesh(new THREE.PlaneGeometry(0.085, PAINEIS_XR.alturaBotao), new THREE.MeshBasicMaterial({ side: THREE.DoubleSide }));
    tecla.position.set((i - 4.5) * 0.098, 0.15, 0.025); tecla.pointerEventsOrder = ORDEM_PONTEIRO_UI;
    tecla.addEventListener("pointerdown", (e) => { e.stopPropagation(); if (deveAcionarBotao3D("pressionar", e)) cliques++; });
    tecla.addEventListener("click", (e) => { e.stopPropagation(); if (deveAcionarBotao3D("clicar", e)) cliques++; });
    painel.add(tecla); teclas.push(tecla);
  }
  for (const mao of [-0.2, 0.2]) {
    const controle = new THREE.Object3D(); controle.position.set(mao, -0.25, 0.1); cena.add(controle);
    const raio = createRayPointer(() => camera, { current: controle }, {});
    let t = 1000;
    const mirar = (ponto: THREE.Vector3) => {
      cena.updateMatrixWorld(true);
      controle.quaternion.setFromRotationMatrix(new THREE.Matrix4().lookAt(controle.position, painel.localToWorld(ponto), new THREE.Vector3(0, 1, 0)));
      cena.updateMatrixWorld(true); raio.move(cena, { timeStamp: t });
    };
    for (const tecla of teclas) {
      mirar(tecla.position.clone());
      assert.equal(raio.getIntersection()?.object, tecla);
      const antes = cliques;
      raio.down({ timeStamp: t, button: 0 }); raio.up({ timeStamp: t + 700, button: 0 }); t += 1000;
      assert.equal(cliques, antes + 1, "gatilho lento confirma uma vez");
      mirar(tecla.position.clone().add(new THREE.Vector3(0.041, 0.03, 0)));
      assert.equal(raio.getIntersection()?.object, tecla, "bordas clicáveis não encolhem");
    }
    mirar(new THREE.Vector3(0, 0.15, 0.025)); // vão entre as teclas centrais
    assert.equal(raio.getIntersection()?.object, escudo);
    raio.down({ timeStamp: t, button: 0 }); raio.up({ timeStamp: t + 70, button: 0 });
    cena.remove(controle);
  }
}

// Mesma store controla camadas, cortes e notas tanto no DOM quanto no XR.
loja().setCurrentOrgan("larynx");
loja().setLayers([{ name: "Epiglottis", label: "Epiglote", visible: true, opacity: 1, color: null, depth: "internal" }]);
loja().setLayerOpacity("Epiglottis", 0.4); loja().applyXray(true); loja().applyXray(false);
assert.equal(loja().layers[0].opacity, 0.4);
loja().setClipPlane("axial", { enabled: true, position: 0.2 });
const planos = computeClippingPlanes(loja().clipping, { center: [0, 0, 0], size: [2, 2, 2] });
const root = new THREE.Group(); root.position.set(1, 0.5, -1); root.scale.setScalar(0.08); root.rotation.z = 0.4; root.updateMatrixWorld();
const pontoNoPlano = planos[0].coplanarPoint(new THREE.Vector3());
assert.ok(Math.abs(planos[0].clone().applyMatrix4(root.matrixWorld).distanceToPoint(root.localToWorld(pontoNoPlano))) < 1e-6);
const caixa = new THREE.Mesh(new THREE.BoxGeometry(), new THREE.MeshStandardMaterial({ side: THREE.DoubleSide }));
const camadasCaixa = prepareModel(caixa);
const raioCorte = new THREE.Raycaster(new THREE.Vector3(0, 0, 2), new THREE.Vector3(0, 0, -1));
applyModelState(caixa, camadasCaixa, [new THREE.Plane(new THREE.Vector3(0, 0, -1), 0)], false);
assert.ok(raioCorte.intersectObject(caixa).every((hit) => hit.point.z <= 0), "a superfície recortada não rouba a seleção da parte visível");
applyModelState(caixa, camadasCaixa.map((l) => ({ ...l, opacity: 0 })), [], false);
assert.equal(raioCorte.intersectObject(caixa).length, 0, "transparência total não seleciona superfície invisível");
applyModelState(caixa, camadasCaixa, [], false);
assert.ok(raioCorte.intersectObject(caixa).length > 0, "restaurar camadas restaura a seleção");
loja().addAnnotation("larynx", { id: "nota-teste", text: "Teste", position: [0, 0.1, 0], color: "#5896c8", hideLabel: false });
loja().updateAnnotation("larynx", "nota-teste", { text: "Nota XR", hideLabel: true });
assert.equal(loja().annotationsByOrgan.larynx[0].text, "Nota XR");
loja().removeAnnotation("larynx", "nota-teste");
assert.equal(loja().annotationsByOrgan.larynx.length, 0);

const encoder = new TextEncoder();
let pedidos = 0;
let fluxo!: ReadableStreamDefaultController<Uint8Array>;
globalThis.fetch = async (_url, init) => {
  pedidos++;
  const corpo = JSON.parse(String(init?.body));
  assert.equal(corpo.messages.filter((m: { content: string }) => m.content === "Explique a epiglote").length, 1);
  return new Response(new ReadableStream({ start(c) { fluxo = c; } }), { headers: { "Content-Type": "application/x-ndjson" } });
};
loja().clearChat(); useTutor3D.getState().registrar("larynx", "Laringe", ["Epiglote"]);
const primeiro = conversa.enviarPerguntaTutor("Explique a epiglote");
await conversa.enviarPerguntaTutor("Duplo clique");
assert.equal(pedidos, 1);
await setImmediate();
fluxo.enqueue(encoder.encode('{"tipo":"texto","texto":"A epiglote ajuda na deglutição."}\n'));
fluxo.enqueue(encoder.encode('{"tipo":"comando","comando":{"acao":"focar","alvo":"e0"}}\n{"tipo":"fim"}\n'));
fluxo.close(); await primeiro;
assert.equal(loja().chat.length, 2);
assert.equal(loja().chat[1].content, "A epiglote ajuda na deglutição.");
assert.equal(useTutor3D.getState().foco?.label, "Epiglote");
assert.equal(conversa.useConversaTutor.getState().ocupado, false);

// Trocar órgão cancela pedido, remove placeholder vazio e rejeita foco tardio.
const segundo = conversa.enviarPerguntaTutor("Outra pergunta");
await setImmediate();
loja().setCurrentOrgan("coracao");
const terceiro = conversa.enviarPerguntaTutor("Pergunta no novo órgão");
await segundo;
assert.equal(conversa.useConversaTutor.getState().ocupado, true, "finally do pedido antigo não libera o novo");
await setImmediate();
fluxo.enqueue(encoder.encode('{"tipo":"texto","texto":"Resposta no novo órgão."}\n{"tipo":"fim"}\n'));
fluxo.close(); await terceiro;
assert.equal(conversa.useConversaTutor.getState().ocupado, false);
assert.equal(loja().chat.filter((m) => m.role === "assistant" && !m.content).length, 0);
assert.equal(useTutor3D.getState().foco, null);
assert.equal(conversa.useConversaTutor.getState().erro, null);

// Falha não vira fala da IA e limpar conversa cancela antes de apagar.
globalThis.fetch = async () => new Response('{"error":"Falha simulada"}', { status: 503, headers: { "Content-Type": "application/json" } });
await conversa.enviarPerguntaTutor("Teste de erro");
assert.equal(conversa.useConversaTutor.getState().erro, "Falha simulada");
assert.ok(loja().chat.every((m) => m.content !== "Falha simulada"));
conversa.limparConversaTutor(); assert.deepEqual(loja().chat, []);

// Voz falsa e relógio determinístico: parar antes de 80 ms não deixa voz fantasma.
const tarefas = new Map<number, () => void>(); let proximoTimer = 1;
let falas = 0;
let ultimaFala: { onend?: () => void; onerror?: () => void } | null = null;
const sintetizador = {
  speaking: false, paused: false, pending: false,
  cancel() { this.speaking = false; this.paused = false; },
  pause() { this.paused = true; }, resume() { this.paused = false; },
  speak(utterance: typeof ultimaFala) { falas++; ultimaFala = utterance; this.speaking = true; },
  getVoices: () => [{ lang: "pt-BR", localService: true }],
};
class Fala { text: string; constructor(text: string) { this.text = text; } }
Object.defineProperty(globalThis, "SpeechSynthesisUtterance", { configurable: true, value: Fala });
Object.defineProperty(globalThis, "window", { configurable: true, value: {
  speechSynthesis: sintetizador, SpeechSynthesisUtterance: Fala,
  setTimeout(fn: () => void) { const id = proximoTimer++; tarefas.set(id, fn); return id; },
  clearTimeout(id: number) { tarefas.delete(id); },
  setInterval: () => 10000, clearInterval: () => {},
}});
const avancar = () => { const lista = [...tarefas.values()]; tarefas.clear(); lista.forEach((fn) => fn()); };
tts.speak("Teste"); tts.cancelSpeech(); avancar(); assert.equal(falas, 0);
globalThis.fetch = async () => Response.json({ name: "Coração", shortDescription: "Teste", fullDescription: "Descrição local de teste.", sources: ["Fonte de teste"] });
await narracao.prepararNarracao("coracao");
narracao.ouvirNarracao(); avancar(); assert.equal(falas, 1);
narracao.pausarNarracao(); assert.equal(narracao.useNarracaoEstudo.getState().status, "paused");
narracao.ouvirNarracao(); assert.equal(narracao.useNarracaoEstudo.getState().status, "playing");
narracao.velocidadeNarracao(4); assert.equal(narracao.useNarracaoEstudo.getState().rate, 2);
const anterior = ultimaFala as { onend?: () => void } | null;
narracao.pararNarracao(); narracao.ouvirNarracao(); avancar();
anterior?.onend?.();
assert.equal(narracao.useNarracaoEstudo.getState().status, "playing", "fim de fala antiga não encerra a nova");
narracao.encerrarNarracao(); assert.equal(narracao.useNarracaoEstudo.getState().status, "idle");
// Uma descrição antiga não pode repor o órgão depois de limpar a seleção.
let resolverDescricao!: (resposta: Response) => void;
globalThis.fetch = () => new Promise((resolve) => { resolverDescricao = resolve; });
const descricaoAntiga = narracao.prepararNarracao("larynx");
await narracao.prepararNarracao(null);
resolverDescricao(Response.json({ name: "Antiga", fullDescription: "Não exibir.", sources: [] }));
await descricaoAntiga;
assert.equal(narracao.useNarracaoEstudo.getState().description, null);
assert.equal(narracao.useNarracaoEstudo.getState().loading, false);
Reflect.deleteProperty(globalThis, "window"); Reflect.deleteProperty(globalThis, "SpeechSynthesisUtterance");
globalThis.fetch = originalFetch;

const scene = readFileSync("components/viewer/Scene.tsx", "utf8");
assert.match(scene, /process.env.NODE_ENV === "development" && !inSession/);
assert.match(scene, /\(inSession \|\| inspecao\) && <PaineisEstudoXR/);
assert.match(scene, /dpr=\{inXR \? 1/);
const ancoragem = readFileSync("components/viewer/PaineisEstudoXR.tsx", "utf8");
assert.match(ancoragem, /if \(!reposicionar.current\) return/);
assert.ok(!/camera\.position|camera\.lookAt/.test(ancoragem), "painéis nunca movimentam a câmera XR");
assert.match(ancoragem, /"y-button"/); assert.match(ancoragem, /"b-button"/);
assert.ok(!readFileSync("components/viewer/OrganModel.tsx", "utf8").includes("inSession ? [] : computeClippingPlanes"));
console.log("ok: painéis XR — paginação, teclado, dois raios/lados, escudo, gatilho lento, camadas/cortes/notas, conversa compartilhada, cancelamento, falhas e narração");
