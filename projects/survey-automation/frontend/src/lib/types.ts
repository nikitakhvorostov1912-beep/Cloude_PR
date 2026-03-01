// ============================================================
// TypeScript types matching backend Pydantic models
// ============================================================

// --- Project ---

export interface Project {
  id: string;
  name: string;
  description: string;
  created_at: string;
  updated_at: string;
  status: ProjectStatus;
  pipeline_state: PipelineState;
}

export type ProjectStatus =
  | "new"
  | "in_progress"
  | "completed"
  | "error";

export interface ProjectCreate {
  name: string;
  description?: string;
}

export interface ProjectListResponse {
  projects: Project[];
  total: number;
}

export interface ProjectResponse {
  project: Project;
}

// --- Pipeline ---

export interface PipelineState {
  stage: PipelineStage;
  progress: number;
  completed_stages: PipelineStage[];
  current_stage_status: StageStatus;
  error: string | null;
}

export type PipelineStage =
  | "upload"
  | "transcribe"
  | "extract"
  | "generate_bpmn"
  | "gap_analysis"
  | "generate_tobe"
  | "generate_docs";

export type StageStatus =
  | "pending"
  | "running"
  | "completed"
  | "error"
  | "skipped";

export interface PipelineStatus {
  stages: StageInfo[];
  overall_progress: number;
}

export interface StageInfo {
  name: PipelineStage;
  label: string;
  status: StageStatus;
  progress: number;
  error: string | null;
  completed: boolean;
}

// --- Transcript ---

export interface Transcript {
  id: string;
  project_id: string;
  filename: string;
  source_type: "audio" | "text" | "imported";
  language: string;
  duration_seconds: number | null;
  speaker_count: number;
  text: string;
  segments: TranscriptSegment[];
  created_at: string;
}

export interface TranscriptSegment {
  id: string;
  speaker: string;
  start_time: number;
  end_time: number;
  text: string;
}

export interface TranscriptListResponse {
  transcripts: Transcript[];
  total: number;
}

// --- Process ---

export interface Process {
  id: string;
  project_id: string;
  name: string;
  description: string;
  department: string;
  participants: string[];
  steps: ProcessStep[];
  decisions: Decision[];
  pain_points: PainPoint[];
  source_transcript_ids: string[];
  bpmn_xml: string | null;
  status: "draft" | "reviewed" | "approved";
  created_at: string;
  updated_at: string;
}

export interface ProcessStep {
  id: string;
  order: number;
  name: string;
  description: string;
  actor: string;
  system: string | null;
  inputs: string[];
  outputs: string[];
  duration_estimate: string | null;
  step_type: "task" | "subprocess" | "manual" | "service" | "script";
}

export interface Decision {
  id: string;
  after_step_id: string;
  question: string;
  options: DecisionOption[];
}

export interface DecisionOption {
  label: string;
  target_step_id: string;
}

export interface PainPoint {
  id: string;
  step_id: string | null;
  description: string;
  severity: "low" | "medium" | "high" | "critical";
  category: string;
}

export interface ProcessListResponse {
  processes: Process[];
  total: number;
}

// --- Gap Analysis ---

export interface Gap {
  id: string;
  project_id: string;
  process_id: string;
  process_name: string;
  description: string;
  gap_type: "missing_feature" | "customization" | "integration" | "workflow" | "data_migration";
  severity: "low" | "medium" | "high" | "critical";
  erp_module: string | null;
  recommendation: string;
  effort_estimate: string | null;
  created_at: string;
}

export interface GapListResponse {
  gaps: Gap[];
  total: number;
  summary: GapSummary;
}

export interface GapSummary {
  total_gaps: number;
  by_severity: Record<string, number>;
  by_type: Record<string, number>;
}

// --- Requirements ---

export interface Requirement {
  id: string;
  project_id: string;
  process_id: string | null;
  gap_id: string | null;
  title: string;
  description: string;
  requirement_type: "functional" | "non_functional" | "integration" | "data" | "security";
  priority: "low" | "medium" | "high" | "critical";
  status: "draft" | "reviewed" | "approved" | "rejected";
  acceptance_criteria: string[];
  created_at: string;
}

export interface RequirementListResponse {
  requirements: Requirement[];
  total: number;
}

// --- Upload responses ---

export interface UploadResponse {
  id: string;
  filename: string;
  size: number;
  status: string;
  message: string;
}

export interface ImportFolderResponse {
  imported_count: number;
  files: string[];
  message: string;
}

// --- API error ---

export interface ApiError {
  detail: string;
  status_code: number;
}
