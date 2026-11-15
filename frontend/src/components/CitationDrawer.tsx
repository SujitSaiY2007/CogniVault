"use client";

import React, { useEffect, useState } from "react";
import { BookOpen, MapPin, X } from "lucide-react";
import { api } from "@/lib/api";
import { Citation, locatorLabel } from "@/lib/types";

const MODALITY: Record<string, string> = { pdf: "PDF", pptx: "Slides", video: "Lecture transcript", image: "Figure", text: "Notes" };

export const CitationDrawer: React.FC<{ citation: Citation | null; onClose: () => void }> = ({ citation, onClose }) => {
  const [img, setImg] = useState<string | null>(null);
  const assetId = citation?.asset_id || undefined;

  useEffect(() => {
    setImg(null);
    let url: string | null = null;
    if (assetId) {
      api
        .assetUrl(assetId)
        .then((u) => {
          url = u;
          setImg(u);
        })
        .catch(() => setImg(null));
    }
    return () => {
      if (url) URL.revokeObjectURL(url);
    };
  }, [assetId]);

  useEffect(() => {
    const onKey = (e: KeyboardEvent) => e.key === "Escape" && onClose();
    window.addEventListener("keydown", onKey);
    return () => window.removeEventListener("keydown", onKey);
  }, [onClose]);

  if (!citation) return null;

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/60 p-4 backdrop-blur-sm" onClick={onClose}>
      <div className="relative w-full max-w-lg rounded-2xl border border-slate-700 bg-slate-900 p-6 shadow-2xl" onClick={(e) => e.stopPropagation()}>
        <div className="flex items-start justify-between border-b border-slate-800 pb-4">
          <div className="flex items-center gap-2.5">
            <div className="flex h-9 w-9 items-center justify-center rounded-xl border border-indigo-500/20 bg-indigo-500/10 text-indigo-400">
              <BookOpen className="h-4 w-4" />
            </div>
            <div>
              <h3 className="text-base font-semibold text-slate-100">{citation.source_title || "Course material"}</h3>
              <div className="mt-0.5 flex items-center gap-2">
                <span className="rounded border border-slate-700 bg-slate-800 px-1.5 py-0.5 text-[10px] font-bold uppercase text-slate-300">{MODALITY[citation.modality] || citation.modality}</span>
                <span className="flex items-center gap-1 text-xs font-medium text-indigo-400">
                  <MapPin className="h-3 w-3" />
                  {locatorLabel(citation)}
                </span>
              </div>
            </div>
          </div>
          <button onClick={onClose} aria-label="Close" className="rounded-lg p-1.5 text-slate-400 hover:bg-slate-800 hover:text-slate-100">
            <X className="h-5 w-5" />
          </button>
        </div>
        <div className="mt-5 space-y-4">
          {img && <img src={img} alt="Figure from the source" className="max-h-64 w-full rounded-xl border border-slate-800 bg-white object-contain" />}
          <div>
            <p className="mb-1.5 text-xs font-semibold uppercase tracking-wider text-slate-400">Passage from your source</p>
            <div className="max-h-72 overflow-y-auto whitespace-pre-wrap rounded-xl border border-l-4 border-slate-800 border-l-indigo-500 bg-slate-950 p-4 text-sm leading-relaxed text-slate-200">
              {citation.snippet || "No text recorded."}
            </div>
          </div>
          <p className="text-[11px] text-slate-500">
            Open your copy of “{citation.source_title}” at <b>{locatorLabel(citation)}</b> to read it in context.
          </p>
        </div>
      </div>
    </div>
  );
};
