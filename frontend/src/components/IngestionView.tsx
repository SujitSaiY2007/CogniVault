"use client";

import React, { useState, useEffect } from "react";
import { Citation, EvidenceUnit, SourceRecord } from "@/lib/types";
import { api } from "@/lib/api";
import {
  BookOpen,
  CheckCircle2,
  Database,
  ExternalLink,
  FileText,
  Hash,
  MapPin,
  RefreshCw,
  Sparkles,
  Upload,
  Video,
} from "lucide-react";

interface IngestionViewProps {
  onOpenCitation: (cit: Citation) => void;
  onCurriculumUpdated?: () => void;
}

export const IngestionView: React.FC<IngestionViewProps> = ({ onOpenCitation, onCurriculumUpdated }) => {
  const [sources, setSources] = useState<SourceRecord[]>([]);
  const [selectedSource, setSelectedSource] = useState<SourceRecord | null>(null);
  const [evidenceUnits, setEvidenceUnits] = useState<EvidenceUnit[]>([]);
  const [loading, setLoading] = useState(true);
  const [uploading, setUploading] = useState(false);
  const [syncing, setSyncing] = useState(false);
  const [seeding, setSeeding] = useState(false);
  const [syncStatus, setSyncStatus] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);

  const loadSources = async () => {
    setLoading(true);
    setError(null);
    try {
      const data = await api.listSources();
      setSources(data);
    } catch (err: any) {
      setError(err.message || "Failed to load indexed sources.");
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    loadSources();
  }, []);

  const handleInspect = async (src: SourceRecord) => {
    setSelectedSource(src);
    try {
      const units = await api.getSourceEvidence(src.source_id);
      setEvidenceUnits(units);
    } catch {
      setEvidenceUnits([]);
    }
  };

  const handleFileUpload = async (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0];
    if (!file) return;

    setUploading(true);
    setError(null);
    try {
      await api.uploadMaterial(file);
      await loadSources();
    } catch (err: any) {
      setError(err.message || "File upload failed.");
    } finally {
      setUploading(false);
      e.target.value = "";
    }
  };

  const handleSyncChroma = async () => {
    setSyncing(true);
    setSyncStatus(null);
    try {
      const res = await api.syncChroma();
      setSyncStatus(`Successfully synchronized ${res.synced_units} evidence units into ChromaDB!`);
      await loadSources();
    } catch (err: any) {
      setError(err.message || "Failed to synchronize ChromaDB.");
    } finally {
      setSyncing(false);
    }
  };

  const handleSeedCorpus = async () => {
    setSeeding(true);
    setError(null);
    try {
      await api.seedCorpus();
      setSyncStatus("Successfully seeded baseline curriculum topics and verified question bank!");
      await loadSources();
      if (onCurriculumUpdated) onCurriculumUpdated();
    } catch (err: any) {
      setError(err.message || "Failed to seed default corpus.");
    } finally {
      setSeeding(false);
    }
  };

  const getModalityBadge = (m: string) => {
    switch (m.toLowerCase()) {
      case "pdf":
        return "bg-rose-500/10 text-rose-400 border-rose-500/20";
      case "pptx":
        return "bg-amber-500/10 text-amber-400 border-amber-500/20";
      case "video":
        return "bg-sky-500/10 text-sky-400 border-sky-500/20";
      default:
        return "bg-slate-800 text-slate-300 border-slate-700";
    }
  };

  return (
    <div className="max-w-5xl mx-auto p-4 sm:p-6 space-y-6">
      {/* Top Header */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4 pb-4 border-b border-slate-800">
        <div>
          <h2 className="text-lg font-bold text-slate-100 flex items-center gap-2">
            <BookOpen className="h-5 w-5 text-indigo-400" />
            <span>Course Knowledge Base & Materials Ingestion</span>
          </h2>
          <p className="text-xs text-slate-400">
            Multimodal sources (PDFs, PPTX decks, video transcripts) indexed with physical locators & SHA-256 provenance.
          </p>
        </div>

        <div className="flex flex-wrap items-center gap-2">
          <button
            onClick={handleSeedCorpus}
            disabled={seeding}
            className="flex items-center gap-1.5 rounded-xl border border-slate-700 bg-slate-900 hover:bg-slate-800 px-3.5 py-2 text-xs font-semibold text-slate-200 transition-colors disabled:opacity-50"
          >
            <RefreshCw className={`h-3.5 w-3.5 ${seeding ? "animate-spin" : ""}`} />
            <span>{seeding ? "Seeding Corpus..." : "Seed Default Corpus"}</span>
          </button>

          <button
            onClick={handleSyncChroma}
            disabled={syncing}
            className="flex items-center gap-1.5 rounded-xl border border-indigo-500/30 bg-indigo-500/10 hover:bg-indigo-500/20 px-3.5 py-2 text-xs font-semibold text-indigo-300 transition-colors disabled:opacity-50"
          >
            <Database className={`h-3.5 w-3.5 ${syncing ? "animate-spin" : ""}`} />
            <span>{syncing ? "Syncing ChromaDB..." : "Sync Vector Store"}</span>
          </button>

          <label className="flex items-center gap-1.5 rounded-xl bg-indigo-600 hover:bg-indigo-500 px-3.5 py-2 text-xs font-semibold text-white shadow-md shadow-indigo-600/25 transition-all cursor-pointer">
            <Upload className="h-3.5 w-3.5" />
            <span>{uploading ? "Ingesting..." : "Upload Material"}</span>
            <input
              type="file"
              accept=".pdf,.pptx,.txt"
              onChange={handleFileUpload}
              disabled={uploading}
              className="hidden"
            />
          </label>
        </div>
      </div>

      {syncStatus && (
        <div className="rounded-xl border border-emerald-500/30 bg-emerald-500/10 p-3.5 text-xs text-emerald-400 flex items-center gap-2">
          <CheckCircle2 className="h-4 w-4 shrink-0" />
          <span>{syncStatus}</span>
        </div>
      )}

      {error && (
        <div className="rounded-xl border border-rose-500/30 bg-rose-500/10 p-4 text-xs text-rose-400">
          {error}
        </div>
      )}

      {/* Sources Table */}
      <div className="rounded-2xl border border-slate-800 bg-slate-900 shadow-xl overflow-hidden">
        <div className="p-4 sm:p-5 border-b border-slate-800 flex items-center justify-between">
          <h3 className="text-sm font-bold uppercase tracking-wider text-slate-300">
            Indexed Course Sources ({sources.length})
          </h3>
          <span className="text-xs text-slate-400 font-mono">Provenance Track D</span>
        </div>

        <div className="overflow-x-auto">
          <table className="w-full text-left text-xs">
            <thead className="bg-slate-950/60 text-slate-400 uppercase text-[10px] tracking-wider border-b border-slate-800">
              <tr>
                <th className="py-3 px-4">Title & Source ID</th>
                <th className="py-3 px-4">Modality</th>
                <th className="py-3 px-4">Evidence Units</th>
                <th className="py-3 px-4">SHA-256 Provenance</th>
                <th className="py-3 px-4 text-right">Action</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-slate-800/80">
              {sources.map((s) => (
                <tr key={s.source_id} className="hover:bg-slate-800/40 transition-colors">
                  <td className="py-3.5 px-4">
                    <div className="font-semibold text-slate-200">{s.title}</div>
                    <div className="font-mono text-[11px] text-slate-500">{s.source_id}</div>
                  </td>
                  <td className="py-3.5 px-4">
                    <span className={`px-2 py-0.5 rounded border uppercase text-[10px] font-bold ${getModalityBadge(s.modality)}`}>
                      {s.modality}
                    </span>
                  </td>
                  <td className="py-3.5 px-4 font-mono text-slate-300">
                    {s.evidence_count ?? "—"} units
                  </td>
                  <td className="py-3.5 px-4 font-mono text-[11px] text-slate-500 truncate max-w-xs" title={s.sha256}>
                    {s.sha256 ? `${s.sha256.slice(0, 16)}...` : "—"}
                  </td>
                  <td className="py-3.5 px-4 text-right">
                    <button
                      onClick={() => handleInspect(s)}
                      className="px-2.5 py-1 rounded-lg border border-slate-700 bg-slate-800 hover:bg-slate-700 text-slate-200 text-xs transition-colors"
                    >
                      View Units
                    </button>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </div>

      {/* Evidence Units Inspector */}
      {selectedSource && (
        <div className="rounded-2xl border border-slate-800 bg-slate-900 p-6 shadow-xl space-y-4">
          <div className="flex items-center justify-between pb-3 border-b border-slate-800">
            <div>
              <h3 className="text-sm font-bold text-slate-100">
                Extracted Evidence: {selectedSource.title}
              </h3>
              <p className="text-xs text-slate-400">
                Physical locators verified for source `{selectedSource.source_id}` ({evidenceUnits.length} units).
              </p>
            </div>
            <button
              onClick={() => setSelectedSource(null)}
              className="text-xs text-slate-400 hover:text-slate-200 transition-colors"
            >
              Close Inspector
            </button>
          </div>

          <div className="space-y-3 max-h-96 overflow-y-auto pr-1">
            {evidenceUnits.map((u) => {
              const loc = u.location || {};
              let locText = "Location";
              if (loc.page !== undefined) locText = `Page ${loc.page}`;
              else if (loc.slide !== undefined) locText = `Slide ${loc.slide}`;
              else if (loc.timestamp !== undefined) locText = `Timestamp ${loc.timestamp}`;

              return (
                <div
                  key={u.evidence_id}
                  className="rounded-xl border border-slate-800 bg-slate-950 p-3.5 space-y-1.5 text-xs"
                >
                  <div className="flex items-center justify-between">
                    <span className="flex items-center gap-1.5 font-semibold text-indigo-400">
                      <MapPin className="h-3.5 w-3.5" />
                      <span>{locText}</span>
                    </span>
                    <span className="font-mono text-[11px] text-slate-500">
                      {u.evidence_id}
                    </span>
                  </div>
                  <p className="text-slate-300 font-serif italic line-clamp-3">
                    "{u.text}"
                  </p>
                </div>
              );
            })}
          </div>
        </div>
      )}
    </div>
  );
};
