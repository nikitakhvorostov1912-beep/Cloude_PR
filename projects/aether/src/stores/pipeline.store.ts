import { create } from 'zustand';
import { persist } from 'zustand/middleware';
import type { PipelineStage, StageStatus, FileProcessingStatus, PipelineState } from '@/types/pipeline.types';

const initialStages: Record<PipelineStage, StageStatus> = {
  upload: 'pending',
  extract: 'pending',
  transcribe: 'pending',
  generate: 'pending',
  complete: 'pending',
};

interface PipelineStore extends PipelineState {
  startPipeline: (meetingId: string, projectId?: string, files?: Array<{ fileId: string; fileName: string; order: number; sizeBytes: number }>) => void;
  setStage: (stage: PipelineStage) => void;
  setStageStatus: (stage: PipelineStage, status: StageStatus) => void;
  completePipeline: () => void;
  setProgress: (progress: number) => void;
  appendStreamingText: (text: string) => void;
  setError: (error: string) => void;
  setEstimatedCost: (cost: number) => void;
  /** Обновить статус обработки конкретного файла */
  updateFileStatus: (fileId: string, progress: number, status: StageStatus, error: string | null) => void;
  /** Удалить файл из очереди */
  removeFile: (fileId: string) => void;
  /** Изменить порядок файла */
  reorderFile: (fileId: string, newOrder: number) => void;
  resetPipeline: () => void;
}

export const usePipelineStore = create<PipelineStore>()(
  persist(
    (set) => ({
      meetingId: null,
      projectId: null,
      currentStage: 'upload',
      stages: { ...initialStages },
      progress: 0,
      streamingText: '',
      error: null,
      estimatedCostUsd: null,
      fileStatuses: {},
      totalFiles: 0,
      completedFiles: 0,

      startPipeline: (meetingId, projectId, files) => {
        const fileStatuses: Record<string, FileProcessingStatus> = {};
        if (files) {
          for (const f of files) {
            fileStatuses[f.fileId] = {
              fileId: f.fileId,
              fileName: f.fileName,
              order: f.order,
              status: 'pending',
              progress: 0,
              error: null,
              sizeBytes: f.sizeBytes,
            };
          }
        }

        set({
          meetingId,
          projectId: projectId ?? null,
          currentStage: 'upload',
          stages: { ...initialStages, upload: 'active' },
          progress: 0,
          streamingText: '',
          error: null,
          fileStatuses,
          totalFiles: files?.length ?? 0,
          completedFiles: 0,
        });
      },

      setStage: (stage) =>
        set((s) => {
          const stages = { ...s.stages };
          const order: PipelineStage[] = ['upload', 'extract', 'transcribe', 'generate', 'complete'];
          const stageIdx = order.indexOf(stage);
          order.forEach((st, i) => {
            if (i < stageIdx) stages[st] = 'completed';
            else if (i === stageIdx) stages[st] = 'active';
          });
          return { currentStage: stage, stages };
        }),

      completePipeline: () =>
        set((s) => ({
          stages: {
            ...s.stages,
            complete: 'completed',
          },
          progress: 100,
        })),

      setStageStatus: (stage, status) =>
        set((s) => ({
          stages: { ...s.stages, [stage]: status },
        })),

      setProgress: (progress) => set({ progress }),
      appendStreamingText: (text) =>
        set((s) => {
          const combined = s.streamingText + text;
          return { streamingText: combined.length > 10_000 ? combined.slice(-10_000) : combined };
        }),
      setError: (error) =>
        set((s) => ({
          error,
          stages: { ...s.stages, [s.currentStage]: 'error' },
        })),
      setEstimatedCost: (cost) => set({ estimatedCostUsd: cost }),

      updateFileStatus: (fileId, progress, status, error) =>
        set((s) => {
          const prev = s.fileStatuses[fileId];
          if (!prev) return s;

          const updated: FileProcessingStatus = {
            ...prev,
            progress,
            status,
            error,
          };
          const newStatuses = { ...s.fileStatuses, [fileId]: updated };

          // Пересчитываем completedFiles
          const completedFiles = Object.values(newStatuses).filter(
            (f) => f.status === 'completed' || f.status === 'error',
          ).length;

          return { fileStatuses: newStatuses, completedFiles };
        }),

      removeFile: (fileId) =>
        set((s) => {
          const { [fileId]: _removed, ...rest } = s.fileStatuses;
          const totalFiles = Object.keys(rest).length;
          const completedFiles = Object.values(rest).filter(
            (f) => f.status === 'completed' || f.status === 'error',
          ).length;
          return { fileStatuses: rest, totalFiles, completedFiles };
        }),

      reorderFile: (fileId, newOrder) =>
        set((s) => {
          const prev = s.fileStatuses[fileId];
          if (!prev) return s;
          return {
            fileStatuses: {
              ...s.fileStatuses,
              [fileId]: { ...prev, order: newOrder },
            },
          };
        }),

      resetPipeline: () =>
        set({
          meetingId: null,
          projectId: null,
          currentStage: 'upload',
          stages: { ...initialStages },
          progress: 0,
          streamingText: '',
          error: null,
          estimatedCostUsd: null,
          fileStatuses: {},
          totalFiles: 0,
          completedFiles: 0,
        }),
    }),
    {
      name: 'aether-pipeline',
      // Сохраняем только meetingId и stages — стриминг текст, прогресс и fileStatuses не нужны
      // fileStatuses содержит File-подобные данные, не сериализуется
      partialize: (s) => ({
        meetingId: s.meetingId,
        projectId: s.projectId,
        stages: s.stages,
        progress: s.progress,
        currentStage: s.currentStage,
      }),
    }
  )
);
