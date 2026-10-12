"use client";

import React, { useState } from "react";
import { CurriculumTopic } from "@/lib/types";
import { api } from "@/lib/api";
import { CheckCircle2, Sparkles, UserPlus, X, Zap } from "lucide-react";

interface ColdStartModalProps {
  isOpen: boolean;
  onClose: () => void;
  topics: CurriculumTopic[];
  onComplete: (learnerId: string) => void;
}

export const ColdStartModal: React.FC<ColdStartModalProps> = ({
  isOpen,
  onClose,
  topics,
  onComplete,
}) => {
  const [learnerId, setLearnerId] = useState("");
  const [masteryLevels, setMasteryLevels] = useState<Record<string, number>>({});
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  if (!isOpen) return null;

  const handleSliderChange = (topicId: string, value: number) => {
    setMasteryLevels((prev) => ({
      ...prev,
      [topicId]: value,
    }));
  };

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    const cleanId = learnerId.trim();
    if (!cleanId) {
      setError("Please enter a valid learner ID.");
      return;
    }

    setLoading(true);
    setError(null);

    try {
      // Build masteries map (defaults to 0.10 if untouched)
      const masteries: Record<string, number> = {};
      topics.forEach((t) => {
        masteries[t.topic_id] = masteryLevels[t.topic_id] ?? 0.10;
      });

      await api.coldStartIntake(cleanId, masteries, []);
      onComplete(cleanId);
      onClose();
    } catch (err: any) {
      setError(err.message || "Failed to complete intake.");
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/70 backdrop-blur-sm p-4 animate-in fade-in duration-150">
      <div className="relative w-full max-w-lg rounded-2xl border border-slate-700 bg-slate-900 shadow-2xl p-6 sm:p-7 max-h-[90vh] overflow-y-auto">
        <div className="flex items-start justify-between pb-4 border-b border-slate-800">
          <div className="flex items-center gap-2.5">
            <div className="flex h-10 w-10 items-center justify-center rounded-xl bg-gradient-to-tr from-indigo-600 to-cyan-400 text-white shadow-lg shadow-indigo-500/25">
              <UserPlus className="h-5 w-5" />
            </div>
            <div>
              <h3 className="text-lg font-bold text-slate-100">Learner Diagnostic Intake</h3>
              <p className="text-xs text-slate-400">Establish a personalized BKT baseline for a fresh student</p>
            </div>
          </div>
          <button
            onClick={onClose}
            className="rounded-lg p-1.5 text-slate-400 hover:bg-slate-800 hover:text-slate-100 transition-colors"
          >
            <X className="h-5 w-5" />
          </button>
        </div>

        {error && (
          <div className="mt-4 rounded-xl border border-rose-500/30 bg-rose-500/10 p-3 text-xs text-rose-400">
            {error}
          </div>
        )}

        <form onSubmit={handleSubmit} className="mt-5 space-y-5">
          <div>
            <label className="text-xs font-semibold uppercase tracking-wider text-slate-300 block mb-1.5">
              Learner Identifier
            </label>
            <input
              type="text"
              required
              placeholder="e.g. learner_sophia_2026"
              value={learnerId}
              onChange={(e) => setLearnerId(e.target.value)}
              className="w-full rounded-xl border border-slate-700 bg-slate-950 px-3.5 py-2.5 text-sm text-slate-100 placeholder:text-slate-500 focus:outline-none focus:border-indigo-500 focus:ring-1 focus:ring-indigo-500"
            />
          </div>

          <div>
            <div className="flex items-center justify-between mb-2">
              <label className="text-xs font-semibold uppercase tracking-wider text-slate-300">
                Prior Knowledge Baseline
              </label>
              <span className="text-[11px] text-slate-400">Default: 0.10 (Novice)</span>
            </div>
            <p className="text-xs text-slate-400 mb-3">
              Configure initial belief probability P(L₀) for each topic. Bayesian Knowledge Tracing will mathematically update latent mastery from this baseline.
            </p>

            <div className="space-y-3.5 max-h-56 overflow-y-auto pr-1">
              {topics.map((t) => {
                const currentVal = masteryLevels[t.topic_id] ?? 0.10;
                return (
                  <div
                    key={t.topic_id}
                    className="rounded-xl border border-slate-800 bg-slate-950/70 p-3"
                  >
                    <div className="flex items-center justify-between mb-1.5">
                      <span className="text-xs font-semibold text-slate-200">{t.name}</span>
                      <span className="font-mono text-xs font-bold text-indigo-400">
                        {(currentVal * 100).toFixed(0)}%
                      </span>
                    </div>
                    <input
                      type="range"
                      min="0.05"
                      max="0.80"
                      step="0.05"
                      value={currentVal}
                      onChange={(e) => handleSliderChange(t.topic_id, parseFloat(e.target.value))}
                      className="w-full accent-indigo-500 h-1.5 bg-slate-800 rounded-lg cursor-pointer"
                    />
                    <div className="flex justify-between text-[10px] text-slate-500 mt-1">
                      <span>Beginner (5%)</span>
                      <span>Intermediate (40%)</span>
                      <span>Advanced (80%)</span>
                    </div>
                  </div>
                );
              })}
            </div>
          </div>

          <div className="flex justify-end gap-2 pt-2 border-t border-slate-800">
            <button
              type="button"
              onClick={onClose}
              className="px-4 py-2 text-xs font-medium text-slate-300 hover:bg-slate-800 rounded-xl transition-colors"
            >
              Cancel
            </button>
            <button
              type="submit"
              disabled={loading}
              className="flex items-center gap-2 px-5 py-2.5 rounded-xl bg-gradient-to-r from-indigo-600 to-indigo-500 hover:from-indigo-500 hover:to-indigo-400 text-xs font-semibold text-white shadow-lg shadow-indigo-500/25 transition-all disabled:opacity-50"
            >
              {loading ? (
                <span>Initializing Profile...</span>
              ) : (
                <>
                  <Zap className="h-4 w-4" />
                  <span>Initialize Learner Profile</span>
                </>
              )}
            </button>
          </div>
        </form>
      </div>
    </div>
  );
};
