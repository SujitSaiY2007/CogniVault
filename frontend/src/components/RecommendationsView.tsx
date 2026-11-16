"use client";

import React, { useCallback, useEffect, useRef, useState } from "react";
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
      <div className="flex justify-between text-xs text-slate-500">
        <span>{c.topic_name}</span>
        <span>
          {i + 1} / {cards.length}
        </span>
      </div>
      <button onClick={() => setFlipped(!flipped)} className="flex min-h-[160px] w-full flex-col items-center justify-center rounded-2xl border-2 border-slate-200 bg-[#fbfaf7] p-6 text-center hover:border-indigo-400">
        <p className="text-[10px] font-bold uppercase tracking-wider text-slate-500">{flipped ? "Answer" : c.kind === "formula" ? "Formula" : "Term"}</p>
        <p className={`mt-2 ${flipped ? "text-sm text-slate-800" : "text-xl font-bold text-slate-900"}`}>{flipped ? c.back : c.front}</p>
        {!flipped && <p className="mt-3 text-[11px] text-slate-500">Tap to reveal</p>}
      </button>
      {flipped && (
        <>
          {c.citation && (
            <button onClick={() => onOpenCitation(c.citation!)} className="flex items-center gap-1 text-xs text-indigo-600 underline decoration-dotted">
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

const QUICK_RANGES = [
  { label: "1 week", days: 7 },
  { label: "2 weeks", days: 14 },
  { label: "1 month", days: 30 },
];
const DAILY_MINUTES = [30, 60, 90, 120];

function isoIn(days: number) {
  const d = new Date();
  d.setDate(d.getDate() + days);
  return `${d.getFullYear()}-${String(d.getMonth() + 1).padStart(2, "0")}-${String(d.getDate()).padStart(2, "0")}`;
}
function todayIso() {
  return isoIn(0);
}
function hoursLabel(min: number) {
  const h = Math.floor(min / 60);
  const m = min % 60;
  return h ? (m ? `${h} h ${m} min` : `${h} h`) : `${m} min`;
}

function Plan() {
  const [plan, setPlan] = useState<StudyPlan | null>(null);
  const [exam, setExam] = useState("");
  const [minutes, setMinutes] = useState(60);
  const [error, setError] = useState<string | null>(null);
  const [updating, setUpdating] = useState(false);
  const [showAll, setShowAll] = useState(false);
  const savedKey = useRef<string | null>(null);
  const requestId = useRef(0);

  useEffect(() => {
    api
      .studyPlan()
      .then((p) => {
        setPlan(p);
        setExam(p.exam_date);
        setMinutes(p.minutes_per_day);
        savedKey.current = `${p.exam_date}|${p.minutes_per_day}`;
      })
      .catch((e) => setError(e.message));
  }, []);

  // Re-plan automatically when the exam date or daily time changes (no Update button to press).
  useEffect(() => {
    // Skip the values just loaded from the server; only re-plan after the user changes something.
    if (savedKey.current === null || !exam || savedKey.current === `${exam}|${minutes}`) return;
    if (exam < todayIso()) {
      setError("Pick an exam date that is today or later.");
      return;
    }
    setError(null);
    const id = ++requestId.current;
    setUpdating(true);
    const timer = setTimeout(async () => {
      try {
        const next = await api.saveStudyPlan(exam, minutes);
        if (id === requestId.current) {
          setPlan(next);
          savedKey.current = `${exam}|${minutes}`;
        }
      } catch (e: any) {
        if (id === requestId.current) setError(e.message);
      } finally {
        if (id === requestId.current) setUpdating(false);
      }
    }, 500);
    return () => clearTimeout(timer);
  }, [exam, minutes]);

  const today = todayIso();
  // Merge repeated blocks of the same topic and activity into one row ("Voltage and Resistance · 60 min").
  const days = plan
    ? plan.plan
        .filter((d) => d.blocks.length)
        .map((d) => ({
          ...d,
          blocks: d.blocks.reduce<StudyPlan["plan"][number]["blocks"]>((acc, b) => {
            const same = acc.find((x) => x.topic_id === b.topic_id && x.activity === b.activity && x.kind === b.kind);
            if (same) same.minutes += b.minutes;
            else acc.push({ ...b });
            return acc;
          }, []),
        }))
    : [];
  const visible = showAll ? days : days.slice(0, 7);

  return (
    <div className="space-y-5">
      <div className="flex flex-wrap items-end gap-4 text-xs font-semibold text-slate-600">
        <div>
          <p className="mb-1.5">When is your exam?</p>
          <div className="flex flex-wrap items-center gap-2">
            {QUICK_RANGES.map((r) => (
              <GhostButton key={r.label} onClick={() => setExam(isoIn(r.days))} className={exam === isoIn(r.days) ? "border-indigo-400 bg-indigo-50 text-indigo-700" : ""}>
                {r.label}
              </GhostButton>
            ))}
            <input type="date" min={today} value={exam} onChange={(e) => e.target.value && setExam(e.target.value)} className="rounded-xl border border-slate-200 bg-white px-3 py-2 text-xs text-slate-800 focus:border-indigo-400 focus:outline-none focus:ring-4 focus:ring-indigo-100" />
          </div>
        </div>
        <div>
          <p className="mb-1.5">Time per day</p>
          <div className="flex gap-2">
            {DAILY_MINUTES.map((m) => (
              <GhostButton key={m} onClick={() => setMinutes(m)} className={minutes === m ? "border-indigo-400 bg-indigo-50 text-indigo-700" : ""}>
                {hoursLabel(m)}
              </GhostButton>
            ))}
          </div>
        </div>
        {updating && <span className="pb-2 text-slate-500">Updating…</span>}
      </div>

      {error && <ErrorBanner message={error} />}
      {!plan && !error && <Spinner label="Building your plan…" />}

      {plan?.empty && <EmptyState icon={CalendarDays} title="No topics to plan yet" body="Upload your materials first. The plan is built from your own topics." />}

      {plan && !plan.empty && (
        <div className={`space-y-4 transition-opacity ${updating ? "opacity-60" : "opacity-100"}`}>
          <div className="grid grid-cols-3 gap-3">
            <Stat label="Days to exam" value={String(plan.days)} />
            <Stat label="Planned study" value={hoursLabel(plan.total_minutes)} />
            <Stat label="Topics covered" value={`${plan.topics_covered} / ${plan.topics_total}`} />
          </div>
          {plan.warning && <div className="rounded-xl border border-amber-200 bg-amber-50 p-3 text-xs leading-5 text-amber-800">{plan.warning}</div>}
          {days.length === 0 && <p className="text-xs text-slate-500">Everything is mastered. Keep up with flashcards.</p>}
          <div className="space-y-2">
            {visible.map((d) => {
              const isToday = d.date === today;
              return (
                <div key={d.date} className={`rounded-2xl border p-4 ${isToday ? "border-indigo-200 bg-indigo-50/60" : "border-slate-200 bg-white"}`}>
                  <p className="mb-2 flex items-center gap-2 text-xs font-extrabold text-slate-800">
                    {new Date(d.date + "T00:00:00").toLocaleDateString(undefined, { weekday: "short", day: "numeric", month: "short" })}
                    {isToday && <span className="rounded-full bg-indigo-600 px-2 py-0.5 text-[10px] font-bold text-white">Today</span>}
                  </p>
                  <div className="space-y-1.5">
                    {d.blocks.map((b, i) => (
                      <p key={i} className="flex justify-between gap-3 text-xs text-slate-500">
                        <span>
                          <b className={b.kind === "exam" ? "text-violet-700" : b.kind === "review" ? "text-teal-700" : "text-slate-800"}>{b.topic_name}</b> · {b.activity}
                        </span>
                        <span className="shrink-0 font-mono text-slate-500">{b.minutes} min</span>
                      </p>
                    ))}
                  </div>
                </div>
              );
            })}
          </div>
          {days.length > 7 && (
            <GhostButton onClick={() => setShowAll((v) => !v)}>{showAll ? "Show first week only" : `Show all ${days.length} study days`}</GhostButton>
          )}
        </div>
      )}
    </div>
  );
}

function Stat({ label, value }: { label: string; value: string }) {
  return (
    <div className="rounded-2xl border border-slate-200 bg-[#fbfaf7] p-3 text-center">
      <p className="text-lg font-black text-slate-900">{value}</p>
      <p className="text-[11px] font-semibold text-slate-500">{label}</p>
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
        <Panel className="flex flex-col gap-3 border-indigo-200 sm:flex-row sm:items-center sm:justify-between">
          <div>
            <p className="text-xs font-bold uppercase tracking-wider text-indigo-600">Next step · {ACTION_LABELS[rec.recommended_action]}</p>
            <p className="mt-1 text-base font-bold text-slate-900">{rec.topic_name}</p>
            <p className="mt-1 text-sm text-slate-600">{rec.rationale}</p>
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
