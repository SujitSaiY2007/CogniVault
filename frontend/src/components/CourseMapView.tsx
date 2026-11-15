"use client";

import React, { useCallback, useEffect, useMemo, useState } from "react";
import { Network } from "lucide-react";
import { api } from "@/lib/api";
import { CourseMap, SourceRecord } from "@/lib/types";
import { ErrorBanner, SectionHeader, Spinner } from "./ui";

const W = 200;
const H = 58;
const GX = 70;
const GY = 18;

const STATUS: Record<string, { fill: string; stroke: string; label: string }> = {
  mastered: { fill: "#064e3b", stroke: "#34d399", label: "Mastered" },
  in_progress: { fill: "#422006", stroke: "#f59e0b", label: "In progress" },
  ready: { fill: "#1e1b4b", stroke: "#818cf8", label: "Ready to start" },
  locked: { fill: "#0f172a", stroke: "#475569", label: "Prerequisites first" },
};

export const CourseMapView: React.FC<{ refreshKey: number; onPractice: (topicId: string) => void }> = ({ refreshKey, onPractice }) => {
  const [map, setMap] = useState<CourseMap | null>(null);
  const [sources, setSources] = useState<SourceRecord[]>([]);
  const [error, setError] = useState<string | null>(null);

  const load = useCallback(async () => {
    setError(null);
    try {
      const [m, s] = await Promise.all([api.courseMap(), api.listSources()]);
      setMap(m);
      setSources(s);
    } catch (e: any) {
      setError(e.message);
    }
  }, []);
  useEffect(() => {
    load();
  }, [load, refreshKey]);

  const layout = useMemo(() => {
    if (!map) return null;
    const titles = Object.fromEntries(sources.map((s) => [s.source_id, s.title]));
    const order = sources.map((s) => s.source_id);
    const groups = Array.from(new Set(map.nodes.map((n) => n.source_id))).sort((a, b) => order.indexOf(a) - order.indexOf(b));
    const pos: Record<string, { x: number; y: number }> = {};
    const headers: { y: number; title: string }[] = [];
    let y = 10;
    let maxX = 0;
    for (const g of groups) {
      const nodes = map.nodes.filter((n) => n.source_id === g);
      headers.push({ y, title: titles[g] || g });
      y += 30;
      const cols: Record<number, number> = {};
      let rows = 0;
      for (const n of nodes) {
        const d = Math.min(n.depth, 5);
        const r = cols[d] || 0;
        cols[d] = r + 1;
        rows = Math.max(rows, r + 1);
        pos[n.topic_id] = { x: 10 + d * (W + GX), y: y + r * (H + GY) };
        maxX = Math.max(maxX, 10 + d * (W + GX) + W);
      }
      y += rows * (H + GY) + 20;
    }
    return { pos, headers, width: maxX + 20, height: y };
  }, [map, sources]);

  return (
    <div className="mx-auto max-w-7xl space-y-5 p-4 sm:p-6">
      <SectionHeader
        icon={Network}
        title="Course Map"
        subtitle="Topics found in your material and the prerequisites between them. Arrows point from a prerequisite to the topic that builds on it. Click a topic to practise it."
        right={
          <div className="flex flex-wrap gap-3 text-[11px] text-slate-300">
            {Object.values(STATUS).map((s) => (
              <span key={s.label} className="flex items-center gap-1">
                <span className="h-3 w-3 rounded border" style={{ background: s.fill, borderColor: s.stroke }} /> {s.label}
              </span>
            ))}
          </div>
        }
      />
      {error && <ErrorBanner message={error} onRetry={load} />}
      {!map && !error && <Spinner label="Drawing your course map…" />}
      {map && layout && (
        <div className="overflow-auto rounded-2xl border border-slate-800 bg-slate-950 p-3">
          <svg width={layout.width} height={layout.height} role="img" aria-label="Course topic map">
            <defs>
              <marker id="arrow" viewBox="0 0 10 10" refX="9" refY="5" markerWidth="6" markerHeight="6" orient="auto-start-reverse">
                <path d="M 0 0 L 10 5 L 0 10 z" fill="#64748b" />
              </marker>
            </defs>
            {layout.headers.map((h) => (
              <text key={h.title + h.y} x={10} y={h.y + 16} fill="#a5b4fc" fontSize={12} fontWeight={700}>
                {h.title}
              </text>
            ))}
            {map.edges.map((e) => {
              const a = layout.pos[e.from];
              const b = layout.pos[e.to];
              if (!a || !b) return null;
              const x1 = a.x + W,
                y1 = a.y + H / 2,
                x2 = b.x,
                y2 = b.y + H / 2;
              const back = x2 <= x1;
              const d = back
                ? `M ${a.x + W / 2} ${a.y + H} C ${a.x + W / 2} ${a.y + H + 40}, ${b.x + W / 2} ${b.y - 40}, ${b.x + W / 2} ${b.y}`
                : `M ${x1} ${y1} C ${x1 + GX / 2} ${y1}, ${x2 - GX / 2} ${y2}, ${x2} ${y2}`;
              return <path key={e.from + e.to} d={d} stroke="#64748b" strokeWidth={1.5} fill="none" markerEnd="url(#arrow)" />;
            })}
            {map.nodes.map((n) => {
              const p = layout.pos[n.topic_id];
              const s = STATUS[n.status];
              return (
                <g key={n.topic_id} transform={`translate(${p.x},${p.y})`} onClick={() => onPractice(n.topic_id)} style={{ cursor: "pointer" }}>
                  <title>{`${n.name}\nMastery ${Math.round(n.p_mastery * 100)}%\n${n.concepts.join(", ")}`}</title>
                  <rect width={W} height={H} rx={12} fill={s.fill} stroke={s.stroke} strokeWidth={1.5} />
                  <text x={12} y={23} fill="#f1f5f9" fontSize={12} fontWeight={700}>
                    {n.name.length > 26 ? n.name.slice(0, 25) + "…" : n.name}
                  </text>
                  <rect x={12} y={36} width={W - 24} height={6} rx={3} fill="#1e293b" />
                  <rect x={12} y={36} width={(W - 24) * n.p_mastery} height={6} rx={3} fill={s.stroke} />
                </g>
              );
            })}
          </svg>
        </div>
      )}
    </div>
  );
};
