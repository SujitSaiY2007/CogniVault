"use client";

import React, { useCallback, useEffect, useRef, useState } from "react";
import { BookOpen, CheckCircle2, Eye, FileUp, Image as ImageIcon, Trash2, Upload, X } from "lucide-react";
import { api } from "@/lib/api";
import { EvidenceUnit, SourceRecord, UploadResult } from "@/lib/types";
import { EmptyState, ErrorBanner, GhostButton, Panel, SectionHeader, Spinner } from "./ui";

const ACCEPT = ".pdf,.pptx,.srt,.vtt,.txt,.md";

const badge = (m: string) =>
  ({
    pdf: "bg-rose-500/10 text-rose-300 border-rose-500/30",
    pptx: "bg-amber-500/10 text-amber-300 border-amber-500/30",
    video: "bg-sky-500/10 text-sky-300 border-sky-500/30",
    text: "bg-slate-800 text-slate-300 border-slate-700",
  }[m] || "bg-slate-800 text-slate-300 border-slate-700");

const modalityName = (m: string) => ({ pdf: "PDF", pptx: "Slides", video: "Transcript", text: "Notes" }[m] || m);

function locLabel(u: EvidenceUnit) {
  const l = u.location;
  if (l.page !== undefined) return `Page ${l.page}`;
  if (l.slide !== undefined) return `Slide ${l.slide}${l.part === "notes" ? " notes" : ""}`;
  if (l.timestamp !== undefined) return String(l.timestamp);
  return String(l.section ?? "");
}

export const IngestionView: React.FC<{ onCurriculumUpdated?: () => void }> = ({ onCurriculumUpdated }) => {
  const [sources, setSources] = useState<SourceRecord[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [queue, setQueue] = useState<{ name: string; state: "uploading" | "done" | "error"; result?: UploadResult; error?: string }[]>([]);
  const [viewing, setViewing] = useState<SourceRecord | null>(null);
  const [units, setUnits] = useState<EvidenceUnit[]>([]);
  const [dragOver, setDragOver] = useState(false);
  const fileRef = useRef<HTMLInputElement>(null);

  const load = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      setSources(await api.listSources());
    } catch (e: any) {
      setError(e.message);
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    load();
  }, [load]);

  async function upload(files: FileList | File[]) {
    for (const file of Array.from(files)) {
      setQueue((q) => [{ name: file.name, state: "uploading" }, ...q]);
      try {
        const result = await api.uploadMaterial(file);
        setQueue((q) => q.map((x) => (x.name === file.name && x.state === "uploading" ? { ...x, state: "done", result } : x)));
        onCurriculumUpdated?.();
      } catch (e: any) {
        setQueue((q) => q.map((x) => (x.name === file.name && x.state === "uploading" ? { ...x, state: "error", error: e.message } : x)));
      }
    }
    load();
  }

  async function remove(s: SourceRecord) {
    if (!window.confirm(`Delete "${s.title}"? Its topics, questions and stored file will be removed. Your past answers stay in your history.`)) return;
    try {
      await api.deleteSource(s.source_id);
      await load();
      onCurriculumUpdated?.();
    } catch (e: any) {
      setError(e.message);
    }
  }

  async function view(s: SourceRecord) {
    setViewing(s);
    setUnits([]);
    try {
      setUnits(await api.getSourceEvidence(s.source_id));
    } catch (e: any) {
      setError(e.message);
    }
  }

  const mine = sources.filter((s) => s.owner === "you");
  const demo = sources.filter((s) => s.owner !== "you");

  const Row = ({ s }: { s: SourceRecord }) => (
    <tr className="transition-colors hover:bg-slate-800/40">
      <td className="px-4 py-3">
        <div className="font-semibold text-slate-200">{s.title}</div>
        <div className="mt-0.5 text-[11px] text-slate-500">{(s.topics || []).map((t) => t.name).join(" · ") || "—"}</div>
      </td>
      <td className="px-4 py-3">
        <span className={`rounded border px-2 py-0.5 text-[10px] font-bold uppercase ${badge(s.modality)}`}>{modalityName(s.modality)}</span>
      </td>
      <td className="px-4 py-3 font-mono text-slate-300">{s.evidence_count}</td>
      <td className="px-4 py-3 text-right">
        <div className="flex justify-end gap-2">
          <GhostButton onClick={() => view(s)}>
            <Eye className="h-3.5 w-3.5" /> Passages
          </GhostButton>
          {s.owner === "you" && (
            <GhostButton onClick={() => remove(s)} className="hover:border-rose-400">
              <Trash2 className="h-3.5 w-3.5" />
            </GhostButton>
          )}
        </div>
      </td>
    </tr>
  );

  return (
    <div className="mx-auto max-w-5xl space-y-6 p-4 sm:p-6">
      <SectionHeader icon={BookOpen} title="Course Materials" subtitle="Upload PDFs, PowerPoint decks, lecture transcripts (.srt/.vtt) or notes (.txt/.md). Each is split into cited passages, topics and practice questions." />
      {error && <ErrorBanner message={error} onRetry={load} />}

      <div
        onDragOver={(e) => {
          e.preventDefault();
          setDragOver(true);
        }}
        onDragLeave={() => setDragOver(false)}
        onDrop={(e) => {
          e.preventDefault();
          setDragOver(false);
          if (e.dataTransfer.files.length) upload(e.dataTransfer.files);
        }}
        onClick={() => fileRef.current?.click()}
        className={`flex cursor-pointer flex-col items-center justify-center rounded-2xl border-2 border-dashed p-8 text-center transition-colors ${
          dragOver ? "border-indigo-400 bg-indigo-500/10" : "border-slate-700 hover:border-slate-500"
        }`}
      >
        <FileUp className="h-8 w-8 text-indigo-400" />
        <p className="mt-2 text-sm font-bold text-slate-200">Drop files here or click to upload</p>
        <p className="mt-1 text-xs text-slate-500">PDF · PPTX · SRT · VTT · TXT · MD, up to 25 MB each. Videos: upload the transcript or captions file.</p>
        <input ref={fileRef} type="file" accept={ACCEPT} multiple className="hidden" onChange={(e) => e.target.files && upload(e.target.files)} />
      </div>

      {queue.length > 0 && (
        <div className="space-y-2">
          {queue.map((q, i) => (
            <div
              key={`${q.name}-${i}`}
              className={`rounded-xl border p-3 text-xs ${q.state === "error" ? "border-rose-500/30 bg-rose-950/20 text-rose-200" : q.state === "done" ? "border-emerald-500/30 bg-emerald-950/20 text-emerald-200" : "border-slate-700 bg-slate-900 text-slate-300"}`}
            >
              <div className="flex items-center gap-2 font-semibold">
                {q.state === "uploading" ? <Spinner label={`Reading ${q.name}… larger files take longer.`} /> : q.state === "done" ? <CheckCircle2 className="h-4 w-4" /> : <X className="h-4 w-4" />}
                {q.state !== "uploading" && <span>{q.name}</span>}
              </div>
              {q.result && (
                <p className="mt-1 text-slate-300">
                  {q.result.evidence_count} passages{q.result.figure_count ? `, ${q.result.figure_count} figures` : ""}, {q.result.topics.length} topics ({q.result.topics.map((t) => t.name).join(", ")}),{" "}
                  {q.result.question_count} verified questions.
                  {q.result.warnings.map((w) => (
                    <span key={w} className="block text-amber-300">
                      ⚠ {w}
                    </span>
                  ))}
                </p>
              )}
              {q.error && <p className="mt-1">{q.error}</p>}
            </div>
          ))}
        </div>
      )}

      {loading ? (
        <Spinner label="Loading your library…" />
      ) : (
        <>
          <Panel className="overflow-hidden p-0">
            <div className="border-b border-slate-800 p-4 text-sm font-bold uppercase tracking-wider text-slate-300">Your material ({mine.length})</div>
            {mine.length === 0 ? (
              <div className="p-6">
                <EmptyState icon={Upload} title="Nothing uploaded yet" body="Until you upload your own files, the tutor and quizzes use the demo course below." />
              </div>
            ) : (
              <table className="w-full text-left text-xs">
                <tbody className="divide-y divide-slate-800/80">
                  {mine.map((s) => (
                    <Row key={s.source_id} s={s} />
                  ))}
                </tbody>
              </table>
            )}
          </Panel>
          <Panel className="overflow-hidden p-0">
            <div className="border-b border-slate-800 p-4 text-sm font-bold uppercase tracking-wider text-slate-300">Demo course ({demo.length})</div>
            <table className="w-full text-left text-xs">
              <tbody className="divide-y divide-slate-800/80">
                {demo.map((s) => (
                  <Row key={s.source_id} s={s} />
                ))}
              </tbody>
            </table>
          </Panel>
        </>
      )}

      {viewing && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/60 p-4 backdrop-blur-sm" onClick={() => setViewing(null)}>
          <div className="max-h-[85vh] w-full max-w-3xl overflow-y-auto rounded-2xl border border-slate-700 bg-slate-900 p-6" onClick={(e) => e.stopPropagation()}>
            <div className="mb-4 flex items-center justify-between">
              <h3 className="text-base font-bold text-slate-100">{viewing.title}</h3>
              <button onClick={() => setViewing(null)} className="rounded-lg p-1.5 text-slate-400 hover:bg-slate-800">
                <X className="h-5 w-5" />
              </button>
            </div>
            {units.length === 0 ? (
              <Spinner />
            ) : (
              <div className="space-y-2">
                {units.map((u) => (
                  <div key={u.evidence_id} className="rounded-xl border border-slate-800 bg-slate-950 p-3 text-xs">
                    <div className="mb-1 flex items-center gap-2 text-[11px] text-indigo-300">
                      {u.evidence_type === "figure" && <ImageIcon className="h-3 w-3" />}
                      <b>{locLabel(u)}</b>
                      {u.section && <span className="text-slate-500">· {u.section}</span>}
                    </div>
                    <p className="whitespace-pre-wrap text-slate-300">{u.text}</p>
                  </div>
                ))}
              </div>
            )}
          </div>
        </div>
      )}
    </div>
  );
};
