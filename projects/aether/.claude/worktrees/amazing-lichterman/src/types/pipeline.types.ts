export type PipelineStage =
  | 'upload'
  | 'extract'
  | 'transcribe'
  | 'generate'
  | 'complete';

export type StageStatus = 'pending' | 'active' | 'completed' | 'error';

export interface PipelineState {
  meetingId: string | null;
  currentStage: PipelineStage;
  stages: Record<PipelineStage, StageStatus>;
  progress: number;
  streamingText: string;
  error: string | null;
  estimatedCostUsd: number | null;
}

export const STAGE_LABELS: Record<PipelineStage, string> = {
  upload: 'Загрузка',
  extract: 'Извлечение аудио',
  transcribe: 'Транскрипция',
  generate: 'Генерация артефактов',
  complete: 'Готово',
};

export const STAGE_DESCRIPTIONS: Record<PipelineStage, string> = {
  upload: 'Приём и валидация файла',
  extract: 'Извлечение аудиодорожки через ffmpeg',
  transcribe: 'Распознавание речи через Whisper API',
  generate: 'Генерация артефактов через Claude / GPT',
  complete: 'Все артефакты сохранены',
};
