"use client";

import { RotateCcw, Trophy } from "lucide-react";
import { formatDuration } from "@/lib/format";
import { Button } from "@/components/ui/button";
import { Card } from "@/components/ui/card";
import type { QuizAnswer, QuizQuestion, QuizResult } from "@/types";

interface ScoreBoardProps {
  result: QuizResult;
  questions: QuizQuestion[];
  answers: QuizAnswer[];
  onRestart: () => void;
  onNewQuiz: () => void;
}

function performanceMessage(percent: number): string {
  if (percent >= 85) return "Excelente domínio do conteúdo!";
  if (percent >= 60) return "Bom trabalho — continue revisando.";
  return "Vale revisitar o modelo e tentar de novo.";
}

/** Tela de resultado do quiz, com pontuação e revisão dos erros. */
export function ScoreBoard({
  result,
  questions,
  answers,
  onRestart,
  onNewQuiz,
}: ScoreBoardProps) {
  const percent = result.total
    ? Math.round((result.score / result.total) * 100)
    : 0;

  const wrongAnswers = answers
    .filter((answer) => !answer.correct)
    .map((answer) => ({
      answer,
      question: questions.find((q) => q.id === answer.questionId),
    }))
    .filter((item) => item.question !== undefined);

  return (
    <div className="grid place-items-center p-6">
      <Card className="w-full max-w-lg p-8">
        <div className="flex flex-col items-center text-center">
          <span className="grid size-16 place-items-center rounded-2xl bg-accent text-accent-foreground">
            <Trophy className="size-8" />
          </span>
          <h2 className="mt-4 font-serif text-2xl font-medium">
            Quiz concluído
          </h2>
          <p className="mt-1 text-sm text-muted-foreground">
            {result.organName} · {performanceMessage(percent)}
          </p>
          <p className="mt-5 font-serif text-5xl font-medium text-primary">
            {result.score}
            <span className="text-2xl text-muted-foreground">
              {" "}
              / {result.total}
            </span>
          </p>
          <p className="mt-1 text-sm text-muted-foreground">
            {percent}% de acerto · {formatDuration(result.durationMs)}
          </p>
        </div>

        {wrongAnswers.length > 0 && (
          <div className="mt-6 border-t border-border pt-4">
            <h3 className="text-sm font-semibold">Revisão dos erros</h3>
            <ul className="mt-2 flex flex-col gap-2">
              {wrongAnswers.map(({ answer, question }) => (
                <li
                  key={answer.questionId}
                  className="rounded-lg border border-border p-2.5 text-sm"
                >
                  <p className="text-muted-foreground">
                    Sua resposta:{" "}
                    <span className="text-destructive">
                      {answer.selected || "(sem resposta)"}
                    </span>
                  </p>
                  <p className="text-muted-foreground">
                    Correta:{" "}
                    <span className="font-medium text-success">
                      {question?.correctAnswer}
                    </span>
                  </p>
                </li>
              ))}
            </ul>
          </div>
        )}

        <div className="mt-6 flex flex-wrap justify-center gap-2">
          <Button variant="outline" onClick={onNewQuiz}>
            Novo quiz
          </Button>
          <Button onClick={onRestart}>
            <RotateCcw />
            Refazer este quiz
          </Button>
        </div>
      </Card>
    </div>
  );
}
