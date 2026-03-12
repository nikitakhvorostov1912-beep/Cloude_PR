export type ArtifactType =
  | 'protocol'
  | 'requirements'
  | 'risks'
  | 'glossary'
  | 'questions'
  | 'transcript';

export interface Artifact {
  id: string;
  meetingId: string;
  type: ArtifactType;
  version: number;
  data: Record<string, unknown>;
  llmProvider: 'claude' | 'openai';
  llmModel: string;
  tokensUsed: number;
  costUsd: number;
  createdAt: string;
}

export interface Template {
  id: string;
  name: string;
  description: string;
  artifactTypes: ArtifactType[];
  customPrompt: string | null;
  isPreset: boolean;
  createdAt: string;
}

export const ARTIFACT_LABELS: Record<ArtifactType, string> = {
  protocol: 'Протокол',
  requirements: 'Требования',
  risks: 'Карта рисков',
  glossary: 'Глоссарий',
  questions: 'Открытые вопросы',
  transcript: 'Стенограмма',
};

export const ARTIFACT_ICONS: Record<ArtifactType, string> = {
  protocol: '📋',
  requirements: '📝',
  risks: '⚠️',
  glossary: '📖',
  questions: '❓',
  transcript: '🎙️',
};
