"use client";

import React, { useState } from "react";
import { GraduationCap, X } from "lucide-react";
import { api } from "@/lib/api";
import { CurriculumTopic, QuizSession } from "@/lib/types";
import { ErrorBanner, GhostButton, PrimaryButton } from "./ui";

const LEVELS = ["New to me", "Heard of it", "Comfortable", "Confident"];

export const ColdStartModal: React.FC<{
  isOpen: boolean;
  onClose: () => void;
  learnerId: string;
  topics: CurriculumTopic[];
  onComplete: (quiz: QuizSession | null) => void;
}> = ({ isOpen, onClose, learnerId, topics, onComplete }) => {
  const [ratings, setRatings] = useState<Record<string, number>>({});
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);
  if (!isOpen) return null;

  const shown = (topics.some((t) => t.owner === "you") ? topics.filter((t) => t.owner === "you") : topics).slice(0, 14);

  async function finish(withQuiz: boolean) {
    setBusy(true);
    setError(null);
    try {
      const scaled = Object.fromEntries(Object.entries(ratings).map(([k, v]) => [k, v / 3]));
      await api.intake(learnerId, scaled);
      const quiz = withQuiz ? await api.diagnostic() : null;
      onComplete(quiz);
    } catch (e: any) {
      setError(e.message);
    } finally {
      setBusy(false);
    }
  }

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/60 p-4 backdrop-blur-sm">
      <div className="max-h-[90vh] w-full max-w-2xl overflow-y-auto rounded-2xl border border-slate-700 bg-slate-900 p-6">
        <div className="mb-4 flex items-start justify-between">
          <div className="flex items-center gap-2.5">
            <div className="flex h-9 w-9 items-center justify-center rounded-xl border border-indigo-500/20 bg-indigo-500/10 text-indigo-400">
              <GraduationCap className="h-4 w-4" />
            </div>
            <div>
              <h3 className="text-base font-bold text-slate-100">Placement check</h3>
              <p className="text-xs text-slate-400">Tell us roughly what you know, then take a short quiz (one easy question per topic). Self-ratings count as weak evidence; your answers matter more.</p>
            </div>
          </div>
          <button onClick={onClose} className="rounded-lg p-1.5 text-slate-400 hover:bg-slate-800">
            <X className="h-5 w-5" />
          </button>
        </div>
        {error && <ErrorBanner message={error} />}
        <div className="mt-3 space-y-3">
          {shown.map((t) => (
            <div key={t.topic_id} className="rounded-xl border border-slate-800 bg-slate-950 p-3">
              <p className="text-xs font-semibold text-slate-200">{t.name}</p>
              <div className="mt-2 grid grid-cols-4 gap-1.5">
                {LEVELS.map((label, i) => (
                  <button
                    key={label}
                    onClick={() => setRatings((r) => ({ ...r, [t.topic_id]: i }))}
                    className={`rounded-lg border px-2 py-1.5 text-[11px] font-semibold ${ratings[t.topic_id] === i ? "border-indigo-400 bg-indigo-500/20 text-white" : "border-slate-700 text-slate-400 hover:border-slate-500"}`}
                  >
                    {label}
                  </button>
                ))}
              </div>
            </div>
          ))}
        </div>
        <div className="mt-5 flex flex-wrap justify-end gap-2">
          <GhostButton onClick={() => finish(false)} disabled={busy}>
            Save ratings only
          </GhostButton>
          <PrimaryButton onClick={() => finish(true)} disabled={busy}>
            {busy ? "Preparing…" : "Save and start placement quiz"}
          </PrimaryButton>
        </div>
      </div>
    </div>
  );
};
