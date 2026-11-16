/**
 * Typed client for the CogniVault API.
 *
 * Free hosting puts the backend to sleep when idle; the first request can
 * take 30-60 s. Requests therefore retry network errors and 502/503/504
 * responses with backoff, and report "waking up" through onStatus so the UI
 * can explain the wait. Errors are never hidden behind fake data.
 */
import type {
  AssessmentCycleResult,
  CourseMap,
  CurriculumTopic,
  Difficulty,
  EvidenceUnit,
  Flashcard,
  LearnerProfile,
  Question,
  QuestionType,
  QuizReport,
  QuizSession,
  Recommendation,
  RemediationPackage,
  SourceRecord,
  StudyPlan,
  SystemHealth,
  TutorResponse,
  UploadResult,
} from "./types";

export const API_BASE = (process.env.NEXT_PUBLIC_API_URL || "https://cognivault-backend-znn4.onrender.com").replace(/\/+$/, "");

export class ApiError extends Error {
  status: number;
  constructor(message: string, status: number) {
    super(message);
    this.status = status;
  }
}

type StatusListener = (state: "waking" | "ok") => void;
const listeners = new Set<StatusListener>();
export function onConnectionStatus(fn: StatusListener) {
  listeners.add(fn);
  return () => {
    listeners.delete(fn);
  };
}
function emit(state: "waking" | "ok") {
  listeners.forEach((fn) => fn(state));
}

function token(): string | null {
  return typeof window !== "undefined" ? window.localStorage.getItem("cognivault_session") : null;
}

function clearSession() {
  if (typeof window === "undefined") return;
  ["cognivault_session", "cognivault_username", "cognivault_learner_id"].forEach((k) => window.localStorage.removeItem(k));
}

const sleep = (ms: number) => new Promise((r) => setTimeout(r, ms));

async function request<T>(path: string, options: RequestInit = {}, timeoutMs = 30000, retries = 3): Promise<T> {
  const headers: Record<string, string> = { ...(options.headers as Record<string, string>) };
  if (!(options.body instanceof FormData) && options.body !== undefined) headers["Content-Type"] = "application/json";
  const t = token();
  if (t) headers["Authorization"] = `Bearer ${t}`;

  let lastError: Error | null = null;
  for (let attempt = 0; attempt <= retries; attempt++) {
    const controller = new AbortController();
    const timer = setTimeout(() => controller.abort(), timeoutMs);
    try {
      const res = await fetch(`${API_BASE}${path}`, { ...options, headers, signal: controller.signal });
      clearTimeout(timer);
      if ([502, 503, 504].includes(res.status) && attempt < retries) {
        emit("waking");
        await sleep(2000 * (attempt + 1));
        continue;
      }
      if (!res.ok) {
        let detail = `Request failed (${res.status}).`;
        try {
          const body = await res.json();
          if (body?.detail) detail = typeof body.detail === "string" ? body.detail : JSON.stringify(body.detail);
        } catch {
          /* keep default */
        }
        if (res.status === 401 && path !== "/api/v1/auth/login") {
          clearSession();
          if (typeof window !== "undefined" && !window.location.pathname.startsWith("/login")) {
            window.location.replace("/login?mode=login");
          }
        }
        throw new ApiError(detail, res.status);
      }
      emit("ok");
      if (res.status === 204) return undefined as T;
      return (await res.json()) as T;
    } catch (err: any) {
      clearTimeout(timer);
      if (err instanceof ApiError) throw err;
      lastError = err;
      if (attempt < retries) {
        emit("waking");
        await sleep(2500 * (attempt + 1));
        continue;
      }
    }
  }
  throw new ApiError(
    lastError?.name === "AbortError"
      ? "The server took too long to respond. It may be starting up; please try again in a moment."
      : "Cannot reach the CogniVault server. Check your connection and try again.",
    0
  );
}

const post = <T>(path: string, body?: unknown, timeoutMs?: number) =>
  request<T>(path, { method: "POST", body: body === undefined ? undefined : JSON.stringify(body) }, timeoutMs);

export const api = {
  getHealth: () => request<SystemHealth>("/api/v1/health", {}, 60000, 4),

  queryTutor: (query: string, history: string[] = [], allowGeneral = false, topic?: string) =>
    post<TutorResponse>("/api/v1/tutor/query", { query, history, allow_general_knowledge: allowGeneral, topic }, 60000),

  listSources: () => request<SourceRecord[]>("/api/v1/sources"),
  getSourceEvidence: (id: string) => request<EvidenceUnit[]>(`/api/v1/sources/${encodeURIComponent(id)}/evidence`),
  deleteSource: (id: string) => request<{ status: string }>(`/api/v1/sources/${encodeURIComponent(id)}`, { method: "DELETE" }),
  uploadMaterial: (file: File) => {
    const form = new FormData();
    form.append("file", file);
    return request<UploadResult>("/api/v1/ingest/upload", { method: "POST", body: form }, 180000, 1);
  },
  assetUrl: async (assetId: string): Promise<string> => {
    const res = await fetch(`${API_BASE}/api/v1/assets/${encodeURIComponent(assetId)}`, {
      headers: token() ? { Authorization: `Bearer ${token()}` } : {},
    });
    if (!res.ok) throw new ApiError("Image unavailable", res.status);
    return URL.createObjectURL(await res.blob());
  },

  listTopics: () => request<CurriculumTopic[]>("/api/v1/topics"),
  courseMap: () => request<CourseMap>("/api/v1/course-map"),

  selectQuestion: (topicId: string, served: string[] = [], difficulty?: Difficulty, questionType?: QuestionType) =>
    post<Question>("/api/v1/assessment/select", {
      topic_id: topicId,
      served_question_ids: served,
      target_difficulty: difficulty,
      question_type: questionType,
    }),
  submitAnswer: (questionId: string, answer: string) =>
    post<AssessmentCycleResult>("/api/v1/assessment/submit", { question_id: questionId, answer }),

  createQuiz: (opts: { topic_ids: string[]; count: number; types: string[]; difficulty?: string; mode: string }) =>
    post<QuizSession>("/api/v1/quiz", opts),
  answerQuiz: (sessionId: string, questionId: string, answer: string) =>
    post<AssessmentCycleResult & { recorded?: boolean }>(`/api/v1/quiz/${sessionId}/answer`, { question_id: questionId, answer }),
  finishQuiz: (sessionId: string) => post<QuizReport>(`/api/v1/quiz/${sessionId}/finish`),
  quizHistory: () => request<{ session_id: string; mode: string; created_at: string; finished: boolean; total: number; answered: number; percent: number | null }[]>("/api/v1/quiz"),

  getProfile: (learnerId: string) => request<LearnerProfile>(`/api/v1/learner/${encodeURIComponent(learnerId)}/profile`),
  getMisconceptions: (learnerId: string) => request<RemediationPackage[]>(`/api/v1/learner/${encodeURIComponent(learnerId)}/misconceptions`),
  resolveMisconception: (learnerId: string, signalId: string) =>
    post<{ status: string }>(`/api/v1/learner/${encodeURIComponent(learnerId)}/misconceptions/${encodeURIComponent(signalId)}/resolve`),
  getRecommendation: (learnerId: string, activeTopicId?: string) =>
    request<Recommendation>(
      `/api/v1/learner/${encodeURIComponent(learnerId)}/recommendations${activeTopicId ? `?active_topic_id=${encodeURIComponent(activeTopicId)}` : ""}`
    ),

  flashcards: (topicId?: string) => request<Flashcard[]>(`/api/v1/flashcards${topicId ? `?topic_id=${encodeURIComponent(topicId)}` : ""}`),
  reviewFlashcard: (cardId: string, grade: number) => post<{ due: string; interval_days: number }>(`/api/v1/flashcards/${encodeURIComponent(cardId)}/review`, { grade }),
  studyPlan: () => request<StudyPlan>("/api/v1/study-plan"),
  saveStudyPlan: (examDate: string, minutesPerDay: number) => post<StudyPlan>("/api/v1/study-plan", { exam_date: examDate, minutes_per_day: minutesPerDay }),
};

export interface AuthSession {
  access_token: string;
  token_type: string;
  username: string;
  learner_id: string;
}

export const authApi = {
  signup: (username: string, password: string) => post<AuthSession>("/api/v1/auth/signup", { username, password }, 60000),
  login: (username: string, password: string) => post<AuthSession>("/api/v1/auth/login", { username, password }, 60000),
  me: () => request<{ username: string; learner_id: string }>("/api/v1/auth/me", {}, 60000, 4),
  logout: () => post<void>("/api/v1/auth/logout"),
};
