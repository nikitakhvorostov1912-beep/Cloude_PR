/**
 * Страница просмотра артефактов.
 * Показывает результаты обработки с табами для каждого типа.
 * Без meetingId — показывает список всех встреч с артефактами.
 */

import { useState, useMemo, useCallback } from 'react';
import { useSearchParams, useNavigate } from 'react-router-dom';
import { motion } from 'motion/react';
import { AnimatedPage } from '@/components/shared/AnimatedPage';
import { EmptyState } from '@/components/shared/EmptyState';
import { GlassButton } from '@/components/glass';
import { GlassCard } from '@/components/glass';
import { ArtifactViewer } from '@/components/artifacts/ArtifactViewer';
import { SummaryView } from '@/components/artifacts/views/SummaryView';
import { GenerateArtifactPanel } from '@/components/artifacts/GenerateArtifactPanel';
import { useArtifactsStore } from '@/stores/artifacts.store';
import { useProjectsStore } from '@/stores/projects.store';
import { useUIStore } from '@/stores/ui.store';
import { useSettingsStore } from '@/stores/settings.store';
import type { ArtifactType, Artifact } from '@/types/artifact.types';
import { ARTIFACT_LABELS, ARTIFACT_ICONS } from '@/types/artifact.types';
import { exportArtifactToDocx, exportAllToZip } from '@/services/export.service';
import { buildAggregationPrompt } from '@/lib/prompts';
import { generateArtifact } from '@/services/llm.service';
import { LLM_KEY_MAP } from '@/lib/provider-router';

export function ViewerPage() {
  const [searchParams] = useSearchParams();
  const navigate = useNavigate();
  const meetingId = searchParams.get('meetingId');

  const artifacts = useArtifactsStore((s) => s.artifacts);
  const meetings = useProjectsStore((s) => s.meetings);
  const projects = useProjectsStore((s) => s.projects);

  // === Режим списка всех встреч (нет meetingId в URL) ===
  const meetingsWithArtifacts = useMemo(() => {
    const meetingIds = new Set(artifacts.map((a) => a.meetingId));
    return meetings
      .filter((m) => meetingIds.has(m.id))
      .sort((a, b) => new Date(b.createdAt).getTime() - new Date(a.createdAt).getTime());
  }, [artifacts, meetings]);

  // === Агрегация ===
  const [aggregateMode, setAggregateMode] = useState(false);
  const [selectedMeetings, setSelectedMeetings] = useState<Set<string>>(new Set());
  const [aggregating, setAggregating] = useState(false);

  const toggleMeetingSelection = useCallback((id: string) => {
    setSelectedMeetings((prev) => {
      const next = new Set(prev);
      if (next.has(id)) next.delete(id);
      else next.add(id);
      return next;
    });
  }, []);

  const handleAggregate = useCallback(async () => {
    if (selectedMeetings.size < 2) return;

    const settings = useSettingsStore.getState();
    const keyField = LLM_KEY_MAP[settings.llmProvider];
    const apiKey = keyField ? settings.apiKeys[keyField] : '';
    if (!apiKey) {
      useUIStore.getState().addToast('error', 'Настройте API-ключ в разделе Настройки');
      return;
    }

    setAggregating(true);
    try {
      // Собираем артефакты выбранных встреч
      const selectedArtifacts = artifacts.filter((a) => selectedMeetings.has(a.meetingId));
      const firstMeeting = meetings.find((m) => selectedMeetings.has(m.id));
      const project = firstMeeting ? projects.find((p) => p.id === firstMeeting.projectId) : null;

      // Формируем компактный JSON для промпта
      const artifactsData = selectedArtifacts.map((a) => ({
        meetingId: a.meetingId,
        meetingTitle: meetings.find((m) => m.id === a.meetingId)?.title || '',
        meetingDate: meetings.find((m) => m.id === a.meetingId)?.createdAt || '',
        type: a.type,
        data: a.data,
      }));

      const prompt = buildAggregationPrompt(
        project?.name || 'Без проекта',
        JSON.stringify(artifactsData, null, 2),
      );

      const result = await generateArtifact(
        prompt,
        apiKey,
        settings.llmProvider,
      );

      // Сохраняем как aggregated артефакт (привязан к первой выбранной встрече)
      const addArtifact = useArtifactsStore.getState().addArtifact;
      const newArtifact: Artifact = {
        id: crypto.randomUUID(),
        meetingId: firstMeeting?.id || '',
        type: 'aggregated',
        version: 1,
        data: result.data ?? { raw_text: result.text },
        llmProvider: result.provider,
        llmModel: result.model,
        tokensUsed: result.tokensUsed.total,
        costUsd: 0,
        createdAt: new Date().toISOString(),
      };
      addArtifact(newArtifact);

      useUIStore.getState().addToast('success', 'Сводный отчёт создан');
      setAggregateMode(false);
      setSelectedMeetings(new Set());

      // Переход к просмотру
      navigate(`/viewer?meetingId=${newArtifact.meetingId}`);
    } catch (err) {
      const msg = err instanceof Error ? err.message : 'Ошибка агрегации';
      useUIStore.getState().addToast('error', msg);
    } finally {
      setAggregating(false);
    }
  }, [selectedMeetings, artifacts, meetings, projects, navigate]);

  if (!meetingId) {
    if (meetingsWithArtifacts.length === 0) {
      return (
        <AnimatedPage>
          <div className="max-w-4xl mx-auto">
            <h1 className="text-2xl font-bold text-text mb-6">Артефакты</h1>
            <EmptyState
              title="Нет артефактов"
              description="Обработайте запись встречи, чтобы увидеть результаты"
              icon={
                <svg width="32" height="32" viewBox="0 0 32 32" fill="none">
                  <path d="M6 4H20L26 10V28H6V4Z" stroke="currentColor" strokeWidth="2" strokeLinejoin="round" />
                  <path d="M10 14H22M10 19H22M10 24H16" stroke="currentColor" strokeWidth="2" strokeLinecap="round" />
                </svg>
              }
              actionLabel="Обработать запись"
              onAction={() => navigate('/pipeline')}
            />
          </div>
        </AnimatedPage>
      );
    }

    return (
      <AnimatedPage>
        <div className="max-w-4xl mx-auto">
          <div className="flex items-center justify-between mb-2">
            <h1 className="text-2xl font-bold text-text">Артефакты</h1>
            <div className="flex gap-2">
              {aggregateMode && (
                <GlassButton
                  variant="primary"
                  size="sm"
                  disabled={selectedMeetings.size < 2 || aggregating}
                  onClick={handleAggregate}
                >
                  {aggregating ? 'Генерация...' : `Объединить (${selectedMeetings.size})`}
                </GlassButton>
              )}
              <GlassButton
                variant={aggregateMode ? 'secondary' : 'ghost'}
                size="sm"
                onClick={() => {
                  setAggregateMode(!aggregateMode);
                  setSelectedMeetings(new Set());
                }}
              >
                {aggregateMode ? 'Отмена' : '📑 Сводный отчёт'}
              </GlassButton>
            </div>
          </div>
          <p className="text-sm text-text-secondary mb-6">
            {aggregateMode
              ? 'Выберите 2+ встречи для объединения артефактов'
              : `${meetingsWithArtifacts.length} ${meetingsWithArtifacts.length === 1 ? 'встреча' : 'встреч'} с артефактами`}
          </p>

          <div className="flex flex-col gap-3">
            {meetingsWithArtifacts.map((meeting) => {
              const project = projects.find((p) => p.id === meeting.projectId);
              const meetingArtifacts = artifacts.filter((a) => a.meetingId === meeting.id);
              const date = new Date(meeting.createdAt).toLocaleDateString('ru-RU', {
                day: 'numeric',
                month: 'long',
                year: 'numeric',
              });

              const isSelected = selectedMeetings.has(meeting.id);

              return (
                <GlassCard
                  key={meeting.id}
                  variant="subtle"
                  padding="md"
                  className={`cursor-pointer transition-colors ${
                    isSelected ? 'ring-2 ring-primary/50 bg-primary/5' : 'hover:bg-white/50'
                  }`}
                  onClick={() => {
                    if (aggregateMode) {
                      toggleMeetingSelection(meeting.id);
                    } else {
                      navigate(`/viewer?meetingId=${meeting.id}`);
                    }
                  }}
                >
                  <div className="flex items-start justify-between">
                    <div className="flex items-center gap-3 min-w-0 flex-1">
                      {aggregateMode && (
                        <div className={`w-5 h-5 rounded-md border-2 flex items-center justify-center flex-shrink-0 transition-colors ${
                          isSelected ? 'bg-primary border-primary' : 'border-text-muted/30'
                        }`}>
                          {isSelected && (
                            <svg width="12" height="12" viewBox="0 0 12 12" fill="none">
                              <path d="M2.5 6L5 8.5L9.5 3.5" stroke="white" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" />
                            </svg>
                          )}
                        </div>
                      )}
                      <div className="min-w-0 flex-1">
                        <p className="text-sm font-semibold text-text truncate">
                          {meeting.title || 'Без названия'}
                        </p>
                        <div className="flex items-center gap-2 mt-0.5 text-xs text-text-muted">
                          {project && <span>{project.name}</span>}
                          {project && <span>·</span>}
                          <span>{date}</span>
                        </div>
                      </div>
                    </div>
                    <div className="flex items-center gap-1 ml-3 flex-shrink-0">
                      {meetingArtifacts.map((a) => (
                        <span key={a.type} title={ARTIFACT_LABELS[a.type]} className="text-base">
                          {ARTIFACT_ICONS[a.type]}
                        </span>
                      ))}
                    </div>
                  </div>
                  <div className="mt-2 flex items-center justify-between">
                    <span className="text-xs text-text-secondary">
                      {meetingArtifacts.length} артефактов
                    </span>
                    <span className="text-xs text-primary font-medium">Открыть →</span>
                  </div>
                </GlassCard>
              );
            })}
          </div>
        </div>
      </AnimatedPage>
    );
  }

  // === Режим просмотра конкретной встречи ===
  return <MeetingViewer meetingId={meetingId} />;
}

// ─── Компонент просмотра артефактов конкретной встречи ───────────────────────

type TabType = 'summary' | ArtifactType;

function MeetingViewer({ meetingId }: { meetingId: string }) {
  const navigate = useNavigate();
  const addToast = useUIStore((s) => s.addToast);
  const artifacts = useArtifactsStore((s) => s.artifacts);
  const meetings = useProjectsStore((s) => s.meetings);
  const projects = useProjectsStore((s) => s.projects);

  // Артефакты для текущей встречи
  const meetingArtifacts = useMemo(
    () => artifacts.filter((a) => a.meetingId === meetingId),
    [artifacts, meetingId],
  );

  const meeting = meetings.find((m) => m.id === meetingId);
  const project = projects.find((p) => p.id === meeting?.projectId);

  // Доступные типы артефактов
  const artifactTypes = useMemo(
    () => meetingArtifacts.map((a) => a.type),
    [meetingArtifacts],
  );

  // Активный таб — Summary по умолчанию
  const [activeTab, setActiveTab] = useState<TabType>('summary');
  const isSummary = activeTab === 'summary';

  // Текущий артефакт (не для summary)
  const currentArtifact = isSummary ? null : meetingArtifacts.find((a) => a.type === activeTab);

  // Экспорт
  const [exporting, setExporting] = useState(false);
  const [showGenerate, setShowGenerate] = useState(false);

  const handleExportDocx = async () => {
    if (!currentArtifact || !project || !meeting) return;
    setExporting(true);
    try {
      await exportArtifactToDocx(currentArtifact, project.name, meeting.title || '');
      addToast('success', 'DOCX экспортирован');
    } catch (err) {
      const msg = err instanceof Error ? err.message : 'Ошибка экспорта';
      addToast('error', msg);
    } finally {
      setExporting(false);
    }
  };

  const handleExportAll = async () => {
    if (!project || !meeting) return;
    setExporting(true);
    try {
      await exportAllToZip(meetingArtifacts, project.name, meeting.title || '');
      addToast('success', 'ZIP-архив экспортирован');
    } catch (err) {
      const msg = err instanceof Error ? err.message : 'Ошибка экспорта';
      addToast('error', msg);
    } finally {
      setExporting(false);
    }
  };

  // Встреча не найдена или нет артефактов
  if (meetingArtifacts.length === 0) {
    return (
      <AnimatedPage>
        <div className="max-w-4xl mx-auto">
          <div className="flex items-center gap-3 mb-6">
            <button
              onClick={() => navigate('/viewer')}
              className="text-sm text-text-secondary hover:text-text transition-colors flex items-center gap-1"
            >
              <svg width="16" height="16" viewBox="0 0 16 16" fill="none">
                <path d="M10 4L6 8L10 12" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round" />
              </svg>
              Все встречи
            </button>
            <span className="text-text-muted">/</span>
            <h1 className="text-2xl font-bold text-text">Артефакты</h1>
          </div>
          <EmptyState
            title="Нет артефактов"
            description="Для этой встречи ещё не созданы артефакты"
            icon={
              <svg width="32" height="32" viewBox="0 0 32 32" fill="none">
                <path d="M6 4H20L26 10V28H6V4Z" stroke="currentColor" strokeWidth="2" strokeLinejoin="round" />
                <path d="M10 14H22M10 19H22M10 24H16" stroke="currentColor" strokeWidth="2" strokeLinecap="round" />
              </svg>
            }
            actionLabel="Обработать запись"
            onAction={() => navigate('/pipeline')}
          />
        </div>
      </AnimatedPage>
    );
  }

  // Все табы: Summary + artifact types
  const allTabs: { key: TabType; icon: string; label: string }[] = [
    { key: 'summary', icon: '📊', label: 'Сводка' },
    ...artifactTypes.map((type) => ({
      key: type as TabType,
      icon: ARTIFACT_ICONS[type],
      label: ARTIFACT_LABELS[type],
    })),
  ];

  return (
    <AnimatedPage>
      <div className="max-w-5xl mx-auto">
        {/* Шапка */}
        <div className="flex items-start justify-between mb-6">
          <div>
            <button
              onClick={() => navigate('/viewer')}
              className="text-xs text-text-secondary hover:text-text transition-colors flex items-center gap-1 mb-1"
            >
              <svg width="14" height="14" viewBox="0 0 16 16" fill="none">
                <path d="M10 4L6 8L10 12" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round" />
              </svg>
              Все встречи
            </button>
            <h1 className="text-2xl font-bold text-text">Артефакты</h1>
            <div className="flex items-center gap-2 mt-1 text-sm text-text-secondary">
              {project && <span>{project.name}</span>}
              {meeting?.title && (
                <>
                  <span className="text-text-muted">·</span>
                  <span>{meeting.title}</span>
                </>
              )}
              <span className="text-text-muted">·</span>
              <span>{meetingArtifacts.length} артефактов</span>
            </div>
          </div>

          <div className="flex gap-2">
            <GlassButton
              variant="primary"
              size="sm"
              onClick={() => setShowGenerate(true)}
            >
              ＋ Создать
            </GlassButton>
            <GlassButton
              variant="secondary"
              size="sm"
              onClick={handleExportDocx}
              disabled={isSummary || !currentArtifact || exporting}
              title={isSummary ? 'Выберите конкретный артефакт' : undefined}
            >
              {exporting ? 'Экспорт...' : 'DOCX'}
            </GlassButton>
            <GlassButton
              variant="secondary"
              size="sm"
              onClick={handleExportAll}
              disabled={meetingArtifacts.length === 0 || exporting}
            >
              {exporting ? 'Экспорт...' : 'ZIP архив'}
            </GlassButton>
          </div>
        </div>

        {/* Табы (inline с поддержкой Summary) */}
        <div className="mb-4">
          <div className="flex gap-1 p-1 rounded-xl glass-subtle overflow-x-auto">
            {allTabs.map((tab) => {
              const isActive = tab.key === activeTab;
              return (
                <button
                  key={tab.key}
                  onClick={() => setActiveTab(tab.key)}
                  className={`relative flex items-center gap-1.5 px-3 py-2 rounded-lg text-sm font-medium whitespace-nowrap transition-colors ${
                    isActive ? 'text-primary' : 'text-text-secondary hover:text-text'
                  }`}
                >
                  {isActive && (
                    <motion.div
                      layoutId="artifact-tab-indicator"
                      className="absolute inset-0 bg-white/80 rounded-lg shadow-sm"
                      transition={{ type: 'spring', stiffness: 400, damping: 30 }}
                    />
                  )}
                  <span className="relative z-10 text-base">{tab.icon}</span>
                  <span className="relative z-10">{tab.label}</span>
                </button>
              );
            })}
          </div>
        </div>

        {/* Мета-информация (только для артефактов, не для сводки) */}
        {!isSummary && currentArtifact && (
          <div className="flex items-center gap-3 mb-4 text-xs text-text-muted">
            <span>Модель: {currentArtifact.llmModel}</span>
            {currentArtifact.tokensUsed > 0 && (
              <span>Токены: {currentArtifact.tokensUsed.toLocaleString()}</span>
            )}
            {currentArtifact.costUsd > 0 && (
              <span>Стоимость: ${currentArtifact.costUsd.toFixed(4)}</span>
            )}
            <span>Версия: {currentArtifact.version}</span>
          </div>
        )}

        {/* Содержимое */}
        {isSummary && meeting ? (
          <SummaryView
            artifacts={meetingArtifacts}
            meeting={meeting}
            project={project}
            onNavigateToTab={(type) => setActiveTab(type)}
          />
        ) : currentArtifact ? (
          <ArtifactViewer
            type={currentArtifact.type}
            data={currentArtifact.data}
          />
        ) : (
          <div className="glass rounded-2xl p-8 text-center">
            <p className="text-text-muted">
              Артефакт «{ARTIFACT_LABELS[activeTab as ArtifactType]}» не найден для этой встречи.
            </p>
          </div>
        )}
      </div>

      {/* Модалка генерации артефакта */}
      {meeting && (
        <GenerateArtifactPanel
          open={showGenerate}
          onClose={() => setShowGenerate(false)}
          meetingId={meetingId}
          projectName={project?.name || ''}
          meetingDate={meeting.createdAt}
          existingArtifacts={meetingArtifacts}
          onGenerated={(type) => setActiveTab(type)}
        />
      )}
    </AnimatedPage>
  );
}
