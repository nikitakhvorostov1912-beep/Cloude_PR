const API_BASE = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";

async function fetchAPI<T>(path: string, init?: RequestInit): Promise<T> {
  const res = await fetch(`${API_BASE}${path}`, {
    ...init,
    headers: {
      "Content-Type": "application/json",
      ...init?.headers,
    },
  });
  if (!res.ok) {
    throw new Error(`API error: ${res.status} ${res.statusText}`);
  }
  return res.json() as Promise<T>;
}

export interface KPIData {
  active_calls: number;
  ai_accuracy: number;
  avg_handle_time_sec: number;
  queue_size: number;
  calls_today: number;
  tasks_created_today: number;
  escalations_today: number;
}

export interface CallItem {
  call_id: string;
  phone: string;
  client_name: string;
  department: string;
  priority: string;
  status: string;
  created_at: string;
  duration_sec: number;
}

export interface CallsResponse {
  calls: CallItem[];
  total: number;
  page: number;
  per_page: number;
  pages: number;
}

export interface HealthResponse {
  status: string;
  env: string;
  uptime_seconds: number;
  version: string;
}

export const api = {
  getHealth: () => fetchAPI<HealthResponse>("/health"),
  getKPIs: () => fetchAPI<KPIData>("/api/dashboard/kpis"),
  getCalls: (page = 1) => fetchAPI<CallsResponse>(`/api/dashboard/calls?page=${page}`),
  getCallDetail: (id: string) => fetchAPI<Record<string, unknown>>(`/api/dashboard/calls/${id}`),
};

export function createCallWebSocket(callId: string): WebSocket {
  const wsBase = API_BASE.replace(/^http/, "ws");
  return new WebSocket(`${wsBase}/ws/call/${callId}`);
}
