"use client";

import React, { useMemo, useRef, useState, useEffect } from "react";
import { AlertCircle, Bot, CheckCircle2, ChevronDown, ChevronUp, FileText, HelpCircle, MapPin, Send, User } from "lucide-react";
import { api } from "@/lib/api";
import { Citation, CurriculumTopic, TutorResponse, locatorLabel } from "@/lib/types";

interface Message {
  id: string;
  sender: "user" | "tutor";
  text: string;
  response?: TutorResponse;
  error?: boolean;
}

interface TutorViewProps {
  topics: CurriculumTopic[];
  onOpenCitation: (citation: Citation) => void;
}

/** Render "[2]" markers as clickable citation links. */
function AnswerText({ text, citations, onOpen }: { text: string; citations: Citation[]; onOpen: (c: Citation) => void }) {
  const parts = text.split(/(\[\d+\])/g);
  return (
    <div className="whitespace-pre-wrap">
      {parts.map((p, i) => {
        const m = p.match(/^\[(\d+)\]$/);
        if (m) {
          const c = citations[parseInt(m[1], 10) - 1];
          if (!c) return null;
          return (
            <button
              key={i}
              onClick={() => onOpen(c)}
              title={`${c.source_title}, ${locatorLabel(c)}`}
              className="mx-0.5 inline-flex -translate-y-0.5 items-center rounded-md border border-indigo-500/40 bg-indigo-500/15 px-1.5 text-[10px] font-bold text-indigo-300 hover:bg-indigo-500/30"
            >
              {m[1]}
            </button>
          );
        }
        return <span key={i}>{p}</span>;
      })}
    </div>
  );
}

export const TutorView: React.FC<TutorViewProps> = ({ topics, onOpenCitation }) => {
  const [messages, setMessages] = useState<Message[]>([
    {
      id: "welcome",
      sender: "tutor",
      text:
        "Ask me anything about your course material. I answer only from your uploaded sources and the demo course, and every sentence links to the page, slide or timestamp it came from. If the material doesn't cover your question, I'll say so instead of guessing.",
    },
  ]);
  const [input, setInput] = useState("");
  const [loading, setLoading] = useState(false);
  const [allowGeneral, setAllowGeneral] = useState(false);
  const [showSteps, setShowSteps] = useState<Record<string, boolean>>({});
  const endRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    endRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [messages, loading]);

  const suggestions = useMemo(() => {
    const own = topics.filter((t) => t.owner === "you");
    const pool = (own.length ? own : topics).flatMap((t) => t.concepts.slice(0, 1).map((c) => c));
    const qs = pool.slice(0, 3).map((c) => `What is ${c}?`);
    qs.push("Who won the 2014 football World Cup?");
    return qs;
  }, [topics]);

  const history = messages.filter((m) => m.sender === "user").map((m) => m.text);

  const send = async (text?: string) => {
    const q = (text ?? input).trim();
    if (!q || loading) return;
    const id = `${Date.now()}`;
    setMessages((prev) => [...prev, { id: `u${id}`, sender: "user", text: q }]);
    setInput("");
    setLoading(true);
    try {
      const resp = await api.queryTutor(q, history.slice(-3), allowGeneral);
      setMessages((prev) => [...prev, { id: `t${id}`, sender: "tutor", text: resp.answer, response: resp }]);
    } catch (err: any) {
      setMessages((prev) => [...prev, { id: `t${id}`, sender: "tutor", text: err.message || "The tutor could not answer.", error: true }]);
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="mx-auto flex h-[calc(100vh-130px)] max-w-5xl flex-col p-4 sm:p-6">
      <div className="flex flex-col gap-2 border-b border-slate-800 pb-4 sm:flex-row sm:items-center sm:justify-between">
        <div>
          <h2 className="flex items-center gap-2 text-lg font-bold text-slate-100">
            <Bot className="h-5 w-5 text-indigo-400" />
            <span>Course-Grounded Tutor</span>
          </h2>
          <p className="text-xs text-slate-400">Answers come from your sources with page, slide and timestamp citations. Unsupported questions are declined.</p>
        </div>
        <label className="flex cursor-pointer items-center gap-2 text-xs text-slate-300" title="When the material doesn't cover a question, also show a clearly labelled general-knowledge answer (needs a configured AI model).">
          <input type="checkbox" checked={allowGeneral} onChange={(e) => setAllowGeneral(e.target.checked)} className="accent-indigo-500" />
          Show labelled outside-knowledge answers
        </label>
      </div>

      <div className="flex items-center gap-2 overflow-x-auto py-3 text-xs">
        <span className="shrink-0 text-[11px] font-extrabold uppercase tracking-wider text-indigo-400">Try:</span>
        {suggestions.map((s) => (
          <button
            key={s}
            onClick={() => send(s)}
            disabled={loading}
            className="shrink-0 rounded-full border-2 border-slate-600 bg-slate-800 px-3.5 py-1 font-semibold text-slate-100 transition-all hover:border-indigo-400 hover:bg-slate-700"
          >
            {s}
          </button>
        ))}
      </div>

      <div className="flex-1 space-y-4 overflow-y-auto py-4 pr-1">
        {messages.map((m) => {
          const isUser = m.sender === "user";
          const r = m.response;
          const status = r?.support_status;
          const tone = m.error
            ? "border border-rose-500/30 bg-rose-950/20 text-rose-200"
            : status === "unsupported"
            ? "border border-amber-500/30 bg-amber-950/20 text-amber-100"
            : status === "partial"
            ? "border border-sky-500/30 bg-sky-950/20 text-slate-200"
            : "border border-slate-800 bg-slate-900 text-slate-200";
          return (
            <div key={m.id} className={`flex gap-3 ${isUser ? "justify-end" : "justify-start"}`}>
              {!isUser && (
                <div className="mt-1 flex h-8 w-8 shrink-0 items-center justify-center rounded-xl border border-indigo-500/20 bg-indigo-600/20 text-indigo-400">
                  <Bot className="h-4 w-4" />
                </div>
              )}
              <div
                className={`relative max-w-2xl rounded-2xl p-4 text-sm leading-relaxed sm:p-5 ${
                  isUser ? "rounded-br-none bg-indigo-600 text-white shadow-md shadow-indigo-600/20" : `rounded-bl-none ${tone}`
                }`}
              >
                {status === "unsupported" && (
                  <div className="mb-3 flex items-center gap-2 rounded-xl border border-amber-500/30 bg-amber-500/10 p-2.5 text-xs font-semibold text-amber-300">
                    <AlertCircle className="h-4 w-4 shrink-0" />
                    <span>Not covered by your course material</span>
                  </div>
                )}
                {status === "partial" && (
                  <div className="mb-3 flex items-center gap-2 rounded-xl border border-sky-500/30 bg-sky-500/10 p-2.5 text-xs font-semibold text-sky-300">
                    <HelpCircle className="h-4 w-4 shrink-0" />
                    <span>Partly covered: showing only what your material says</span>
                  </div>
                )}
                {status === "supported" && (
                  <div className="mb-2 flex items-center justify-between gap-2 border-b border-slate-800/80 pb-2 text-xs">
                    <span className="flex items-center gap-1.5 font-semibold text-emerald-400">
                      <CheckCircle2 className="h-3.5 w-3.5" />
                      Grounded in your sources
                    </span>
                    <span className="font-mono text-[11px] text-slate-400" title="How much of your question the cited passages cover">
                      Evidence match {(r!.confidence * 100).toFixed(0)}%
                    </span>
                  </div>
                )}

                {r ? <AnswerText text={m.text} citations={r.citations} onOpen={onOpenCitation} /> : <div className="whitespace-pre-wrap">{m.text}</div>}

                {r && r.citations.length > 0 && (
                  <div className="mt-4 space-y-2 border-t border-slate-800 pt-3">
                    <div className="flex items-center gap-1 text-[11px] font-semibold uppercase tracking-wider text-slate-400">
                      <FileText className="h-3 w-3 text-indigo-400" />
                      Sources
                    </div>
                    <div className="flex flex-wrap gap-2">
                      {r.citations.map((c, i) => (
                        <button
                          key={c.evidence_id}
                          onClick={() => onOpenCitation(c)}
                          className="flex items-center gap-1.5 rounded-lg border border-indigo-500/30 bg-indigo-500/10 px-2.5 py-1 text-xs font-medium text-indigo-300 transition-colors hover:bg-indigo-500/20"
                        >
                          <MapPin className="h-3 w-3" />
                          <span>
                            [{i + 1}] {c.source_title || c.source_id}, {locatorLabel(c)}
                          </span>
                        </button>
                      ))}
                    </div>
                  </div>
                )}

                {r?.metadata?.closest_passages && r.metadata.closest_passages.length > 0 && (
                  <div className="mt-3 text-xs text-amber-200/80">
                    Closest passages in your material:{" "}
                    {r.metadata.closest_passages.map((c: Citation) => (
                      <button key={c.evidence_id} onClick={() => onOpenCitation(c)} className="mr-2 underline decoration-dotted hover:text-amber-100">
                        {c.source_title}, {locatorLabel(c)}
                      </button>
                    ))}
                  </div>
                )}

                {r && r.reasoning_steps.length > 0 && (
                  <div className="mt-3">
                    <button onClick={() => setShowSteps((s) => ({ ...s, [m.id]: !s[m.id] }))} className="flex items-center gap-1 text-[11px] text-slate-400 hover:text-slate-200">
                      How this answer was checked {showSteps[m.id] ? <ChevronUp className="h-3 w-3" /> : <ChevronDown className="h-3 w-3" />}
                    </button>
                    {showSteps[m.id] && (
                      <ol className="mt-2 space-y-1 rounded-xl border border-slate-800 bg-slate-950 p-3 font-mono text-xs text-slate-400">
                        {r.reasoning_steps.map((s, i) => (
                          <li key={i}>
                            {i + 1}. {s}
                          </li>
                        ))}
                      </ol>
                    )}
                  </div>
                )}
              </div>
              {isUser && (
                <div className="mt-1 flex h-8 w-8 shrink-0 items-center justify-center rounded-xl border border-slate-700 bg-slate-800 text-slate-300">
                  <User className="h-4 w-4" />
                </div>
              )}
            </div>
          );
        })}
        {loading && (
          <div className="flex items-center gap-3">
            <div className="flex h-8 w-8 items-center justify-center rounded-xl border border-indigo-500/20 bg-indigo-600/20 text-indigo-400">
              <Bot className="h-4 w-4" />
            </div>
            <div className="flex items-center gap-2 rounded-2xl rounded-bl-none border border-slate-800 bg-slate-900 px-4 py-3 text-xs text-slate-400">
              <div className="h-2 w-2 animate-pulse rounded-full bg-indigo-400" />
              Searching your sources and checking the evidence…
            </div>
          </div>
        )}
        <div ref={endRef} />
      </div>

      <form
        onSubmit={(e) => {
          e.preventDefault();
          send();
        }}
        className="flex items-center gap-2 border-t border-slate-800 pt-3"
      >
        <input
          value={input}
          onChange={(e) => setInput(e.target.value)}
          disabled={loading}
          maxLength={2000}
          placeholder="Ask a question about your course material… (follow-ups like “what are its units?” work too)"
          className="flex-1 rounded-xl border-2 border-slate-600 bg-slate-900 px-4 py-3 text-sm text-slate-100 shadow-inner placeholder:text-slate-400 focus:border-indigo-400 focus:outline-none focus:ring-2 focus:ring-indigo-500/30"
        />
        <button
          type="submit"
          disabled={loading || !input.trim()}
          aria-label="Send"
          className="flex h-12 w-12 shrink-0 items-center justify-center rounded-xl border-2 border-indigo-300/50 bg-gradient-to-r from-indigo-600 via-indigo-500 to-purple-600 text-white shadow-lg shadow-indigo-600/35 transition-all hover:scale-105 disabled:cursor-not-allowed disabled:opacity-40"
        >
          <Send className="h-5 w-5" />
        </button>
      </form>
    </div>
  );
};
