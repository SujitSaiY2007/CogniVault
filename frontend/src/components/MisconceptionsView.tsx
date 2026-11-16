"use client";

import React, { useCallback, useEffect, useState } from "react";
import { AlertTriangle, CheckCircle2, MapPin } from "lucide-react";
import { api } from "@/lib/api";
import { Citation, RemediationPackage } from "@/lib/types";
import { EmptyState, ErrorBanner, GhostButton, Panel, PrimaryButton, SectionHeader, Spinner } from "./ui";

export const MisconceptionsView: React.FC<{
  learnerId: string;
  refreshKey: number;
  onPractice: (topicId: string) => void;
  onOpenCitation: (c: Citation) => void;
}> = ({ learnerId, refreshKey, onPractice, onOpenCitation }) => {
  const [items, setItems] = useState<RemediationPackage[] | null>(null);
  const [error, setError] = useState<string | null>(null);

  const load = useCallback(async () => {
    setError(null);
    try {
      setItems(await api.getMisconceptions(learnerId));
    } catch (e: any) {
      setError(e.message);
    }
  }, [learnerId]);

  useEffect(() => {
    load();
  }, [load, refreshKey]);

  async function resolve(id: string) {
    try {
      await api.resolveMisconception(learnerId, id);
      load();
    } catch (e: any) {
      setError(e.message);
    }
  }

  return (
    <div className="mx-auto max-w-5xl space-y-6 p-4 sm:p-6">
      <SectionHeader icon={AlertTriangle} title="Misconceptions" subtitle="Flagged only after two or more errors on the same concept. Two correct answers in a row clear them automatically." />
      {error && <ErrorBanner message={error} onRetry={load} />}
      {!items && !error && <Spinner />}
      {items && items.length === 0 && <EmptyState icon={CheckCircle2} title="No active misconceptions" body="Repeated errors on the same concept will show up here with the passages to re-read." />}
      {items?.map((m) => (
        <Panel key={m.signal_id} className="space-y-3 border-amber-200">
          <div className="flex flex-wrap items-start justify-between gap-2">
            <div>
              <p className="text-sm font-bold text-amber-800">{m.suspected_misconception}</p>
              <p className="text-xs text-slate-500">
                {m.topic_name} · {m.error_count} errors · confidence {Math.round(m.confidence * 100)}%
              </p>
            </div>
            <div className="flex gap-2">
              <PrimaryButton onClick={() => onPractice(m.remediation_concept_id || m.topic_id)} className="px-3 py-1.5 text-xs">
                Practise easy questions
              </PrimaryButton>
              <GhostButton onClick={() => resolve(m.signal_id)}>Mark resolved</GhostButton>
            </div>
          </div>
          <p className="text-xs text-slate-600">{m.remediation_note}</p>
          <div className="space-y-2">
            {m.evidence_items.map((e) => (
              <button
                key={e.evidence_id}
                onClick={() =>
                  onOpenCitation({ evidence_id: e.evidence_id, source_id: "", modality: e.modality as any, location: e.location, snippet: e.text, source_title: e.source_title, locator_label: e.locator_label })
                }
                className="block w-full rounded-xl border border-slate-200 bg-[#fbfaf7] p-3 text-left text-xs text-slate-600 hover:border-indigo-300"
              >
                <span className="mb-1 flex items-center gap-1 text-[11px] font-bold text-indigo-600">
                  <MapPin className="h-3 w-3" /> {e.source_title}, {e.locator_label}
                </span>
                {e.text.slice(0, 260)}
                {e.text.length > 260 ? "…" : ""}
              </button>
            ))}
          </div>
        </Panel>
      ))}
    </div>
  );
};
