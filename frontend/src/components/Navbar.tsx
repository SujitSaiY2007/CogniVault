"use client";

import React from "react";
import { AlertTriangle, BarChart3, BookOpen, Bot, Brain, CheckSquare, Compass, LogOut, Network, User } from "lucide-react";
import { SystemHealth } from "@/lib/types";

interface NavbarProps {
  activeTab: string;
  setActiveTab: (tab: string) => void;
  health: SystemHealth | null;
  connection: "ok" | "waking" | "down";
  accountUsername: string;
  onLogout: () => void;
}

export const TABS = [
  { id: "tutor", label: "Tutor", icon: Bot },
  { id: "assessment", label: "Practice", icon: CheckSquare },
  { id: "mastery", label: "Progress", icon: BarChart3 },
  { id: "misconceptions", label: "Misconceptions", icon: AlertTriangle },
  { id: "recommendations", label: "Study Plan", icon: Compass },
  { id: "map", label: "Course Map", icon: Network },
  { id: "materials", label: "Materials", icon: BookOpen },
];

export const Navbar: React.FC<NavbarProps> = ({ activeTab, setActiveTab, health, connection, accountUsername, onLogout }) => {
  const status =
    connection === "waking"
      ? { cls: "bg-amber-50 text-amber-700 border-amber-300", dot: "bg-amber-400 animate-pulse", text: "Waking server…" }
      : connection === "down"
      ? { cls: "bg-rose-50 text-rose-700 border-rose-200", dot: "bg-rose-400", text: "Offline" }
      : { cls: "bg-emerald-50 text-emerald-700 border-emerald-200", dot: "bg-emerald-400", text: "Online" };
  const model = health?.model_provider?.active_provider;

  return (
    <header className="sticky top-0 z-40 w-full border-b border-slate-200 bg-[#fbfaf7]/90 backdrop-blur-md">
      <div className="mx-auto flex max-w-7xl flex-wrap items-center justify-between gap-3 px-4 py-3 sm:px-6">
        <div className="flex items-center gap-3">
          <div className="flex h-10 w-10 items-center justify-center rounded-2xl bg-gradient-to-br from-indigo-500 to-violet-600 shadow-lg shadow-indigo-200">
            <Brain className="h-5 w-5 text-white" />
          </div>
          <div>
            <span className="text-xl font-extrabold tracking-tight text-slate-900">CogniVault</span>
            <p className="hidden text-[11px] font-medium text-slate-600 sm:block">Evidence-first adaptive learning</p>
          </div>
        </div>

        <div className="order-2 flex items-center gap-2.5">
          <div className="flex items-center gap-2 rounded-xl border border-slate-200 bg-white px-3 py-2 text-xs font-bold text-slate-800">
            <User className="h-4 w-4 text-indigo-600" /> <span className="max-w-[110px] truncate">{accountUsername}</span>
          </div>
          <button type="button" onClick={onLogout} title="Sign out" className="flex items-center gap-1.5 rounded-xl border border-slate-200 px-3 py-2 text-xs font-bold text-slate-600 transition hover:border-rose-400 hover:text-rose-700">
            <LogOut className="h-4 w-4" />
            <span className="hidden sm:inline">Sign out</span>
          </button>
          <div className={`flex items-center gap-1.5 rounded-full border px-2.5 py-1 text-xs ${status.cls}`} title={model ? `Answer engine: ${model === "none" ? "extractive (no AI model configured)" : model}` : ""}>
            <span className={`h-2 w-2 rounded-full ${status.dot}`} />
            <span className="hidden font-mono font-medium md:inline">{status.text}</span>
          </div>
        </div>

        <nav className="order-3 flex w-full flex-wrap items-center gap-2 py-1">
          {TABS.map((tab) => {
            const Icon = tab.icon;
            const active = activeTab === tab.id;
            return (
              <button
                key={tab.id}
                type="button"
                onClick={() => setActiveTab(tab.id)}
                className={`flex items-center gap-2 rounded-xl border px-3 py-2 text-xs font-bold transition-all sm:text-sm ${
                  active
                    ? "border-indigo-600 bg-indigo-600 text-white shadow-md shadow-indigo-200"
                    : "border-slate-200 bg-white text-slate-700 hover:border-indigo-300 hover:text-indigo-700"
                }`}
              >
                <Icon className={`h-4 w-4 ${active ? "text-white" : "text-indigo-600"}`} />
                <span>{tab.label}</span>
              </button>
            );
          })}
        </nav>
      </div>
    </header>
  );
};
