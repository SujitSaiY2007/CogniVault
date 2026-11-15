"use client";

import React from "react";
import { AlertTriangle, BarChart3, BookOpen, Bot, Brain, CheckSquare, Compass, GraduationCap, LogOut, Network, User } from "lucide-react";
import { SystemHealth } from "@/lib/types";

interface NavbarProps {
  activeTab: string;
  setActiveTab: (tab: string) => void;
  health: SystemHealth | null;
  connection: "ok" | "waking" | "down";
  onOpenColdStart: () => void;
  accountUsername: string;
  onLogout: () => void;
}

export const TABS = [
  { id: "tutor", label: "Tutor", icon: Bot },
  { id: "assessment", label: "Practice & Exams", icon: CheckSquare },
  { id: "mastery", label: "Progress", icon: BarChart3 },
  { id: "misconceptions", label: "Misconceptions", icon: AlertTriangle },
  { id: "recommendations", label: "Study Plan", icon: Compass },
  { id: "map", label: "Course Map", icon: Network },
  { id: "materials", label: "Materials", icon: BookOpen },
];

export const Navbar: React.FC<NavbarProps> = ({ activeTab, setActiveTab, health, connection, onOpenColdStart, accountUsername, onLogout }) => {
  const status =
    connection === "waking"
      ? { cls: "bg-amber-500/15 text-amber-300 border-amber-500/40", dot: "bg-amber-400 animate-pulse", text: "Waking server…" }
      : connection === "down"
      ? { cls: "bg-rose-500/15 text-rose-300 border-rose-500/40", dot: "bg-rose-400", text: "Offline" }
      : { cls: "bg-emerald-500/15 text-emerald-300 border-emerald-500/40", dot: "bg-emerald-400", text: "Online" };
  const model = health?.model_provider?.active_provider;

  return (
    <header className="sticky top-0 z-40 w-full border-b border-slate-800 bg-slate-950/95 shadow-xl shadow-black/50 backdrop-blur-md">
      <div className="mx-auto flex max-w-7xl flex-wrap items-center justify-between gap-3 px-4 py-3 sm:px-6">
        <div className="flex items-center gap-3">
          <div className="flex h-10 w-10 items-center justify-center rounded-xl border border-indigo-400/40 bg-gradient-to-tr from-indigo-600 via-indigo-500 to-cyan-400 shadow-lg shadow-indigo-500/30">
            <Brain className="h-5 w-5 text-white" />
          </div>
          <div>
            <span className="text-xl font-extrabold tracking-tight text-white">CogniVault</span>
            <p className="hidden text-[11px] font-medium text-slate-300 sm:block">Evidence-first adaptive learning</p>
          </div>
        </div>

        <div className="order-2 flex items-center gap-2.5 sm:order-3">
          <button
            type="button"
            onClick={onOpenColdStart}
            className="flex items-center gap-2 rounded-xl border-2 border-indigo-300/60 bg-gradient-to-r from-indigo-600 via-indigo-500 to-purple-600 px-3.5 py-2 text-xs font-extrabold text-white shadow-lg shadow-indigo-600/35 transition-all hover:scale-105"
            title="Rate what you know and take a short placement quiz"
          >
            <GraduationCap className="h-4 w-4" />
            <span className="hidden sm:inline">Placement check</span>
          </button>
          <div className="flex items-center gap-2 rounded-xl border border-slate-700 bg-slate-900 px-3 py-2 text-xs font-bold text-slate-200">
            <User className="h-4 w-4 text-indigo-400" /> <span className="max-w-[110px] truncate">{accountUsername}</span>
          </div>
          <button type="button" onClick={onLogout} title="Sign out" className="flex items-center gap-1.5 rounded-xl border border-slate-700 px-3 py-2 text-xs font-bold text-slate-300 transition hover:border-rose-400 hover:text-rose-300">
            <LogOut className="h-4 w-4" />
            <span className="hidden sm:inline">Sign out</span>
          </button>
          <div className={`flex items-center gap-1.5 rounded-full border px-2.5 py-1 text-xs ${status.cls}`} title={model ? `Answer engine: ${model === "none" ? "extractive (no AI model configured)" : model}` : ""}>
            <span className={`h-2 w-2 rounded-full ${status.dot}`} />
            <span className="hidden font-mono font-medium md:inline">{status.text}</span>
          </div>
        </div>

        <nav className="order-3 flex w-full flex-wrap items-center gap-2 py-1 sm:order-2 sm:w-auto">
          {TABS.map((tab) => {
            const Icon = tab.icon;
            const active = activeTab === tab.id;
            return (
              <button
                key={tab.id}
                type="button"
                onClick={() => setActiveTab(tab.id)}
                className={`flex items-center gap-2 rounded-xl border-2 px-3 py-2 text-xs font-bold transition-all sm:text-sm ${
                  active
                    ? "border-indigo-300 bg-gradient-to-r from-indigo-600 via-indigo-500 to-purple-600 text-white shadow-lg shadow-indigo-500/40"
                    : "border-slate-600 bg-slate-800/90 text-slate-100 shadow-md shadow-black/40 hover:border-indigo-400 hover:bg-slate-700/90"
                }`}
              >
                <Icon className={`h-4 w-4 ${active ? "text-white" : "text-indigo-400"}`} />
                <span>{tab.label}</span>
              </button>
            );
          })}
        </nav>
      </div>
    </header>
  );
};
