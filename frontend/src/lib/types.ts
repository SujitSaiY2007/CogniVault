/**
 * Typed Data Contracts for CogniVault Product Loop Frontend
 * Strictly aligned with Backend Agno AgentOS and FastAPI models.
 */

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
}

export interface TutorResponse {
  query: string;
  answer: string;
  citations: Citation[];
  is_grounded: boolean;
  is_synthesis?: boolean;
  confidence: number;
  support_status: "supported" | "unsupported" | "error";
  reasoning_steps: string[];
  unsupported_reason?: string | null;
}

export interface SourceRecord {
  source_id: string;
  title: string;
  modality: Modality;
  path: string;
  sha256: string;
  metadata?: Record<string, any>;
  evidence_count?: number;
}

export interface EvidenceUnit {
  evidence_id: string;
  source_id: string;
  modality: Modality;
  text: string;
  location: Record<string, string | number>;
  evidence_type: string;
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
  expected_answer: string;
  tolerance?: number | null;
  solution: string;
  verification_status: "verified" | "rejected" | "unverified";
  verification_reason?: string | null;
  fingerprint: string;
  repetition_count?: number;
}

export interface AnswerEvaluation {
  learner_id: string;
  question_id: string;
  is_correct: boolean;
  status: "correct" | "partially_correct" | "incorrect";
  feedback: string;
  citations: Citation[];
  remediation_action?: string | null;
  remediation_evidence_ids: string[];
}

export interface AssessmentCycleResult {
  evaluation: AnswerEvaluation;
  mastery: TopicMasteryRecord;
  misconception_detected: boolean;
  misconception?: MisconceptionSignal | null;
  next_recommendation: Recommendation;
}

export interface TopicMasteryRecord {
  learner_id: string;
  topic_id: string;
  p_mastery: number;
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

export interface RemediationPackage {
  signal_id?: string;
  learner_id: string;
  topic_id: string;
  concept_id?: string | null;
  suspected_misconception: string;
  confidence: number;
  remediation_concept_id?: string | null;
  remediation_note: string;
  evidence_items: {
    evidence_id: string;
    text: string;
    location: Record<string, string | number>;
    modality: string;
  }[];
}

export interface Recommendation {
  learner_id: string;
  recommended_action:
    | "foundational_review"
    | "targeted_practice"
    | "mixed_application"
    | "advance_topic"
    | "remediate_misconception";
  topic_id: string;
  concept_id?: string | null;
  difficulty: Difficulty;
  rationale: string;
  learner_state_evidence?: Record<string, any>;
  suggested_evidence_ids: string[];
  suggested_question_id?: string | null;
}

export interface LearnerProfile {
  learner_id: string;
  topic_mastery: Record<string, number>;
  total_attempts: number;
  total_correct: number;
  interaction_count: number;
  active_misconceptions: string[];
  records: TopicMasteryRecord[];
}

export interface CurriculumTopic {
  topic_id: string;
  name: string;
  description: string;
  concepts: string[];
  prerequisites: string[];
}

export const DEFAULT_CURRICULUM_TOPICS: CurriculumTopic[] = [
  {
    topic_id: "Newtonian Mechanics",
    name: "Newtonian Mechanics",
    description: "Forces and motion",
    concepts: ["First Law", "Second Law", "Third Law", "Momentum"],
    prerequisites: [],
  },
  {
    topic_id: "Work and Energy",
    name: "Work and Energy",
    description: "Work, kinetic and potential energy",
    concepts: ["Work", "Kinetic Energy"],
    prerequisites: ["Newtonian Mechanics"],
  },
  {
    topic_id: "Wave Properties",
    name: "Wave Properties",
    description: "Wave speed, frequency, wavelength",
    concepts: ["Wave Equation"],
    prerequisites: [],
  },
  {
    topic_id: "Geometric Optics",
    name: "Geometric Optics",
    description: "Reflection and refraction",
    concepts: ["Reflection", "Snell's Law", "Refraction"],
    prerequisites: ["Wave Properties"],
  },
  {
    topic_id: "Algebra",
    name: "Algebra",
    description: "Polynomials and quadratic equations",
    concepts: ["Quadratic Formula", "Discriminant"],
    prerequisites: [],
  },
  {
    topic_id: "Differential Calculus",
    name: "Differential Calculus",
    description: "Limits and derivatives",
    concepts: ["Power Rule", "Trig Derivatives"],
    prerequisites: ["Algebra"],
  },
  {
    topic_id: "Cell Biology",
    name: "Cell Biology",
    description: "Cellular organelles and respiration",
    concepts: ["Cell Theory", "Mitochondria", "Chloroplasts"],
    prerequisites: [],
  },
];

export interface SystemHealth {
  status: "healthy" | "ok" | "degraded";
  sqlite_db: {
    path: string;
    sources_count: number;
    evidence_count: number;
    questions_count?: number;
  };
  chroma_db: {
    persist_directory: string;
    indexed_units: number;
  };
  ollama: {
    host: string;
    available: boolean;
    configured_model: string;
    installed_models: string[];
  };
  agno_agents?: {
    tutor: boolean;
    assessment: boolean;
    learning_coach: boolean;
  };
}
