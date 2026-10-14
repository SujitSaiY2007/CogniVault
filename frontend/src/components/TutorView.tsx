"use client";

import React, { useState } from "react";
import { Citation, TutorResponse } from "@/lib/types";
import { api } from "@/lib/api";
import {
  AlertCircle,
  Bot,
  CheckCircle2,
  ChevronDown,
  ChevronUp,
  CornerDownLeft,
  FileText,
  MapPin,
  Send,
  Sparkles,
  User,
} from "lucide-react";

interface Message {
  id: string;
  sender: "user" | "tutor";
  text: string;
  response?: TutorResponse;
}

interface TutorViewProps {
  onOpenCitation: (cit: Citation) => void;
}

export const TutorView: React.FC<TutorViewProps> = ({ onOpenCitation }) => {
  const [messages, setMessages] = useState<Message[]>([
    {
      id: "init",
      sender: "tutor",
      text: "Hello! I am your CogniVault Evidence Tutor. Every answer I provide is strictly grounded in your indexed textbooks, slides, and transcripts with exact physical locators (pages, slides, timestamps). If an answer cannot be proven from your course materials, I will explicitly abstain.",
    },
  ]);
  const [input, setInput] = useState("");
  const [loading, setLoading] = useState(false);
  const [showSteps, setShowSteps] = useState<Record<string, boolean>>({});

  const sampleQueries = [
    { label: "Newton's Second Law", query: "What is Newton's second law of motion?" },
    { label: "Snell's Law (Optics)", query: "Explain Snell's law of refraction and the wave speed equation." },
    { label: "Off-Material Abstention Test", query: "What were the primary economic causes of the French Revolution in 1789?" },
  ];

  const handleSend = async (queryText?: string) => {
    const q = (queryText || input).trim();
    if (!q || loading) return;

    const userMsgId = `user_${Date.now()}`;
    const tutorMsgId = `tutor_${Date.now()}`;

    setMessages((prev) => [...prev, { id: userMsgId, sender: "user", text: q }]);
    setInput("");
    setLoading(true);

    try {
      const resp = await api.queryTutor(q);
      setMessages((prev) => [
        ...prev,
        {
          id: tutorMsgId,
          sender: "tutor",
          text: resp.answer,
          response: resp,
        },
      ]);
    } catch (err: any) {
      setMessages((prev) => [
        ...prev,
        {
          id: tutorMsgId,
          sender: "tutor",
          text: `Error contacting tutor service: ${err.message}`,
        },
      ]);
    } finally {
      setLoading(false);
    }
  };

  const toggleSteps = (msgId: string) => {
    setShowSteps((prev) => ({ ...prev, [msgId]: !prev[msgId] }));
  };

  return (
    <div className="flex flex-col h-[calc(100vh-130px)] max-w-5xl mx-auto p-4 sm:p-6">
      {/* Top Header */}
      <div className="flex items-center justify-between pb-4 border-b border-slate-800">
        <div>
          <h2 className="text-lg font-bold text-slate-100 flex items-center gap-2">
            <Bot className="h-5 w-5 text-indigo-400" />
            <span>Course-Grounded Evidence Tutor</span>
          </h2>
          <p className="text-xs text-slate-400">
            Guaranteed fail-closed abstention & physical citations (PDF pages, slide numbers, video timestamps).
          </p>
        </div>
      </div>

      {/* Suggested Quick Prompts */}
      <div className="flex items-center gap-2 py-3 overflow-x-auto text-xs">
        <span className="text-slate-500 text-[11px] font-semibold uppercase tracking-wider shrink-0">
          Try:
        </span>
        {sampleQueries.map((s, idx) => (
          <button
            key={idx}
            onClick={() => handleSend(s.query)}
            disabled={loading}
            className="shrink-0 rounded-full border border-slate-800 bg-slate-900/80 px-3 py-1 text-slate-300 hover:border-indigo-500/50 hover:text-indigo-300 hover:bg-slate-800 transition-all text-xs"
          >
            {s.label}
          </button>
        ))}
      </div>

      {/* Chat Messages Log */}
      <div className="flex-1 overflow-y-auto space-y-4 py-4 pr-1">
        {messages.map((m) => {
          const isUser = m.sender === "user";
          const resp = m.response;
          const isUnsupported = resp && resp.support_status === "unsupported";

          return (
            <div
              key={m.id}
              className={`flex gap-3 ${isUser ? "justify-end" : "justify-start"}`}
            >
              {!isUser && (
                <div className="flex h-8 w-8 shrink-0 items-center justify-center rounded-xl bg-indigo-600/20 text-indigo-400 border border-indigo-500/20 mt-1">
                  <Bot className="h-4 w-4" />
                </div>
              )}

              <div
                className={`relative max-w-2xl rounded-2xl p-4 sm:p-5 text-sm leading-relaxed ${
                  isUser
                    ? "bg-indigo-600 text-white rounded-br-none shadow-md shadow-indigo-600/20"
                    : isUnsupported
                    ? "rounded-bl-none border border-amber-500/30 bg-amber-950/20 text-amber-200"
                    : "rounded-bl-none border border-slate-800 bg-slate-900 text-slate-200"
                }`}
              >
                {/* Unsupported Abstention Warning Banner */}
                {isUnsupported && (
                  <div className="flex items-center gap-2 mb-3 rounded-xl bg-amber-500/10 border border-amber-500/30 p-2.5 text-xs font-semibold text-amber-300">
                    <AlertCircle className="h-4 w-4 shrink-0 text-amber-400" />
                    <span>Fail-Closed Abstention: Course does not contain sufficient evidence to answer.</span>
                  </div>
                )}

                {/* Grounded Success Header */}
                {!isUser && resp && resp.is_grounded && (
                  <div className="flex items-center justify-between gap-2 mb-2 pb-2 border-b border-slate-800/80 text-xs">
                    <span className="flex items-center gap-1.5 font-semibold text-emerald-400">
                      <CheckCircle2 className="h-3.5 w-3.5" />
                      <span>Course-Grounded Answer</span>
                    </span>
                    <span className="text-slate-400 font-mono text-[11px]">
                      Confidence: {(resp.confidence * 100).toFixed(0)}%
                    </span>
                  </div>
                )}

                {/* Message Text */}
                <div className="whitespace-pre-wrap">{m.text}</div>

                {/* Clickable Citations List */}
                {!isUser && resp && resp.citations && resp.citations.length > 0 && (
                  <div className="mt-4 pt-3 border-t border-slate-800 space-y-2">
                    <div className="text-[11px] font-semibold uppercase tracking-wider text-slate-400 flex items-center gap-1">
                      <FileText className="h-3 w-3 text-indigo-400" />
                      <span>Exact Physical Citations ({resp.citations.length}):</span>
                    </div>
                    <div className="flex flex-wrap gap-2">
                      {resp.citations.map((c, cIdx) => {
                        const loc = c.location || {};
                        let locText = "Locator";
                        if (loc.page !== undefined) locText = `Page ${loc.page}`;
                        else if (loc.slide !== undefined) locText = `Slide ${loc.slide}`;
                        else if (loc.timestamp !== undefined) locText = `Timestamp ${loc.timestamp}`;

                        return (
                          <button
                            key={cIdx}
                            onClick={() => onOpenCitation(c)}
                            className="flex items-center gap-1.5 px-2.5 py-1 rounded-lg bg-indigo-500/10 hover:bg-indigo-500/20 text-indigo-300 border border-indigo-500/30 text-xs font-medium transition-colors"
                            title="Click to inspect exact excerpt & file location"
                          >
                            <MapPin className="h-3 w-3 text-indigo-400" />
                            <span>{c.source_title || c.source_id}: {locText}</span>
                          </button>
                        );
                      })}
                    </div>
                  </div>
                )}

                {/* Reasoning Steps Accordion */}
                {!isUser && resp && resp.reasoning_steps && resp.reasoning_steps.length > 0 && (
                  <div className="mt-3">
                    <button
                      onClick={() => toggleSteps(m.id)}
                      className="flex items-center gap-1 text-[11px] text-slate-400 hover:text-slate-200 transition-colors"
                    >
                      <span>Reasoning Verification Trace</span>
                      {showSteps[m.id] ? <ChevronUp className="h-3 w-3" /> : <ChevronDown className="h-3 w-3" />}
                    </button>
                    {showSteps[m.id] && (
                      <div className="mt-2 rounded-xl border border-slate-800 bg-slate-950 p-3 space-y-1 text-xs font-mono text-slate-400">
                        {resp.reasoning_steps.map((st, sIdx) => (
                          <div key={sIdx} className="flex gap-2">
                            <span className="text-slate-600">{sIdx + 1}.</span>
                            <span>{st}</span>
                          </div>
                        ))}
                      </div>
                    )}
                  </div>
                )}
              </div>

              {isUser && (
                <div className="flex h-8 w-8 shrink-0 items-center justify-center rounded-xl bg-slate-800 text-slate-300 border border-slate-700 mt-1">
                  <User className="h-4 w-4" />
                </div>
              )}
            </div>
          );
        })}

        {loading && (
          <div className="flex gap-3 justify-start items-center">
            <div className="flex h-8 w-8 shrink-0 items-center justify-center rounded-xl bg-indigo-600/20 text-indigo-400 border border-indigo-500/20">
              <Bot className="h-4 w-4" />
            </div>
            <div className="rounded-2xl rounded-bl-none border border-slate-800 bg-slate-900 px-4 py-3 text-xs text-slate-400 flex items-center gap-2">
              <div className="h-2 w-2 rounded-full bg-indigo-400 animate-pulse" />
              <span>Evaluating evidence sufficiency & verifying citations...</span>
            </div>
          </div>
        )}
      </div>

      {/* Input Bar */}
      <div className="pt-3 border-t border-slate-800">
        <form
          onSubmit={(e) => {
            e.preventDefault();
            handleSend();
          }}
          className="flex items-center gap-2"
        >
          <input
            type="text"
            value={input}
            onChange={(e) => setInput(e.target.value)}
            disabled={loading}
            placeholder="Ask a question grounded in your course materials..."
            className="flex-1 rounded-xl border border-slate-700 bg-slate-900 px-4 py-3 text-sm text-slate-100 placeholder:text-slate-500 focus:outline-none focus:border-indigo-500 focus:ring-1 focus:ring-indigo-500"
          />
          <button
            type="submit"
            disabled={loading || !input.trim()}
            className="flex h-11 w-11 shrink-0 items-center justify-center rounded-xl bg-indigo-600 hover:bg-indigo-500 text-white shadow-md shadow-indigo-600/30 transition-all disabled:opacity-40"
          >
            <Send className="h-4 w-4" />
          </button>
        </form>
      </div>
    </div>
  );
};
