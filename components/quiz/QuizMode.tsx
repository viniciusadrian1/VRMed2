"use client";

import { useEffect, useRef, useState } from "react";
import Link from "next/link";
import { Clock, GraduationCap, Play, Timer } from "lucide-react";
import { track } from "@/lib/analytics";
import { formatDate } from "@/lib/format";
import { genId } from "@/lib/format";
import { ALL_MODELS, getOrganById } from "@/lib/organs";
import { QUIZ_TIME_PER_QUESTION, anotacoesQuizaveis, buildQuiz } from "@/lib/quiz";
import { useVRMedStore } from "@/lib/store";
import { cn } from "@/lib/utils";
import { Button } from "@/components/ui/button";
import { Card } from "@/components/ui/card";
import { Progress } from "@/components/ui/progress";
import { Skeleton } from "@/components/ui/skeleton";
import type {
  QuizAnswer,
  QuizQuestion,
  QuizResult,
  QuizTimingMode,
} from "@/types";
import { QuestionCard } from "./QuestionCard";
import { QuizScene } from "./QuizScene";
import { ScoreBoard } from "./ScoreBoard";

type Phase = "setup" | "playing" | "result";
const COUNT_OPTIONS = [3, 5, 10];

/** Controlador do modo quiz: configuração, execução e resultado. */
export function QuizMode() {
  const hasHydrated = useVRMedStore((s) => s.hasHydrated);
  const annotationsByOrgan = useVRMedStore((s) => s.annotationsByOrgan);
  const addQuizResult = useVRMedStore((s) => s.addQuizResult);
  const saveSession = useVRMedStore((s) => s.saveSession);

  const [phase, setPhase] = useState<Phase>("setup");
  const [organId, setOrganId] = useState<string | null>(null);
  const [count, setCount] = useState(5);
  const [timingMode, setTimingMode] = useState<QuizTimingMode>("free");

  const [questions, setQuestions] = useState<QuizQuestion[]>([]);
  const [currentIndex, setCurrentIndex] = useState(0);
  const [answers, setAnswers] = useState<QuizAnswer[]>([]);
  const [selected, setSelected] = useState<string | null>(null);
  const [timeLeft, setTimeLeft] = useState(QUIZ_TIME_PER_QUESTION);
  const [result, setResult] = useState<QuizResult | null>(null);
  const startedAt = useRef(0);

  // Modelos (órgãos ou sistemas) com anotações suficientes para um quiz.
  const quizableOrgans = ALL_MODELS.filter(
    (model) =>
      anotacoesQuizaveis(annotationsByOrgan[model.id] ?? []).length > 0,
  );

  // Contagem regressiva do modo cronometrado.
  useEffect(() => {
    if (
      phase !== "playing" ||
      timingMode !== "timed" ||
      selected !== null ||
      timeLeft <= 0
    ) {
      return;
    }
    const timer = window.setTimeout(() => setTimeLeft((v) => v - 1), 1000);
    return () => window.clearTimeout(timer);
  }, [phase, timingMode, selected, timeLeft]);

  // Esgotado o tempo, a questão é registrada como erro.
  useEffect(() => {
    if (
      phase === "playing" &&
      timingMode === "timed" &&
      selected === null &&
      timeLeft === 0
    ) {
      const question = questions[currentIndex];
      if (!question) return;
      setSelected("");
      setAnswers((prev) => [
        ...prev,
        { questionId: question.id, selected: "", correct: false },
      ]);
    }
  }, [timeLeft, phase, timingMode, selected, questions, currentIndex]);

  const beginQuiz = (targetOrganId: string) => {
    const organ = getOrganById(targetOrganId);
    if (!organ) return;
    const annotations = anotacoesQuizaveis(
      annotationsByOrgan[targetOrganId] ?? [],
    );
    const built = buildQuiz(annotations, count);
    if (built.length === 0) return;

    setOrganId(targetOrganId);
    setQuestions(built);
    setCurrentIndex(0);
    setAnswers([]);
    setSelected(null);
    setResult(null);
    setTimeLeft(QUIZ_TIME_PER_QUESTION);
    startedAt.current = Date.now();
    track("quiz_started", {
      organ: targetOrganId,
      count: built.length,
      mode: timingMode,
    });
    setPhase("playing");
  };

  const handleSelect = (option: string) => {
    if (selected !== null) return;
    const question = questions[currentIndex];
    setSelected(option);
    setAnswers((prev) => [
      ...prev,
      {
        questionId: question.id,
        selected: option,
        correct: option === question.correctAnswer,
      },
    ]);
  };

  const finishQuiz = () => {
    const organ = getOrganById(organId);
    const score = answers.filter((a) => a.correct).length;
    const quizResult: QuizResult = {
      id: genId(),
      organId: organId ?? "",
      organName: organ?.name ?? "",
      score,
      total: questions.length,
      mode: timingMode,
      durationMs: Date.now() - startedAt.current,
      createdAt: Date.now(),
    };
    addQuizResult(quizResult);
    if (organId && organ) {
      saveSession({
        name: `Quiz — ${organ.name} — ${formatDate(Date.now())}`,
        organId,
        organName: organ.name,
        quizResult,
      });
    }
    track("quiz_completed", {
      organ: organId,
      score,
      total: questions.length,
      mode: timingMode,
    });
    setResult(quizResult);
    setPhase("result");
  };

  const handleNext = () => {
    if (currentIndex + 1 < questions.length) {
      setCurrentIndex((index) => index + 1);
      setSelected(null);
      setTimeLeft(QUIZ_TIME_PER_QUESTION);
    } else {
      finishQuiz();
    }
  };

  /* ----------------------------- Setup -------------------------- */
  if (phase === "setup") {
    if (!hasHydrated) {
      return (
        <div className="grid h-full place-items-center p-6">
          <Skeleton className="h-80 w-full max-w-md rounded-2xl" />
        </div>
      );
    }

    if (quizableOrgans.length === 0) {
      return (
        <div className="grid h-full place-items-center p-6">
          <Card className="max-w-md p-8 text-center">
            <span className="mx-auto grid size-14 place-items-center rounded-2xl bg-accent text-accent-foreground">
              <GraduationCap className="size-7" />
            </span>
            <h2 className="mt-4 font-serif text-xl font-medium">
              Nenhum quiz disponível
            </h2>
            <p className="mt-1 text-sm text-muted-foreground">
              O quiz usa as anotações que você cria nos modelos. Marque
              estruturas no visualizador e dê um nome a cada ponto para montar
              um quiz.
            </p>
            <Button asChild className="mt-5">
              <Link href="/viewer">Abrir o visualizador</Link>
            </Button>
          </Card>
        </div>
      );
    }

    return (
      <div className="grid h-full place-items-center overflow-y-auto p-6">
        <Card className="w-full max-w-md p-8">
          <h2 className="font-serif text-2xl font-medium">Configurar quiz</h2>
          <p className="mt-1 text-sm text-muted-foreground">
            Identifique as estruturas anatômicas que você anotou.
          </p>

          <div className="mt-5">
            <p className="mb-2 text-sm font-medium">Órgão</p>
            <div className="flex flex-wrap gap-2">
              {quizableOrgans.map((organ) => (
                <Button
                  key={organ.id}
                  variant={organ.id === organId ? "default" : "outline"}
                  size="sm"
                  onClick={() => setOrganId(organ.id)}
                >
                  {organ.name}
                </Button>
              ))}
            </div>
          </div>

          <div className="mt-4">
            <p className="mb-2 text-sm font-medium">Número de questões</p>
            <div className="flex gap-2">
              {COUNT_OPTIONS.map((option) => (
                <Button
                  key={option}
                  variant={option === count ? "default" : "outline"}
                  size="sm"
                  onClick={() => setCount(option)}
                >
                  {option}
                </Button>
              ))}
            </div>
            <p className="mt-1 text-xs text-muted-foreground">
              Usa todas as anotações disponíveis caso o órgão tenha menos.
            </p>
          </div>

          <div className="mt-4">
            <p className="mb-2 text-sm font-medium">Modalidade</p>
            <div className="flex gap-2">
              <Button
                variant={timingMode === "free" ? "default" : "outline"}
                size="sm"
                onClick={() => setTimingMode("free")}
              >
                <Clock />
                Tempo livre
              </Button>
              <Button
                variant={timingMode === "timed" ? "default" : "outline"}
                size="sm"
                onClick={() => setTimingMode("timed")}
              >
                <Timer />
                Cronometrado
              </Button>
            </div>
          </div>

          <Button
            className="mt-6 w-full"
            disabled={!organId}
            onClick={() => organId && beginQuiz(organId)}
          >
            <Play />
            Iniciar quiz
          </Button>
        </Card>
      </div>
    );
  }

  /* ---------------------------- Result -------------------------- */
  if (phase === "result" && result) {
    return (
      <div className="h-full overflow-y-auto">
        <ScoreBoard
          result={result}
          questions={questions}
          answers={answers}
          onRestart={() => organId && beginQuiz(organId)}
          onNewQuiz={() => setPhase("setup")}
        />
      </div>
    );
  }

  /* ---------------------------- Playing ------------------------- */
  const question = questions[currentIndex];
  if (!question || !organId) return null;
  const organAnnotations = annotationsByOrgan[organId] ?? [];
  const score = answers.filter((a) => a.correct).length;

  return (
    <div className="flex h-full flex-col">
      <div className="flex shrink-0 items-center gap-3 border-b border-border bg-card px-4 py-2">
        <span className="text-sm font-medium">
          Questão {currentIndex + 1} de {questions.length}
        </span>
        <span className="text-sm text-muted-foreground">
          · {score} acerto{score === 1 ? "" : "s"}
        </span>
        {timingMode === "timed" && (
          <div className="ml-auto flex items-center gap-2">
            <Timer
              className={cn(
                "size-4",
                timeLeft <= 5 ? "text-destructive" : "text-muted-foreground",
              )}
            />
            <span
              className={cn(
                "w-6 text-sm tabular-nums",
                timeLeft <= 5 && "font-semibold text-destructive",
              )}
            >
              {selected === null ? timeLeft : "—"}
            </span>
            <Progress
              value={(timeLeft / QUIZ_TIME_PER_QUESTION) * 100}
              className="w-24"
            />
          </div>
        )}
      </div>

      <div className="vrmed-radial relative min-h-0 flex-1">
        <QuizScene
          organId={organId}
          annotations={organAnnotations}
          activeAnnotationId={question.annotationId}
        />
      </div>

      <QuestionCard
        question={question}
        questionNumber={currentIndex + 1}
        total={questions.length}
        selected={selected}
        onSelect={handleSelect}
        onNext={handleNext}
        isLast={currentIndex + 1 === questions.length}
      />
    </div>
  );
}
