"use client";

import React, { useState, useEffect } from "react";
import { Citation, RemediationPackage } from "@/lib/types";
import { api } from "@/lib/api";
import {
  AlertTriangle,
  BookOpen,
  CheckCircle2,
  FileText,
  MapPin,
  RefreshCw,
  ShieldCheck,
  Sparkles,
} from "lucide-react";

interface MisconceptionsViewProps {
  activeLearner: string;
  onOpenCitation: (cit: Citation) => void;
}

export const MisconceptionsView: React.FC<MisconceptionsViewProps> = ({
  activeLearner,
  onOpenCitation,
}) => {
  const [misconceptions, setMisconceptions] = useState<RemediationPackage[]>([]);
  const [loading, setLoading] = useState(true);
  const [resolvingId, setResolvingId] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);

  const loadMisconceptions = async () => {
    setLoading(true);
    setError(null);
    try {
      const data = await api.getMisconceptions(activeLearner);
      setMisconceptions(data);
    } catch (err: any) {
      setError(err.message || "Failed to load misconceptions.");
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    loadMisconceptions();
  }, [activeLearner]);

  const handleResolve = async (pkg: RemediationPackage) => {
    const signalIdToResolve = pkg.signal_id || `misc_${activeLearner}_${pkg.concept_id || pkg.topic_id}`;
    setResolvingId(pkg.topic_id);
    try {
      await api.resolveMisconception(activeLearner, signalIdToResolve);
      await loadMisconceptions();
    } catch {
      await loadMisconceptions();
    } finally {
      setResolvingId(null);
    }
  };

  return (
    <div className="max-w-4xl mx-auto p-4 sm:p-6 space-y-6">
      {/* Top Header */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4 pb-4 border-b border-slate-800">
        <div>
          <h2 className="text-lg font-bold text-slate-100 flex items-center gap-2">
            <AlertTriangle className="h-5 w-5 text-amber-400" />
            <span>Misconception Diagnostics & Remediation</span>
          </h2>
          <p className="text-xs text-slate-400">
            D-016 Policy: Single slips are ignored; 2+ consecutive errors trigger targeted prerequisite remediation.
          </p>
        </div>

        <button
          onClick={loadMisconceptions}
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

      {/* Misconceptions List */}
      {misconceptions.length > 0 ? (
        <div className="space-y-5">
          {misconceptions.map((m, idx) => (
            <div
              key={idx}
              className="rounded-2xl border border-amber-500/30 bg-slate-900 p-6 shadow-xl space-y-4"
            >
              {/* Header Badges */}
              <div className="flex flex-wrap items-center justify-between gap-2 pb-3 border-b border-slate-800">
                <div className="flex items-center gap-2">
                  <span className="rounded-full bg-amber-500/10 px-2.5 py-1 text-xs font-semibold text-amber-400 border border-amber-500/20">
                    Topic: {m.topic_id}
                  </span>
                  {m.concept_id && (
                    <span className="rounded-full bg-indigo-500/10 px-2.5 py-1 text-xs font-semibold text-indigo-400 border border-indigo-500/20">
                      Concept: {m.concept_id}
                    </span>
                  )}
                </div>
                <span className="text-xs font-mono text-amber-300">
                  Confidence: {(m.confidence * 100).toFixed(0)}%
                </span>
              </div>

              {/* Diagnosis Description */}
              <div>
                <h3 className="text-base font-bold text-slate-100">
                  {m.suspected_misconception}
                </h3>
                <p className="text-xs text-slate-300 mt-1 leading-relaxed">
                  {m.remediation_note}
                </p>
              </div>

              {/* Remediation Evidence Cards */}
              {m.evidence_items && m.evidence_items.length > 0 && (
                <div className="pt-2 border-t border-slate-800 space-y-2">
                  <div className="text-[11px] font-semibold uppercase tracking-wider text-slate-400 flex items-center gap-1">
                    <BookOpen className="h-3 w-3 text-indigo-400" />
                    <span>Recommended Foundation Review Materials ({m.evidence_items.length}):</span>
                  </div>
                  <div className="grid grid-cols-1 sm:grid-cols-2 gap-2.5">
                    {m.evidence_items.map((ev, eIdx) => {
                      const loc = ev.location || {};
                      let locText = "Location";
                      if (loc.page !== undefined) locText = `Page ${loc.page}`;
                      else if (loc.slide !== undefined) locText = `Slide ${loc.slide}`;
                      else if (loc.timestamp !== undefined) locText = `Time ${loc.timestamp}`;

                      return (
                        <div
                          key={eIdx}
                          className="rounded-xl border border-slate-800 bg-slate-950 p-3 text-xs space-y-1.5"
                        >
                          <div className="flex items-center justify-between text-indigo-400 font-medium">
                            <span className="flex items-center gap-1">
                              <MapPin className="h-3 w-3" />
                              {locText}
                            </span>
                            <span className="uppercase text-[10px] text-slate-500 font-mono">
                              {ev.modality}
                            </span>
                          </div>
                          <p className="text-slate-300 line-clamp-2 italic font-serif">
                            "{ev.text}"
                          </p>
                        </div>
                      );
                    })}
                  </div>
                </div>
              )}

              {/* Actions */}
              <div className="flex justify-end pt-2 border-t border-slate-800">
                <button
                  onClick={() => handleResolve(m)}
                  disabled={resolvingId === m.topic_id}
                  className="flex items-center gap-1.5 px-4 py-2 rounded-xl bg-emerald-600 hover:bg-emerald-500 text-xs font-semibold text-white shadow-md shadow-emerald-600/20 transition-all disabled:opacity-50"
                >
                  <CheckCircle2 className="h-3.5 w-3.5" />
                  <span>Mark Remediated & Reset Signals</span>
                </button>
              </div>
            </div>
          ))}
        </div>
      ) : (
        /* Empty State */
        <div className="rounded-2xl border border-slate-800 bg-slate-900/60 p-12 text-center space-y-4">
          <div className="mx-auto flex h-14 w-14 items-center justify-center rounded-2xl bg-emerald-500/10 text-emerald-400 border border-emerald-500/20">
            <ShieldCheck className="h-7 w-7" />
          </div>
          <div>
            <h3 className="text-base font-bold text-slate-200">No Active Misconceptions Diagnosed</h3>
            <p className="text-xs text-slate-400 max-w-md mx-auto mt-1">
              Current responses demonstrate consistent understanding. If a student exhibits 2 or more consecutive errors on a concept, targeted remediation materials will appear here automatically.
            </p>
          </div>
        </div>
      )}
    </div>
  );
};
