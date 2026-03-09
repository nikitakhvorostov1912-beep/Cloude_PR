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
  status: string;
  pipeline_state: Record<string, unknown> & { completed_stages?: string[] };
}

export interface ProjectCreate {
  name: string;
  description?: string;
}

export interface ProjectListResponse {
  projects: Project[];
  total: number;
}

export type ProjectResponse = Project;

// --- Pipeline ---

export type PipelineStage =
  | "upload"
  | "transcribe"
  | "extract"
  | "generate-bpmn"
  | "gap-analysis"
  | "generate-tobe"
  | "generate-docs";

export type StageStatus =
  | "pending"
  | "running"
  | "completed"
  | "error"
  | "skipped";

export interface PipelineStatus {
  project_id?: string;
  current_stage?: string | null;
  stages: StageInfo[];
  completed_stages?: string[];
  overall_progress: number;
}

export interface StageInfo {
  name: string;
  label: string;
  status: StageStatus;
  progress: number;
  error: string | null;
  completed: boolean;
}

// --- Transcript ---
// Backend returns: id, filename, dialogue, full_text, metadata, speaker_stats

export interface Transcript {
  id: string;
  filename: string;
  // Backend fields
  dialogue?: TranscriptSegment[];
  full_text?: string;
  metadata?: Record<string, unknown>;
  speaker_stats?: Record<string, unknown>;
  // Frontend convenience fields (mapped from backend data)
  project_id?: string;
  source_type?: "audio" | "text" | "imported";
  language?: string;
  duration_seconds?: number | null;
  speaker_count?: number;
  text?: string;
  segments?: TranscriptSegment[];
  created_at?: string;
}

export interface TranscriptSegment {
  id?: string;
  speaker: string;
  start_time?: number;
  end_time?: number;
  text: string;
}

// Backend returns list[TranscriptResponse] (flat array)
export type TranscriptListResponse = Transcript[];

// --- Process ---

export interface Process {
  id: string;
  name: string;
  description: string;
  department: string;
  trigger: string;
  result: string;
  participants: (string | { role?: string; department?: string })[];
  steps: ProcessStep[];
  decisions: Decision[];
  pain_points: (PainPoint | string)[];
  integrations: string[];
  metrics: Record<string, string | number>;
  status: "draft" | "reviewed" | "approved";
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
  condition?: string;
  yes_branch?: string;
  no_branch?: string;
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
// Backend returns mixed field names; accept both variants

export interface Gap {
  id: string;
  process_id?: string;
  process_name: string;
  // Frontend names
  description?: string;
  gap_type?: string;
  severity?: string;
  effort_estimate?: string | null;
  // Backend names
  function_name?: string;
  coverage?: string | number;
  gap_description?: string;
  effort_days?: number;
  priority?: string;
  erp_module?: string | null;
  erp_document?: string;
  recommendation?: string;
}

export interface GapSummary {
  total_gaps?: number;
  by_severity?: Record<string, number>;
  by_type?: Record<string, number>;
  [key: string]: unknown;
}

export interface GapListResponse {
  gaps: Gap[];
  total: number;
  summary: GapSummary;
}

// --- Requirements ---
// Backend returns raw JSON; accept both frontend and backend field names

export interface Requirement {
  id: string;
  // Frontend field names
  title?: string;
  description?: string;
  requirement_type?: string;
  priority?: string;
  status?: string;
  acceptance_criteria?: string[];
  // Backend field names
  type?: string;
  module?: string;
  source?: string;
  effort?: string;
  [key: string]: unknown;
}

export interface RequirementListResponse {
  requirements: Requirement[];
  total: number;
}

// --- Upload responses ---
// Backend: { message, file_id, filename }

export interface UploadResponse {
  message: string;
  file_id: string;
  filename: string;
}

// Backend: { message, imported_files, skipped_files, total_imported }

export interface ImportFolderResponse {
  message: string;
  imported_files: string[];
  skipped_files: string[];
  total_imported: number;
}

// --- API error ---

export interface ApiError {
  detail: string;
  error_code?: string;
}
