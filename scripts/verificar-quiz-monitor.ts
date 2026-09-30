import assert from "node:assert/strict";
import { readFileSync } from "node:fs";
import { Euler, Vector3 } from "three";
import { buildQuiz, QUIZ_TIME_PER_QUESTION } from "../lib/quiz.ts";
import { iniciarQuizMonitor, reduzirQuizMonitor, vistaParaPonto, paginasTextoMonitor, modeloPermitidoNoMonitor } from "../lib/monitor-quiz.ts";
import { MODOS_ESTUDO } from "../lib/sala-monitor.ts";
import type { Annotation } from "../types/index.ts";

const notas: Annotation[] = [
  { id: "a", text: "Estrutura A", position: [.2, .4, .1], color: "#fff", hideLabel: false },
  { id: "b", text: "Estrutura B", position: [-.5, .3, -.8], color: "#fff", hideLabel: false },
  { id: "c", text: "Nova anotação", position: [0, 0, 0], color: "#fff", hideLabel: false },
];
const questoes = buildQuiz(notas, 5);
assert.equal(questoes.length, 2, "reutiliza as anotações válidas e não inventa perguntas");
assert.ok(questoes.every((q) => q.options.length === 4 && new Set(q.options).size === 4 && q.options.includes(q.correctAnswer)));
let partida = iniciarQuizMonitor(questoes);
const inicial = partida;
assert.equal(reduzirQuizMonitor(partida, { tipo: "proxima", questao: questoes[0].id }), partida, "não pula questão sem responder");
assert.equal(reduzirQuizMonitor(partida, { tipo: "responder", questao: questoes[0].id, opcao: "injetada" }), partida);
partida = reduzirQuizMonitor(partida, { tipo: "responder", questao: questoes[0].id, opcao: questoes[0].correctAnswer });
const respondida = partida;
partida = reduzirQuizMonitor(partida, { tipo: "responder", questao: questoes[0].id, opcao: questoes[0].options[0] });
assert.equal(partida, respondida, "dois controles não duplicam a resposta");
assert.equal(reduzirQuizMonitor(partida, { tipo: "tempo", questao: questoes[0].id }), respondida, "timeout após clique é ignorado");
partida = reduzirQuizMonitor(partida, { tipo: "proxima", questao: questoes[0].id });
assert.equal(reduzirQuizMonitor(partida, { tipo: "proxima", questao: questoes[0].id }), partida, "evento velho não pula outra questão");
for (let i = 0; i < QUIZ_TIME_PER_QUESTION; i++) partida = reduzirQuizMonitor(partida, { tipo: "tempo", questao: questoes[1].id });
assert.equal(partida.restante, 0);
assert.equal(partida.respostas.length, 2);
assert.deepEqual(partida.respostas.map((r) => r.correct), [true, false]);
const esgotada = partida;
assert.equal(reduzirQuizMonitor(partida, { tipo: "responder", questao: questoes[1].id, opcao: questoes[1].correctAnswer }), esgotada);
partida = reduzirQuizMonitor(partida, { tipo: "proxima", questao: questoes[1].id });
assert.equal(partida.concluida, true);
assert.equal(reduzirQuizMonitor(partida, { tipo: "proxima", questao: questoes[1].id }), partida);
assert.equal(inicial.respostas.length, 0, "reducer não modifica estados anteriores");
assert.equal(iniciarQuizMonitor(questoes).respostas.length, 0, "refazer começa limpo");
for (const ponto of notas.map((n) => n.position)) {
  const vista = vistaParaPonto(ponto);
  const girado = new Vector3(...ponto).applyEuler(new Euler(vista.vertical, vista.horizontal, 0));
  assert.ok(Math.abs(girado.x) < 1e-8 && girado.z >= 0 && Math.abs(vista.vertical) <= .6, "giro inicial expõe a face marcada e preserva a silhueta sem mudar a câmera XR");
}
const longo = "Uma anotação longa pode ser lida por completo. ".repeat(20).trim();
const paginas = paginasTextoMonitor(longo);
assert.ok(paginas.every((p) => p.length <= 110));
assert.equal(paginas.join(" "), longo);
assert.equal(modeloPermitidoNoMonitor("myology"), false);
assert.equal(modeloPermitidoNoMonitor("coracao"), true);
assert.deepEqual(MODOS_ESTUDO.map((m) => m.href), ["/viewer", "/compare", "/quiz", "/clinica", "/duelo"]);
const fonte = readFileSync("components/sala/QuizNoMonitor.tsx", "utf8");
assert.doesNotMatch(fonte, /sairENavegar|session\.end|window\.location|<Canvas|html2canvas|setCurrentOrgan/);
assert.match(fonte, /!pronto \|\| !visivel \|\| resposta/);
assert.match(fonte, /salvou\.current = true/);
assert.match(fonte, /adicionar\(registro\)/);
assert.match(fonte, /ModeloNoMonitor/);
assert.match(readFileSync("components/sala/MonitorEstudos.tsx", "utf8"), /<QuizNoMonitor/);
console.log("ok: Quiz no monitor — geração existente, acerto/erro/timeout, controles duplicados, revisão, marcador e isolamento XR");
