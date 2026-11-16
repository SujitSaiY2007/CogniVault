"use client";

import React, { useCallback, useEffect, useState } from "react";
import { BarChart3, TrendingUp } from "lucide-react";
import { api } from "@/lib/api";
import { LearnerProfile } from "@/lib/types";
import { EmptyState, ErrorBanner, GhostButton, MasteryBar, Panel, SectionHeader, Spinner } from "./ui";

export const LearnerProgressView: React.FC<{ learnerId: string; refreshKey: number; onPractice: (topicId: string) => void }> = ({ learnerId, refreshKey, onPractice }) => {
  const [profile, setProfile] = useState<LearnerProfile | null>(null);
  const [error, setError] = useState<string | null>(null);

  const load = useCallback(async () => {
    setError(null);
    try {
      setProfile(await api.getProfile(learnerId));
    } catch (e: any) {
      setError(e.message);
    }
  }, [learnerId]);

  useEffect(() => {
    load();
  }, [load, refreshKey]);

  if (error) return <div className="mx-auto max-w-5xl p-6"><ErrorBanner message={error} onRetry={load} /></div>;
  if (!profile) return <div className="mx-auto max-w-5xl p-6"><Spinner label="Loading your progress…" /></div>;

  const acc = profile.total_attempts ? Math.round((100 * profile.total_correct) / profile.total_attempts) : 0;
  const records = [...profile.records].sort((a, b) => a.p_mastery - b.p_mastery);
  const hist = profile.history;

  return (
    <div className="mx-auto max-w-5xl space-y-6 p-4 sm:p-6">
      <SectionHeader icon={BarChart3} title="Progress" subtitle="Mastery is the probability you know a topic, estimated with Bayesian Knowledge Tracing and decayed over time you spend away from it." />
      <div className="grid gap-4 sm:grid-cols-3">
        {[
          ["Answers", profile.total_attempts],
          ["Accuracy", `${acc}%`],
          ["Topics practised", records.length],
        ].map(([k, v]) => (
          <Panel key={k as string}>
            <p className="text-xs font-bold uppercase tracking-wider text-slate-500">{k}</p>
            <p className="mt-1 text-2xl font-black text-slate-900">{v}</p>
          </Panel>
        ))}
      </div>

      {records.length === 0 ? (
        <EmptyState icon={TrendingUp} title="No practice yet" body="Answer a few questions in Practice & Exams. Your mastery per topic will appear here." />
      ) : (
        <Panel className="space-y-4">
          <h3 className="text-sm font-bold text-slate-900">Topic mastery (weakest first)</h3>
          {records.map((r) => (
            <div key={r.topic_id} className="space-y-1.5">
              <div className="flex items-center justify-between gap-2 text-xs">
                <span className="font-semibold text-slate-800">{r.topic_name || r.topic_id}</span>
                <span className="flex items-center gap-3 font-mono text-slate-500">
                  {r.correct}/{r.attempts} correct
                  {r.p_mastery_stored !== undefined && r.p_mastery_stored - r.p_mastery > 0.02 && (
                    <span className="text-amber-700" title="Estimated forgetting since your last practice">
                      faded from {Math.round(r.p_mastery_stored * 100)}%
                    </span>
                  )}
                  <b className="text-slate-900">{Math.round(r.p_mastery * 100)}%</b>
                  <GhostButton onClick={() => onPractice(r.topic_id)} className="px-2 py-1">
                    Practise
                  </GhostButton>
                </span>
              </div>
              <MasteryBar p={r.p_mastery} />
              {r.misconception_signals.length > 0 && <p className="text-[11px] text-amber-700">⚠ {r.misconception_signals.join("; ")}</p>}
            </div>
          ))}
        </Panel>
      )}

      {hist.length > 1 && (
        <Panel>
          <h3 className="mb-3 text-sm font-bold text-slate-900">Recent answers</h3>
          <div className="flex flex-wrap gap-1">
            {hist.map((h, i) => (
              <span
                key={i}
                title={`${h.topic_name}: ${h.is_correct ? "correct" : "wrong"} → ${Math.round((h.p_after ?? 0) * 100)}%`}
                className={`h-4 w-4 rounded ${h.is_correct ? "bg-emerald-500/80" : "bg-rose-500/80"}`}
              />
            ))}
          </div>
        </Panel>
      )}
    </div>
  );
};
