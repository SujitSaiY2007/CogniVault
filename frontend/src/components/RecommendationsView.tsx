"use client";

import React, { useCallback, useEffect, useState } from "react";
import { CalendarDays, Compass, Layers, MapPin, RotateCw } from "lucide-react";
import { api } from "@/lib/api";
import { ACTION_LABELS, Citation, Flashcard, Recommendation, StudyPlan, locatorLabel } from "@/lib/types";
import { EmptyState, ErrorBanner, GhostButton, Panel, PrimaryButton, SectionHeader, Spinner } from "./ui";

const GRADES = [
  { label: "Again", grade: 1, cls: "hover:border-rose-400" },
  { label: "Hard", grade: 3, cls: "hover:border-amber-400" },
  { label: "Good", grade: 4, cls: "hover:border-teal-400" },
  { label: "Easy", grade: 5, cls: "hover:border-emerald-400" },
];

function Flashcards({ onOpenCitation }: { onOpenCitation: (c: Citation) => void }) {
  const [cards, setCards] = useState<Flashcard[] | null>(null);
  const [i, setI] = useState(0);
  const [flipped, setFlipped] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const load = useCallback(async () => {
    setError(null);
    try {
      setCards(await api.flashcards());
      setI(0);
      setFlipped(false);
    } catch (e: any) {
      setError(e.message);
    }
  }, []);
  useEffect(() => {
    load();
  }, [load]);

  async function grade(g: number) {
    if (!cards) return;
    try {
      await api.reviewFlashcard(cards[i].card_id, g);
    } catch (e: any) {
      setError(e.message);
      return;
    }
    setFlipped(false);
    setI((x) => x + 1);
  }

  if (error) return <ErrorBanner message={error} onRetry={load} />;
  if (!cards) return <Spinner />;
  if (i >= cards.length)
    return (
      <EmptyState
        icon={Layers}
        title={cards.length ? "Done for now" : "No cards due"}
        body="Cards come back when spaced repetition says they are due. Weaker topics come first."
        action={<GhostButton onClick={load}><RotateCw className="h-4 w-4" /> Check again</GhostButton>}
      />
    );
  const c = cards[i];
  return (
    <div className="space-y-3">
      <div className="flex justify-between text-xs text-slate-400">
        <span>{c.topic_name}</span>
        <span>
          {i + 1} / {cards.length}
        </span>
      </div>
      <button onClick={() => setFlipped(!flipped)} className="flex min-h-[160px] w-full flex-col items-center justify-center rounded-2xl border-2 border-slate-700 bg-slate-950 p-6 text-center hover:border-indigo-400">
        <p className="text-[10px] font-bold uppercase tracking-wider text-slate-500">{flipped ? "Answer" : c.kind === "formula" ? "Formula" : "Term"}</p>
        <p className={`mt-2 ${flipped ? "text-sm text-slate-200" : "text-xl font-bold text-white"}`}>{flipped ? c.back : c.front}</p>
        {!flipped && <p className="mt-3 text-[11px] text-slate-500">Tap to reveal</p>}
      </button>
      {flipped && (
        <>
          {c.citation && (
            <button onClick={() => onOpenCitation(c.citation!)} className="flex items-center gap-1 text-xs text-indigo-300 underline decoration-dotted">
              <MapPin className="h-3 w-3" /> {c.citation.source_title}, {locatorLabel(c.citation)}
            </button>
          )}
          <div className="grid grid-cols-4 gap-2">
            {GRADES.map((g) => (
              <GhostButton key={g.label} onClick={() => grade(g.grade)} className={g.cls}>
                {g.label}
              </GhostButton>
            ))}
          </div>
        </>
      )}
    </div>
  );
}

function Plan() {
  const [plan, setPlan] = useState<StudyPlan | null>(null);
  const [exam, setExam] = useState("");
  const [minutes, setMinutes] = useState(60);
  const [error, setError] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);

  useEffect(() => {
    api
      .studyPlan()
      .then((p) => {
        setPlan(p);
        setExam(p.exam_date);
        setMinutes(p.minutes_per_day);
      })
      .catch((e) => setError(e.message));
  }, []);

  async function save() {
    setBusy(true);
    setError(null);
    try {
      setPlan(await api.saveStudyPlan(exam, minutes));
    } catch (e: any) {
      setError(e.message);
    } finally {
      setBusy(false);
    }
  }

  return (
    <div className="space-y-4">
      <div className="flex flex-wrap items-end gap-3 text-xs text-slate-300">
        <label>
          Exam date
          <input type="date" value={exam} onChange={(e) => setExam(e.target.value)} className="mt-1 block rounded-xl border-2 border-slate-600 bg-slate-900 px-3 py-2 text-slate-100" />
        </label>
        <label>
          Minutes per day
          <input type="number" min={10} max={600} step={10} value={minutes} onChange={(e) => setMinutes(+e.target.value)} className="mt-1 block w-28 rounded-xl border-2 border-slate-600 bg-slate-900 px-3 py-2 text-slate-100" />
        </label>
        <PrimaryButton onClick={save} disabled={busy || !exam}>
          {busy ? "Planning…" : "Update plan"}
        </PrimaryButton>
      </div>
      {error && <ErrorBanner message={error} />}
      {!plan && !error && <Spinner />}
      {plan?.warning && <div className="rounded-xl border border-amber-500/30 bg-amber-500/10 p-3 text-xs text-amber-200">{plan.warning}</div>}
      {plan && (
        <div className="space-y-2">
          {plan.plan
            .filter((d) => d.blocks.length)
            .slice(0, 21)
            .map((d) => (
              <div key={d.date} className="rounded-xl border border-slate-800 bg-slate-950 p-3">
                <p className="mb-1.5 text-xs font-bold text-slate-200">
                  {new Date(d.date + "T00:00:00").toLocaleDateString(undefined, { weekday: "short", day: "numeric", month: "short" })}
                </p>
                <div className="space-y-1">
                  {d.blocks.map((b, i) => (
                    <p key={i} className="flex justify-between gap-2 text-xs text-slate-400">
                      <span>
                        <b className={b.kind === "exam" ? "text-purple-300" : b.kind === "review" ? "text-teal-300" : "text-slate-200"}>{b.topic_name}</b> — {b.activity}
                      </span>
                      <span className="shrink-0 font-mono">{b.minutes} min</span>
                    </p>
                  ))}
                </div>
              </div>
            ))}
          {plan.plan.every((d) => !d.blocks.length) && <p className="text-xs text-slate-400">Everything is mastered. Keep up with flashcards.</p>}
        </div>
      )}
    </div>
  );
}

export const RecommendationsView: React.FC<{
  learnerId: string;
  refreshKey: number;
  onPractice: (topicId: string) => void;
  onOpenCitation: (c: Citation) => void;
}> = ({ learnerId, refreshKey, onPractice, onOpenCitation }) => {
  const [rec, setRec] = useState<Recommendation | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [tab, setTab] = useState<"plan" | "cards">("plan");

  const load = useCallback(async () => {
    setError(null);
    try {
      setRec(await api.getRecommendation(learnerId));
    } catch (e: any) {
      setError(e.message);
    }
  }, [learnerId]);
  useEffect(() => {
    load();
  }, [load, refreshKey]);

  return (
    <div className="mx-auto max-w-5xl space-y-6 p-4 sm:p-6">
      <SectionHeader icon={Compass} title="Study Plan" subtitle="Your next best step, a day-by-day plan to your exam, and spaced-repetition flashcards from your sources." />
      {error && <ErrorBanner message={error} onRetry={load} />}
      {rec && rec.topic_id && (
        <Panel className="flex flex-col gap-3 border-indigo-500/40 sm:flex-row sm:items-center sm:justify-between">
          <div>
            <p className="text-xs font-bold uppercase tracking-wider text-indigo-300">Next step · {ACTION_LABELS[rec.recommended_action]}</p>
            <p className="mt-1 text-base font-bold text-white">{rec.topic_name}</p>
            <p className="mt-1 text-sm text-slate-300">{rec.rationale}</p>
          </div>
          <PrimaryButton onClick={() => onPractice(rec.topic_id)}>Practise now</PrimaryButton>
        </Panel>
      )}
      <div className="flex gap-2">
        <GhostButton onClick={() => setTab("plan")} className={tab === "plan" ? "border-indigo-400" : ""}>
          <CalendarDays className="h-4 w-4" /> Day-by-day plan
        </GhostButton>
        <GhostButton onClick={() => setTab("cards")} className={tab === "cards" ? "border-indigo-400" : ""}>
          <Layers className="h-4 w-4" /> Flashcards
        </GhostButton>
      </div>
      <Panel>{tab === "plan" ? <Plan /> : <Flashcards onOpenCitation={onOpenCitation} />}</Panel>
    </div>
  );
};
