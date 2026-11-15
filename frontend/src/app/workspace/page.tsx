"use client";

import React, { useCallback, useEffect, useState } from "react";
import { useRouter } from "next/navigation";
import { api, authApi, onConnectionStatus } from "@/lib/api";
import { Citation, CurriculumTopic, QuizSession, SystemHealth } from "@/lib/types";
import { Navbar, TABS } from "@/components/Navbar";
import { TutorView } from "@/components/TutorView";
import { AssessmentView } from "@/components/AssessmentView";
import { LearnerProgressView } from "@/components/LearnerProgressView";
import { MisconceptionsView } from "@/components/MisconceptionsView";
import { RecommendationsView } from "@/components/RecommendationsView";
import { CourseMapView } from "@/components/CourseMapView";
import { IngestionView } from "@/components/IngestionView";
import { CitationDrawer } from "@/components/CitationDrawer";
import { ColdStartModal } from "@/components/ColdStartModal";
import { ErrorBanner } from "@/components/ui";

export default function Workspace() {
  const router = useRouter();
  const [ready, setReady] = useState(false);
  const [bootMessage, setBootMessage] = useState("Verifying your session…");
  const [username, setUsername] = useState("");
  const [learnerId, setLearnerId] = useState("");
  const [tab, setTab] = useState("tutor");
  const [health, setHealth] = useState<SystemHealth | null>(null);
  const [connection, setConnection] = useState<"ok" | "waking" | "down">("ok");
  const [topics, setTopics] = useState<CurriculumTopic[]>([]);
  const [topicsError, setTopicsError] = useState<string | null>(null);
  const [practiceTopic, setPracticeTopic] = useState<string | undefined>();
  const [pendingQuiz, setPendingQuiz] = useState<QuizSession | null>(null);
  const [citation, setCitation] = useState<Citation | null>(null);
  const [coldStart, setColdStart] = useState(false);
  const [refreshKey, setRefreshKey] = useState(0);

  useEffect(
    () =>
      onConnectionStatus((s) => {
        setConnection(s);
        if (s === "waking") setBootMessage("Waking the server. Free hosting sleeps when idle; this can take up to a minute…");
      }),
    []
  );

  const loadTopics = useCallback(async () => {
    setTopicsError(null);
    try {
      setTopics(await api.listTopics());
    } catch (e: any) {
      setTopicsError(e.message);
    }
  }, []);

  useEffect(() => {
    if (!window.localStorage.getItem("cognivault_session")) {
      router.replace("/login?mode=login");
      return;
    }
    authApi
      .me()
      .then((u) => {
        setUsername(u.username);
        setLearnerId(u.learner_id);
        setReady(true);
        const t = new URLSearchParams(window.location.search).get("tab");
        if (t && TABS.some((x) => x.id === t)) setTab(t);
        loadTopics();
        api.getHealth().then(setHealth).catch(() => setConnection("down"));
      })
      .catch((e) => {
        if (e?.status === 401) router.replace("/login?mode=login");
        else {
          setConnection("down");
          setBootMessage(e.message || "Cannot reach the server.");
        }
      });
  }, []); // eslint-disable-line react-hooks/exhaustive-deps

  const practise = (topicId: string) => {
    setPracticeTopic(topicId);
    setTab("assessment");
  };
  const changed = () => setRefreshKey((k) => k + 1);

  if (!ready)
    return (
      <main className="flex min-h-screen flex-col items-center justify-center gap-4 bg-slate-950 p-6 text-center text-slate-200">
        <div className="h-8 w-8 animate-spin rounded-full border-2 border-indigo-400 border-t-transparent" />
        <p className="max-w-md text-sm font-semibold">{bootMessage}</p>
        {connection === "down" && (
          <button onClick={() => window.location.reload()} className="rounded-xl border border-slate-600 px-4 py-2 text-xs font-bold hover:border-indigo-400">
            Try again
          </button>
        )}
      </main>
    );

  return (
    <div className="flex min-h-screen flex-col bg-slate-950 text-slate-100">
      <Navbar
        activeTab={tab}
        setActiveTab={setTab}
        health={health}
        connection={connection}
        onOpenColdStart={() => setColdStart(true)}
        accountUsername={username}
        onLogout={async () => {
          try {
            await authApi.logout();
          } catch {}
          ["cognivault_session", "cognivault_username", "cognivault_learner_id"].forEach((k) => window.localStorage.removeItem(k));
          router.replace("/login?mode=login");
        }}
      />
      {topicsError && (
        <div className="mx-auto w-full max-w-5xl px-4 pt-4">
          <ErrorBanner message={`Could not load topics: ${topicsError}`} onRetry={loadTopics} />
        </div>
      )}
      <main className="flex-1 overflow-x-hidden">
        <div className={tab === "tutor" ? "block" : "hidden"}>
          <TutorView topics={topics} onOpenCitation={setCitation} />
        </div>
        {tab === "assessment" && (
          <AssessmentView
            topics={topics}
            initialTopic={practiceTopic}
            pendingQuiz={pendingQuiz}
            onPendingQuizConsumed={() => setPendingQuiz(null)}
            onOpenCitation={setCitation}
            onAssessmentCompleted={changed}
          />
        )}
        {tab === "mastery" && <LearnerProgressView learnerId={learnerId} refreshKey={refreshKey} onPractice={practise} />}
        {tab === "misconceptions" && <MisconceptionsView learnerId={learnerId} refreshKey={refreshKey} onPractice={practise} onOpenCitation={setCitation} />}
        {tab === "recommendations" && <RecommendationsView learnerId={learnerId} refreshKey={refreshKey} onPractice={practise} onOpenCitation={setCitation} />}
        {tab === "map" && <CourseMapView refreshKey={refreshKey} onPractice={practise} />}
        {tab === "materials" && (
          <IngestionView
            onCurriculumUpdated={() => {
              loadTopics();
              changed();
            }}
          />
        )}
      </main>
      <CitationDrawer citation={citation} onClose={() => setCitation(null)} />
      <ColdStartModal
        isOpen={coldStart}
        onClose={() => setColdStart(false)}
        learnerId={learnerId}
        topics={topics}
        onComplete={(quiz) => {
          setColdStart(false);
          changed();
          if (quiz) {
            setPendingQuiz(quiz);
            setTab("assessment");
          } else setTab("recommendations");
        }}
      />
    </div>
  );
}
