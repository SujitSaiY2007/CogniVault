"use client";

import React, { useState, useEffect } from "react";
import { useRouter } from "next/navigation";
import { Citation, CurriculumTopic, DEFAULT_CURRICULUM_TOPICS, SystemHealth } from "@/lib/types";
import { api, authApi } from "@/lib/api";
import { Navbar } from "@/components/Navbar";
import { TutorView } from "@/components/TutorView";
import { AssessmentView } from "@/components/AssessmentView";
import { LearnerProgressView } from "@/components/LearnerProgressView";
import { MisconceptionsView } from "@/components/MisconceptionsView";
import { RecommendationsView } from "@/components/RecommendationsView";
import { IngestionView } from "@/components/IngestionView";
import { CitationDrawer } from "@/components/CitationDrawer";
import { ColdStartModal } from "@/components/ColdStartModal";

export default function Home() {
  const router = useRouter();
  const [authReady, setAuthReady] = useState(false);
  const [accountUsername, setAccountUsername] = useState("");
  const [activeTab, setActiveTab] = useState<string>("tutor");
  const [activeLearner, setActiveLearner] = useState<string>("learner_demo");
  const [learners, setLearners] = useState<string[]>(["learner_demo"]);
  const [health, setHealth] = useState<SystemHealth | null>(null);
  const [topics, setTopics] = useState<CurriculumTopic[]>(DEFAULT_CURRICULUM_TOPICS);
  const [practiceTopic, setPracticeTopic] = useState<string>("");
  const [inspectCitation, setInspectCitation] = useState<Citation | null>(null);
  const [coldStartOpen, setColdStartOpen] = useState<boolean>(false);

  const loadInitialData = async () => {
    try {
      const [healthData, topicData, learnerList] = await Promise.all([
        api.getHealth().catch(() => null),
        api.listTopics().catch(() => []),
        api.listLearners().catch(() => []),
      ]);

      if (healthData) setHealth(healthData);
      if (topicData && topicData.length > 0) {
        setTopics(topicData);
      } else {
        setTopics(DEFAULT_CURRICULUM_TOPICS);
      }
      // Each signed-in account is bound to its own learner identity; never switch into another profile.
      setLearners([activeLearner]);
    } catch {
      // Graceful offline fallback
    }
  };

  useEffect(() => {
    const token = window.localStorage.getItem("cognivault_session");
    if (!token) { router.replace("/login?mode=login"); return; }
    authApi.me().then((user) => {
      setAccountUsername(user.username);
      setActiveLearner(user.learner_id);
      setLearners([user.learner_id]);
      setAuthReady(true);
      loadInitialData();
      const params = new URLSearchParams(window.location.search);
      const requestedTab = params.get("tab");
      if (["tutor", "assessment", "mastery", "misconceptions", "recommendations", "materials"].includes(requestedTab || "")) setActiveTab(requestedTab || "tutor");
      if (params.get("demo_citation") === "true") setInspectCitation({
        evidence_id: "physics_mechanics:e00001", source_id: "physics_mechanics",
        source_title: "Classical Mechanics & Dynamics", modality: "pdf", location: { page: 1 },
        snippet: "Newton's Second Law of Motion: The rate of change of momentum of a body is directly proportional to the applied force: F = m * a.",
      });
    }).catch(() => {
      window.localStorage.removeItem("cognivault_session");
      window.localStorage.removeItem("cognivault_username");
      window.localStorage.removeItem("cognivault_learner_id");
      router.replace("/login?mode=login");
    });
  }, []);

  const refreshLearners = async () => { setLearners([activeLearner]); };

  if (!authReady) return <main className="flex min-h-screen items-center justify-center bg-slate-950 text-slate-200"><div className="text-sm font-semibold">Verifying your CogniVault session…</div></main>;

  return (
    <div className="min-h-screen bg-slate-950 text-slate-100 flex flex-col">
      {/* Navigation Bar */}
      <Navbar
        activeTab={activeTab}
        setActiveTab={setActiveTab}
        activeLearner={activeLearner}
        setActiveLearner={setActiveLearner}
        learners={learners}
        health={health}
        onOpenColdStart={() => setColdStartOpen(true)}
        accountUsername={accountUsername}
        onLogout={async () => { try { await authApi.logout(); } catch {} window.localStorage.removeItem("cognivault_session"); window.localStorage.removeItem("cognivault_username"); window.localStorage.removeItem("cognivault_learner_id"); router.replace("/login?mode=login"); }}
      />

      {/* Main View Area */}
      <main className="flex-1 overflow-x-hidden">
        <div className={activeTab === "tutor" ? "block" : "hidden"}>
          <TutorView onOpenCitation={setInspectCitation} />
        </div>

        <div className={activeTab === "assessment" ? "block" : "hidden"}>
          <AssessmentView
            activeLearner={activeLearner}
            topics={topics}
            initialTopic={practiceTopic}
            onOpenCitation={setInspectCitation}
            onAssessmentCompleted={refreshLearners}
          />
        </div>

        <div className={activeTab === "mastery" ? "block" : "hidden"}>
          <LearnerProgressView activeLearner={activeLearner} />
        </div>

        <div className={activeTab === "misconceptions" ? "block" : "hidden"}>
          <MisconceptionsView
            activeLearner={activeLearner}
            onOpenCitation={setInspectCitation}
          />
        </div>

        <div className={activeTab === "recommendations" ? "block" : "hidden"}>
          <RecommendationsView
            activeLearner={activeLearner}
            onNavigateToPractice={(topicId) => {
              setPracticeTopic(topicId);
              setActiveTab("assessment");
            }}
          />
        </div>

        <div className={activeTab === "materials" ? "block" : "hidden"}>
          <IngestionView
            onOpenCitation={setInspectCitation}
            onCurriculumUpdated={loadInitialData}
          />
        </div>
      </main>

      {/* Modals & Drawers */}
      <CitationDrawer
        citation={inspectCitation}
        onClose={() => setInspectCitation(null)}
      />

      <ColdStartModal
        isOpen={coldStartOpen}
        onClose={() => setColdStartOpen(false)}
        topics={topics}
        onComplete={(newLearnerId) => {
          setLearners((prev) => (prev.includes(newLearnerId) ? prev : [...prev, newLearnerId]));
          setActiveLearner(newLearnerId);
          refreshLearners();
          setActiveTab("mastery");
        }}
      />
    </div>
  );
}
