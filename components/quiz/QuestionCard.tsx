"use client";

import { Check, X } from "lucide-react";
import { cn } from "@/lib/utils";
import { Button } from "@/components/ui/button";
import type { QuizQuestion } from "@/types";

interface QuestionCardProps {
  question: QuizQuestion;
  questionNumber: number;
  total: number;
  /** Alternativa escolhida; `null` enquanto não respondida. */
  selected: string | null;
  onSelect: (option: string) => void;
  onNext: () => void;
  isLast: boolean;
}

/** Cartão com a pergunta atual e as quatro alternativas. */
export function QuestionCard({
  question,
  questionNumber,
  total,
  selected,
  onSelect,
  onNext,
  isLast,
}: QuestionCardProps) {
  const answered = selected !== null;
  const isRight = selected === question.correctAnswer;

  return (
    <div className="border-t border-border bg-card p-4">
      <div className="mx-auto flex max-w-3xl flex-col gap-3">
        <div>
          <p className="text-xs font-medium uppercase tracking-wide text-muted-foreground">
            Questão {questionNumber} de {total}
          </p>
          <h2 className="mt-0.5 font-medium">{question.prompt}</h2>
        </div>

        <div className="grid gap-2 sm:grid-cols-2">
          {question.options.map((option) => {
            const isCorrectOption = option === question.correctAnswer;
            const isChosen = option === selected;
            return (
              <button
                key={option}
                type="button"
                disabled={answered}
                onClick={() => onSelect(option)}
                className={cn(
                  "flex items-center justify-between gap-2 rounded-lg border px-3 py-2.5 text-left text-sm transition-colors",
                  !answered && "border-border hover:bg-muted",
                  answered &&
                    isCorrectOption &&
                    "border-success bg-success/10 font-medium",
                  answered &&
                    isChosen &&
                    !isCorrectOption &&
                    "border-destructive bg-destructive/10",
                  answered &&
                    !isCorrectOption &&
                    !isChosen &&
                    "border-border opacity-55",
                )}
              >
                <span>{option}</span>
                {answered && isCorrectOption && (
                  <Check className="size-4 shrink-0 text-success" />
                )}
                {answered && isChosen && !isCorrectOption && (
                  <X className="size-4 shrink-0 text-destructive" />
                )}
              </button>
            );
          })}
        </div>

        {answered && (
          <div className="flex flex-wrap items-center justify-between gap-2">
            <p className="text-sm">
              {isRight ? (
                <span className="font-medium text-success">
                  Resposta correta!
                </span>
              ) : (
                <span className="text-muted-foreground">
                  Resposta correta:{" "}
                  <span className="font-medium text-foreground">
                    {question.correctAnswer}
                  </span>
                </span>
              )}
            </p>
            <Button onClick={onNext}>
              {isLast ? "Ver resultado" : "Próxima questão"}
            </Button>
          </div>
        )}
      </div>
    </div>
  );
}
