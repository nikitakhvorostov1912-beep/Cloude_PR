/**
 * Страница обработки AI-пайплайна.
 * Upload → Extract → Transcribe → Generate → Complete
 */

import { useState, useCallback, useRef } from 'react';
import { useNavigate } from 'react-router-dom';
import { motion } from 'motion/react';
import { AnimatedPage } from '@/components/shared/AnimatedPage';
import { GlassCard } from '@/components/glass';
import { PipelineStages } from '@/components/pipeline/PipelineStages';
import { StreamingText } from '@/components/pipeline/StreamingText';
import { ArtifactProgress, type ArtifactStatus } from '@/components/pipeline/ArtifactProgress';
import { usePipelineStore } from '@/stores/pipeline.store';
import { useSettingsStore } from '@/stores/settings.store';
import { useProjectsStore } from '@/stores/projects.store';
import { useArtifactsStore } from '@/stores/artifacts.store';
import { useShallow } from 'zustand/react/shallow';
import { runPipeline, type PipelineConfig } from '@/services/pipeline.service';
import { formatCost, estimateCostBeforeProcessing } from '@/lib/cost-estimator';
import type { ArtifactType } from '@/types/artifact.types';
import type { PipelineStage } from '@/types/pipeline.types';

interface ArtifactProgressState {
  type: ArtifactType;
  status: ArtifactStatus;
  error?: string;
}

export function PipelinePage() {
  const navigate = useNavigate();

  // Pipeline store
  const { meetingId, stages, streamingText, progress, error, currentStage } = usePipelineStore(
    useShallow((s) => ({
      meetingId: s.meetingId,
      stages: s.stages,
      streamingText: s.streamingText,
      progress: s.progress,
      error: s.error,
      currentStage: s.currentStage,
    })),
  );

  // Settings
  const apiKeys = useSettingsStore((s) => s.apiKeys);
  const llmProvider = useSettingsStore((s) => s.llmProvider);

  // Pipeline actions
  const startPipeline = usePipelineStore((s) => s.startPipeline);
  const setStage = usePipelineStore((s) => s.setStage);
  const setProgress = usePipelineStore((s) => s.setProgress);
  const appendStreamingText = usePipelineStore((s) => s.appendStreamingText);
  const setError = usePipelineStore((s) => s.setError);
  const setEstimatedCost = usePipelineStore((s) => s.setEstimatedCost);
  const resetPipeline = usePipelineStore((s) => s.resetPipeline);

  // Project store
  const activeProjectId = useProjectsStore((s) => s.activeProjectId);
  const allProjects = useProjectsStore((s) => s.projects);
  const addMeeting = useProjectsStore((s) => s.addMeeting);
  const updateMeeting = useProjectsStore((s) => s.updateMeeting);

  // Artifacts store
  const addArtifact = useArtifactsStore((s) => s.addArtifact);
  const selectedTemplate = useArtifactsStore((s) => s.selectedTemplate);
  const templates = useArtifactsStore((s) => s.templates);

  // Local state
  const [artifactStatuses, setArtifactStatuses] = useState<ArtifactProgressState[]>([]);
  const [qualityWarnings, setQualityWarnings] = useState<string[]>([]);
  const [isRunning, setIsRunning] = useState(false);
  const [costEstimate, setCostEstimate] = useState<string | null>(null);
  const abortRef = useRef(false);

  const activeProject = allProjects.find((p) => p.id === activeProjectId);

  // Получаем типы артефактов из выбранного шаблона
  const getSelectedArtifactTypes = useCallback((): ArtifactType[] => {
    const template = templates.find((t) => t.id === selectedTemplate);
    return template?.artifactTypes || ['protocol', 'requirements', 'risks', 'glossary', 'questions', 'transcript'];
  }, [templates, selectedTemplate]);

  // Запуск пайплайна
  const handleStartPipeline = useCallback(async (file: File) => {
    if (isRunning) return;

    // Проверка API-ключей
    if (!apiKeys.openaiKey) {
      setError('Не указан API-ключ OpenAI. Перейдите в настройки.');
      return;
    }

    const llmKey = llmProvider === 'claude' ? apiKeys.claudeKey : apiKeys.openaiKey;
    if (!llmKey) {
      setError(`Не указан API-ключ ${llmProvider === 'claude' ? 'Claude' : 'OpenAI'}. Перейдите в настройки.`);
      return;
    }

    const artifactTypes = getSelectedArtifactTypes();
    const newMeetingId = `meeting-${Date.now()}`;

    // Создаём встречу
    addMeeting({
      id: newMeetingId,
      projectId: activeProjectId || 'default',
      title: file.name.replace(/\.[^.]+$/, ''),
      filePath: file.name,
      audioPath: '',
      durationSeconds: 0,
      fileSizeBytes: file.size,
      qualityScore: 0,
      status: 'processing',
      errorMessage: null,
      createdAt: new Date().toISOString(),
      processedAt: null,
    });

    // Инициализация пайплайна
    setIsRunning(true);
    abortRef.current = false;
    startPipeline(newMeetingId);

    setArtifactStatuses(
      artifactTypes.map((type) => ({ type, status: 'pending' as ArtifactStatus })),
    );

    // Предварительная оценка стоимости
    const preEstimate = estimateCostBeforeProcessing(0, artifactTypes.length, llmProvider);
    setCostEstimate(formatCost(preEstimate));

    const config: PipelineConfig = {
      meetingId: newMeetingId,
      projectName: activeProject?.name || 'Проект',
      meetingDate: new Date().toISOString().split('T')[0],
      meetingType: 'обследование',
      artifactTypes,
      provider: llmProvider,
      apiKeys,
    };

    try {
      const result = await runPipeline(file, config, {
        onStageChange: (stage: PipelineStage) => {
          setStage(stage);
        },
        onProgress: (p: number) => {
          setProgress(p);
        },
        onStreamingText: (text: string) => {
          appendStreamingText(text);
        },
        onError: (err: string) => {
          setError(err);
        },
        onCostEstimate: (cost: number) => {
          setEstimatedCost(cost);
          setCostEstimate(formatCost(cost));
        },
        onQualityWarnings: (warnings: string[]) => {
          setQualityWarnings(warnings);
        },
        onArtifactComplete: (type: ArtifactType, data: Record<string, unknown> | null, isEmpty: boolean) => {
          setArtifactStatuses((prev) =>
            prev.map((a) => (a.type === type ? { ...a, status: isEmpty ? 'empty' : 'completed' } : a)),
          );

          if (data && !isEmpty) {
            addArtifact({
              id: `artifact-${type}-${Date.now()}`,
              meetingId: newMeetingId,
              type,
              version: 1,
              data,
              llmProvider: type === 'transcript' ? 'openai' : llmProvider,
              llmModel: type === 'transcript' ? 'whisper-1' : (llmProvider === 'claude' ? 'claude-sonnet-4-20250514' : 'gpt-4o'),
              tokensUsed: 0,
              costUsd: 0,
              createdAt: new Date().toISOString(),
            });
          }
        },
        onArtifactError: (type: ArtifactType, errMsg: string) => {
          setArtifactStatuses((prev) =>
            prev.map((a) => (a.type === type ? { ...a, status: 'error', error: errMsg } : a)),
          );
        },
      });

      updateMeeting(newMeetingId, {
        status: result.success ? 'completed' : 'error',
        processedAt: new Date().toISOString(),
        durationSeconds: result.transcript?.duration || 0,
        errorMessage: result.errors.length > 0 ? result.errors.join('; ') : null,
      });
    } catch (err) {
      const message = err instanceof Error ? err.message : 'Неизвестная ошибка';
      setError(message);
      updateMeeting(newMeetingId, { status: 'error', errorMessage: message });
    } finally {
      setIsRunning(false);
    }
  }, [
    isRunning, apiKeys, llmProvider, activeProjectId, activeProject, getSelectedArtifactTypes,
    startPipeline, setStage, setProgress, appendStreamingText, setError, setEstimatedCost,
    addMeeting, updateMeeting, addArtifact, selectedTemplate, templates,
  ]);

  // Сброс пайплайна
  const handleReset = useCallback(() => {
    resetPipeline();
    setArtifactStatuses([]);
    setQualityWarnings([]);
    setIsRunning(false);
    setCostEstimate(null);
    abortRef.current = true;
  }, [resetPipeline]);

  // === Пустое состояние: выбор файла ===
  if (!meetingId && !isRunning) {
    return (
      <AnimatedPage>
        <div className="max-w-3xl mx-auto">
          <h1 className="text-2xl font-bold text-text mb-2">Обработка записи</h1>
          <p className="text-sm text-text-secondary mb-8">
            Загрузите аудио или видеозапись встречи для извлечения артефактов
          </p>

          {/* Зона загрузки */}
          <GlassCard variant="default" padding="lg" className="text-center">
            <div className="mb-4">
              <svg width="48" height="48" viewBox="0 0 48 48" fill="none" className="mx-auto text-primary/40">
                <path d="M14 30L24 20L34 30" stroke="currentColor" strokeWidth="2.5" strokeLinecap="round" strokeLinejoin="round" />
                <path d="M24 20V40" stroke="currentColor" strokeWidth="2.5" strokeLinecap="round" />
                <path d="M40 32C40 36.4183 36.4183 40 32 40H16C11.5817 40 8 36.4183 8 32V16C8 11.5817 11.5817 8 16 8H32C36.4183 8 40 11.5817 40 16" stroke="currentColor" strokeWidth="2.5" strokeLinecap="round" />
              </svg>
            </div>
            <p className="text-sm text-text mb-1">Перетащите файл или нажмите для выбора</p>
            <p className="text-xs text-text-muted mb-4">MP3, WAV, M4A, MP4, MKV, WEBM и другие</p>

            <label className="inline-flex items-center gap-2 px-5 py-2.5 rounded-xl bg-primary text-white cursor-pointer hover:bg-primary/90 transition-colors">
              <svg width="16" height="16" viewBox="0 0 16 16" fill="none">
                <path d="M8 3V13M3 8H13" stroke="currentColor" strokeWidth="2" strokeLinecap="round" />
              </svg>
              <span className="text-sm font-medium">Выбрать файл</span>
              <input
                type="file"
                className="hidden"
                accept="audio/*,video/*,.mp3,.wav,.m4a,.ogg,.flac,.aac,.mp4,.mkv,.webm,.mov"
                onChange={(e) => {
                  const file = e.target.files?.[0];
                  if (file) handleStartPipeline(file);
                }}
              />
            </label>
          </GlassCard>

          {/* Информация о настройках */}
          <div className="flex gap-3 mt-4">
            <GlassCard variant="subtle" padding="sm" className="flex-1">
              <p className="text-xs text-text-muted mb-0.5">Шаблон</p>
              <div className="flex items-center justify-between">
                <p className="text-sm font-medium text-text">
                  {templates.find((t) => t.id === selectedTemplate)?.name || 'Полный пакет'}
                </p>
                <button
                  onClick={() => navigate('/templates')}
                  className="text-xs text-primary hover:text-primary/80"
                >
                  Изменить
                </button>
              </div>
            </GlassCard>

            <GlassCard variant="subtle" padding="sm" className="flex-1">
              <p className="text-xs text-text-muted mb-0.5">Провайдер</p>
              <div className="flex items-center justify-between">
                <p className="text-sm font-medium text-text">
                  {llmProvider === 'claude' ? 'Claude' : 'OpenAI'}
                </p>
                {!apiKeys.openaiKey && (
                  <button
                    onClick={() => navigate('/settings')}
                    className="text-xs text-warning font-medium"
                  >
                    Настроить
                  </button>
                )}
              </div>
            </GlassCard>
          </div>
        </div>
      </AnimatedPage>
    );
  }

  // === Пайплайн запущен / завершён ===
  return (
    <AnimatedPage>
      <div className="max-w-3xl mx-auto">
        {/* Header */}
        <div className="flex items-center justify-between mb-6">
          <div>
            <h1 className="text-2xl font-bold text-text">Обработка</h1>
            <p className="text-sm text-text-secondary mt-0.5">
              {Math.round(progress)}%
              {costEstimate && <span className="ml-2 text-text-muted">~{costEstimate}</span>}
            </p>
          </div>

          <div className="flex gap-2">
            {stages.complete === 'completed' && (
              <motion.button
                initial={{ opacity: 0, scale: 0.9 }}
                animate={{ opacity: 1, scale: 1 }}
                onClick={() => navigate(`/viewer/${meetingId}`)}
                className="px-4 py-2 rounded-xl bg-primary text-white text-sm font-medium hover:bg-primary/90 transition-colors"
              >
                Просмотр артефактов
              </motion.button>
            )}
            <button
              onClick={handleReset}
              className="px-4 py-2 rounded-xl glass text-sm text-text-secondary hover:text-text transition-colors"
            >
              {stages.complete === 'completed' ? 'Новая обработка' : 'Сбросить'}
            </button>
          </div>
        </div>

        {/* Предупреждения о качестве (EC-05) */}
        {qualityWarnings.length > 0 && (
          <motion.div
            initial={{ opacity: 0, y: -10 }}
            animate={{ opacity: 1, y: 0 }}
            className="mb-4"
          >
            <GlassCard variant="subtle" padding="sm" className="border-warning/30">
              <div className="flex items-start gap-2">
                <span className="text-warning text-sm mt-0.5">⚠</span>
                <div>
                  <p className="text-sm font-medium text-warning">Низкое качество аудио</p>
                  <p className="text-xs text-text-secondary mt-0.5">
                    {qualityWarnings.join('. ')}. Точность транскрипции может быть снижена.
                  </p>
                </div>
              </div>
            </GlassCard>
          </motion.div>
        )}

        {/* Этапы пайплайна */}
        <div className="mb-6">
          <PipelineStages stages={stages} progress={progress} />
        </div>

        {/* Прогресс артефактов */}
        {artifactStatuses.length > 0 && (currentStage === 'generate' || stages.complete === 'completed') && (
          <div className="mb-6">
            <h3 className="text-sm font-semibold text-text mb-3">Артефакты</h3>
            <ArtifactProgress items={artifactStatuses} />
          </div>
        )}

        {/* Стриминг текста */}
        <div className="mb-6">
          <StreamingText
            text={streamingText}
            isActive={isRunning && currentStage !== 'complete'}
          />
        </div>

        {/* Ошибка */}
        {error && (
          <motion.div
            initial={{ opacity: 0, y: 10 }}
            animate={{ opacity: 1, y: 0 }}
          >
            <GlassCard variant="subtle" padding="md" className="border-error/30">
              <div className="flex items-start gap-3">
                <div className="w-8 h-8 rounded-lg bg-error/15 flex items-center justify-center flex-shrink-0">
                  <svg width="16" height="16" viewBox="0 0 16 16" fill="none" className="text-error">
                    <path d="M4 4L12 12M4 12L12 4" stroke="currentColor" strokeWidth="2" strokeLinecap="round" />
                  </svg>
                </div>
                <div>
                  <p className="text-sm font-medium text-error mb-1">Ошибка обработки</p>
                  <p className="text-xs text-text-secondary">{error}</p>
                  <button
                    onClick={handleReset}
                    className="mt-2 text-xs text-primary hover:text-primary/80 transition-colors font-medium"
                  >
                    Попробовать снова
                  </button>
                </div>
              </div>
            </GlassCard>
          </motion.div>
        )}

        {/* Результаты — завершение */}
        {stages.complete === 'completed' && (
          <motion.div
            initial={{ opacity: 0, y: 20 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ delay: 0.3 }}
          >
            <GlassCard variant="default" padding="md" className="border-success/20">
              <div className="flex items-center gap-3 mb-4">
                <div className="w-10 h-10 rounded-xl bg-success/15 flex items-center justify-center">
                  <svg width="20" height="20" viewBox="0 0 20 20" fill="none" className="text-success">
                    <path d="M4 10L8.5 14.5L16 5.5" stroke="currentColor" strokeWidth="2.5" strokeLinecap="round" strokeLinejoin="round" />
                  </svg>
                </div>
                <div>
                  <p className="text-sm font-semibold text-text">Обработка завершена</p>
                  <p className="text-xs text-text-secondary">
                    {artifactStatuses.filter((a) => a.status === 'completed').length} артефактов готово
                    {costEstimate && ` • ${costEstimate}`}
                  </p>
                </div>
              </div>

              <div className="flex gap-2">
                <button
                  onClick={() => navigate(`/viewer/${meetingId}`)}
                  className="flex-1 px-4 py-2.5 rounded-xl bg-primary text-white text-sm font-medium hover:bg-primary/90 transition-colors"
                >
                  Открыть артефакты
                </button>
                <button
                  onClick={handleReset}
                  className="px-4 py-2.5 rounded-xl glass text-sm text-text-secondary hover:text-text transition-colors"
                >
                  Обработать ещё
                </button>
              </div>
            </GlassCard>
          </motion.div>
        )}
      </div>
    </AnimatedPage>
  );
}
