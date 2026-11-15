"use client";

import React, { useEffect, useState } from "react";
import Link from "next/link";
import { useRouter } from "next/navigation";
import { Brain, Eye, EyeOff, ArrowRight, ShieldCheck } from "lucide-react";
import { authApi } from "@/lib/api";

export default function LoginPage() {
  const router = useRouter();
  const [search, setSearch] = useState(() => new URLSearchParams(""));
  const [mode, setMode] = useState("login");
  useEffect(() => {
    // Read the query string after mount so server and client render the same HTML.
    const params = new URLSearchParams(window.location.search);
    setSearch(params);
    if (params.get("mode") === "signup") setMode("signup");
  }, []);
  const [username, setUsername] = useState("");
  const [password, setPassword] = useState("");
  const [showPassword, setShowPassword] = useState(false);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState("");

  async function submit(e: React.FormEvent) {
    e.preventDefault(); setError(""); setBusy(true);
    try {
      const session = mode === "signup" ? await authApi.signup(username.trim(), password) : await authApi.login(username.trim(), password);
      window.localStorage.setItem("cognivault_session", session.access_token);
      window.localStorage.setItem("cognivault_username", session.username);
      window.localStorage.setItem("cognivault_learner_id", session.learner_id);
      const nextTab = search.get("next"); router.replace(nextTab ? `/workspace?tab=${encodeURIComponent(nextTab)}` : "/workspace");
    } catch (err) {
      setError(err instanceof Error ? err.message : "Unable to continue. Please try again.");
    } finally { setBusy(false); }
  }

  return <main className="min-h-screen bg-[#fbfaf7] text-slate-900">
    <header className="mx-auto flex max-w-7xl items-center justify-between px-5 py-5 sm:px-8">
      <Link href="/" className="flex items-center gap-3"><span className="flex h-11 w-11 items-center justify-center rounded-2xl bg-gradient-to-br from-indigo-500 to-violet-600 text-white shadow-lg"><Brain className="h-6 w-6"/></span><span><b className="block text-xl font-extrabold tracking-tight">CogniVault</b><small className="text-xs text-slate-500">Evidence-first adaptive learning</small></span></Link>
      <Link href="/" className="text-sm font-bold text-slate-600 hover:text-indigo-600">Back to home</Link>
    </header>
    <section className="mx-auto grid max-w-6xl items-center gap-12 px-5 py-10 sm:px-8 md:py-16 lg:grid-cols-2">
      <div className="hidden lg:block">
        <p className="inline-flex rounded-full border border-indigo-100 bg-white px-3 py-2 text-xs font-extrabold text-indigo-700">YOUR LEARNING SPACE</p>
        <h1 className="mt-6 max-w-xl text-5xl font-black leading-tight tracking-[-.04em]">Your course material.<br/><span className="text-indigo-600">Your progress.</span><br/>Your space.</h1>
        <p className="mt-5 max-w-lg text-lg leading-8 text-slate-600">Sign in to return to your learning workspace, or create a username to start building your own learning history.</p>
        <div className="mt-8 flex items-center gap-3 text-sm font-semibold text-slate-600"><ShieldCheck className="h-5 w-5 text-emerald-600"/> Username and password. No email required.</div>
      </div>
      <div className="mx-auto w-full max-w-md rounded-[28px] border border-slate-200 bg-white p-6 shadow-[0_24px_80px_-32px_rgba(55,65,120,.25)] sm:p-9">
        <div className="mb-7"><p className="text-xs font-extrabold uppercase tracking-[.18em] text-indigo-600">{mode === "signup" ? "Create your account" : "Welcome back"}</p><h2 className="mt-2 text-3xl font-black tracking-tight">{mode === "signup" ? "Start learning" : "Log in to CogniVault"}</h2><p className="mt-2 text-sm leading-6 text-slate-500">{mode === "signup" ? "Choose a username you can remember and a strong password." : "Use the username and password you created."}</p></div>
        <form onSubmit={submit} className="space-y-5">
          <div><label htmlFor="username" className="mb-2 block text-sm font-bold text-slate-700">Username</label><input id="username" autoComplete="username" required minLength={3} maxLength={32} pattern="[A-Za-z0-9_.\-]+" value={username} onChange={e=>setUsername(e.target.value)} placeholder="e.g. learner_sai" className="w-full rounded-xl border border-slate-200 bg-[#fbfaf7] px-4 py-3.5 text-sm outline-none transition focus:border-indigo-400 focus:ring-4 focus:ring-indigo-100"/></div>
          <div><label htmlFor="password" className="mb-2 block text-sm font-bold text-slate-700">Password</label><div className="relative"><input id="password" type={showPassword?"text":"password"} autoComplete={mode==="signup"?"new-password":"current-password"} required minLength={8} maxLength={128} value={password} onChange={e=>setPassword(e.target.value)} placeholder="At least 8 characters" className="w-full rounded-xl border border-slate-200 bg-[#fbfaf7] px-4 py-3.5 pr-12 text-sm outline-none transition focus:border-indigo-400 focus:ring-4 focus:ring-indigo-100"/><button type="button" aria-label={showPassword?"Hide password":"Show password"} onClick={()=>setShowPassword(v=>!v)} className="absolute right-3 top-1/2 -translate-y-1/2 rounded-lg p-2 text-slate-400 hover:bg-slate-100">{showPassword?<EyeOff className="h-4 w-4"/>:<Eye className="h-4 w-4"/>}</button></div></div>
          {error && <p role="alert" className="rounded-xl border border-rose-100 bg-rose-50 px-4 py-3 text-sm font-medium text-rose-700">{error}</p>}
          <button disabled={busy} type="submit" className="flex w-full items-center justify-center gap-2 rounded-xl bg-indigo-600 px-5 py-4 text-sm font-extrabold text-white shadow-lg shadow-indigo-200 transition hover:bg-indigo-700 disabled:cursor-wait disabled:opacity-60">{busy ? "Please wait…" : mode==="signup"?"Create account":"Log in"} {!busy&&<ArrowRight className="h-4 w-4"/>}</button>
        </form>
        <p className="mt-6 text-center text-sm text-slate-500">{mode==="signup"?"Already have an account?":"New to CogniVault?"} <button type="button" onClick={()=>{setMode(v=>v==="signup"?"login":"signup");setError("");}} className="font-extrabold text-indigo-600 hover:text-indigo-800">{mode==="signup"?"Log in":"Create an account"}</button></p>
        <p className="mt-5 text-center text-[11px] leading-5 text-slate-400">Use a unique password. Passwords are stored as salted hashes, not as plain text.</p>
      </div>
    </section>
  </main>;
}
