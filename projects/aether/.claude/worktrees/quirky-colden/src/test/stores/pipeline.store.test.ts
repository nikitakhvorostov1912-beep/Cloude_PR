import { describe, it, expect, beforeEach } from 'vitest';
import { usePipelineStore } from '@/stores/pipeline.store';

function resetStore() {
  usePipelineStore.setState({
    meetingId: null,
    currentStage: 'upload',
    stages: {
      upload: 'pending',
      extract: 'pending',
      transcribe: 'pending',
      generate: 'pending',
      complete: 'pending',
    },
    progress: 0,
    streamingText: '',
    error: null,
    estimatedCostUsd: null,
  });
}

describe('usePipelineStore', () => {
  beforeEach(() => {
    resetStore();
  });

  describe('initial state', () => {
    it('has correct defaults', () => {
      const s = usePipelineStore.getState();
      expect(s.meetingId).toBeNull();
      expect(s.currentStage).toBe('upload');
      expect(s.progress).toBe(0);
      expect(s.streamingText).toBe('');
      expect(s.error).toBeNull();
      expect(s.estimatedCostUsd).toBeNull();
      expect(s.stages.upload).toBe('pending');
      expect(s.stages.extract).toBe('pending');
    });
  });

  describe('startPipeline', () => {
    it('sets meetingId and activates upload stage', () => {
      usePipelineStore.getState().startPipeline('meeting-123');
      const s = usePipelineStore.getState();
      expect(s.meetingId).toBe('meeting-123');
      expect(s.stages.upload).toBe('active');
      expect(s.currentStage).toBe('upload');
      expect(s.progress).toBe(0);
      expect(s.streamingText).toBe('');
      expect(s.error).toBeNull();
    });

    it('resets previous error when starting', () => {
      usePipelineStore.getState().setError('Previous error');
      usePipelineStore.getState().startPipeline('new-meeting');
      expect(usePipelineStore.getState().error).toBeNull();
    });
  });

  describe('setStage', () => {
    it('marks previous stages as completed when moving forward', () => {
      usePipelineStore.getState().startPipeline('meeting-1');
      usePipelineStore.getState().setStage('transcribe');
      const s = usePipelineStore.getState();
      expect(s.stages.upload).toBe('completed');
      expect(s.stages.extract).toBe('completed');
      expect(s.stages.transcribe).toBe('active');
      expect(s.currentStage).toBe('transcribe');
    });

    it('calculates progress correctly for generate stage', () => {
      // generate is index 3 out of 4 (0-indexed), order: upload(0), extract(1), transcribe(2), generate(3), complete(4)
      usePipelineStore.getState().setStage('generate');
      const s = usePipelineStore.getState();
      expect(s.progress).toBe(75); // 3/4 * 100
    });

    it('sets progress to 0 for upload stage', () => {
      usePipelineStore.getState().setStage('upload');
      expect(usePipelineStore.getState().progress).toBe(0);
    });

    it('sets progress to 100 for complete stage', () => {
      usePipelineStore.getState().setStage('complete');
      expect(usePipelineStore.getState().progress).toBe(100);
    });
  });

  describe('setStageStatus', () => {
    it('updates status of a specific stage', () => {
      usePipelineStore.getState().setStageStatus('extract', 'active');
      expect(usePipelineStore.getState().stages.extract).toBe('active');
    });

    it('sets stage to error status', () => {
      usePipelineStore.getState().setStageStatus('transcribe', 'error');
      expect(usePipelineStore.getState().stages.transcribe).toBe('error');
    });
  });

  describe('setProgress', () => {
    it('updates progress', () => {
      usePipelineStore.getState().setProgress(42);
      expect(usePipelineStore.getState().progress).toBe(42);
    });
  });

  describe('appendStreamingText', () => {
    it('appends text', () => {
      usePipelineStore.getState().appendStreamingText('Привет ');
      usePipelineStore.getState().appendStreamingText('мир');
      expect(usePipelineStore.getState().streamingText).toBe('Привет мир');
    });

    it('appends to empty string', () => {
      usePipelineStore.getState().appendStreamingText('Первый текст');
      expect(usePipelineStore.getState().streamingText).toBe('Первый текст');
    });
  });

  describe('setError', () => {
    it('sets error message', () => {
      usePipelineStore.getState().startPipeline('meeting-1');
      usePipelineStore.getState().setStage('transcribe');
      usePipelineStore.getState().setError('Ошибка транскрипции');
      const s = usePipelineStore.getState();
      expect(s.error).toBe('Ошибка транскрипции');
      expect(s.stages.transcribe).toBe('error');
    });
  });

  describe('setEstimatedCost', () => {
    it('sets estimated cost', () => {
      usePipelineStore.getState().setEstimatedCost(0.15);
      expect(usePipelineStore.getState().estimatedCostUsd).toBe(0.15);
    });
  });

  describe('resetPipeline', () => {
    it('resets all state to initial', () => {
      usePipelineStore.getState().startPipeline('meeting-1');
      usePipelineStore.getState().setStage('generate');
      usePipelineStore.getState().appendStreamingText('Some text');
      usePipelineStore.getState().setEstimatedCost(0.5);
      usePipelineStore.getState().resetPipeline();
      const s = usePipelineStore.getState();
      expect(s.meetingId).toBeNull();
      expect(s.currentStage).toBe('upload');
      expect(s.progress).toBe(0);
      expect(s.streamingText).toBe('');
      expect(s.error).toBeNull();
      expect(s.estimatedCostUsd).toBeNull();
      expect(s.stages.upload).toBe('pending');
    });
  });
});
