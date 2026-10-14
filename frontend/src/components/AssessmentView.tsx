"use client";

import React, { useState, useEffect } from "react";
import { Citation, CurriculumTopic, Difficulty, Question, QuestionType, AssessmentCycleResult } from "@/lib/types";
import { api } from "@/lib/api";
import {
  AlertTriangle,
  ArrowRight,
  CheckCircle2,
  CheckSquare,
  ChevronRight,
  Clock,
  HelpCircle,
  MapPin,
  RefreshCw,
  Send,
  ShieldCheck,
  TrendingUp,
  XCircle,
} from "lucide-react";

interface AssessmentViewProps {
  activeLearner: string;
  topics: CurriculumTopic[];
  initialTopic?: string;
  onOpenCitation: (cit: Citation) => void;
  onAssessmentCompleted?: () => void;
}

export const AssessmentView: React.FC<AssessmentViewProps> = ({
  activeLearner,
  topics,
  initialTopic,
  onOpenCitation,
  onAssessmentCompleted,
}) => {
  const [selectedTopic, setSelectedTopic] = useState<string>(initialTopic || "");
  const [selectedDifficulty, setSelectedDifficulty] = useState<Difficulty | undefined>(undefined);
  const [currentQuestion, setCurrentQuestion] = useState<Question | null>(null);
  const [servedIds, setServedIds] = useState<string[]>([]);
  const [userAnswer, setUserAnswer] = useState<string>("");
  const [loadingQuestion, setLoadingQuestion] = useState<boolean>(false);
  const [submitting, setSubmitting] = useState<boolean>(false);
  const [result, setResult] = useState<AssessmentCycleResult | null>(null);
  const [error, setError] = useState<string | null>(null);

  const fetchNextQuestion = async (topicOverride?: string, difficultyOverride?: Difficulty) => {
    const topicToUse = topicOverride || selectedTopic || (topics.length > 0 ? topics[0].topic_id : "");
    if (!topicToUse) {
      setError("Please select a curriculum topic above to start adaptive practice.");
      return;
    }
    if (selectedTopic !== topicToUse) {
      setSelectedTopic(topicToUse);
    }
    setLoadingQuestion(true);
    setError(null);
    setResult(null);
    setUserAnswer("");

    try {
      const q = await api.selectAdaptiveQuestion(
        topicToUse,
        servedIds,
        difficultyOverride !== undefined ? difficultyOverride : selectedDifficulty
      );
      setCurrentQuestion(q);
      setServedIds((prev) => [...prev, q.question_id]);
    } catch (err: any) {
      setError(err.message || "No verified questions available for the selected topic and difficulty.");
      setCurrentQuestion(null);
    } finally {
      setLoadingQuestion(false);
    }
  };

  // Sync initial or default topic and auto-load first question
  useEffect(() => {
    if (initialTopic && initialTopic !== selectedTopic) {
      setSelectedTopic(initialTopic);
      fetchNextQuestion(initialTopic);
      return;
    }
    if (topics.length > 0) {
      const topicToUse = selectedTopic || topics[0].topic_id;
      if (!selectedTopic) {
        setSelectedTopic(topicToUse);
      }
      if (!currentQuestion && !loadingQuestion && !error) {
        fetchNextQuestion(topicToUse);
      }
    }
  }, [topics, initialTopic]);

  const handleTopicChange = (newTopic: string) => {
    setSelectedTopic(newTopic);
    fetchNextQuestion(newTopic);
  };

  const handleDifficultyChange = (diff?: Difficulty) => {
    setSelectedDifficulty(diff);
    fetchNextQuestion(selectedTopic, diff);
  };

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!currentQuestion || !userAnswer.trim() || submitting) return;

    setSubmitting(true);
    setError(null);

    try {
      const cycleResult = await api.submitAssessment(
        activeLearner,
        currentQuestion.question_id,
        userAnswer.trim()
      );
      setResult(cycleResult);
      if (onAssessmentCompleted) {
        onAssessmentCompleted();
      }
    } catch (err: any) {
      setError(err.message || "Failed to submit assessment.");
    } finally {
      setSubmitting(false);
    }
  };

  return (
    <div className="max-w-4xl mx-auto p-4 sm:p-6 space-y-6">
      {/* Top Controls Header */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4 pb-4 border-b border-slate-800">
        <div>
          <h2 className="text-lg font-bold text-slate-100 flex items-center gap-2">
            <CheckSquare className="h-5 w-5 text-indigo-400" />
            <span>Adaptive Assessment Practice</span>
          </h2>
          <p className="text-xs text-slate-400">
            Topic-targeted questions verified against course evidence with BKT tracking and repetition suppression.
          </p>
        </div>

        {/* Filter Controls */}
        <div className="flex flex-wrap items-center gap-2">
          {/* Topic Select */}
          <select
            value={selectedTopic}
            onChange={(e) => handleTopicChange(e.target.value)}
            className="rounded-xl border border-slate-700 bg-slate-900 px-3 py-2 text-xs text-slate-200 focus:outline-none focus:border-indigo-500"
          >
            {topics.length === 0 && <option value="">Loading topics...</option>}
            {topics.map((t) => (
              <option key={t.topic_id} value={t.topic_id}>
                {t.name}
              </option>
            ))}
          </select>

          {/* Difficulty Select */}
          <select
            value={selectedDifficulty || ""}
            onChange={(e) => handleDifficultyChange((e.target.value as Difficulty) || undefined)}
            className="rounded-xl border border-slate-700 bg-slate-900 px-3 py-2 text-xs text-slate-200 focus:outline-none focus:border-indigo-500"
          >
            <option value="">Any Difficulty</option>
            <option value="easy">Easy</option>
            <option value="medium">Medium</option>
            <option value="hard">Hard</option>
          </select>

          <button
            onClick={() => fetchNextQuestion()}
            disabled={loadingQuestion}
            className="flex items-center gap-1.5 rounded-xl bg-indigo-600 hover:bg-indigo-500 px-3.5 py-2 text-xs font-semibold text-white shadow-md shadow-indigo-600/25 transition-all disabled:opacity-50"
          >
            <RefreshCw className={`h-3.5 w-3.5 ${loadingQuestion ? "animate-spin" : ""}`} />
            <span>{currentQuestion ? "New Question" : "Start Practice"}</span>
          </button>
        </div>
      </div>

      {/* Repetition Suppression Info Banner */}
      {servedIds.length > 0 && (
        <div className="flex items-center justify-between px-4 py-2.5 rounded-xl border border-slate-800 bg-slate-950/60 text-xs text-slate-400">
          <span>
            Practice Session: <strong className="text-slate-200">{servedIds.length}</strong> unique questions served
          </span>
          <span className="font-mono text-[11px] text-indigo-400">Fingerprint tracking active</span>
        </div>
      )}

      {/* Error Banner */}
      {error && (
        <div className="rounded-xl border border-rose-500/30 bg-rose-500/10 p-4 text-xs text-rose-400 flex items-start gap-2.5">
          <AlertTriangle className="h-4 w-4 shrink-0 text-rose-400 mt-0.5" />
          <div>
            <p className="font-semibold">Assessment Notice</p>
            <p className="mt-0.5 text-rose-300/90">{error}</p>
          </div>
        </div>
      )}

      {/* Question Card */}
      {currentQuestion ? (
        <div className="rounded-2xl border border-slate-800 bg-slate-900 p-6 sm:p-7 shadow-xl space-y-6">
          {/* Question Badges */}
          <div className="flex flex-wrap items-center justify-between gap-2 pb-4 border-b border-slate-800">
            <div className="flex items-center gap-2">
              <span className="rounded-full bg-indigo-500/10 px-2.5 py-1 text-xs font-semibold text-indigo-400 border border-indigo-500/20">
                {currentQuestion.topic_id}
              </span>
              <span className="uppercase text-[10px] font-bold px-2 py-0.5 rounded bg-slate-800 text-slate-300 border border-slate-700">
                {currentQuestion.difficulty}
              </span>
              <span className="uppercase text-[10px] font-bold px-2 py-0.5 rounded bg-slate-800 text-slate-400 border border-slate-700">
                {currentQuestion.question_type}
              </span>
            </div>

            <div className="flex items-center gap-1.5 text-xs text-emerald-400 font-mono">
              <ShieldCheck className="h-4 w-4" />
              <span>Verified Key</span>
            </div>
          </div>

          {/* Prompt */}
          <div>
            <h3 className="text-base sm:text-lg font-semibold text-slate-100 leading-snug">
              {currentQuestion.prompt}
            </h3>
          </div>

          {/* Submission Form */}
          <form onSubmit={handleSubmit} className="space-y-5">
            {/* MCQ Options */}
            {currentQuestion.question_type === "mcq" && (
              <div className="space-y-2.5">
                {currentQuestion.options.map((opt) => {
                  const isSelected = userAnswer === opt.key;
                  return (
                    <button
                      type="button"
                      key={opt.key}
                      onClick={() => !result && setUserAnswer(opt.key)}
                      disabled={!!result}
                      className={`w-full text-left flex items-center gap-3.5 p-3.5 sm:p-4 rounded-xl border text-sm transition-all ${
                        isSelected
                          ? "border-indigo-500 bg-indigo-500/10 text-white shadow-sm shadow-indigo-500/20"
                          : "border-slate-800 bg-slate-950/70 text-slate-300 hover:border-slate-700 hover:bg-slate-950"
                      } ${result ? "cursor-default opacity-85" : "cursor-pointer"}`}
                    >
                      <span
                        className={`flex h-7 w-7 shrink-0 items-center justify-center rounded-lg font-bold text-xs ${
                          isSelected
                            ? "bg-indigo-600 text-white"
                            : "bg-slate-800 text-slate-400"
                        }`}
                      >
                        {opt.key}
                      </span>
                      <span className="flex-1">{opt.text}</span>
                    </button>
                  );
                })}
              </div>
            )}

            {/* Numerical Input */}
            {currentQuestion.question_type === "numerical" && (
              <div>
                <label className="text-xs font-semibold text-slate-400 block mb-1.5">
                  Enter your numerical answer:
                </label>
                <input
                  type="text"
                  disabled={!!result}
                  placeholder="e.g. 18.0"
                  value={userAnswer}
                  onChange={(e) => setUserAnswer(e.target.value)}
                  className="w-full rounded-xl border border-slate-700 bg-slate-950 px-4 py-3 text-sm text-slate-100 focus:outline-none focus:border-indigo-500 font-mono"
                />
                {currentQuestion.tolerance !== undefined && currentQuestion.tolerance !== null && (
                  <p className="text-[11px] text-slate-500 mt-1">
                    Tolerance: ±{currentQuestion.tolerance}
                  </p>
                )}
              </div>
            )}

            {/* Short Answer Input */}
            {currentQuestion.question_type === "short_answer" && (
              <div>
                <label className="text-xs font-semibold text-slate-400 block mb-1.5">
                  Type your explanation or summary:
                </label>
                <textarea
                  rows={3}
                  disabled={!!result}
                  placeholder="Explain based on course concepts..."
                  value={userAnswer}
                  onChange={(e) => setUserAnswer(e.target.value)}
                  className="w-full rounded-xl border border-slate-700 bg-slate-950 p-3.5 text-sm text-slate-100 focus:outline-none focus:border-indigo-500"
                />
              </div>
            )}

            {/* Submit / Next Buttons */}
            {!result ? (
              <div className="flex justify-end pt-2">
                <button
                  type="submit"
                  disabled={submitting || !userAnswer.trim()}
                  className="flex items-center gap-2 rounded-xl bg-gradient-to-r from-indigo-600 to-indigo-500 hover:from-indigo-500 hover:to-indigo-400 px-6 py-2.5 text-sm font-semibold text-white shadow-lg shadow-indigo-500/25 transition-all disabled:opacity-40"
                >
                  <Send className="h-4 w-4" />
                  <span>{submitting ? "Scoring Answer..." : "Submit Answer"}</span>
                </button>
              </div>
            ) : null}
          </form>

          {/* Instant Verified Feedback & Citations */}
          {result && (
            <div
              className={`rounded-xl border p-5 space-y-4 animate-in fade-in duration-200 ${
                result.evaluation.is_correct
                  ? "border-emerald-500/30 bg-emerald-950/20"
                  : "border-rose-500/30 bg-rose-950/20"
              }`}
            >
              <div className="flex items-center justify-between">
                <div className="flex items-center gap-2">
                  {result.evaluation.is_correct ? (
                    <CheckCircle2 className="h-5 w-5 text-emerald-400" />
                  ) : (
                    <XCircle className="h-5 w-5 text-rose-400" />
                  )}
                  <span
                    className={`font-bold text-sm ${
                      result.evaluation.is_correct ? "text-emerald-300" : "text-rose-300"
                    }`}
                  >
                    {result.evaluation.is_correct ? "Correct! Verified." : "Incorrect Answer"}
                  </span>
                </div>

                {/* BKT Mastery update delta */}
                <div className="flex items-center gap-1.5 text-xs text-indigo-300 font-mono bg-indigo-500/10 px-2.5 py-1 rounded-lg border border-indigo-500/20">
                  <TrendingUp className="h-3.5 w-3.5" />
                  <span>BKT Mastery P(L_t): {(result.mastery.p_mastery * 100).toFixed(1)}%</span>
                </div>
              </div>

              {/* Feedback text */}
              <p className="text-sm text-slate-200 leading-relaxed whitespace-pre-wrap">
                {result.evaluation.feedback}
              </p>

              {/* Misconception Diagnostic Warning */}
              {result.misconception_detected && result.misconception && (
                <div className="rounded-xl border border-amber-500/30 bg-amber-500/10 p-3.5 text-xs text-amber-300 space-y-1">
                  <div className="flex items-center gap-2 font-semibold">
                    <AlertTriangle className="h-4 w-4 text-amber-400" />
                    <span>Misconception Signal Diagnosed (≥ 2 repeated errors)</span>
                  </div>
                  <p className="text-amber-200/90 pl-6">
                    {result.misconception.suspected_misconception}
                  </p>
                  <p className="text-amber-400/90 pl-6 font-medium">
                    {result.misconception.remediation_note}
                  </p>
                </div>
              )}

              {/* Evidence Citations */}
              {result.evaluation.citations && result.evaluation.citations.length > 0 && (
                <div className="pt-2 border-t border-slate-800 space-y-2">
                  <span className="text-[11px] font-semibold uppercase tracking-wider text-slate-400">
                    Source Evidence Verification:
                  </span>
                  <div className="flex flex-wrap gap-2">
                    {result.evaluation.citations.map((c, idx) => (
                      <button
                        key={idx}
                        onClick={() => onOpenCitation(c)}
                        className="flex items-center gap-1.5 px-2.5 py-1 rounded-lg bg-indigo-500/10 hover:bg-indigo-500/20 text-indigo-300 border border-indigo-500/30 text-xs font-medium transition-colors"
                      >
                        <MapPin className="h-3 w-3 text-indigo-400" />
                        <span>{c.source_title || c.source_id} (Page/Slide/Time)</span>
                      </button>
                    ))}
                  </div>
                </div>
              )}

              {/* Action Button: Next Question */}
              <div className="flex justify-end pt-2">
                <button
                  onClick={() => fetchNextQuestion()}
                  className="flex items-center gap-2 rounded-xl bg-indigo-600 hover:bg-indigo-500 px-5 py-2.5 text-xs font-semibold text-white shadow-md shadow-indigo-600/25 transition-all"
                >
                  <span>Next Adaptive Question</span>
                  <ArrowRight className="h-4 w-4" />
                </button>
              </div>
            </div>
          )}
        </div>
      ) : (
        /* Empty State */
        <div className="rounded-2xl border border-slate-800 bg-slate-900/60 p-12 text-center space-y-4">
          <div className="mx-auto flex h-14 w-14 items-center justify-center rounded-2xl bg-indigo-500/10 text-indigo-400 border border-indigo-500/20">
            <CheckSquare className="h-7 w-7" />
          </div>
          <div>
            <h3 className="text-base font-bold text-slate-200">No Active Assessment Question</h3>
            <p className="text-xs text-slate-400 max-w-sm mx-auto mt-1">
              Select a curriculum topic above and start adaptive practice to test your knowledge against verified course material.
            </p>
          </div>
          <button
            onClick={() => fetchNextQuestion()}
            className="inline-flex items-center gap-2 rounded-xl bg-indigo-600 hover:bg-indigo-500 px-5 py-2.5 text-xs font-semibold text-white shadow-lg shadow-indigo-600/25 transition-all"
          >
            <span>Start Adaptive Practice</span>
            <ChevronRight className="h-4 w-4" />
          </button>
        </div>
      )}
    </div>
  );
};
