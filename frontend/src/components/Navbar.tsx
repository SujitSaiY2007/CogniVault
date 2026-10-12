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
}

export const Navbar: React.FC<NavbarProps> = ({
  activeTab,
  setActiveTab,
  activeLearner,
  setActiveLearner,
  learners,
  health,
  onOpenColdStart,
}) => {
  const tabs = [
    { id: "tutor", label: "Evidence Tutor", icon: Bot },
    { id: "assessment", label: "Adaptive Practice", icon: CheckSquare },
    { id: "mastery", label: "BKT Mastery", icon: BarChart3 },
    { id: "misconceptions", label: "Misconceptions", icon: AlertTriangle },
    { id: "recommendations", label: "Curriculum Roadmap", icon: Compass },
    { id: "materials", label: "Course Materials", icon: BookOpen },
  ];

  const isHealthy = health?.status === "healthy" || health?.status === "ok";

  return (
    <header className="sticky top-0 z-40 w-full border-b border-slate-800 bg-slate-950/80 backdrop-blur-md">
      <div className="mx-auto flex max-w-7xl items-center justify-between px-4 py-3 sm:px-6">
        {/* Brand */}
        <div className="flex items-center gap-3">
          <div className="flex h-10 w-10 items-center justify-center rounded-xl bg-gradient-to-tr from-indigo-600 via-indigo-500 to-cyan-400 shadow-lg shadow-indigo-500/20">
            <Brain className="h-5 w-5 text-white" />
          </div>
          <div>
            <div className="flex items-center gap-2">
              <span className="text-xl font-bold tracking-tight text-white">CogniVault</span>
              <span className="rounded-full bg-indigo-500/10 px-2 py-0.5 text-xs font-semibold text-indigo-400 border border-indigo-500/20">
                AgentOS
              </span>
            </div>
            <p className="text-xs text-slate-400 hidden sm:block">Evidence-First Adaptive Learning</p>
          </div>
        </div>

        {/* Navigation Tabs (Desktop) */}
        <nav className="hidden lg:flex items-center gap-1">
          {tabs.map((tab) => {
            const Icon = tab.icon;
            const isActive = activeTab === tab.id;
            return (
              <button
                key={tab.id}
                onClick={() => setActiveTab(tab.id)}
                className={`flex items-center gap-2 px-3 py-2 text-sm font-medium rounded-lg transition-all ${
                  isActive
                    ? "bg-indigo-600 text-white shadow-md shadow-indigo-600/25"
                    : "text-slate-400 hover:text-slate-200 hover:bg-slate-900"
                }`}
              >
                <Icon className="h-4 w-4" />
                <span>{tab.label}</span>
              </button>
            );
          })}
        </nav>

        {/* Right Controls: Learner Selector + Health Indicator */}
        <div className="flex items-center gap-3">
          {/* Learner Selector */}
          <div className="flex items-center gap-1.5 rounded-lg border border-slate-800 bg-slate-900/90 px-2.5 py-1.5 text-xs shadow-inner">
            <User className="h-3.5 w-3.5 text-indigo-400" />
            <select
              value={activeLearner}
              onChange={(e) => {
                if (e.target.value === "__new__") {
                  onOpenColdStart();
                } else {
                  setActiveLearner(e.target.value);
                }
              }}
              className="bg-transparent text-slate-200 focus:outline-none cursor-pointer"
            >
              {learners.map((lid) => (
                <option key={lid} value={lid} className="bg-slate-900 text-slate-100">
                  {lid}
                </option>
              ))}
              <option value="__new__" className="bg-slate-900 text-indigo-400 font-semibold">
                + New Learner Intake
              </option>
            </select>
          </div>

          {/* Quick Intake Button */}
          <button
            onClick={onOpenColdStart}
            className="flex items-center gap-1.5 rounded-lg bg-indigo-500/10 hover:bg-indigo-500/20 px-2.5 py-1.5 text-xs font-medium text-indigo-400 border border-indigo-500/20 transition-colors"
            title="Start Cold-Start Intake for fresh learner"
          >
            <PlusCircle className="h-3.5 w-3.5" />
            <span className="hidden sm:inline">Intake</span>
          </button>

          {/* Health Badge */}
          <div
            className={`flex items-center gap-1.5 rounded-full px-2.5 py-1 text-xs border ${
              isHealthy
                ? "bg-emerald-500/10 text-emerald-400 border-emerald-500/20"
                : "bg-amber-500/10 text-amber-400 border-amber-500/20"
            }`}
            title={`ChromaDB: ${health?.chroma_db?.indexed_units ?? 0} units | SQLite: ${health?.sqlite_db?.evidence_count ?? 0} evidence`}
          >
            <span
              className={`h-1.5 w-1.5 rounded-full ${
                isHealthy ? "bg-emerald-400 animate-pulse" : "bg-amber-400"
              }`}
            />
            <span className="hidden md:inline font-mono">
              {isHealthy ? "API Online" : "Connecting..."}
            </span>
          </div>
        </div>
      </div>

      {/* Mobile Navigation Tabs */}
      <div className="flex lg:hidden overflow-x-auto px-4 py-2 border-t border-slate-900 gap-1 bg-slate-950">
        {tabs.map((tab) => {
          const Icon = tab.icon;
          const isActive = activeTab === tab.id;
          return (
            <button
              key={tab.id}
              onClick={() => setActiveTab(tab.id)}
              className={`flex shrink-0 items-center gap-1.5 px-3 py-1.5 text-xs font-medium rounded-lg transition-all ${
                isActive
                  ? "bg-indigo-600 text-white"
                  : "text-slate-400 hover:text-slate-200 hover:bg-slate-900"
              }`}
            >
              <Icon className="h-3.5 w-3.5" />
              <span>{tab.label}</span>
            </button>
          );
        })}
      </div>
    </header>
  );
};
