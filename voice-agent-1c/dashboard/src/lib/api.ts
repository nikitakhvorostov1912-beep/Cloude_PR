import type {
  CallDetail,
  CallsListResponse,
  DashboardSummary,
  DepartmentsResponse,
  VoicesResponse,
} from "./types";

const API_BASE = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";

async function fetchAPI<T>(path: string): Promise<T> {
  const res = await fetch(`${API_BASE}${path}`);

  if (!res.ok) {
    let message = `Ошибка сервера: ${res.status}`;
    try {
      const body = await res.json();
      if (body.detail) message = body.detail;
    } catch {
      // ignore parse error
    }
    throw new Error(message);
  }

  return res.json() as Promise<T>;
}

export const dashboardApi = {
  summary(period = 7) {
    return fetchAPI<DashboardSummary>(`/api/dashboard/summary?period=${period}`);
  },

  calls(params: { period?: number; limit?: number; offset?: number } = {}) {
    const qs = new URLSearchParams();
    if (params.period) qs.set("period", String(params.period));
    if (params.limit) qs.set("limit", String(params.limit));
    if (params.offset !== undefined) qs.set("offset", String(params.offset));
    return fetchAPI<CallsListResponse>(`/api/dashboard/calls?${qs}`);
  },

  departments(period = 7) {
    return fetchAPI<DepartmentsResponse>(`/api/dashboard/departments?period=${period}`);
  },

  callDetail(callId: string) {
    return fetchAPI<CallDetail>(`/api/dashboard/calls/${callId}`);
  },
};

export const voicesApi = {
  list() {
    return fetchAPI<VoicesResponse>("/api/voices");
  },

  async preview(voiceId: string, text: string, speed: number, emotion: string): Promise<string> {
    const res = await fetch(`${API_BASE}/api/voices/preview`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        voice_id: voiceId,
        text,
        speed,
        emotion,
      }),
    });
    if (!res.ok) {
      const body = await res.json().catch(() => ({}));
      throw new Error(body.detail || `Ошибка синтеза: ${res.status}`);
    }
    const blob = await res.blob();
    return URL.createObjectURL(blob);
  },

  audioUrl(callId: string) {
    return `${API_BASE}/api/calls/${callId}/audio`;
  },
};

export const healthApi = {
  check() {
    return fetchAPI<{ status: string; dialog_ready: boolean }>("/api/health");
  },
};
