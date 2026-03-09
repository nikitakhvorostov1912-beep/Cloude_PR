import type {
  ProjectListResponse,
  ProjectCreate,
  ProjectResponse,
  PipelineStatus,
  TranscriptListResponse,
  Transcript,
  ProcessListResponse,
  Process,
  GapListResponse,
  RequirementListResponse,
  UploadResponse,
  ImportFolderResponse,
  ApiError,
} from "./types";

const API_BASE = process.env.NEXT_PUBLIC_API_URL || "http://127.0.0.1:8000";

// ----------------------------------------------------------------
// Generic fetch wrapper
// ----------------------------------------------------------------

async function fetchAPI<T>(path: string, options?: RequestInit): Promise<T> {
  const url = `${API_BASE}${path}`;

  const headers: HeadersInit = {
    "Content-Type": "application/json",
    ...(options?.headers as Record<string, string> | undefined),
  };

  // If body is FormData, let the browser set Content-Type (multipart boundary)
  if (options?.body instanceof FormData) {
    delete (headers as Record<string, string>)["Content-Type"];
  }

  const response = await fetch(url, {
    ...options,
    headers,
  });

  if (!response.ok) {
    let detail = `Ошибка запроса: ${response.status} ${response.statusText}`;
    try {
      const errorBody: ApiError = await response.json();
      if (errorBody.detail) {
        detail = errorBody.detail;
      }
    } catch {
      // ignore parse errors — use default detail
    }
    throw new Error(detail);
  }

  // 204 No Content — nothing to parse
  if (response.status === 204) {
    return undefined as T;
  }

  return response.json() as Promise<T>;
}

// ----------------------------------------------------------------
// Project API
// ----------------------------------------------------------------

export const projectsApi = {
  list(): Promise<ProjectListResponse> {
    return fetchAPI<ProjectListResponse>("/api/projects");
  },

  create(data: ProjectCreate): Promise<ProjectResponse> {
    return fetchAPI<ProjectResponse>("/api/projects", {
      method: "POST",
      body: JSON.stringify(data),
    });
  },

  get(id: string): Promise<ProjectResponse> {
    return fetchAPI<ProjectResponse>(`/api/projects/${id}`);
  },

  delete(id: string): Promise<void> {
    return fetchAPI<void>(`/api/projects/${id}`, { method: "DELETE" });
  },
};

// ----------------------------------------------------------------
// Upload API
// ----------------------------------------------------------------

export const uploadApi = {
  audio(projectId: string, file: File): Promise<UploadResponse> {
    const formData = new FormData();
    formData.append("file", file);
    return fetchAPI<UploadResponse>(
      `/api/projects/${projectId}/upload/audio`,
      { method: "POST", body: formData },
    );
  },

  transcript(projectId: string, file: File): Promise<UploadResponse> {
    const formData = new FormData();
    formData.append("file", file);
    return fetchAPI<UploadResponse>(
      `/api/projects/${projectId}/upload/transcript`,
      { method: "POST", body: formData },
    );
  },

  importFolder(projectId: string, path: string): Promise<ImportFolderResponse> {
    return fetchAPI<ImportFolderResponse>(
      `/api/projects/${projectId}/import-folder`,
      { method: "POST", body: JSON.stringify({ path }) },
    );
  },
};

// ----------------------------------------------------------------
// Pipeline API
// ----------------------------------------------------------------

export const pipelineApi = {
  transcribe(projectId: string): Promise<void> {
    return fetchAPI<void>(
      `/api/projects/${projectId}/pipeline/transcribe`,
      { method: "POST" },
    );
  },

  extract(projectId: string): Promise<void> {
    return fetchAPI<void>(
      `/api/projects/${projectId}/pipeline/extract`,
      { method: "POST" },
    );
  },

  generateBpmn(projectId: string): Promise<void> {
    return fetchAPI<void>(
      `/api/projects/${projectId}/pipeline/generate-bpmn`,
      { method: "POST" },
    );
  },

  gapAnalysis(projectId: string, erpConfig?: string): Promise<void> {
    return fetchAPI<void>(
      `/api/projects/${projectId}/pipeline/gap-analysis`,
      {
        method: "POST",
        body: JSON.stringify({ erp_config: erpConfig ?? null }),
      },
    );
  },

  generateTobe(projectId: string): Promise<void> {
    return fetchAPI<void>(
      `/api/projects/${projectId}/pipeline/generate-tobe`,
      { method: "POST" },
    );
  },

  generateDocs(projectId: string): Promise<void> {
    return fetchAPI<void>(
      `/api/projects/${projectId}/pipeline/generate-docs`,
      { method: "POST" },
    );
  },

  status(projectId: string): Promise<PipelineStatus> {
    return fetchAPI<PipelineStatus>(
      `/api/projects/${projectId}/pipeline/status`,
    );
  },
};

// ----------------------------------------------------------------
// Data API
// ----------------------------------------------------------------

export const dataApi = {
  transcripts(projectId: string): Promise<TranscriptListResponse> {
    return fetchAPI<TranscriptListResponse>(
      `/api/projects/${projectId}/transcripts`,
    );
  },

  transcript(projectId: string, id: string): Promise<Transcript> {
    return fetchAPI<Transcript>(
      `/api/projects/${projectId}/transcripts/${id}`,
    );
  },

  processes(projectId: string): Promise<ProcessListResponse> {
    return fetchAPI<ProcessListResponse>(
      `/api/projects/${projectId}/processes`,
    );
  },

  process(projectId: string, id: string): Promise<Process> {
    return fetchAPI<Process>(
      `/api/projects/${projectId}/processes/${id}`,
    );
  },

  updateProcess(
    projectId: string,
    id: string,
    data: Partial<Process>,
  ): Promise<Process> {
    return fetchAPI<Process>(
      `/api/projects/${projectId}/processes/${id}`,
      { method: "PUT", body: JSON.stringify(data) },
    );
  },

  gaps(projectId: string): Promise<GapListResponse> {
    return fetchAPI<GapListResponse>(
      `/api/projects/${projectId}/gaps`,
    );
  },

  requirements(projectId: string): Promise<RequirementListResponse> {
    return fetchAPI<RequirementListResponse>(
      `/api/projects/${projectId}/requirements`,
    );
  },
};

// ----------------------------------------------------------------
// Export API — returns download URLs (not fetched, used as hrefs)
// ----------------------------------------------------------------

export const exportApi = {
  visio(projectId: string, processId: string): string {
    return `${API_BASE}/api/projects/${projectId}/export/visio/${processId}`;
  },

  processDoc(projectId: string): string {
    return `${API_BASE}/api/projects/${projectId}/export/process-doc`;
  },

  requirementsExcel(projectId: string): string {
    return `${API_BASE}/api/projects/${projectId}/export/requirements-excel`;
  },

  requirementsWord(projectId: string): string {
    return `${API_BASE}/api/projects/${projectId}/export/requirements-word`;
  },

  gapReport(projectId: string): string {
    return `${API_BASE}/api/projects/${projectId}/export/gap-report`;
  },

  all(projectId: string): string {
    return `${API_BASE}/api/projects/${projectId}/export/all`;
  },

  /** URL для inline-просмотра SVG-диаграммы процесса */
  svgPreview(projectId: string, processId: string): string {
    return `${API_BASE}/api/projects/${projectId}/export/svg/${processId}`;
  },

  /** URL для скачивания BPMN XML файла */
  bpmn(projectId: string, processId: string): string {
    return `${API_BASE}/api/projects/${projectId}/export/bpmn/${processId}`;
  },
};

/**
 * Загружает содержимое SVG как текст для inline-рендеринга.
 */
export async function fetchSvgContent(
  projectId: string,
  processId: string,
): Promise<string> {
  const url = exportApi.svgPreview(projectId, processId);
  const response = await fetch(url);
  if (!response.ok) {
    throw new Error(`Не удалось загрузить SVG: ${response.status}`);
  }
  return response.text();
}
