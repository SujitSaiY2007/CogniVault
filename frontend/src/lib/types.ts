/** Data contracts shared with the FastAPI backend (app/models.py, app/service.py). */

export type Modality = "pdf" | "pptx" | "video" | "image" | "text";
export type QuestionType = "mcq" | "numerical" | "short_answer";
export type Difficulty = "easy" | "medium" | "hard";

export interface Citation {
  evidence_id: string;
  source_id: string;
  modality: Modality;
  location: Record<string, string | number>;
  snippet: string;
  source_path?: string | null;
  source_title?: string | null;
  locator_label?: string;
  asset_id?: string | null;
}

export interface TutorResponse {
  query: string;
  answer: string;
  citations: Citation[];
  is_grounded: boolean;
  is_synthesis?: boolean;
  confidence: number;
  support_status: "supported" | "partial" | "unsupported" | "error";
  reasoning_steps: string[];
  unsupported_reason?: string | null;
  topics?: string[];
  generator?: string;
  metadata?: Record<string, any>;
}

export interface SourceTopic {
  topic_id: string;
  name: string;
}

export interface SourceRecord {
  source_id: string;
  title: string;
  modality: Modality;
  path: string;
  sha256: string;
  metadata?: Record<string, any>;
  evidence_count?: number;
  created_at?: string;
  owner?: "you" | "demo";
  topics?: SourceTopic[];
}

export interface UploadResult {
  source_id: string;
  title: string;
  modality: string;
  sha256: string;
  evidence_count: number;
  figure_count: number;
  topics: SourceTopic[];
  question_count: number;
  warnings: string[];
  status: string;
}

export interface EvidenceUnit {
  evidence_id: string;
  source_id: string;
  modality: Modality;
  text: string;
  location: Record<string, string | number>;
  evidence_type: string;
  section?: string;
  topics?: string[];
  concepts?: string[];
  metadata?: Record<string, any>;
}

export interface QuestionOption {
  key: string;
  text: string;
}

export interface Question {
  question_id: string;
  topic_id: string;
  concept_id?: string | null;
  evidence_ids: string[];
  difficulty: Difficulty;
  question_type: QuestionType;
  prompt: string;
  options: QuestionOption[];
  tolerance?: number | null;
  verification_status: "verified" | "rejected" | "unverified";
  fingerprint: string;
  metadata?: Record<string, any>;
}

export interface AnswerEvaluation {
  learner_id: string;
  question_id: string;
  is_correct: boolean;
  status: "correct" | "partially_correct" | "incorrect";
  score: number;
  feedback: string;
  expected_answer: string;
  solution: string;
  citations: Citation[];
  remediation_action?: string | null;
  remediation_evidence_ids: string[];
}

export interface TopicMasteryRecord {
  learner_id: string;
  topic_id: string;
  topic_name?: string;
  p_mastery: number;
  p_mastery_stored?: number;
  attempts: number;
  correct: number;
  recent_correctness: boolean[];
  last_seen?: string | null;
  misconception_signals: string[];
}

export interface MisconceptionSignal {
  signal_id: string;
  learner_id: string;
  topic_id: string;
  concept_id?: string | null;
  suspected_misconception: string;
  error_count: number;
  confidence: number;
  remediation_concept_id?: string | null;
  remediation_evidence_ids: string[];
  remediation_note: string;
  created_at?: string | null;
}

export interface RemediationPackage extends MisconceptionSignal {
  topic_name: string;
  evidence_items: {
    evidence_id: string;
    text: string;
    location: Record<string, string | number>;
    modality: string;
    source_title?: string;
    locator_label?: string;
  }[];
}

export type RecommendedAction =
  | "foundational_review"
  | "targeted_practice"
  | "mixed_application"
  | "advance_topic"
  | "spaced_review"
  | "remediate_misconception"
  | "upload_material";

export interface Recommendation {
  learner_id: string;
  recommended_action: RecommendedAction;
  topic_id: string;
  topic_name?: string;
  concept_id?: string | null;
  difficulty: Difficulty;
  rationale: string;
  learner_state_evidence?: Record<string, any>;
  suggested_evidence_ids: string[];
  suggested_question_id?: string | null;
}

export interface AssessmentCycleResult {
  evaluation: AnswerEvaluation;
  mastery: TopicMasteryRecord;
  p_before: number;
  misconception_detected: boolean;
  misconception?: MisconceptionSignal | null;
  next_recommendation: Recommendation;
  answered?: number;
  total?: number;
}

export interface LearnerProfile {
  learner_id: string;
  topic_mastery: Record<string, number>;
  total_attempts: number;
  total_correct: number;
  interaction_count: number;
  active_misconceptions: string[];
  records: TopicMasteryRecord[];
  history: { timestamp: string; topic_id: string; topic_name: string; is_correct: boolean; p_after: number }[];
  meta?: Record<string, any>;
}

export interface CurriculumTopic {
  topic_id: string;
  name: string;
  description: string;
  concepts: string[];
  prerequisites: string[];
  source_id?: string;
  owner?: "you" | "demo";
  question_count?: number;
}

export interface QuizSession {
  session_id: string;
  mode: "practice" | "exam";
  created_at: string;
  topic_ids: string[];
  question_ids: string[];
  questions: Question[];
  answers: Record<string, { answer: string; is_correct: boolean; score: number; status: string }>;
  finished: boolean;
}

export interface QuizReportTopic {
  topic_id: string;
  topic_name: string;
  answered: number;
  correct: number;
  accuracy: number | null;
  mastery_before: number | null;
  mastery_after: number;
  status: "strong" | "developing" | "weak";
}

export interface QuizReport {
  session_id: string;
  mode: string;
  total: number;
  answered: number;
  score: number;
  percent: number;
  topics: QuizReportTopic[];
  weak_topics: QuizReportTopic[];
  misconceptions: MisconceptionSignal[];
  confusions: { concept: string; chosen: string; topic_name: string; note: string }[];
  review: { topic_name: string; citation: Citation }[];
  items: {
    question_id: string;
    prompt: string;
    topic_name: string;
    your_answer: string | null;
    is_correct: boolean;
    status: string;
    expected_answer: string;
    solution: string;
    citation?: Citation;
  }[];
  next_recommendation: Recommendation;
}

export interface Flashcard {
  card_id: string;
  topic_id: string;
  topic_name: string;
  front: string;
  back: string;
  evidence_id: string;
  kind: "definition" | "formula";
  due: string;
  reps: number;
  priority: number;
  citation?: Citation;
}

export interface StudyBlock {
  topic_id: string;
  topic_name: string;
  activity: string;
  minutes: number;
  kind: "practice" | "review" | "exam";
}

export interface StudyPlan {
  exam_date: string;
  days: number;
  minutes_per_day: number;
  plan: { date: string; blocks: StudyBlock[] }[];
  blocks_needed: number;
  blocks_available: number;
  warning: string | null;
  total_minutes: number;
  topics_covered: number;
  topics_total: number;
  empty: boolean;
}

export interface CourseMap {
  nodes: {
    topic_id: string;
    name: string;
    source_id: string;
    depth: number;
    p_mastery: number;
    status: "mastered" | "in_progress" | "ready" | "locked";
    concepts: string[];
  }[];
  edges: { from: string; to: string }[];
}

export interface SystemHealth {
  status: "healthy" | "ok" | "degraded";
  version?: string;
  sqlite_db: { sources_count: number; evidence_count: number; questions_count?: number };
  model_provider?: { active_provider: string; available: boolean };
  embedding_model?: string;
  persistence?: string;
}

export function locatorLabel(c: { location?: Record<string, string | number>; locator_label?: string }): string {
  if (c.locator_label) return c.locator_label;
  const loc = c.location || {};
  if (loc.page !== undefined) return `Page ${loc.page}`;
  if (loc.slide !== undefined) return `Slide ${loc.slide}`;
  if (loc.timestamp !== undefined) return String(loc.timestamp);
  if (loc.section !== undefined) return String(loc.section);
  return "Course material";
}

export const ACTION_LABELS: Record<string, string> = {
  foundational_review: "Foundational review",
  targeted_practice: "Targeted practice",
  mixed_application: "Mixed application",
  advance_topic: "Start next topic",
  spaced_review: "Spaced review",
  remediate_misconception: "Fix a misconception",
  upload_material: "Upload material",
};
