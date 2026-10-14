"use client";

import React from "react";
import { Citation } from "@/lib/types";
import { BookOpen, ExternalLink, FileText, Hash, MapPin, X } from "lucide-react";

interface CitationDrawerProps {
  citation: Citation | null;
  onClose: () => void;
}

export const CitationDrawer: React.FC<CitationDrawerProps> = ({ citation, onClose }) => {
  if (!citation) return null;

  const loc = citation.location || {};
  let locString = "Physical locator details";
  if (loc.page !== undefined) {
    locString = `Page ${loc.page}`;
  } else if (loc.slide !== undefined) {
    locString = `Slide ${loc.slide}`;
  } else if (loc.timestamp !== undefined) {
    locString = `Timestamp ${loc.timestamp}`;
  }

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/60 backdrop-blur-sm p-4 animate-in fade-in duration-150">
      <div className="relative w-full max-w-lg rounded-2xl border border-slate-700 bg-slate-900 shadow-2xl p-6 sm:p-7">
        {/* Header */}
        <div className="flex items-start justify-between pb-4 border-b border-slate-800">
          <div className="flex items-center gap-2.5">
            <div className="flex h-9 w-9 items-center justify-center rounded-xl bg-indigo-500/10 text-indigo-400 border border-indigo-500/20">
              <BookOpen className="h-4 w-4" />
            </div>
            <div>
              <h3 className="text-base font-semibold text-slate-100">
                {citation.source_title || citation.source_id}
              </h3>
              <div className="flex items-center gap-2 mt-0.5">
                <span className="uppercase text-[10px] font-bold px-1.5 py-0.5 rounded bg-slate-800 text-slate-300 border border-slate-700">
                  {citation.modality}
                </span>
                <span className="flex items-center gap-1 text-xs text-indigo-400 font-medium">
                  <MapPin className="h-3 w-3" />
                  {locString}
                </span>
              </div>
            </div>
          </div>
          <button
            onClick={onClose}
            className="rounded-lg p-1.5 text-slate-400 hover:bg-slate-800 hover:text-slate-100 transition-colors"
          >
            <X className="h-5 w-5" />
          </button>
        </div>

        {/* Content Body */}
        <div className="mt-5 space-y-4">
          {/* Excerpt Snippet */}
          <div>
            <label className="text-xs font-semibold uppercase tracking-wider text-slate-400 block mb-1.5">
              Verified Source Excerpt
            </label>
            <div className="rounded-xl border border-slate-800 bg-slate-950 p-4 text-sm text-slate-200 font-serif leading-relaxed italic border-l-4 border-l-indigo-500">
              "{citation.snippet || "No text snippet recorded."}"
            </div>
          </div>

          {/* Source Provenance Info */}
          <div className="rounded-xl border border-slate-800 bg-slate-950/60 p-3 space-y-2 text-xs">
            <div className="flex items-center justify-between text-slate-400">
              <span className="flex items-center gap-1.5">
                <FileText className="h-3.5 w-3.5" /> Source ID:
              </span>
              <span className="font-mono text-slate-200">{citation.source_id}</span>
            </div>
            <div className="flex items-center justify-between text-slate-400">
              <span className="flex items-center gap-1.5">
                <Hash className="h-3.5 w-3.5" /> Evidence ID:
              </span>
              <span className="font-mono text-slate-200">{citation.evidence_id}</span>
            </div>
            {citation.source_path && (
              <div className="flex items-center justify-between text-slate-400">
                <span className="flex items-center gap-1.5">
                  <ExternalLink className="h-3.5 w-3.5" /> File Path:
                </span>
                <span className="font-mono text-slate-300 truncate max-w-[240px]">
                  {citation.source_path}
                </span>
              </div>
            )}
          </div>
        </div>

        {/* Close Button */}
        <div className="mt-6 flex justify-end">
          <button
            onClick={onClose}
            className="px-4 py-2 rounded-xl bg-slate-800 hover:bg-slate-700 text-sm font-medium text-slate-100 transition-colors"
          >
            Dismiss
          </button>
        </div>
      </div>
    </div>
  );
};
