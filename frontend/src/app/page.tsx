"use client";

import React, { useState, useEffect } from "react";
import { Citation, CurriculumTopic, DEFAULT_CURRICULUM_TOPICS, SystemHealth } from "@/lib/types";
import { api } from "@/lib/api";
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
      if (learnerList && learnerList.length > 0) {
        const ids = learnerList.map((l: any) => l.learner_id);
        setLearners(ids);
        if (!ids.includes(activeLearner)) {
          setActiveLearner(ids[0]);
        }
      }
    } catch {
      // Graceful offline fallback
    }
  };

  useEffect(() => {
    loadInitialData();
    if (typeof window !== "undefined") {
      const params = new URLSearchParams(window.location.search);
      if (params.get("demo_citation") === "true") {
        setInspectCitation({
          evidence_id: "physics_mechanics:e00001",
          source_id: "physics_mechanics",
          source_title: "Classical Mechanics & Dynamics",
          modality: "pdf",
          location: { page: 1 },
          snippet: "Newton's Second Law of Motion: The rate of change of momentum of a body is directly proportional to the applied force: F = m * a.",
        });
      }
    }
  }, []);

  const refreshLearners = async () => {
    try {
      const learnerList = await api.listLearners();
      if (learnerList && learnerList.length > 0) {
        setLearners(learnerList.map((l: any) => l.learner_id));
      }
    } catch {}
  };

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
      />

      {/* Main View Area */}
      <main className="flex-1 overflow-x-hidden">
        {activeTab === "tutor" && (
          <TutorView onOpenCitation={setInspectCitation} />
        )}

        {activeTab === "assessment" && (
          <AssessmentView
            activeLearner={activeLearner}
            topics={topics}
            initialTopic={practiceTopic}
            onOpenCitation={setInspectCitation}
            onAssessmentCompleted={refreshLearners}
          />
        )}

        {activeTab === "mastery" && (
          <LearnerProgressView activeLearner={activeLearner} />
        )}

        {activeTab === "misconceptions" && (
          <MisconceptionsView
            activeLearner={activeLearner}
            onOpenCitation={setInspectCitation}
          />
        )}

        {activeTab === "recommendations" && (
          <RecommendationsView
            activeLearner={activeLearner}
            onNavigateToPractice={(topicId) => {
              setPracticeTopic(topicId);
              setActiveTab("assessment");
            }}
          />
        )}

        {activeTab === "materials" && (
          <IngestionView
            onOpenCitation={setInspectCitation}
            onCurriculumUpdated={loadInitialData}
          />
        )}
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
          setActiveLearner(newLearnerId);
          refreshLearners();
          setActiveTab("mastery");
        }}
      />
    </div>
  );
}
