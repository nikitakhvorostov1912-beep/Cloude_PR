/**
 * Страница обработки AI-пайплайна.
 * Upload → Extract → Transcribe → Generate → Complete
 */

import { useState, useCallback, useRef, useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import { motion } from 'motion/react';
import { AnimatedPage } from '@/components/shared/AnimatedPage';
import { GlassCard } from '@/components/glass';
import { DragDropZone } from '@/components/upload/DragDropZone';
import type { FileInfo } from '@/services/file.service';
import { PipelineStages } from '@/components/pipeline/PipelineStages';
import { StreamingText } from '@/components/pipeline/StreamingText';
import { ArtifactProgress, type ArtifactStatus } from '@/components/pipeline/ArtifactProgress';
import { usePipelineStore } from '@/stores/pipeline.store';
import { useSettingsStore } from '@/stores/settings.store';
import { useProjectsStore } from '@/stores/projects.store';
import { useArtifactsStore } from '@/stores/artifacts.store';
import { useShallow } from 'zustand/react/shallow';
import { runPipeline, type PipelineConfig, type PipelineInputFile, type PipelineOptions } from '@/services/pipeline.service';
import { formatCost, estimateCostBeforeProcessing } from '@/lib/cost-estimator';
import type { ArtifactType } from '@/types/artifact.types';
import { ARTIFACT_ICONS, ARTIFACT_LABELS, ARTIFACT_DESCRIPTIONS } from '@/types/artifact.types';
import type { PipelineStage } from '@/types/pipeline.types';
import { getAudioFile, storeAudioFile } from '@/services/file-storage.service';
import { PROVIDER_NAMES, DEFAULT_STT_MODELS, DEFAULT_LLM_MODELS } from '@/lib/constants';

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
  const llmModel = useSettingsStore((s) => s.llmModel);
  const sttProvider = useSettingsStore((s) => s.sttProvider);
  const routingMode = useSettingsStore((s) => s.routingMode);

  // Pipeline actions
  const startPipeline = usePipelineStore((s) => s.startPipeline);
  const setStage = usePipelineStore((s) => s.setStage);
  const completePipeline = usePipelineStore((s) => s.completePipeline);
  const setProgress = usePipelineStore((s) => s.setProgress);
  const appendStreamingText = usePipelineStore((s) => s.appendStreamingText);
  const setError = usePipelineStore((s) => s.setError);
  const setEstimatedCost = usePipelineStore((s) => s.setEstimatedCost);
  const updateFileStatus = usePipelineStore((s) => s.updateFileStatus);
  const resetPipeline = usePipelineStore((s) => s.resetPipeline);

  // Project store
  const activeProjectId = useProjectsStore((s) => s.activeProjectId);
  const activeMeetingId = useProjectsStore((s) => s.activeMeetingId);
  const setActiveMeeting = useProjectsStore((s) => s.setActiveMeeting);
  const setActiveProject = useProjectsStore((s) => s.setActiveProject);
  const allProjects = useProjectsStore((s) => s.projects);
  const allMeetings = useProjectsStore((s) => s.meetings);
  const addProject = useProjectsStore((s) => s.addProject);
  const addMeeting = useProjectsStore((s) => s.addMeeting);
  const updateMeeting = useProjectsStore((s) => s.updateMeeting);
  const getProjectMeetings = useProjectsStore((s) => s.getProjectMeetings);
  const meetingIdRef = useRef<string | null>(null);

  // Artifacts store
  const addArtifact = useArtifactsStore((s) => s.addArtifact);
  const getArtifactsByMeeting = useArtifactsStore((s) => s.getArtifactsByMeeting);
  const selectedTemplate = useArtifactsStore((s) => s.selectedTemplate);
  const templates = useArtifactsStore((s) => s.templates);

  // Local state
  const [artifactStatuses, setArtifactStatuses] = useState<ArtifactProgressState[]>([]);
  const [qualityWarnings, setQualityWarnings] = useState<string[]>([]);
  const [isRunning, setIsRunning] = useState(false);
  const [costEstimate, setCostEstimate] = useState<string | null>(null);
  const [fileError, setFileError] = useState<string | null>(null);
  const [pendingFiles, setPendingFiles] = useState<FileInfo[]>([]);
  const abortControllerRef = useRef<AbortController | null>(null);

  const activeProject = allProjects.find((p) => p.id === activeProjectId);
  const autoStartedRef = useRef(false);

  // Автозапуск: если пришли со страницы проекта с activeMeetingId
  useEffect(() => {
    if (!activeMeetingId || isRunning || meetingId || autoStartedRef.current) return;
    autoStartedRef.current = true;

    const meeting = allMeetings.find((m) => m.id === activeMeetingId);
    const meetingIdForLookup = activeMeetingId;
    if (!meeting) return;

    const startWithFile = (file: File) => {
      setActiveMeeting(null); // Сбрасываем только после успешного получения файла (P1-C)
      handleStartPipeline([{ file, name: file.name, knownDuration: meeting.durationSeconds }]);
    };

    // 1. Пробуем IndexedDB (переживает перезапуск)
    getAudioFile(meetingIdForLookup)
      .then((file) => {
        if (file) {
          startWithFile(file);
          return;
        }
        // 2. Fallback: blob URL (работает только в текущей сессии)
        if (!meeting.audioPath) {
          setActiveMeeting(null);
          setFileError('Файл не найден. Загрузите запись заново.');
          return;
        }
        return fetch(meeting.audioPath)
          .then((r) => {
            if (!r.ok) throw new Error('Blob URL expired');
            return r.blob();
          })
          .then((blob) => {
            const fileName = meeting.filePath || meeting.title || 'recording';
            startWithFile(new File([blob], fileName, { type: blob.type || 'audio/mpeg' }));
          });
      })
      .catch((err) => {
        console.warn('[Pipeline] File load failed:', err);
        setActiveMeeting(null);
        const detail = err instanceof Error ? err.message : '';
        setFileError(
          detail.includes('Blob URL') || detail.includes('expired')
            ? 'Файл доступен только в рамках одной сессии. Загрузите запись заново.'
            : 'Файл из предыдущей сессии недоступен. Загрузите запись заново.'
        );
      });
  // eslint-disable-next-line react-hooks/exhaustive-deps -- handleStartPipeline intentionally excluded to prevent re-triggers
  }, [activeMeetingId, allMeetings]);

  // Получаем типы артефактов из выбранного шаблона
  const getSelectedArtifactTypes = useCallback((): ArtifactType[] => {
    const template = templates.find((t) => t.id === selectedTemplate);
    return template?.artifactTypes || ['protocol', 'requirements', 'risks', 'glossary', 'questions', 'transcript', 'development'];
  }, [templates, selectedTemplate]);

  // Запуск пайплайна (multi-file)
  const handleStartPipeline = useCallback(async (files: Array<{ file: File; name: string; knownDuration?: number; nativePath?: string }>) => {
    if (isRunning) return;

    // Проверка API-ключей для STT
    const sttKeyMap: Record<string, keyof typeof apiKeys> = {
      groq: 'groqKey', openai: 'openaiKey', gemini: 'geminiKey',
    };
    const sttKeyField = sttKeyMap[sttProvider];
    if (!sttKeyField) {
      setError(`Неизвестный STT-провайдер: ${sttProvider}. Перейдите в настройки.`);
      return;
    }
    if (!apiKeys[sttKeyField]) {
      setError(`Не указан API-ключ ${PROVIDER_NAMES[sttProvider]} (транскрипция). Перейдите в настройки.`);
      return;
    }

    // Проверка API-ключей для LLM
    const llmKeyMap: Record<string, keyof typeof apiKeys> = {
      claude: 'claudeKey', openai: 'openaiKey', gemini: 'geminiKey', groq: 'groqKey',
      deepseek: 'deepseekKey', mimo: 'mimoKey', cerebras: 'cerebrasKey',
      mistral: 'mistralKey', openrouter: 'openrouterKey',
    };

    if (routingMode === 'auto') {
      // В auto-routing достаточно хотя бы одного LLM-ключа
      const hasAnyLLMKey = Object.values(llmKeyMap).some((field) => apiKeys[field]);
      if (!hasAnyLLMKey) {
        setError('Не указан ни один API-ключ для генерации. Перейдите в настройки.');
        return;
      }
    } else {
      const llmKeyField = llmKeyMap[llmProvider];
      if (!llmKeyField) {
        setError(`Неизвестный LLM-провайдер: ${llmProvider}. Перейдите в настройки.`);
        return;
      }
      if (!apiKeys[llmKeyField]) {
        setError(`Не указан API-ключ ${PROVIDER_NAMES[llmProvider]} (генерация). Перейдите в настройки.`);
        return;
      }
    }

    const artifactTypes = getSelectedArtifactTypes();
    const newMeetingId = `meeting-${crypto.randomUUID()}`;

    // Формируем PipelineInputFile[] из массива файлов
    const pipelineFiles: PipelineInputFile[] = files.map((f, i) => ({
      file: f.file,
      fileId: `file-${crypto.randomUUID()}`,
      order: i,
      label: f.name,
      nativePath: f.nativePath,
    }));

    const totalSize = files.reduce((sum, f) => sum + f.file.size, 0);
    const firstFile = files[0];

    // Гарантируем наличие проекта (P1-A: не допускаем orphaned meetings с projectId='default')
    let projectId = activeProjectId;
    if (!projectId) {
      const fallbackId = crypto.randomUUID();
      const now = new Date().toISOString();
      addProject({
        id: fallbackId,
        name: 'Без проекта',
        description: '',
        folder: '',
        meetingIds: [],
        createdAt: now,
        updatedAt: now,
      });
      setActiveProject(fallbackId);
      projectId = fallbackId;
    }

    // Создаём встречу
    addMeeting({
      id: newMeetingId,
      projectId,
      title: files.length === 1
        ? firstFile.name.replace(/\.[^.]+$/, '')
        : `${files.length} записей (${firstFile.name.replace(/\.[^.]+$/, '')}...)`,
      filePath: firstFile.nativePath || firstFile.name,
      audioPath: '',
      durationSeconds: firstFile.knownDuration || 0,
      fileSizeBytes: totalSize,
      qualityScore: 0,
      status: 'processing',
      errorMessage: null,
      createdAt: new Date().toISOString(),
      processedAt: null,
    });

    // Сохраняем первый файл в IndexedDB для возможности переслушивания
    storeAudioFile(newMeetingId, firstFile.file).catch(() => {
      // Некритичная ошибка — файл не сохранён, но пайплайн продолжает работу
    });

    // Сохраняем meetingId для cleanup при abort (P2-B)
    meetingIdRef.current = newMeetingId;

    // Инициализация пайплайна с файлами
    setIsRunning(true);
    const abortController = new AbortController();
    abortControllerRef.current = abortController;
    startPipeline(newMeetingId, projectId, pipelineFiles.map((f) => ({
      fileId: f.fileId,
      fileName: f.label,
      order: f.order,
      sizeBytes: f.file.size,
    })));

    setArtifactStatuses(
      artifactTypes.map((type) => ({ type, status: 'pending' as ArtifactStatus })),
    );

    // Предварительная оценка стоимости
    const preEstimate = estimateCostBeforeProcessing(0, artifactTypes.length, llmProvider);
    setCostEstimate(formatCost(preEstimate));

    // Кумулятивный контекст: собираем артефакты из предыдущих встреч проекта
    let previousArtifacts: Record<string, string> | undefined;
    const projectMeetings = getProjectMeetings(projectId);
    const completedMeetings = projectMeetings
      .filter((m) => m.status === 'completed')
      .sort((a, b) => new Date(a.createdAt).getTime() - new Date(b.createdAt).getTime());

    if (completedMeetings.length > 0) {
      const cumulativeTypes: ArtifactType[] = ['requirements', 'risks', 'glossary', 'questions'];
      const collected: Record<string, string> = {};

      for (const type of cumulativeTypes) {
        const allData: Record<string, unknown>[] = [];
        for (const meeting of completedMeetings) {
          const meetingArtifacts = getArtifactsByMeeting(meeting.id);
          const artifact = meetingArtifacts.find((a) => a.type === type);
          if (artifact?.data) {
            allData.push(artifact.data);
          }
        }
        if (allData.length > 0) {
          collected[type] = JSON.stringify(allData, null, 2);
        }
      }

      if (Object.keys(collected).length > 0) {
        previousArtifacts = collected;
      }
    }

    const config: PipelineConfig = {
      meetingId: newMeetingId,
      projectName: activeProject?.name || 'Проект',
      meetingDate: new Date().toISOString().split('T')[0],
      meetingType: 'обследование',
      artifactTypes,
      provider: llmProvider,
      llmModel: llmModel || undefined,
      sttProvider,
      apiKeys,
      previousArtifacts,
      routingMode,
    };

    try {
      const pipelineOptions: PipelineOptions = { signal: abortController.signal };
      const result = await runPipeline(pipelineFiles, config, {
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
        onFileProgress: (fileId, fileProgress, status, fileError) => {
          updateFileStatus(fileId, fileProgress, status, fileError);
        },
        onArtifactComplete: (type: ArtifactType, data: Record<string, unknown> | null, isEmpty: boolean) => {
          console.log('[Pipeline] onArtifactComplete:', { type, hasData: !!data, isEmpty, dataKeys: data ? Object.keys(data) : null });

          setArtifactStatuses((prev) =>
            prev.map((a) => (a.type === type ? { ...a, status: isEmpty ? 'empty' : 'completed' } : a)),
          );

          if (data && !isEmpty) {
            const artifact = {
              id: `artifact-${type}-${crypto.randomUUID()}`,
              meetingId: newMeetingId,
              type,
              version: 1,
              data,
              llmProvider: type === 'transcript' ? sttProvider : llmProvider,
              llmModel: type === 'transcript' ? DEFAULT_STT_MODELS[sttProvider] : DEFAULT_LLM_MODELS[llmProvider],
              tokensUsed: 0,
              costUsd: 0,
              createdAt: new Date().toISOString(),
            };
            console.log('[Pipeline] addArtifact:', { id: artifact.id, type: artifact.type, meetingId: artifact.meetingId });
            addArtifact(artifact);
          } else {
            console.warn('[Pipeline] SKIPPED addArtifact:', { type, data: data === null ? 'NULL' : 'exists', isEmpty });
          }
        },
        onArtifactError: (type: ArtifactType, errMsg: string) => {
          setArtifactStatuses((prev) =>
            prev.map((a) => (a.type === type ? { ...a, status: 'error', error: errMsg } : a)),
          );
        },
      }, pipelineOptions);

      // Финализация: переводим этап 'complete' из 'active' в 'completed'
      // Проверяем что pipeline не был отменён через handleReset (race condition guard)
      if (!meetingIdRef.current) return; // abort уже обработал cleanup
      if (result.success) {
        completePipeline();
      }

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
    isRunning, apiKeys, llmProvider, sttProvider, activeProjectId, activeProject, getSelectedArtifactTypes,
    startPipeline, setStage, completePipeline, setProgress, appendStreamingText, setError, setEstimatedCost,
    updateFileStatus, addProject, setActiveProject, addMeeting, updateMeeting, addArtifact, selectedTemplate, templates,
    getProjectMeetings, getArtifactsByMeeting,
  ]);

  // Обработка файлов из DragDropZone — только сохраняет в state
  const handleFilesChanged = useCallback((infos: FileInfo[]) => {
    setFileError(null);
    setPendingFiles(infos);
  }, []);

  // Запуск обработки загруженных файлов
  const handleStartFromPending = useCallback(() => {
    if (pendingFiles.length === 0) return;
    handleStartPipeline(pendingFiles.map((info) => ({ file: info.file, name: info.name, knownDuration: info.durationSeconds, nativePath: info.nativePath })));
  }, [pendingFiles, handleStartPipeline]);

  const handleFileError = useCallback((message: string) => {
    setFileError(message);
  }, []);

  // Сброс пайплайна
  const handleReset = useCallback(() => {
    abortControllerRef.current?.abort();
    abortControllerRef.current = null;
    // P2-B: помечаем прерванную встречу как ошибку
    if (meetingIdRef.current) {
      updateMeeting(meetingIdRef.current, { status: 'error', errorMessage: 'Обработка прервана пользователем' });
      meetingIdRef.current = null;
    }
    resetPipeline();
    setArtifactStatuses([]);
    setQualityWarnings([]);
    setIsRunning(false);
    setCostEstimate(null);
  }, [resetPipeline, updateMeeting]);

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
          <DragDropZone
            onFilesProcessed={handleFilesChanged}
            onError={handleFileError}
          />

          {/* Кнопка запуска */}
          {pendingFiles.length > 0 && (
            <motion.button
              initial={{ opacity: 0, y: 8 }}
              animate={{ opacity: 1, y: 0 }}
              onClick={handleStartFromPending}
              className="mt-4 w-full px-6 py-3 rounded-xl bg-primary text-white text-sm font-semibold hover:bg-primary/90 transition-colors"
            >
              Обработать {pendingFiles.length === 1
                ? 'запись'
                : `${pendingFiles.length} ${pendingFiles.length < 5 ? 'записи' : 'записей'}`
              }
            </motion.button>
          )}

          {/* Ошибка файла */}
          {fileError && (
            <GlassCard variant="subtle" padding="sm" className="mt-3 border-error/30">
              <div className="flex items-center gap-2">
                <svg width="16" height="16" viewBox="0 0 16 16" fill="none" className="text-error flex-shrink-0">
                  <circle cx="8" cy="8" r="6.5" stroke="currentColor" strokeWidth="1.2" />
                  <path d="M8 5V9" stroke="currentColor" strokeWidth="1.2" strokeLinecap="round" />
                  <circle cx="8" cy="11.5" r="0.6" fill="currentColor" />
                </svg>
                <p className="text-xs text-error">{fileError}</p>
              </div>
            </GlassCard>
          )}

          {/* Ошибка пайплайна (ключи, конфигурация) */}
          {error && (
            <GlassCard variant="subtle" padding="sm" className="mt-3 border-error/30">
              <div className="flex items-center gap-2">
                <svg width="16" height="16" viewBox="0 0 16 16" fill="none" className="text-error flex-shrink-0">
                  <circle cx="8" cy="8" r="6.5" stroke="currentColor" strokeWidth="1.2" />
                  <path d="M8 5V9" stroke="currentColor" strokeWidth="1.2" strokeLinecap="round" />
                  <circle cx="8" cy="11.5" r="0.6" fill="currentColor" />
                </svg>
                <p className="text-xs text-error">{error}</p>
              </div>
            </GlassCard>
          )}

          {/* Информация о настройках */}
          <div className="flex gap-3 mt-4">
            {/* P2-G: Текущий проект */}
            <div
              className="flex-1 glass-card p-3 transition-all duration-200 hover:-translate-y-0.5"
            >
              <p className="text-xs text-text-muted mb-0.5">Проект</p>
              <p className="text-sm font-medium text-text truncate">
                {activeProject?.name || 'Не выбран'}
              </p>
            </div>

            <div
              className="flex-1 glass-card p-3 transition-all duration-200 hover:-translate-y-0.5"
            >
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
            </div>

            <div
              className="flex-1 glass-card p-3 transition-all duration-200 hover:-translate-y-0.5"
            >
              <p className="text-xs text-text-muted mb-0.5">Провайдер</p>
              <div className="flex items-center justify-between">
                <p className="text-sm font-medium text-text">
                  {PROVIDER_NAMES[llmProvider] || llmProvider}
                </p>
                {(!apiKeys[({ claude: 'claudeKey', openai: 'openaiKey', gemini: 'geminiKey', groq: 'groqKey', deepseek: 'deepseekKey', mimo: 'mimoKey', cerebras: 'cerebrasKey', mistral: 'mistralKey', openrouter: 'openrouterKey' } as const)[llmProvider]] || !apiKeys[({ openai: 'openaiKey', groq: 'groqKey', gemini: 'geminiKey' } as const)[sttProvider]]) && (
                  <button
                    onClick={() => navigate('/settings')}
                    className="text-xs text-warning font-medium"
                  >
                    Настроить
                  </button>
                )}
              </div>
            </div>
          </div>

          {/* Артефакты выбранного шаблона */}
          <div className="mt-4 glass-card p-4">
            <p className="text-xs text-text-muted mb-2.5">
              Будут сгенерированы ({getSelectedArtifactTypes().length})
            </p>
            <div className="grid grid-cols-1 sm:grid-cols-2 gap-2">
              {getSelectedArtifactTypes().map((type) => (
                <div
                  key={type}
                  className="flex items-start gap-2 px-3 py-2.5 glass-card transition-all duration-150 hover:-translate-y-px"
                  title={ARTIFACT_DESCRIPTIONS[type].bestFor}
                >
                  <span className="text-sm flex-shrink-0 text-primary">{ARTIFACT_ICONS[type]}</span>
                  <div className="min-w-0">
                    <p className="text-xs font-medium text-text">{ARTIFACT_LABELS[type]}</p>
                    <p className="text-[11px] text-text-muted leading-snug mt-0.5">
                      {ARTIFACT_DESCRIPTIONS[type].summary}
                    </p>
                  </div>
                </div>
              ))}
            </div>
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
                onClick={() => navigate(`/viewer?meetingId=${meetingId}`)}
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
                  <p className="text-sm font-medium text-error mb-1">
                    {currentStage === 'upload' ? 'Ошибка загрузки файла'
                      : currentStage === 'extract' ? 'Ошибка извлечения аудио'
                      : currentStage === 'transcribe' ? 'Ошибка транскрипции'
                      : currentStage === 'generate' ? 'Ошибка генерации артефактов'
                      : 'Ошибка обработки'}
                  </p>
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
                  onClick={() => navigate(`/viewer?meetingId=${meetingId}`)}
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
