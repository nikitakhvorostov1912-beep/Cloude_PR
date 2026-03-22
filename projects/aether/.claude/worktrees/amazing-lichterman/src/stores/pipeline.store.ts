import { create } from 'zustand';
import type { PipelineStage, StageStatus, PipelineState } from '@/types/pipeline.types';

const initialStages: Record<PipelineStage, StageStatus> = {
  upload: 'pending',
  extract: 'pending',
  transcribe: 'pending',
  generate: 'pending',
  complete: 'pending',
};

interface PipelineStore extends PipelineState {
  startPipeline: (meetingId: string) => void;
  setStage: (stage: PipelineStage) => void;
  setStageStatus: (stage: PipelineStage, status: StageStatus) => void;
  setProgress: (progress: number) => void;
  appendStreamingText: (text: string) => void;
  setError: (error: string) => void;
  setEstimatedCost: (cost: number) => void;
  resetPipeline: () => void;
}

export const usePipelineStore = create<PipelineStore>()((set) => ({
  meetingId: null,
  currentStage: 'upload',
  stages: { ...initialStages },
  progress: 0,
  streamingText: '',
  error: null,
  estimatedCostUsd: null,

  startPipeline: (meetingId) =>
    set({
      meetingId,
      currentStage: 'upload',
      stages: { ...initialStages, upload: 'active' },
      progress: 0,
      streamingText: '',
      error: null,
    }),

  setStage: (stage) =>
    set((s) => {
      const stages = { ...s.stages };
      const order: PipelineStage[] = ['upload', 'extract', 'transcribe', 'generate', 'complete'];
      const stageIdx = order.indexOf(stage);
      order.forEach((st, i) => {
        if (i < stageIdx) stages[st] = 'completed';
        else if (i === stageIdx) stages[st] = 'active';
      });
      return { currentStage: stage, stages, progress: (stageIdx / (order.length - 1)) * 100 };
    }),

  setStageStatus: (stage, status) =>
    set((s) => ({
      stages: { ...s.stages, [stage]: status },
    })),

  setProgress: (progress) => set({ progress }),
  appendStreamingText: (text) =>
    set((s) => ({ streamingText: s.streamingText + text })),
  setError: (error) =>
    set((s) => ({
      error,
      stages: { ...s.stages, [s.currentStage]: 'error' },
    })),
  setEstimatedCost: (cost) => set({ estimatedCostUsd: cost }),
  resetPipeline: () =>
    set({
      meetingId: null,
      currentStage: 'upload',
      stages: { ...initialStages },
      progress: 0,
      streamingText: '',
      error: null,
      estimatedCostUsd: null,
    }),
}));
