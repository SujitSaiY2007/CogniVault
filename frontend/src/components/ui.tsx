"use client";

import React from "react";
import { AlertCircle, Loader2, RefreshCw } from "lucide-react";

export const Panel: React.FC<{ className?: string; children: React.ReactNode }> = ({ className = "", children }) => (
  <div className={`rounded-3xl border border-slate-200 bg-white p-5 shadow-[0_18px_60px_-34px_rgba(55,65,120,.28)] sm:p-6 ${className}`}>{children}</div>
);

export const SectionHeader: React.FC<{ icon: React.ElementType; title: string; subtitle?: string; right?: React.ReactNode }> = ({
  icon: Icon,
  title,
  subtitle,
  right,
}) => (
  <div className="flex flex-col gap-3 border-b border-slate-200 pb-4 sm:flex-row sm:items-center sm:justify-between">
    <div>
      <h2 className="flex items-center gap-2 text-lg font-bold text-slate-900">
        <Icon className="h-5 w-5 text-indigo-600" />
        <span>{title}</span>
      </h2>
      {subtitle && <p className="mt-0.5 text-xs text-slate-500">{subtitle}</p>}
    </div>
    {right}
  </div>
);

export const ErrorBanner: React.FC<{ message: string; onRetry?: () => void }> = ({ message, onRetry }) => (
  <div role="alert" className="flex items-start justify-between gap-3 rounded-xl border border-rose-200 bg-rose-50 p-3 text-sm text-rose-700">
    <span className="flex items-start gap-2">
      <AlertCircle className="mt-0.5 h-4 w-4 shrink-0 text-rose-600" />
      <span>{message}</span>
    </span>
    {onRetry && (
      <button onClick={onRetry} className="flex shrink-0 items-center gap-1 rounded-lg border border-rose-200 px-2 py-1 text-xs font-bold hover:bg-rose-50">
        <RefreshCw className="h-3 w-3" /> Retry
      </button>
    )}
  </div>
);

export const Spinner: React.FC<{ label?: string }> = ({ label = "Loading…" }) => (
  <div className="flex items-center gap-2 text-sm text-slate-500">
    <Loader2 className="h-4 w-4 animate-spin text-indigo-600" />
    <span>{label}</span>
  </div>
);

export const EmptyState: React.FC<{ icon: React.ElementType; title: string; body: string; action?: React.ReactNode }> = ({
  icon: Icon,
  title,
  body,
  action,
}) => (
  <div className="flex flex-col items-center justify-center rounded-2xl border border-dashed border-slate-200 p-10 text-center">
    <Icon className="h-8 w-8 text-slate-500" />
    <p className="mt-3 text-sm font-bold text-slate-800">{title}</p>
    <p className="mt-1 max-w-md text-xs text-slate-500">{body}</p>
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
  <div className="relative h-2.5 w-full overflow-hidden rounded-full bg-slate-50">
    {before !== undefined && before !== null && (
      <div className="absolute inset-y-0 left-0 rounded-full bg-slate-300" style={{ width: `${Math.round(before * 100)}%` }} />
    )}
    <div className={`absolute inset-y-0 left-0 rounded-full transition-all duration-700 ${masteryColor(p)}`} style={{ width: `${Math.round(p * 100)}%`, opacity: 0.9 }} />
  </div>
);

export const PrimaryButton: React.FC<React.ButtonHTMLAttributes<HTMLButtonElement>> = ({ className = "", children, ...rest }) => (
  <button
    {...rest}
    className={`inline-flex items-center justify-center gap-2 rounded-xl bg-indigo-600 px-4 py-2.5 text-sm font-bold text-white shadow-md shadow-indigo-200 transition-all hover:bg-indigo-700 disabled:cursor-not-allowed disabled:opacity-40 ${className}`}
  >
    {children}
  </button>
);

export const GhostButton: React.FC<React.ButtonHTMLAttributes<HTMLButtonElement>> = ({ className = "", children, ...rest }) => (
  <button
    {...rest}
    className={`inline-flex items-center justify-center gap-2 rounded-xl border border-slate-200 bg-white px-3.5 py-2 text-xs font-bold text-slate-700 transition-colors hover:border-indigo-300 hover:text-indigo-700 disabled:opacity-40 ${className}`}
  >
    {children}
  </button>
);

export const Select: React.FC<React.SelectHTMLAttributes<HTMLSelectElement>> = ({ className = "", children, ...rest }) => (
  <select
    {...rest}
    className={`rounded-xl border border-slate-200 bg-[#fbfaf7] px-3 py-2 text-xs font-semibold text-slate-800 focus:border-indigo-400 focus:outline-none focus:ring-4 focus:ring-indigo-100 ${className}`}
  >
    {children}
  </select>
);
