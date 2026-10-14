/**
 * Typed API client for CogniVault AgentOS backend.
 * Provides typed methods for all learning loop, ingestion, and assessment endpoints.
 */

import {
  CurriculumTopic,
  Difficulty,
  EvidenceUnit,
  LearnerProfile,
  Question,
  QuestionType,
  Recommendation,
  RemediationPackage,
  SourceRecord,
  SystemHealth,
  TopicMasteryRecord,
  TutorResponse,
  AssessmentCycleResult,
} from "./types";

const API_BASE = (process.env.NEXT_PUBLIC_API_URL || "http://127.0.0.1:8000").replace(/\/+$/, "");

async function request<T>(
  path: string,
  options: RequestInit = {},
  learnerId?: string
): Promise<T> {
  const headers: Record<string, string> = {
    "Content-Type": "application/json",
    ...(options.headers as Record<string, string>),
  };

  if (learnerId) {
    headers["X-Learner-Id"] = learnerId;
  }

  const url = `${API_BASE}${path}`;

  try {
    const res = await fetch(url, {
      ...options,
      headers,
    });

    if (!res.ok) {
      let errDetail = `API Error ${res.status}: ${res.statusText}`;
      try {
        const errJson = await res.json();
        if (errJson.detail) {
          errDetail = typeof errJson.detail === "string" ? errJson.detail : JSON.stringify(errJson.detail);
        }
      } catch {
        // Fallback to status text
      }
      throw new Error(errDetail);
    }

    return (await res.json()) as T;
  } catch (error: any) {
    if (error.name === "TypeError" && error.message.includes("fetch")) {
      throw new Error(`Cannot connect to CogniVault backend (${API_BASE}). If the cloud container is waking up, please wait ~15 seconds and refresh.`);
    }
    throw error;
  }
}

export const api = {
  // System Health
  async getHealth(): Promise<SystemHealth> {
    return request<SystemHealth>("/api/v1/health");
  },

  // Tutor
  async queryTutor(query: string, topic?: string): Promise<TutorResponse> {
    return request<TutorResponse>("/api/v1/tutor/query", {
      method: "POST",
      body: JSON.stringify({ query, topic }),
    });
  },

  // Evidence & Search
  async searchEvidence(q: string, k = 5, mode = "hybrid") {
    return request<{
      query: string;
      mode: string;
      result_count: number;
      unsupported: boolean;
      reason: string | null;
      results: Array<{
        evidence_id: string;
        source_id: string;
        score: number;
        snippet: string;
        location: Record<string, string | number>;
      }>;
    }>(`/api/v1/evidence/search?q=${encodeURIComponent(q)}&k=${k}&mode=${mode}`);
  },

  // Sources & Ingestion
  async listSources(): Promise<SourceRecord[]> {
    return request<SourceRecord[]>("/api/v1/sources");
  },

  async getSourceDetails(sourceId: string): Promise<SourceRecord> {
    return request<SourceRecord>(`/api/v1/sources/${encodeURIComponent(sourceId)}`);
  },

  async getSourceEvidence(sourceId: string): Promise<EvidenceUnit[]> {
    return request<EvidenceUnit[]>(`/api/v1/sources/${encodeURIComponent(sourceId)}/evidence`);
  },

  async uploadMaterial(file: File): Promise<{
    source_id: string;
    title: string;
    modality: string;
    sha256: string;
    evidence_count: number;
    status: string;
  }> {
    const formData = new FormData();
    formData.append("file", file);

    const res = await fetch(`${API_BASE}/api/v1/ingest/upload`, {
      method: "POST",
      body: formData,
    });

    if (!res.ok) {
      const err = await res.json().catch(() => ({}));
      throw new Error(err.detail || `Upload failed with status ${res.status}`);
    }

    return res.json();
  },

  async syncChroma(): Promise<{ status: string; synced_units: number }> {
    return request<{ status: string; synced_units: number }>("/api/v1/evidence/sync-chroma", {
      method: "POST",
    });
  },

  async seedCorpus(): Promise<{ status: string; stats: any }> {
    return request<{ status: string; stats: any }>("/api/v1/corpus/seed", {
      method: "POST",
    });
  },

  // Curriculum & Topics
  async listTopics(): Promise<CurriculumTopic[]> {
    return request<CurriculumTopic[]>("/api/v1/topics");
  },

  // Assessment
  async listQuestions(topicId?: string, difficulty?: Difficulty, questionType?: QuestionType): Promise<Question[]> {
    const params = new URLSearchParams();
    if (topicId) params.append("topic_id", topicId);
    if (difficulty) params.append("difficulty", difficulty);
    if (questionType) params.append("question_type", questionType);
    const qs = params.toString();
    return request<Question[]>(`/api/v1/assessment/questions${qs ? `?${qs}` : ""}`);
  },

  async selectAdaptiveQuestion(
    topicId: string,
    servedQuestionIds: string[] = [],
    targetDifficulty?: Difficulty
  ): Promise<Question> {
    return request<Question>("/api/v1/assessment/select", {
      method: "POST",
      body: JSON.stringify({
        topic_id: topicId,
        served_question_ids: servedQuestionIds,
        target_difficulty: targetDifficulty,
      }),
    });
  },

  async submitAssessment(
    learnerId: string,
    questionId: string,
    answer: string
  ): Promise<AssessmentCycleResult> {
    return request<AssessmentCycleResult>(
      "/api/v1/assessment/submit",
      {
        method: "POST",
        body: JSON.stringify({
          learner_id: learnerId,
          question_id: questionId,
          answer: answer,
        }),
      },
      learnerId
    );
  },

  // Learner Model & BKT
  async listLearners(): Promise<Array<{
    learner_id: string;
    topics_tracked: number;
    total_attempts: number;
    total_correct: number;
    active_misconceptions: number;
  }>> {
    return request("/api/v1/learners");
  },

  async getLearnerProfile(learnerId: string): Promise<LearnerProfile> {
    return request<LearnerProfile>(`/api/v1/learner/${encodeURIComponent(learnerId)}/profile`, {}, learnerId);
  },

  async getLearnerMastery(learnerId: string): Promise<TopicMasteryRecord[]> {
    return request<TopicMasteryRecord[]>(`/api/v1/learner/${encodeURIComponent(learnerId)}/mastery`, {}, learnerId);
  },

  async recordObservation(
    learnerId: string,
    topicId: string,
    isCorrect: boolean
  ): Promise<TopicMasteryRecord> {
    return request<TopicMasteryRecord>(
      `/api/v1/learner/${encodeURIComponent(learnerId)}/observation`,
      {
        method: "POST",
        body: JSON.stringify({
          topic_id: topicId,
          is_correct: isCorrect,
        }),
      },
      learnerId
    );
  },

  // Misconceptions
  async getMisconceptions(learnerId: string, topicId?: string): Promise<RemediationPackage[]> {
    const qs = topicId ? `?topic_id=${encodeURIComponent(topicId)}` : "";
    return request<RemediationPackage[]>(
      `/api/v1/learner/${encodeURIComponent(learnerId)}/misconceptions${qs}`,
      {},
      learnerId
    );
  },

  async resolveMisconception(learnerId: string, signalId: string): Promise<{ status: string; learner_id: string; topic_id: string }> {
    return request<{ status: string; learner_id: string; topic_id: string }>(
      `/api/v1/learner/${encodeURIComponent(learnerId)}/misconceptions/${encodeURIComponent(signalId)}/resolve`,
      { method: "POST" },
      learnerId
    );
  },

  // Recommendations
  async getRecommendations(learnerId: string, activeTopicId?: string): Promise<Recommendation> {
    const qs = activeTopicId ? `?active_topic_id=${encodeURIComponent(activeTopicId)}` : "";
    return request<Recommendation>(
      `/api/v1/learner/${encodeURIComponent(learnerId)}/recommendations${qs}`,
      {},
      learnerId
    );
  },

  // Cold-Start Diagnostic Intake
  async coldStartIntake(
    learnerId: string,
    initialMasteries?: Record<string, number>,
    diagnosticResponses?: Array<{ topic_id: string; is_correct: boolean }>
  ): Promise<{
    learner_id: string;
    intake_status: string;
    profile: LearnerProfile;
    initial_recommendation: Recommendation;
  }> {
    return request(
      `/api/v1/learner/${encodeURIComponent(learnerId)}/intake`,
      {
        method: "POST",
        body: JSON.stringify({
          initial_topic_masteries: initialMasteries,
          diagnostic_responses: diagnosticResponses,
        }),
      },
      learnerId
    );
  },
};
