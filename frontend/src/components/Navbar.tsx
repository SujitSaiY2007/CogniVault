"use client";

import React from "react";
import {
  BookOpen,
  Bot,
  Brain,
  CheckSquare,
  Compass,
  AlertTriangle,
  BarChart3,
  User,
  PlusCircle,
  Activity,
  LogOut,
} from "lucide-react";
import { SystemHealth } from "@/lib/types";

interface NavbarProps {
  activeTab: string;
  setActiveTab: (tab: string) => void;
  activeLearner: string;
  setActiveLearner: (learnerId: string) => void;
  learners: string[];
  health: SystemHealth | null;
  onOpenColdStart: () => void;
  accountUsername: string;
  onLogout: () => void;
}

export const Navbar: React.FC<NavbarProps> = ({
  activeTab,
  setActiveTab,
  activeLearner,
  setActiveLearner,
  learners,
  health,
  onOpenColdStart,
  accountUsername,
  onLogout,
}) => {
  const tabs = [
    { id: "tutor", label: "Evidence Tutor", icon: Bot },
    { id: "assessment", label: "Adaptive Assessment", icon: CheckSquare },
    { id: "mastery", label: "BKT Mastery", icon: BarChart3 },
    { id: "misconceptions", label: "Misconceptions", icon: AlertTriangle },
    { id: "recommendations", label: "Curriculum Roadmap", icon: Compass },
    { id: "materials", label: "Course Materials", icon: BookOpen },
  ];

  const isHealthy = health?.status === "healthy" || health?.status === "ok";

  return (
    <header className="sticky top-0 z-40 w-full border-b border-slate-800 bg-slate-950/95 backdrop-blur-md shadow-xl shadow-black/50">
      <div className="mx-auto flex max-w-7xl flex-wrap items-center justify-between gap-3 px-4 py-3 sm:px-6">
        {/* Brand */}
        <div className="flex items-center gap-3">
          <div className="flex h-10 w-10 items-center justify-center rounded-xl bg-gradient-to-tr from-indigo-600 via-indigo-500 to-cyan-400 shadow-lg shadow-indigo-500/30 border border-indigo-400/40">
            <Brain className="h-5 w-5 text-white" />
          </div>
          <div>
            <div className="flex items-center gap-2">
              <span className="text-xl font-extrabold tracking-tight text-white drop-shadow-sm">CogniVault</span>
              <span className="rounded-full bg-indigo-500/30 px-2 py-0.5 text-xs font-extrabold text-indigo-300 border border-indigo-400/50">
                AgentOS
              </span>
            </div>
            <p className="text-[11px] text-slate-300 font-medium hidden sm:block">Evidence-First Adaptive Learning</p>
          </div>
        </div>

        {/* Right Controls: Learner Selector + Dedicated Intake Button + Health Indicator */}
        <div className="flex items-center gap-2.5 order-2 sm:order-3">
          {/* Learner Selector Dropdown */}
          <div className="relative flex items-center gap-1.5 rounded-xl border-2 border-slate-600 bg-slate-850 bg-slate-900 hover:border-indigo-400 px-3 py-1.5 text-xs shadow-md transition-colors cursor-pointer focus-within:border-indigo-400 focus-within:ring-2 focus-within:ring-indigo-500/30">
            <User className="h-4 w-4 text-indigo-400 shrink-0" />
            <select
              id="navbar-learner-select"
              value={activeLearner}
              onChange={(e) => {
                const chosen = e.target.value;
                if (chosen === "__new__") {
                  onOpenColdStart();
                  e.target.value = activeLearner;
                } else {
                  setActiveLearner(chosen);
                }
              }}
              className="bg-transparent font-bold text-slate-100 focus:outline-none cursor-pointer max-w-[130px] truncate pr-4"
              title="Current learner profile"
            >
              {learners.map((lid) => (
                <option key={lid} value={lid} className="bg-slate-900 text-slate-100 font-sans font-medium">
                  {lid}
                </option>
              ))}
              <option value="__new__" className="bg-slate-900 text-indigo-300 font-bold">
                + New Learner Intake...
              </option>
            </select>
          </div>

          {/* Prominent High-Contrast New Learner Intake Button */}
          <button
            id="btn-navbar-new-intake"
            type="button"
            onClick={onOpenColdStart}
            className="flex items-center gap-2 rounded-xl bg-gradient-to-r from-indigo-600 via-indigo-500 to-purple-600 hover:from-indigo-500 hover:to-purple-500 text-white font-extrabold px-3.5 py-2 text-xs shadow-lg shadow-indigo-600/35 border-2 border-indigo-300/60 transition-all cursor-pointer hover:scale-105 active:scale-95"
            title="Start Cold-Start Diagnostic Intake for a new learner"
          >
            <PlusCircle className="h-4 w-4 text-indigo-100" />
            <span className="font-bold tracking-wide">New Learner Intake</span>
          </button>

          <div className="flex items-center gap-2 rounded-xl border border-slate-700 bg-slate-900 px-3 py-2 text-xs font-bold text-slate-200">
            <User className="h-4 w-4 text-indigo-400" /> <span className="max-w-[110px] truncate">{accountUsername}</span>
          </div>
          <button type="button" onClick={onLogout} title="Sign out" className="flex items-center gap-1.5 rounded-xl border border-slate-700 px-3 py-2 text-xs font-bold text-slate-300 transition hover:border-rose-400 hover:text-rose-300">
            <LogOut className="h-4 w-4" /><span className="hidden sm:inline">Sign out</span>
          </button>

          {/* Health Badge */}
          <div
            className={`flex items-center gap-1.5 rounded-full px-2.5 py-1 text-xs border ${
              isHealthy
                ? "bg-emerald-500/15 text-emerald-300 border-emerald-500/40"
                : "bg-amber-500/15 text-amber-300 border-amber-500/40"
            }`}
            title={`ChromaDB: ${health?.chroma_db?.indexed_units ?? 0} units | SQLite: ${health?.sqlite_db?.evidence_count ?? 0} evidence`}
          >
            <span
              className={`h-2 w-2 rounded-full ${
                isHealthy ? "bg-emerald-400 animate-pulse" : "bg-amber-400"
              }`}
            />
            <span className="hidden md:inline font-mono font-medium">
              {isHealthy ? "Online" : "Connecting"}
            </span>
          </div>
        </div>

        {/* Navigation Tabs (Always High-Contrast, Clearly Visible Buttons) */}
        <nav className="w-full sm:w-auto flex flex-wrap items-center gap-2 order-3 sm:order-2 py-1">
          {tabs.map((tab) => {
            const Icon = tab.icon;
            const isActive = activeTab === tab.id;
            return (
              <button
                key={tab.id}
                id={`nav-tab-${tab.id}`}
                type="button"
                onClick={() => setActiveTab(tab.id)}
                className={`flex items-center gap-2 px-3.5 py-2 text-xs sm:text-sm font-bold rounded-xl border-2 transition-all cursor-pointer ${
                  isActive
                    ? "bg-gradient-to-r from-indigo-600 via-indigo-500 to-purple-600 text-white border-indigo-300 shadow-lg shadow-indigo-500/40 ring-2 ring-indigo-400/30 scale-102"
                    : "bg-slate-850 bg-slate-800/90 text-slate-100 hover:bg-slate-700/90 hover:text-white border-slate-600 hover:border-indigo-400 shadow-md shadow-black/40"
                }`}
              >
                <Icon className={`h-4 w-4 ${isActive ? "text-white" : "text-indigo-400"}`} />
                <span>{tab.label}</span>
              </button>
            );
          })}
        </nav>
      </div>
    </header>
  );
};
