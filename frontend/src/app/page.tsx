"use client";

import React from "react";
import Link from "next/link";
import { ArrowRight, Brain, BookOpen, CheckCircle2, FileUp, GraduationCap, Layers3, MessageCircle, Sparkles, Target, Upload, WandSparkles } from "lucide-react";

const capabilities = [
  { icon: BookOpen, title: "Learn from your materials", description: "Ask questions from your own notes, slides and PDFs—with source citations that help you trace the answer.", tint: "bg-indigo-50 text-indigo-600" },
  { icon: Target, title: "Practice that adapts", description: "Build quizzes and focused practice around topics you’re learning, then use feedback to decide what comes next.", tint: "bg-emerald-50 text-emerald-700" },
  { icon: Layers3, title: "See your learning take shape", description: "Explore your topic mastery, curriculum roadmap and misconceptions in one connected learning workspace.", tint: "bg-amber-50 text-amber-700" },
];

export default function Home() {
  return (
    <main className="min-h-screen overflow-hidden bg-[#fbfaf7] text-[#172033]">
      <header className="mx-auto flex max-w-7xl items-center justify-between px-5 py-5 sm:px-8 lg:px-12">
        <Link href="/" className="flex items-center gap-3" aria-label="CogniVault home">
          <span className="flex h-11 w-11 items-center justify-center rounded-2xl bg-gradient-to-br from-indigo-500 to-violet-600 text-white shadow-lg shadow-indigo-200"><Brain className="h-6 w-6" /></span>
          <span><span className="block text-xl font-extrabold tracking-tight">CogniVault</span><span className="block text-xs font-medium text-slate-500">Evidence-first adaptive learning</span></span>
        </Link>
        <nav className="hidden items-center gap-8 text-sm font-semibold text-slate-600 md:flex">
          <a href="#capabilities" className="transition hover:text-indigo-600">Capabilities</a>
          <a href="#how-it-works" className="transition hover:text-indigo-600">How it works</a>
          <Link href="/login?mode=login" className="transition hover:text-indigo-600">Workspace</Link>
        </nav>
        <div className="flex items-center gap-2 sm:gap-3">
          <Link href="/login?mode=login" className="rounded-xl px-3 py-2 text-sm font-bold text-slate-700 transition hover:bg-white">Log in</Link>
          <Link href="/login?mode=signup&next=materials" className="rounded-xl bg-indigo-600 px-4 py-2.5 text-sm font-bold text-white shadow-md shadow-indigo-200 transition hover:bg-indigo-700">Get started <span aria-hidden="true">↗</span></Link>
        </div>
      </header>

      <section className="mx-auto grid max-w-7xl items-center gap-12 px-5 pb-16 pt-10 sm:px-8 md:pt-16 lg:grid-cols-[1.02fr_.98fr] lg:px-12 lg:pb-24">
        <div className="max-w-2xl">
          <div className="mb-6 inline-flex items-center gap-2 rounded-full border border-indigo-100 bg-white px-3.5 py-2 text-xs font-bold text-indigo-700 shadow-sm"><Sparkles className="h-4 w-4" /> Your personal AI learning companion</div>
          <h1 className="text-4xl font-black leading-[1.08] tracking-[-.04em] text-slate-950 sm:text-5xl lg:text-6xl">Your course material.<br/><span className="text-indigo-600">A smarter way to learn.</span></h1>
          <p className="mt-6 max-w-xl text-base leading-7 text-slate-600 sm:text-lg">Turn your notes, lecture slides and textbooks into a learning experience that answers with evidence, helps you practice, and makes your next step clearer.</p>
          <div className="mt-8 flex flex-col gap-3 sm:flex-row">
            <Link href="/login?mode=signup&next=materials" className="inline-flex items-center justify-center gap-2 rounded-2xl bg-indigo-600 px-6 py-4 text-sm font-extrabold text-white shadow-lg shadow-indigo-200 transition hover:-translate-y-0.5 hover:bg-indigo-700"><Upload className="h-4 w-4"/> Upload materials to learn <ArrowRight className="h-4 w-4"/></Link>
            <Link href="/login?mode=signup&next=assessment" className="inline-flex items-center justify-center gap-2 rounded-2xl border border-slate-200 bg-white px-6 py-4 text-sm font-extrabold text-slate-700 transition hover:border-indigo-200 hover:text-indigo-700"><WandSparkles className="h-4 w-4"/> Explore learning tools</Link>
          </div>
          <div className="mt-7 flex flex-wrap items-center gap-x-5 gap-y-2 text-xs font-semibold text-slate-500"><span className="inline-flex items-center gap-1.5"><CheckCircle2 className="h-4 w-4 text-emerald-600"/> Grounded in your course sources</span><span className="inline-flex items-center gap-1.5"><GraduationCap className="h-4 w-4 text-indigo-600"/> Made for college learners</span></div>
        </div>

        <div className="relative mx-auto w-full max-w-[580px]">
          <div className="absolute -right-8 -top-8 h-40 w-40 rounded-full bg-violet-200/60 blur-3xl"/>
          <div className="absolute -bottom-8 -left-8 h-40 w-40 rounded-full bg-indigo-200/70 blur-3xl"/>
          <div className="relative rounded-[28px] border border-slate-200/80 bg-white p-4 shadow-[0_24px_80px_-32px_rgba(55,65,120,.25)] sm:p-5">
            <div className="flex items-center justify-between border-b border-slate-100 pb-4">
              <div className="flex items-center gap-3"><div className="flex h-10 w-10 items-center justify-center rounded-xl bg-indigo-50 text-indigo-600"><GraduationCap className="h-5 w-5"/></div><div><p className="text-sm font-extrabold">Your learning space</p><p className="text-xs text-slate-500">A connected course workspace</p></div></div>
              <span className="rounded-full bg-emerald-50 px-3 py-1 text-[11px] font-bold text-emerald-700">Ready to explore</span>
            </div>
            <div className="grid gap-3 py-4 sm:grid-cols-2">
              <Link href="/login?mode=signup&next=materials" className="group rounded-2xl border border-indigo-100 bg-indigo-50/70 p-5 transition hover:border-indigo-300 hover:bg-indigo-50"><div className="mb-4 flex h-10 w-10 items-center justify-center rounded-xl bg-white text-indigo-600 shadow-sm"><FileUp className="h-5 w-5"/></div><p className="font-extrabold">Upload & learn</p><p className="mt-1 text-xs leading-5 text-slate-600">Bring your notes and course files into your learning space.</p><span className="mt-4 inline-flex items-center gap-1 text-xs font-bold text-indigo-700">Add materials <ArrowRight className="h-3 w-3"/></span></Link>
              <Link href="/login?mode=signup&next=assessment" className="group rounded-2xl border border-emerald-100 bg-emerald-50/70 p-5 transition hover:border-emerald-300 hover:bg-emerald-50"><div className="mb-4 flex h-10 w-10 items-center justify-center rounded-xl bg-white text-emerald-700 shadow-sm"><WandSparkles className="h-5 w-5"/></div><p className="font-extrabold">Quizzes & practice</p><p className="mt-1 text-xs leading-5 text-slate-600">Check your understanding and strengthen tricky concepts.</p><span className="mt-4 inline-flex items-center gap-1 text-xs font-bold text-emerald-700">Start practice <ArrowRight className="h-3 w-3"/></span></Link>
            </div>
            <div className="rounded-2xl bg-[#f8f7f4] p-4 sm:p-5"><div className="flex items-center gap-2 text-xs font-extrabold uppercase tracking-[.12em] text-slate-500"><MessageCircle className="h-4 w-4 text-indigo-500"/> Ask your doubts</div><Link href="/login?mode=signup&next=tutor" className="mt-3 flex items-center justify-between gap-3 rounded-xl border border-slate-200 bg-white px-4 py-3 text-sm text-slate-400 shadow-sm transition hover:border-indigo-300"><span>Ask a question about your course...</span><span className="flex h-8 w-8 items-center justify-center rounded-lg bg-indigo-600 text-white"><ArrowRight className="h-4 w-4"/></span></Link><p className="mt-3 text-[11px] text-slate-500">Answers are designed to be grounded in indexed course evidence.</p></div>
          </div>
        </div>
      </section>

      <section id="capabilities" className="border-y border-slate-200/70 bg-white/70">
        <div className="mx-auto max-w-7xl px-5 py-16 sm:px-8 lg:px-12">
          <div className="mx-auto max-w-2xl text-center"><p className="text-xs font-extrabold uppercase tracking-[.18em] text-indigo-600">Made for the way students study</p><h2 className="mt-3 text-3xl font-black tracking-tight text-slate-950 sm:text-4xl">More than a place to ask AI.</h2><p className="mt-4 text-sm leading-6 text-slate-600 sm:text-base">A set of learning tools that work together—from your first upload to your next revision session.</p></div>
          <div className="mt-10 grid gap-5 md:grid-cols-3">{capabilities.map((item) => {const Icon=item.icon;return <article key={item.title} className="rounded-3xl border border-slate-200 bg-white p-6 shadow-sm transition hover:-translate-y-1 hover:shadow-lg"><div className={`flex h-12 w-12 items-center justify-center rounded-2xl ${item.tint}`}><Icon className="h-5 w-5"/></div><h3 className="mt-5 text-lg font-extrabold">{item.title}</h3><p className="mt-2 text-sm leading-6 text-slate-600">{item.description}</p></article>})}</div>
        </div>
      </section>

      <section id="how-it-works" className="mx-auto max-w-7xl px-5 py-16 sm:px-8 lg:px-12">
        <div className="grid items-center gap-8 rounded-[32px] bg-[#171b35] px-6 py-10 text-white sm:px-10 lg:grid-cols-[1fr_auto] lg:px-14">
          <div><p className="text-xs font-extrabold uppercase tracking-[.18em] text-indigo-300">Your study flow</p><h2 className="mt-3 max-w-2xl text-3xl font-black leading-tight tracking-tight sm:text-4xl">Personalize your learning.<br/>Make it sharper.</h2><p className="mt-4 max-w-xl text-sm leading-6 text-slate-300">Bring your material. Ask your doubts. Practice with purpose. Use your learning signals to guide what you revisit.</p></div>
          <Link href="/login?mode=signup&next=materials" className="inline-flex items-center justify-center gap-2 rounded-2xl bg-white px-6 py-4 text-sm font-extrabold text-indigo-700 transition hover:bg-indigo-50">Start with your materials <ArrowRight className="h-4 w-4"/></Link>
        </div>
      </section>
      <footer className="border-t border-slate-200 bg-white/70"><div className="mx-auto flex max-w-7xl flex-col gap-3 px-5 py-7 text-xs text-slate-500 sm:flex-row sm:items-center sm:justify-between sm:px-8 lg:px-12"><span className="font-bold text-slate-700">CogniVault · Evidence-first adaptive learning</span><span>Built to support college learners studying from their own course materials.</span></div></footer>
    </main>
  );
}
