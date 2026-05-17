import { genId } from "@/lib/format";
import type { Annotation, QuizQuestion } from "@/types";

/** Tempo por questão no modo cronometrado (segundos). */
export const QUIZ_TIME_PER_QUESTION = 25;

/**
 * Termos anatômicos genéricos usados como distratores quando o órgão não
 * tem anotações suficientes para gerar alternativas erradas plausíveis.
 */
const FALLBACK_TERMS = [
  "Artéria",
  "Veia",
  "Músculo liso",
  "Ligamento",
  "Membrana serosa",
  "Nervo",
  "Vaso linfático",
  "Septo fibroso",
  "Tecido conjuntivo",
  "Cápsula",
  "Cartilagem",
  "Camada mucosa",
];

/** Embaralha um array (Fisher–Yates) sem mutar o original. */
function shuffle<T>(input: T[]): T[] {
  const result = [...input];
  for (let i = result.length - 1; i > 0; i -= 1) {
    const j = Math.floor(Math.random() * (i + 1));
    [result[i], result[j]] = [result[j], result[i]];
  }
  return result;
}

/**
 * Monta um quiz a partir das anotações de um órgão.
 *
 * Cada questão pergunta qual é a estrutura destacada; a resposta correta é o
 * texto da anotação. Os distratores vêm das demais anotações do órgão e, se
 * necessário, de uma lista de termos anatômicos genéricos.
 */
export function buildQuiz(
  annotations: Annotation[],
  count: number,
): QuizQuestion[] {
  const labelled = annotations.filter((a) => a.text.trim().length > 0);
  const selected = shuffle(labelled).slice(0, Math.min(count, labelled.length));

  return selected.map((annotation) => {
    const correct = annotation.text.trim();
    const otherLabels = labelled
      .map((a) => a.text.trim())
      .filter((label) => label !== correct);

    const distractorPool = shuffle([
      ...new Set([...otherLabels, ...FALLBACK_TERMS]),
    ])
      .filter((term) => term !== correct)
      .slice(0, 3);

    // Garante três distratores mesmo em casos extremos.
    let fallbackIndex = 0;
    while (distractorPool.length < 3) {
      const term = FALLBACK_TERMS[fallbackIndex];
      fallbackIndex += 1;
      if (term !== correct && !distractorPool.includes(term)) {
        distractorPool.push(term);
      }
      if (fallbackIndex > FALLBACK_TERMS.length) break;
    }

    return {
      id: genId(),
      annotationId: annotation.id,
      prompt: "Qual é a estrutura destacada no modelo?",
      correctAnswer: correct,
      options: shuffle([correct, ...distractorPool]),
    };
  });
}
