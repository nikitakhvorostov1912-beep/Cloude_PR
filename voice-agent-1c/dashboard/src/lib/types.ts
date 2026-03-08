export interface DashboardSummary {
  period_days: number;
  total_calls: number;
  successful_calls: number;
  success_rate: number;
  avg_duration_seconds: number;
  total_tasks_created: number;
  escalation_count: number;
  escalation_rate: number;
}

export interface CallEntry {
  call_id: string;
  caller_number: string;
  client_name: string | null;
  department: string | null;
  priority: string | null;
  duration_seconds: number | null;
  created_at: string;
}

export interface CallsListResponse {
  period_days: number;
  count: number;
  calls: CallEntry[];
}

export interface DepartmentEntry {
  department: string;
  count: number;
  percentage: number;
}

export interface DepartmentsResponse {
  period_days: number;
  departments: DepartmentEntry[];
}

export interface CallDetail {
  id: number;
  mango_call_id: string;
  caller_number: string;
  called_number: string | null;
  client_id: string | null;
  client_name: string | null;
  is_known_client: boolean;
  task_id: string | null;
  department: string | null;
  priority: string | null;
  duration_seconds: number | null;
  event_type: string;
  call_state: string | null;
  direction: string;
  call_started_at: string | null;
  call_ended_at: string | null;
  created_at: string;
  transcript: TranscriptDetail | null;
}

export interface TranscriptDetail {
  id: number;
  full_text: string | null;
  segments: TranscriptSegment[] | null;
  classification: Classification | null;
  confidence: number | null;
}

export interface TranscriptSegment {
  speaker: string;
  text: string;
  start_time: number;
  end_time: number;
}

export interface Classification {
  department: string;
  product: string;
  task_type: string;
  priority: string;
  description: string;
  summary: string;
  confidence: number;
}

export interface VoiceInfo {
  id: string;
  name: string;
  gender: "male" | "female";
  description: string;
  emotions: string[];
  sample_text: string;
}

export interface VoicesResponse {
  voices: VoiceInfo[];
  active_voice: string;
  tts_available: boolean;
  mode: "yandex" | "demo";
}
