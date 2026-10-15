"use client";

import React, { useState, useEffect } from "react";
import { LearnerProfile, TopicMasteryRecord } from "@/lib/types";
import { api } from "@/lib/api";
import {
  AlertTriangle,
  Award,
  BarChart3,
  CheckCircle2,
  Clock,
  History,
  Layers,
  RefreshCw,
  TrendingUp,
  User,
  XCircle,
} from "lucide-react";

interface LearnerProgressViewProps {
  activeLearner: string;
}

export const LearnerProgressView: React.FC<LearnerProgressViewProps> = ({ activeLearner }) => {
  const [profile, setProfile] = useState<LearnerProfile | null>(null);
  const [loading, setLoading] = useState<boolean>(true);
  const [error, setError] = useState<string | null>(null);

  const loadProfile = async () => {
    setLoading(true);
    setError(null);
    try {
      const data = await api.getLearnerProfile(activeLearner);
      setProfile(data);
    } catch (err: any) {
      setError(err.message || "Failed to load learner profile.");
      setProfile(null);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    loadProfile();
  }, [activeLearner]);

  const getPolicyBracket = (p: number) => {
    if (p < 0.4) {
      return {
        label: "Foundational Review",
        color: "bg-amber-500/10 text-amber-400 border-amber-500/30",
        barColor: "bg-amber-500",
      };
    }
    if (p < 0.7) {
      return {
        label: "Targeted Practice",
        color: "bg-indigo-500/10 text-indigo-400 border-indigo-500/30",
        barColor: "bg-indigo-500",
      };
    }
    if (p <= 0.85) {
      return {
        label: "Mixed Application",
        color: "bg-cyan-500/10 text-cyan-400 border-cyan-500/30",
        barColor: "bg-cyan-500",
      };
    }
    return {
      label: "Topic Mastered",
      color: "bg-emerald-500/10 text-emerald-400 border-emerald-500/30",
      barColor: "bg-emerald-500",
    };
  };

  const records = profile?.records || [];
  const accuracy =
    profile && profile.total_attempts > 0
      ? ((profile.total_correct / profile.total_attempts) * 100).toFixed(1)
      : "0.0";

  return (
    <div className="max-w-5xl mx-auto p-4 sm:p-6 space-y-6">
      {/* Top Header */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4 pb-4 border-b border-slate-800">
        <div>
          <h2 className="text-lg font-bold text-slate-100 flex items-center gap-2">
            <BarChart3 className="h-5 w-5 text-indigo-400" />
            <span>Bayesian Knowledge Tracing (BKT) Mastery</span>
          </h2>
          <p className="text-xs text-slate-400">
            Durable mathematical model tracking latent skill mastery P(L_t) updated after every verified observation.
          </p>
        </div>

        <button
          onClick={loadProfile}
          disabled={loading}
          className="flex items-center gap-2 self-start sm:self-auto rounded-xl border-2 border-slate-600 bg-slate-800 hover:border-indigo-400 px-4 py-2 text-xs font-bold text-slate-100 hover:text-white shadow-md transition-all cursor-pointer"
        >
          <RefreshCw className={`h-3.5 w-3.5 ${loading ? "animate-spin" : ""}`} />
          <span>Refresh Data</span>
        </button>
      </div>

      {error && (
        <div className="rounded-xl border border-rose-500/30 bg-rose-500/10 p-4 text-xs text-rose-400">
          {error}
        </div>
      )}

      {/* Summary KPI Tiles */}
      <div className="grid grid-cols-2 lg:grid-cols-4 gap-3.5">
        <div className="rounded-2xl border border-slate-800 bg-slate-900/80 p-4 shadow-sm">
          <div className="flex items-center gap-2 text-xs text-slate-400 mb-1.5">
            <User className="h-4 w-4 text-indigo-400" />
            <span>Active Learner</span>
          </div>
          <div className="text-base font-bold text-slate-100 font-mono truncate">
            {activeLearner}
          </div>
        </div>

        <div className="rounded-2xl border border-slate-800 bg-slate-900/80 p-4 shadow-sm">
          <div className="flex items-center gap-2 text-xs text-slate-400 mb-1.5">
            <Layers className="h-4 w-4 text-indigo-400" />
            <span>Total Attempts</span>
          </div>
          <div className="text-xl font-bold text-slate-100 font-mono">
            {profile?.total_attempts ?? 0}
          </div>
        </div>

        <div className="rounded-2xl border border-slate-800 bg-slate-900/80 p-4 shadow-sm">
          <div className="flex items-center gap-2 text-xs text-slate-400 mb-1.5">
            <Award className="h-4 w-4 text-emerald-400" />
            <span>Accuracy Rate</span>
          </div>
          <div className="text-xl font-bold text-emerald-400 font-mono">
            {accuracy}%
          </div>
        </div>

        <div className="rounded-2xl border border-slate-800 bg-slate-900/80 p-4 shadow-sm">
          <div className="flex items-center gap-2 text-xs text-slate-400 mb-1.5">
            <AlertTriangle className="h-4 w-4 text-amber-400" />
            <span>Active Misconceptions</span>
          </div>
          <div className="text-xl font-bold text-amber-400 font-mono">
            {profile?.active_misconceptions.length ?? 0}
          </div>
        </div>
      </div>

      {/* Latent Topic Mastery Cards */}
      <div className="rounded-2xl border border-slate-800 bg-slate-900 p-6 shadow-xl space-y-4">
        <div className="flex items-center justify-between pb-3 border-b border-slate-800">
          <h3 className="text-sm font-bold uppercase tracking-wider text-slate-300 flex items-center gap-2">
            <TrendingUp className="h-4 w-4 text-indigo-400" />
            <span>Latent Skill Mastery per Curriculum Topic</span>
          </h3>
          <span className="text-xs text-slate-400">{records.length} topics tracked</span>
        </div>

        {records.length > 0 ? (
          <div className="space-y-4 pt-1">
            {records.map((rec) => {
              const bracket = getPolicyBracket(rec.p_mastery);
              const pct = (rec.p_mastery * 100).toFixed(1);

              return (
                <div
                  key={rec.topic_id}
                  className="rounded-xl border border-slate-800/80 bg-slate-950/60 p-4 space-y-2.5"
                >
                  <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-2">
                    <div>
                      <h4 className="text-sm font-semibold text-slate-100">{rec.topic_id}</h4>
                      <div className="flex items-center gap-3 text-xs text-slate-400 mt-0.5">
                        <span>Attempts: <strong className="text-slate-300">{rec.attempts}</strong></span>
                        <span>Correct: <strong className="text-slate-300">{rec.correct}</strong></span>
                        {rec.last_seen && (
                          <span className="text-[11px] text-slate-500">
                            Last: {new Date(rec.last_seen).toLocaleDateString()}
                          </span>
                        )}
                      </div>
                    </div>

                    <div className="flex items-center gap-2.5">
                      <span className={`px-2.5 py-1 rounded-lg border text-xs font-semibold ${bracket.color}`}>
                        {bracket.label}
                      </span>
                      <span className="font-mono text-sm font-bold text-slate-100 w-16 text-right">
                        {pct}%
                      </span>
                    </div>
                  </div>

                  {/* Progress Bar */}
                  <div className="w-full bg-slate-800/80 h-2 rounded-full overflow-hidden">
                    <div
                      className={`h-full transition-all duration-500 rounded-full ${bracket.barColor}`}
                      style={{ width: `${Math.min(100, Math.max(2, rec.p_mastery * 100))}%` }}
                    />
                  </div>
                </div>
              );
            })}
          </div>
        ) : (
          <div className="text-center py-8 text-xs text-slate-500">
            No topic mastery records found for this learner yet. Complete an adaptive practice session or diagnostic intake to begin tracking!
          </div>
        )}
      </div>
    </div>
  );
};
