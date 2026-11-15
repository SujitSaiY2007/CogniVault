"use client";

import React from "react";
import { AlertCircle, Loader2, RefreshCw } from "lucide-react";

export const Panel: React.FC<{ className?: string; children: React.ReactNode }> = ({ className = "", children }) => (
  <div className={`rounded-2xl border border-slate-800 bg-slate-900/70 p-5 ${className}`}>{children}</div>
);

export const SectionHeader: React.FC<{ icon: React.ElementType; title: string; subtitle?: string; right?: React.ReactNode }> = ({
  icon: Icon,
  title,
  subtitle,
  right,
}) => (
  <div className="flex flex-col gap-3 border-b border-slate-800 pb-4 sm:flex-row sm:items-center sm:justify-between">
    <div>
      <h2 className="flex items-center gap-2 text-lg font-bold text-slate-100">
        <Icon className="h-5 w-5 text-indigo-400" />
        <span>{title}</span>
      </h2>
      {subtitle && <p className="mt-0.5 text-xs text-slate-400">{subtitle}</p>}
    </div>
    {right}
  </div>
);

export const ErrorBanner: React.FC<{ message: string; onRetry?: () => void }> = ({ message, onRetry }) => (
  <div role="alert" className="flex items-start justify-between gap-3 rounded-xl border border-rose-500/30 bg-rose-950/30 p-3 text-sm text-rose-200">
    <span className="flex items-start gap-2">
      <AlertCircle className="mt-0.5 h-4 w-4 shrink-0 text-rose-400" />
      <span>{message}</span>
    </span>
    {onRetry && (
      <button onClick={onRetry} className="flex shrink-0 items-center gap-1 rounded-lg border border-rose-400/40 px-2 py-1 text-xs font-bold hover:bg-rose-500/10">
        <RefreshCw className="h-3 w-3" /> Retry
      </button>
    )}
  </div>
);

export const Spinner: React.FC<{ label?: string }> = ({ label = "Loading…" }) => (
  <div className="flex items-center gap-2 text-sm text-slate-400">
    <Loader2 className="h-4 w-4 animate-spin text-indigo-400" />
    <span>{label}</span>
  </div>
);

export const EmptyState: React.FC<{ icon: React.ElementType; title: string; body: string; action?: React.ReactNode }> = ({
  icon: Icon,
  title,
  body,
  action,
}) => (
  <div className="flex flex-col items-center justify-center rounded-2xl border border-dashed border-slate-700 p-10 text-center">
    <Icon className="h-8 w-8 text-slate-500" />
    <p className="mt-3 text-sm font-bold text-slate-200">{title}</p>
    <p className="mt-1 max-w-md text-xs text-slate-400">{body}</p>
    {action && <div className="mt-4">{action}</div>}
  </div>
);

export function masteryColor(p: number) {
  if (p >= 0.85) return "bg-emerald-500";
  if (p >= 0.7) return "bg-teal-500";
  if (p >= 0.4) return "bg-amber-500";
  return "bg-rose-500";
}

export const MasteryBar: React.FC<{ p: number; before?: number | null }> = ({ p, before }) => (
  <div className="relative h-2.5 w-full overflow-hidden rounded-full bg-slate-800">
    {before !== undefined && before !== null && (
      <div className="absolute inset-y-0 left-0 rounded-full bg-slate-600" style={{ width: `${Math.round(before * 100)}%` }} />
    )}
    <div className={`absolute inset-y-0 left-0 rounded-full transition-all duration-700 ${masteryColor(p)}`} style={{ width: `${Math.round(p * 100)}%`, opacity: 0.9 }} />
  </div>
);

export const PrimaryButton: React.FC<React.ButtonHTMLAttributes<HTMLButtonElement>> = ({ className = "", children, ...rest }) => (
  <button
    {...rest}
    className={`inline-flex items-center justify-center gap-2 rounded-xl border-2 border-indigo-300/50 bg-gradient-to-r from-indigo-600 via-indigo-500 to-purple-600 px-4 py-2.5 text-sm font-bold text-white shadow-lg shadow-indigo-600/30 transition-all hover:from-indigo-500 hover:to-purple-500 disabled:cursor-not-allowed disabled:opacity-40 ${className}`}
  >
    {children}
  </button>
);

export const GhostButton: React.FC<React.ButtonHTMLAttributes<HTMLButtonElement>> = ({ className = "", children, ...rest }) => (
  <button
    {...rest}
    className={`inline-flex items-center justify-center gap-2 rounded-xl border-2 border-slate-600 bg-slate-800 px-3.5 py-2 text-xs font-bold text-slate-100 transition-colors hover:border-indigo-400 hover:bg-slate-700 disabled:opacity-40 ${className}`}
  >
    {children}
  </button>
);

export const Select: React.FC<React.SelectHTMLAttributes<HTMLSelectElement>> = ({ className = "", children, ...rest }) => (
  <select
    {...rest}
    className={`rounded-xl border-2 border-slate-600 bg-slate-900 px-3 py-2 text-xs font-semibold text-slate-100 focus:border-indigo-400 focus:outline-none ${className}`}
  >
    {children}
  </select>
);
