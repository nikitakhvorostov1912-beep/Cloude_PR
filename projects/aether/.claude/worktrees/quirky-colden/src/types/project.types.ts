export interface Project {
  id: string;
  name: string;
  description: string;
  folder: string;
  createdAt: string;
  updatedAt: string;
}

export interface Meeting {
  id: string;
  projectId: string;
  title: string;
  filePath: string;
  audioPath: string;
  durationSeconds: number;
  fileSizeBytes: number;
  qualityScore: number;
  status: MeetingStatus;
  errorMessage: string | null;
  createdAt: string;
  processedAt: string | null;
}

export type MeetingStatus = 'uploaded' | 'processing' | 'completed' | 'error';
