/**
 * Страница просмотра артефактов.
 * Показывает результаты обработки с табами для каждого типа.
 */

import { useState, useMemo } from 'react';
import { useSearchParams, useNavigate } from 'react-router';
import { AnimatedPage } from '@/components/shared/AnimatedPage';
import { EmptyState } from '@/components/shared/EmptyState';
import { GlassButton } from '@/components/glass';
import { ArtifactTabs } from '@/components/artifacts/ArtifactTabs';
import { ArtifactViewer } from '@/components/artifacts/ArtifactViewer';
import { useArtifactsStore } from '@/stores/artifacts.store';
import { useProjectsStore } from '@/stores/projects.store';
import type { ArtifactType } from '@/types/artifact.types';
import { ARTIFACT_LABELS } from '@/types/artifact.types';
import { exportArtifactToDocx, exportAllToZip } from '@/services/export.service';

export function ViewerPage() {
  const [searchParams] = useSearchParams();
  const navigate = useNavigate();
  const meetingId = searchParams.get('meetingId');

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

  // Активный таб
  const [activeType, setActiveType] = useState<ArtifactType>(
    artifactTypes[0] || 'protocol',
  );

  // Текущий артефакт
  const currentArtifact = meetingArtifacts.find((a) => a.type === activeType);

  // Экспорт
  const [exporting, setExporting] = useState(false);

  const handleExportDocx = async () => {
    if (!currentArtifact || !project || !meeting) return;
    setExporting(true);
    try {
      await exportArtifactToDocx(currentArtifact, project.name, meeting.title || '');
    } catch (err) {
      console.error('Export error:', err);
    } finally {
      setExporting(false);
    }
  };

  const handleExportAll = async () => {
    if (!project || !meeting) return;
    setExporting(true);
    try {
      await exportAllToZip(meetingArtifacts, project.name, meeting.title || '');
    } catch (err) {
      console.error('Export all error:', err);
    } finally {
      setExporting(false);
    }
  };

  // Пустое состояние
  if (!meetingId || meetingArtifacts.length === 0) {
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
      <div className="max-w-5xl mx-auto">
        {/* Шапка */}
        <div className="flex items-start justify-between mb-6">
          <div>
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
              variant="secondary"
              size="sm"
              onClick={handleExportDocx}
              disabled={!currentArtifact || exporting}
            >
              {exporting ? '...' : `📄 DOCX`}
            </GlassButton>
            <GlassButton
              variant="secondary"
              size="sm"
              onClick={handleExportAll}
              disabled={meetingArtifacts.length === 0 || exporting}
            >
              {exporting ? '...' : '📦 Экспорт всего'}
            </GlassButton>
          </div>
        </div>

        {/* Табы */}
        <div className="mb-4">
          <ArtifactTabs
            types={artifactTypes}
            activeType={activeType}
            onSelect={setActiveType}
          />
        </div>

        {/* Мета-информация */}
        {currentArtifact && (
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
        {currentArtifact ? (
          <ArtifactViewer
            type={currentArtifact.type}
            data={currentArtifact.data}
          />
        ) : (
          <div className="glass rounded-2xl p-8 text-center">
            <p className="text-text-muted">
              Артефакт «{ARTIFACT_LABELS[activeType]}» не найден для этой встречи.
            </p>
          </div>
        )}
      </div>
    </AnimatedPage>
  );
}
