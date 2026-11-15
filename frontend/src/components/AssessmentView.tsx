"use client";

import React, { useEffect, useMemo, useState } from "react";
import { AlertTriangle, ArrowRight, CheckCircle2, CheckSquare, ClipboardList, FileText, MapPin, Play, RotateCcw, Target, XCircle } from "lucide-react";
import { api } from "@/lib/api";
import {
  ACTION_LABELS,
  AssessmentCycleResult,
  Citation,
  CurriculumTopic,
  Difficulty,
  Question,
  QuestionType,
  QuizReport,
  QuizSession,
  locatorLabel,
} from "@/lib/types";
import { EmptyState, ErrorBanner, GhostButton, MasteryBar, Panel, PrimaryButton, SectionHeader, Select, Spinner } from "./ui";

interface Props {
  topics: CurriculumTopic[];
  initialTopic?: string;
  pendingQuiz?: QuizSession | null;
  onPendingQuizConsumed?: () => void;
  onOpenCitation: (c: Citation) => void;
  onAssessmentCompleted?: () => void;
}

const TYPE_LABEL: Record<QuestionType, string> = { mcq: "Multiple choice", numerical: "Numerical", short_answer: "Short answer" };

function TopicOptions({ topics }: { topics: CurriculumTopic[] }) {
  const own = topics.filter((t) => t.owner === "you");
  const demo = topics.filter((t) => t.owner !== "you");
  return (
    <>
      {own.length > 0 && (
        <optgroup label="Your material">
          {own.map((t) => (
            <option key={t.topic_id} value={t.topic_id}>
              {t.name}
            </option>
          ))}
        </optgroup>
      )}
      <optgroup label="Demo course">
        {demo.map((t) => (
          <option key={t.topic_id} value={t.topic_id}>
            {t.name}
          </option>
        ))}
      </optgroup>
    </>
  );
}

/* --------------------------------------------------------------- question */
function QuestionCard({
  question,
  topicName,
  onSubmit,
  result,
  submitting,
  showFeedback = true,
  onOpenCitation,
}: {
  question: Question;
  topicName: string;
  onSubmit: (answer: string) => void;
  result: AssessmentCycleResult | null;
  submitting: boolean;
  showFeedback?: boolean;
  onOpenCitation: (c: Citation) => void;
}) {
  const [answer, setAnswer] = useState("");
  useEffect(() => {
    setAnswer("");
  }, [question.question_id]);
  const locked = !!result || submitting;
  const ev = result?.evaluation;

  return (
    <Panel className="space-y-4">
      <div className="flex flex-wrap items-center gap-2 text-[11px] font-bold uppercase tracking-wide">
        <span className="rounded-md border border-indigo-500/40 bg-indigo-500/10 px-2 py-0.5 text-indigo-300">{topicName}</span>
        <span className="rounded-md border border-slate-700 px-2 py-0.5 text-slate-300">{TYPE_LABEL[question.question_type]}</span>
        <span className="rounded-md border border-slate-700 px-2 py-0.5 text-slate-400">{question.difficulty}</span>
        <span className="rounded-md border border-emerald-500/30 px-2 py-0.5 text-emerald-300" title={(question.metadata?.checks || []).join(", ")}>
          verified
        </span>
      </div>
      <p className="text-base font-semibold leading-relaxed text-slate-100">{question.prompt}</p>

      <form
        onSubmit={(e) => {
          e.preventDefault();
          if (answer.trim() && !locked) onSubmit(answer.trim());
        }}
        className="space-y-3"
      >
        {question.question_type === "mcq" ? (
          <div className="grid gap-2">
            {question.options.map((o) => {
              const chosen = answer === o.key;
              const isKey = ev && ev.expected_answer.startsWith(`${o.key}.`);
              const style =
                ev && showFeedback
                  ? isKey
                    ? "border-emerald-500/60 bg-emerald-500/10"
                    : chosen
                    ? "border-rose-500/60 bg-rose-500/10"
                    : "border-slate-700 opacity-70"
                  : chosen
                  ? "border-indigo-400 bg-indigo-500/15"
                  : "border-slate-700 hover:border-slate-500";
              return (
                <button
                  type="button"
                  key={o.key}
                  disabled={locked}
                  onClick={() => setAnswer(o.key)}
                  className={`flex items-start gap-3 rounded-xl border-2 p-3 text-left text-sm text-slate-200 transition-colors ${style}`}
                >
                  <span className="flex h-6 w-6 shrink-0 items-center justify-center rounded-lg bg-slate-800 text-xs font-bold">{o.key}</span>
                  <span>{o.text}</span>
                </button>
              );
            })}
          </div>
        ) : (
          <input
            value={answer}
            onChange={(e) => setAnswer(e.target.value)}
            disabled={locked}
            inputMode={question.question_type === "numerical" ? "decimal" : "text"}
            placeholder={question.question_type === "numerical" ? "Enter a number (units optional)" : "Type your answer"}
            className="w-full rounded-xl border-2 border-slate-600 bg-slate-950 px-4 py-3 text-sm text-slate-100 focus:border-indigo-400 focus:outline-none"
          />
        )}
        {!result && (
          <PrimaryButton type="submit" disabled={!answer.trim() || submitting}>
            {submitting ? "Checking…" : "Submit answer"}
          </PrimaryButton>
        )}
      </form>

      {ev && showFeedback && (
        <div className="space-y-3 border-t border-slate-800 pt-4">
          <div
            className={`flex items-start gap-2 rounded-xl border p-3 text-sm ${
              ev.is_correct ? "border-emerald-500/40 bg-emerald-500/10 text-emerald-200" : ev.status === "partially_correct" ? "border-amber-500/40 bg-amber-500/10 text-amber-200" : "border-rose-500/40 bg-rose-500/10 text-rose-200"
            }`}
          >
            {ev.is_correct ? <CheckCircle2 className="mt-0.5 h-4 w-4 shrink-0" /> : <XCircle className="mt-0.5 h-4 w-4 shrink-0" />}
            <span>{ev.feedback}</span>
          </div>
          {ev.solution && (
            <div className="rounded-xl border border-slate-800 bg-slate-950 p-3 text-xs text-slate-300">
              <span className="font-bold text-slate-200">From the source: </span>
              {ev.solution}
            </div>
          )}
          <div className="flex flex-wrap gap-2">
            {ev.citations.map((c) => (
              <button key={c.evidence_id} onClick={() => onOpenCitation(c)} className="flex items-center gap-1.5 rounded-lg border border-indigo-500/30 bg-indigo-500/10 px-2.5 py-1 text-xs text-indigo-300 hover:bg-indigo-500/20">
                <MapPin className="h-3 w-3" /> {c.source_title}, {locatorLabel(c)}
              </button>
            ))}
          </div>
          {result && (
            <div className="space-y-1.5">
              <div className="flex items-center justify-between text-xs text-slate-400">
                <span>Mastery of {topicName}</span>
                <span className="font-mono">
                  {(result.p_before * 100).toFixed(0)}% → <b className="text-slate-100">{(result.mastery.p_mastery * 100).toFixed(0)}%</b>
                </span>
              </div>
              <MasteryBar p={result.mastery.p_mastery} before={result.p_before} />
            </div>
          )}
          {result?.misconception_detected && result.misconception && (
            <div className="flex items-start gap-2 rounded-xl border border-amber-500/40 bg-amber-500/10 p-3 text-xs text-amber-200">
              <AlertTriangle className="mt-0.5 h-4 w-4 shrink-0" />
              <span>
                <b>Possible misconception:</b> {result.misconception.suspected_misconception}. {result.misconception.remediation_note}
              </span>
            </div>
          )}
        </div>
      )}
    </Panel>
  );
}

/* ----------------------------------------------------------------- report */
function Report({ report, onOpenCitation, onRestart }: { report: QuizReport; onOpenCitation: (c: Citation) => void; onRestart: () => void }) {
  const rec = report.next_recommendation;
  return (
    <div className="space-y-5">
      <Panel className="flex flex-col gap-4 sm:flex-row sm:items-center sm:justify-between">
        <div>
          <p className="text-xs font-bold uppercase tracking-wider text-indigo-300">{report.mode === "exam" ? "Mock exam report" : report.mode === "diagnostic" ? "Placement check report" : "Quiz report"}</p>
          <p className="mt-1 text-3xl font-black text-white">{report.percent.toFixed(0)}%</p>
          <p className="text-xs text-slate-400">
            {report.score} of {report.total} points · {report.answered} answered
          </p>
        </div>
        <GhostButton onClick={onRestart}>
          <RotateCcw className="h-4 w-4" /> New quiz
        </GhostButton>
      </Panel>

      <Panel>
        <h3 className="mb-3 text-sm font-bold text-slate-100">Topics</h3>
        <div className="space-y-3">
          {report.topics.map((t) => (
            <div key={t.topic_id}>
              <div className="mb-1 flex items-center justify-between text-xs">
                <span className="font-semibold text-slate-200">
                  {t.topic_name}{" "}
                  <span className={`ml-1 rounded px-1.5 py-0.5 text-[10px] uppercase ${t.status === "strong" ? "bg-emerald-500/15 text-emerald-300" : t.status === "weak" ? "bg-rose-500/15 text-rose-300" : "bg-amber-500/15 text-amber-300"}`}>
                    {t.status}
                  </span>
                </span>
                <span className="font-mono text-slate-400">
                  {t.correct}/{t.answered} · mastery {Math.round((t.mastery_before ?? 0) * 100)}% → {Math.round(t.mastery_after * 100)}%
                </span>
              </div>
              <MasteryBar p={t.mastery_after} before={t.mastery_before} />
            </div>
          ))}
        </div>
      </Panel>

      {(report.weak_topics.length > 0 || report.confusions.length > 0 || report.misconceptions.length > 0) && (
        <Panel className="space-y-3">
          <h3 className="flex items-center gap-2 text-sm font-bold text-slate-100">
            <AlertTriangle className="h-4 w-4 text-amber-400" /> What to work on
          </h3>
          {report.weak_topics.length > 0 && (
            <p className="text-sm text-slate-300">
              Weak topics: <b>{report.weak_topics.map((t) => t.topic_name).join(", ")}</b>
            </p>
          )}
          {report.confusions.map((c, i) => (
            <p key={i} className="text-sm text-amber-200">
              • {c.note}
            </p>
          ))}
          {report.misconceptions.map((m) => (
            <p key={m.signal_id} className="text-sm text-amber-200">
              • Likely misconception: {m.suspected_misconception} ({m.error_count} errors)
            </p>
          ))}
        </Panel>
      )}

      {report.review.length > 0 && (
        <Panel>
          <h3 className="mb-3 flex items-center gap-2 text-sm font-bold text-slate-100">
            <FileText className="h-4 w-4 text-indigo-400" /> Re-read these passages
          </h3>
          <div className="flex flex-wrap gap-2">
            {report.review.map((r) => (
              <button key={r.citation.evidence_id} onClick={() => onOpenCitation(r.citation)} className="flex items-center gap-1.5 rounded-lg border border-indigo-500/30 bg-indigo-500/10 px-2.5 py-1 text-xs text-indigo-300 hover:bg-indigo-500/20">
                <MapPin className="h-3 w-3" /> {r.citation.source_title}, {locatorLabel(r.citation)}
              </button>
            ))}
          </div>
        </Panel>
      )}

      <Panel>
        <h3 className="mb-3 text-sm font-bold text-slate-100">Answers</h3>
        <div className="space-y-2">
          {report.items.map((it, i) => (
            <details key={it.question_id} className="rounded-xl border border-slate-800 bg-slate-950 p-3 text-sm">
              <summary className="flex cursor-pointer items-start gap-2 text-slate-200">
                {it.is_correct ? <CheckCircle2 className="mt-0.5 h-4 w-4 shrink-0 text-emerald-400" /> : <XCircle className="mt-0.5 h-4 w-4 shrink-0 text-rose-400" />}
                <span>
                  {i + 1}. {it.prompt}
                </span>
              </summary>
              <div className="mt-2 space-y-1 pl-6 text-xs text-slate-400">
                <p>Your answer: {it.your_answer ?? "—"}</p>
                <p>Correct answer: <span className="text-slate-200">{it.expected_answer}</span></p>
                {it.solution && <p>Source: {it.solution}</p>}
                {it.citation && (
                  <button onClick={() => onOpenCitation(it.citation!)} className="text-indigo-300 underline decoration-dotted">
                    {it.citation.source_title}, {locatorLabel(it.citation)}
                  </button>
                )}
              </div>
            </details>
          ))}
        </div>
      </Panel>

      {rec && rec.topic_id && (
        <Panel className="border-indigo-500/40">
          <p className="text-xs font-bold uppercase tracking-wider text-indigo-300">Next step · {ACTION_LABELS[rec.recommended_action]}</p>
          <p className="mt-1 text-sm text-slate-200">{rec.rationale}</p>
        </Panel>
      )}
    </div>
  );
}

/* ------------------------------------------------------------------- view */
export const AssessmentView: React.FC<Props> = ({ topics, initialTopic, pendingQuiz, onPendingQuizConsumed, onOpenCitation, onAssessmentCompleted }) => {
  const [mode, setMode] = useState<"practice" | "builder" | "quiz" | "report">("practice");
  const names = useMemo(() => Object.fromEntries(topics.map((t) => [t.topic_id, t.name])), [topics]);
  const withQuestions = topics.filter((t) => (t.question_count ?? 1) > 0);

  // quick practice
  const [topic, setTopic] = useState<string>(initialTopic || "");
  const [difficulty, setDifficulty] = useState<Difficulty | "">("");
  const [qtype, setQtype] = useState<QuestionType | "">("");
  const [question, setQuestion] = useState<Question | null>(null);
  const [served, setServed] = useState<string[]>([]);
  const [result, setResult] = useState<AssessmentCycleResult | null>(null);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);

  // quiz
  const [scope, setScope] = useState<string[]>([]);
  const [count, setCount] = useState(8);
  const [types, setTypes] = useState<QuestionType[]>(["mcq", "numerical", "short_answer"]);
  const [quizMode, setQuizMode] = useState<"practice" | "exam">("practice");
  const [quiz, setQuiz] = useState<QuizSession | null>(null);
  const [qi, setQi] = useState(0);
  const [quizResults, setQuizResults] = useState<Record<string, AssessmentCycleResult | { recorded: boolean }>>({});
  const [report, setReport] = useState<QuizReport | null>(null);

  useEffect(() => {
    if (!topic && withQuestions.length) setTopic((withQuestions.find((t) => t.owner === "you") || withQuestions[0]).topic_id);
  }, [topics]); // eslint-disable-line react-hooks/exhaustive-deps

  useEffect(() => {
    if (initialTopic) {
      setTopic(initialTopic);
      setMode("practice");
      loadQuestion(initialTopic);
    }
  }, [initialTopic]); // eslint-disable-line react-hooks/exhaustive-deps

  useEffect(() => {
    if (pendingQuiz) {
      startQuiz(pendingQuiz);
      onPendingQuizConsumed?.();
    }
  }, [pendingQuiz]); // eslint-disable-line react-hooks/exhaustive-deps

  async function loadQuestion(t = topic, d = difficulty, ty = qtype) {
    if (!t) return;
    setBusy(true);
    setError(null);
    setResult(null);
    try {
      const q = await api.selectQuestion(t, served, d || undefined, ty || undefined);
      setQuestion(q);
      setServed((s) => [...s.slice(-50), q.question_id]);
    } catch (e: any) {
      setQuestion(null);
      setError(e.message);
    } finally {
      setBusy(false);
    }
  }

  async function submitPractice(answer: string) {
    if (!question) return;
    setBusy(true);
    setError(null);
    try {
      setResult(await api.submitAnswer(question.question_id, answer));
      onAssessmentCompleted?.();
    } catch (e: any) {
      setError(e.message);
    } finally {
      setBusy(false);
    }
  }

  function startQuiz(q: QuizSession) {
    setQuiz(q);
    setQi(0);
    setQuizResults({});
    setReport(null);
    setMode("quiz");
  }

  async function createQuiz() {
    setBusy(true);
    setError(null);
    try {
      startQuiz(await api.createQuiz({ topic_ids: scope, count, types, mode: quizMode }));
    } catch (e: any) {
      setError(e.message);
    } finally {
      setBusy(false);
    }
  }

  async function answerQuiz(answer: string) {
    if (!quiz) return;
    const q = quiz.questions[qi];
    setBusy(true);
    setError(null);
    try {
      const r = await api.answerQuiz(quiz.session_id, q.question_id, answer);
      setQuizResults((s) => ({ ...s, [q.question_id]: r }));
      onAssessmentCompleted?.();
      if (quiz.mode === "exam" && qi < quiz.questions.length - 1) setQi(qi + 1);
    } catch (e: any) {
      setError(e.message);
    } finally {
      setBusy(false);
    }
  }

  async function finishQuiz() {
    if (!quiz) return;
    setBusy(true);
    setError(null);
    try {
      setReport(await api.finishQuiz(quiz.session_id));
      setMode("report");
      onAssessmentCompleted?.();
    } catch (e: any) {
      setError(e.message);
    } finally {
      setBusy(false);
    }
  }

  if (!topics.length) {
    return (
      <div className="mx-auto max-w-4xl p-6">
        <EmptyState icon={CheckSquare} title="No topics yet" body="Upload course material in the Materials tab. Topics and verified questions are generated automatically." />
      </div>
    );
  }

  const current = quiz?.questions[qi];
  const currentResult = current ? quizResults[current.question_id] : undefined;
  const answeredCount = Object.keys(quizResults).length;

  return (
    <div className="mx-auto max-w-4xl space-y-5 p-4 sm:p-6">
      <SectionHeader
        icon={CheckSquare}
        title="Practice & Exams"
        subtitle="Questions are generated from your sources, checked before use, and never repeat until a topic's bank runs out."
        right={
          <div className="flex gap-2">
            <GhostButton onClick={() => setMode("practice")} className={mode === "practice" ? "border-indigo-400" : ""}>
              <Target className="h-4 w-4" /> Quick practice
            </GhostButton>
            <GhostButton onClick={() => setMode("builder")} className={mode === "builder" ? "border-indigo-400" : ""}>
              <ClipboardList className="h-4 w-4" /> Quiz / mock exam
            </GhostButton>
          </div>
        }
      />
      {error && <ErrorBanner message={error} onRetry={mode === "practice" ? () => loadQuestion() : undefined} />}

      {mode === "practice" && (
        <div className="space-y-4">
          <div className="flex flex-wrap items-center gap-2">
            <Select value={topic} onChange={(e) => { setTopic(e.target.value); setQuestion(null); setResult(null); }}>
              <TopicOptions topics={withQuestions} />
            </Select>
            <Select value={difficulty} onChange={(e) => setDifficulty(e.target.value as Difficulty | "")}>
              <option value="">Adaptive difficulty</option>
              <option value="easy">Easy</option>
              <option value="medium">Medium</option>
              <option value="hard">Hard</option>
            </Select>
            <Select value={qtype} onChange={(e) => setQtype(e.target.value as QuestionType | "")}>
              <option value="">Any type</option>
              <option value="mcq">Multiple choice</option>
              <option value="numerical">Numerical</option>
              <option value="short_answer">Short answer</option>
            </Select>
            <PrimaryButton onClick={() => loadQuestion()} disabled={busy || !topic}>
              {question ? "Next question" : "Start"} <ArrowRight className="h-4 w-4" />
            </PrimaryButton>
          </div>
          {busy && !question && <Spinner label="Choosing a question for your current level…" />}
          {question && (
            <QuestionCard question={question} topicName={names[question.topic_id] || question.topic_id} onSubmit={submitPractice} result={result} submitting={busy} onOpenCitation={onOpenCitation} />
          )}
          {result && (
            <Panel className="flex items-center justify-between gap-3">
              <p className="text-xs text-slate-300">
                <b className="text-indigo-300">{ACTION_LABELS[result.next_recommendation.recommended_action]}:</b> {result.next_recommendation.rationale}
              </p>
              <PrimaryButton onClick={() => loadQuestion()} disabled={busy}>
                Next <ArrowRight className="h-4 w-4" />
              </PrimaryButton>
            </Panel>
          )}
        </div>
      )}

      {mode === "builder" && (
        <Panel className="space-y-5">
          <div>
            <p className="mb-2 text-xs font-bold uppercase tracking-wider text-slate-400">Scope (leave empty for all topics)</p>
            <div className="grid max-h-64 gap-1.5 overflow-y-auto sm:grid-cols-2">
              {withQuestions.map((t) => (
                <label key={t.topic_id} className="flex cursor-pointer items-center gap-2 rounded-lg border border-slate-800 px-3 py-2 text-xs text-slate-200 hover:border-slate-600">
                  <input type="checkbox" className="accent-indigo-500" checked={scope.includes(t.topic_id)} onChange={(e) => setScope((s) => (e.target.checked ? [...s, t.topic_id] : s.filter((x) => x !== t.topic_id)))} />
                  <span className="truncate">{t.name}</span>
                  {t.owner === "you" && <span className="ml-auto text-[10px] font-bold text-indigo-300">yours</span>}
                </label>
              ))}
            </div>
          </div>
          <div className="grid gap-4 sm:grid-cols-3">
            <label className="text-xs text-slate-300">
              Questions: <b>{count}</b>
              <input type="range" min={3} max={25} value={count} onChange={(e) => setCount(+e.target.value)} className="mt-2 w-full accent-indigo-500" />
            </label>
            <div className="text-xs text-slate-300">
              Types
              <div className="mt-2 flex flex-wrap gap-2">
                {(Object.keys(TYPE_LABEL) as QuestionType[]).map((ty) => (
                  <label key={ty} className="flex items-center gap-1">
                    <input type="checkbox" className="accent-indigo-500" checked={types.includes(ty)} onChange={(e) => setTypes((s) => (e.target.checked ? [...s, ty] : s.filter((x) => x !== ty)))} />
                    {TYPE_LABEL[ty]}
                  </label>
                ))}
              </div>
            </div>
            <div className="text-xs text-slate-300">
              Mode
              <div className="mt-2 flex gap-3">
                <label className="flex items-center gap-1">
                  <input type="radio" className="accent-indigo-500" checked={quizMode === "practice"} onChange={() => setQuizMode("practice")} /> Feedback after each
                </label>
                <label className="flex items-center gap-1">
                  <input type="radio" className="accent-indigo-500" checked={quizMode === "exam"} onChange={() => setQuizMode("exam")} /> Mock exam
                </label>
              </div>
            </div>
          </div>
          <p className="text-[11px] text-slate-500">Weaker topics get more questions. Questions you have already seen are used last.</p>
          <PrimaryButton onClick={createQuiz} disabled={busy || types.length === 0}>
            <Play className="h-4 w-4" /> {busy ? "Preparing…" : "Start"}
          </PrimaryButton>
        </Panel>
      )}

      {mode === "quiz" && quiz && current && (
        <div className="space-y-4">
          <div className="flex items-center justify-between text-xs text-slate-400">
            <span>
              {quiz.mode === "exam" ? "Mock exam" : quiz.mode === "diagnostic" ? "Placement check" : "Quiz"} · question {qi + 1} of {quiz.questions.length}
            </span>
            <span>{answeredCount} answered</span>
          </div>
          <div className="h-1.5 w-full overflow-hidden rounded-full bg-slate-800">
            <div className="h-full bg-indigo-500 transition-all" style={{ width: `${(answeredCount / quiz.questions.length) * 100}%` }} />
          </div>
          <QuestionCard
            question={current}
            topicName={names[current.topic_id] || current.topic_id}
            onSubmit={answerQuiz}
            result={currentResult && "evaluation" in currentResult ? (currentResult as AssessmentCycleResult) : null}
            submitting={busy}
            showFeedback={quiz.mode !== "exam"}
            onOpenCitation={onOpenCitation}
          />
          {quiz.mode === "exam" && currentResult && <p className="text-xs text-slate-400">Answer recorded. Feedback comes in the report.</p>}
          <div className="flex flex-wrap justify-between gap-2">
            <GhostButton onClick={() => setQi(Math.max(0, qi - 1))} disabled={qi === 0}>
              Previous
            </GhostButton>
            <div className="flex gap-2">
              {qi < quiz.questions.length - 1 && (
                <GhostButton onClick={() => setQi(qi + 1)}>{currentResult ? "Next" : "Skip"}</GhostButton>
              )}
              <PrimaryButton onClick={finishQuiz} disabled={busy || answeredCount === 0}>
                Finish & see report
              </PrimaryButton>
            </div>
          </div>
        </div>
      )}

      {mode === "report" && report && <Report report={report} onOpenCitation={onOpenCitation} onRestart={() => setMode("builder")} />}
    </div>
  );
};
