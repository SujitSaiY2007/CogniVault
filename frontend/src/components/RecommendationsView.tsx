"use client";

import React, { useState, useEffect } from "react";
import { CurriculumTopic, Recommendation } from "@/lib/types";
import { api } from "@/lib/api";
import {
  ArrowRight,
  BookOpen,
  CheckCircle2,
  Compass,
  GitBranch,
  Layers,
  Lock,
  RefreshCw,
  Sparkles,
  Unlock,
} from "lucide-react";

interface RecommendationsViewProps {
  activeLearner: string;
  onNavigateToPractice: (topicId: string) => void;
}

export const RecommendationsView: React.FC<RecommendationsViewProps> = ({
  activeLearner,
  onNavigateToPractice,
}) => {
  const [recommendation, setRecommendation] = useState<Recommendation | null>(null);
  const [topics, setTopics] = useState<CurriculumTopic[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const loadData = async () => {
    setLoading(true);
    setError(null);
    try {
      const [recData, topicList] = await Promise.all([
        api.getRecommendations(activeLearner),
        api.listTopics(),
      ]);
      setRecommendation(recData);
      setTopics(topicList);
    } catch (err: any) {
      setError(err.message || "Failed to load curriculum recommendations.");
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    loadData();
  }, [activeLearner]);

  const getActionBadge = (action: string) => {
    switch (action) {
      case "foundational_review":
        return { label: "Foundational Review", color: "bg-amber-500/10 text-amber-400 border-amber-500/30" };
      case "targeted_practice":
        return { label: "Targeted Practice", color: "bg-indigo-500/10 text-indigo-400 border-indigo-500/30" };
      case "mixed_application":
        return { label: "Mixed Application", color: "bg-cyan-500/10 text-cyan-400 border-cyan-500/30" };
      case "advance_topic":
        return { label: "Advance to Next Topic", color: "bg-emerald-500/10 text-emerald-400 border-emerald-500/30" };
      case "remediate_misconception":
        return { label: "Misconception Remediation", color: "bg-rose-500/10 text-rose-400 border-rose-500/30" };
      default:
        return { label: action, color: "bg-slate-800 text-slate-300 border-slate-700" };
    }
  };

  return (
    <div className="max-w-4xl mx-auto p-4 sm:p-6 space-y-6">
      {/* Top Header */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4 pb-4 border-b border-slate-800">
        <div>
          <h2 className="text-lg font-bold text-slate-100 flex items-center gap-2">
            <Compass className="h-5 w-5 text-indigo-400" />
            <span>Curriculum Roadmap & Recommendations</span>
          </h2>
          <p className="text-xs text-slate-400">
            Prerequisite gatekeeping (threshold ≥ 0.70) and BKT mastery policy brackets dictate next best learning actions.
          </p>
        </div>

        <button
          onClick={loadData}
          disabled={loading}
          className="flex items-center gap-1.5 self-start sm:self-auto rounded-xl border border-slate-700 bg-slate-900 px-3.5 py-2 text-xs font-semibold text-slate-300 hover:bg-slate-800 transition-colors"
        >
          <RefreshCw className={`h-3.5 w-3.5 ${loading ? "animate-spin" : ""}`} />
          <span>Refresh</span>
        </button>
      </div>

      {error && (
        <div className="rounded-xl border border-rose-500/30 bg-rose-500/10 p-4 text-xs text-rose-400">
          {error}
        </div>
      )}

      {/* Recommended Next Step Hero Card */}
      {recommendation && (
        <div className="rounded-2xl border border-indigo-500/30 bg-gradient-to-br from-slate-900 via-indigo-950/20 to-slate-900 p-6 sm:p-7 shadow-xl space-y-4">
          <div className="flex flex-wrap items-center justify-between gap-2">
            <div className="flex items-center gap-2">
              <span className="flex items-center gap-1.5 text-xs font-bold uppercase tracking-wider text-indigo-400">
                <Sparkles className="h-4 w-4" />
                <span>Next Pedagogical Recommendation</span>
              </span>
            </div>
            <span className={`px-3 py-1 rounded-xl border text-xs font-semibold ${getActionBadge(recommendation.recommended_action).color}`}>
              {getActionBadge(recommendation.recommended_action).label}
            </span>
          </div>

          <div>
            <h3 className="text-xl font-bold text-slate-100">
              Target Topic: {recommendation.topic_id}
            </h3>
            <p className="text-sm text-slate-300 mt-2 leading-relaxed">
              {recommendation.rationale}
            </p>
          </div>

          <div className="flex flex-wrap items-center justify-between gap-3 pt-4 border-t border-slate-800">
            <div className="flex items-center gap-3 text-xs text-slate-400">
              <span>Suggested Difficulty: <strong className="text-slate-200 capitalize">{recommendation.difficulty}</strong></span>
              <span>Evidence units to review: <strong className="text-slate-200">{recommendation.suggested_evidence_ids.length}</strong></span>
            </div>

            <button
              onClick={() => onNavigateToPractice(recommendation.topic_id)}
              className="flex items-center gap-2 px-5 py-2.5 rounded-xl bg-indigo-600 hover:bg-indigo-500 text-xs font-semibold text-white shadow-lg shadow-indigo-600/25 transition-all"
            >
              <span>Start Suggested Action</span>
              <ArrowRight className="h-4 w-4" />
            </button>
          </div>
        </div>
      )}

      {/* Prerequisite Topology Visualizer */}
      <div className="rounded-2xl border border-slate-800 bg-slate-900 p-6 shadow-xl space-y-4">
        <div className="flex items-center justify-between pb-3 border-b border-slate-800">
          <h3 className="text-sm font-bold uppercase tracking-wider text-slate-300 flex items-center gap-2">
            <GitBranch className="h-4 w-4 text-indigo-400" />
            <span>Curriculum Dependency & Prerequisite Map</span>
          </h3>
          <span className="text-xs text-slate-400">{topics.length} registered topics</span>
        </div>

        <div className="grid grid-cols-1 md:grid-cols-2 gap-3.5 pt-1">
          {topics.map((t) => {
            const hasPrereqs = t.prerequisites && t.prerequisites.length > 0;
            return (
              <div
                key={t.topic_id}
                className="rounded-xl border border-slate-800 bg-slate-950/70 p-4 space-y-2.5"
              >
                <div className="flex items-start justify-between gap-2">
                  <div>
                    <h4 className="text-sm font-semibold text-slate-100">{t.name}</h4>
                    <p className="text-xs text-slate-400 mt-0.5 line-clamp-1">{t.description}</p>
                  </div>
                  {hasPrereqs ? (
                    <span className="flex items-center gap-1 text-[11px] text-amber-400 bg-amber-500/10 px-2 py-0.5 rounded border border-amber-500/20">
                      <Lock className="h-3 w-3" />
                      <span>Has Prereqs</span>
                    </span>
                  ) : (
                    <span className="flex items-center gap-1 text-[11px] text-emerald-400 bg-emerald-500/10 px-2 py-0.5 rounded border border-emerald-500/20">
                      <Unlock className="h-3 w-3" />
                      <span>Foundational</span>
                    </span>
                  )}
                </div>

                {hasPrereqs && (
                  <div className="text-xs text-slate-400 pt-1 border-t border-slate-800/80">
                    <span className="text-[11px] text-slate-500 font-semibold uppercase block mb-1">
                      Required Prerequisites:
                    </span>
                    <div className="flex flex-wrap gap-1.5">
                      {t.prerequisites.map((p, pIdx) => (
                        <span
                          key={pIdx}
                          className="px-2 py-0.5 rounded bg-slate-800 text-slate-300 text-[11px] border border-slate-700"
                        >
                          {p}
                        </span>
                      ))}
                    </div>
                  </div>
                )}
              </div>
            );
          })}
        </div>
      </div>
    </div>
  );
};
