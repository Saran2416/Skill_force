// Mirrors contracts/schemas.py — keep in sync with the Pydantic models.

export type SkillSource = "user" | "assessment" | "inferred";

export interface Skill {
  name: string;
  level: number;
  source: SkillSource;
}

export interface UserProfile {
  name: string;
  skills: Skill[];
  certs: string[];
  projects: string[];
  target_role: string;
  target_company: string | null;
}

export type Priority = "must" | "good" | "bonus";

export interface RoleRequirement {
  skill: string;
  level_required: number;
  priority: Priority;
  note: string;
}

export interface RoleRequirements {
  role: string;
  company: string | null;
  requirements: RoleRequirement[];
  tools: string[];
  certs: string[];
  interview_process: string[];
  confidence: "curated" | "ai_estimated";
  disclaimer: string;
}

export type RecommendationType =
  | "project"
  | "cert"
  | "interview_prep"
  | "open_source"
  | "networking";

export interface Recommendation {
  title: string;
  type: RecommendationType;
  why: string;
  effort_hours: number;
}

export interface GapItem {
  skill: string;
  current: number;
  required: number;
  gap: number;
  priority: Priority;
}

export interface GapReport {
  match_percent: number;
  gaps: GapItem[];
  strengths: string[];
}

export interface Resource {
  title: string;
  url: string;
}

export type StepStatus = "todo" | "doing" | "done" | "revision";

export interface RoadmapStep {
  order: number;
  skill: string;
  target_level: number;
  resources: Resource[];
  mini_project: string;
  practice_tasks: string[];
  status: StepStatus;
}

export interface Roadmap {
  steps: RoadmapStep[];
  est_hours: number;
}

export interface QuizQuestion {
  id: string;
  q: string;
  options: string[];
  answer_index: number;
  explanation: string;
}

export interface Quiz {
  skill: string;
  questions: QuizQuestion[];
}

export interface ScoreResult {
  skill: string;
  score_percent: number;
  new_level: number;
  weak: boolean;
}

export interface LogEntry {
  agent: string;
  action: string;
  reason: string;
  timestamp: string;
}

export interface AppState {
  profile: UserProfile;
  requirements: RoleRequirements | null;
  gap: GapReport | null;
  roadmap: Roadmap | null;
  recommendations: Recommendation[];
  scores: ScoreResult[];
  log: LogEntry[];
}

/** Shape returned by agents.career_matcher.radar_data for the gap radar chart. */
export interface RadarData {
  labels: string[];
  current: number[];
  required: number[];
}

/** Shape returned by agents.mentor.explain_changes progress summary. */
export interface ProgressSummary {
  [key: string]: unknown;
}

/* ---------------------------------------------------------------------------
   API response envelopes (server/app.py)
   --------------------------------------------------------------------------- */

export type Theme = "Dark" | "Light";

export interface SessionResponse {
  username: string | null;
  fixture_mode: boolean;
}

export interface StateResponse {
  username: string;
  fixture_mode: boolean;
  state: AppState;
  latest_explanation: string;
  profile_ready: boolean;
}

export interface MetaResponse {
  roles: string[];
  companies: string[];
  known_skills: string[];
  known_certs: string[];
  fixture_mode: boolean;
}

export interface MutationResponse {
  state: AppState;
  latest_explanation: string;
  error: string | null;
}

export interface ScoreResponse extends MutationResponse {
  result: ScoreResult;
}

export interface ChatResponse extends MutationResponse {
  reply: string;
}

export interface SkillRow {
  name: string;
  level: number;
}

export interface RequiredSkillRow {
  skill: string;
  required: number;
  current: number;
  priority: Priority;
  status: "met" | "gap" | "missing";
}

export interface RoadmapProgress {
  done: number;
  total: number;
  percent: number;
  next_step: string | null;
}

export interface DashboardResponse {
  known_languages: SkillRow[];
  required_skills: RequiredSkillRow[];
  advantages: string[];
  disadvantages: string[];
  progress: RoadmapProgress;
}
