import { useState, useMemo } from 'react';
import { useNavigate } from 'react-router-dom';
import { motion } from 'motion/react';
import { AnimatedPage } from '@/components/shared/AnimatedPage';
import { GlassCard, GlassButton } from '@/components/glass';
import { DragDropZone } from '@/components/upload/DragDropZone';
import { NewProjectModal } from '@/components/shared/NewProjectModal';
import { SelectProjectModal } from '@/components/shared/SelectProjectModal';
import { useProjectsStore } from '@/stores/projects.store';
import { useArtifactsStore } from '@/stores/artifacts.store';
import { useUIStore } from '@/stores/ui.store';
import { useShallow } from 'zustand/react/shallow';
import { useSound } from '@/hooks/useSound';
import { ARTIFACT_ICONS } from '@/types/artifact.types';
import type { FileInfo } from '@/services/file.service';

export function DashboardPage() {
  const { projects, meetings } = useProjectsStore(
    useShallow((s) => ({ projects: s.projects, meetings: s.meetings }))
  );
  const { setActiveProject, setActiveMeeting } = useProjectsStore(
    useShallow((s) => ({ setActiveProject: s.setActiveProject, setActiveMeeting: s.setActiveMeeting }))
  );
  const artifacts = useArtifactsStore((s) => s.artifacts);
  const addToast = useUIStore((s) => s.addToast);
  const navigate = useNavigate();
  const { play } = useSound();

  const [showNewProject, setShowNewProject] = useState(false);
  const [showSelectProject, setShowSelectProject] = useState(false);
  const [initialFile, setInitialFile] = useState<FileInfo | null>(null);
  const [pendingFiles, setPendingFiles] = useState<FileInfo[]>([]);
  /** Сырые File объекты для SelectProjectModal */
  const [pendingRawFiles, setPendingRawFiles] = useState<File[]>([]);

  // Последние 5 встреч из всех проектов
  const recentMeetings = useMemo(() =>
    [...meetings]
      .sort((a, b) => new Date(b.createdAt).getTime() - new Date(a.createdAt).getTime())
      .slice(0, 5),
    [meetings]
  );

  const handleFilesProcessed = (files: FileInfo[]) => {
    if (files.length === 0) return;

    // Если есть проекты — показать выбор проекта
    if (projects.length > 0) {
      const rawFiles = files.map((f) => f.file).filter(Boolean) as File[];
      if (rawFiles.length > 0) {
        setPendingRawFiles(rawFiles);
        setShowSelectProject(true);
        return;
      }
    }

    // Нет проектов — создать новый (как раньше)
    setPendingFiles(files);
    setInitialFile(files[0]);
    setShowNewProject(true);
  };

  const handleProjectSelected = (projectId: string, meetingId: string) => {
    play('navigate');
    setActiveProject(projectId);
    setActiveMeeting(meetingId);
    navigate(`/projects/${projectId}`);
  };

  const handleFileError = (message: string) => {
    addToast('error', message);
  };

  return (
    <AnimatedPage>
      <div className="max-w-5xl mx-auto">
        <div className="flex items-center justify-between mb-6">
          <div>
            <h1 className="text-2xl font-bold text-text">Главная</h1>
            <p className="text-sm text-text-secondary mt-1">
              Загрузите запись встречи или продолжите работу
            </p>
          </div>
          <GlassButton onClick={() => { play('click'); setShowNewProject(true); }}>
            <svg width="16" height="16" viewBox="0 0 16 16" fill="none">
              <path d="M8 3V13M3 8H13" stroke="currentColor" strokeWidth="2" strokeLinecap="round" />
            </svg>
            Новый проект
          </GlassButton>
        </div>

        {/* DnD Zone */}
        <div className="mb-8">
          <DragDropZone
            onFilesProcessed={handleFilesProcessed}
            onError={handleFileError}
          />
        </div>

        {/* Недавняя активность */}
        {recentMeetings.length > 0 && (
          <div>
            <h2 className="text-lg font-semibold text-text mb-4">Недавняя активность</h2>
            <div className="flex flex-col gap-2">
              {recentMeetings.map((meeting, i) => {
                const project = projects.find((p) => p.id === meeting.projectId);
                const meetingArtifacts = artifacts.filter((a) => a.meetingId === meeting.id);
                const artifactTypes = [...new Set(meetingArtifacts.map((a) => a.type))];

                return (
                  <motion.div
                    key={meeting.id}
                    initial={{ opacity: 0, x: -10 }}
                    animate={{ opacity: 1, x: 0 }}
                    transition={{ delay: i * 0.05 }}
                  >
                    <GlassCard
                      variant="subtle"
                      padding="sm"
                      hoverable
                      className="cursor-pointer"
                      onClick={() => {
                        play('navigate');
                        if (meeting.status === 'completed') {
                          navigate(`/viewer?meetingId=${meeting.id}`);
                        } else {
                          navigate(`/projects/${meeting.projectId}`);
                        }
                      }}
                    >
                      <div className="flex items-center justify-between">
                        <div className="flex items-center gap-3 min-w-0 flex-1">
                          {/* Status dot */}
                          <div className={`w-2 h-2 rounded-full flex-shrink-0 ${
                            meeting.status === 'completed' ? 'bg-success' :
                            meeting.status === 'processing' ? 'bg-primary' :
                            meeting.status === 'error' ? 'bg-error' : 'bg-secondary'
                          }`} />
                          <div className="min-w-0 flex-1">
                            <p className="text-sm font-medium text-text truncate">
                              {meeting.title || 'Без названия'}
                            </p>
                            <div className="flex items-center gap-2 text-xs text-text-muted">
                              {project && <span>{project.name}</span>}
                              <span>·</span>
                              <span>{new Date(meeting.createdAt).toLocaleDateString('ru-RU')}</span>
                            </div>
                          </div>
                        </div>
                        <div className="flex items-center gap-2 ml-3 flex-shrink-0">
                          {/* Artifact badges */}
                          {artifactTypes.length > 0 && (
                            <div className="flex gap-0.5">
                              {artifactTypes.map((type) => (
                                <span key={type} className="text-xs">{ARTIFACT_ICONS[type]}</span>
                              ))}
                            </div>
                          )}
                          {/* Action button */}
                          {meeting.status === 'completed' ? (
                            <span className="text-xs text-primary font-medium">Артефакты</span>
                          ) : meeting.status === 'uploaded' ? (
                            <GlassButton
                              variant="primary"
                              size="sm"
                              onClick={(e) => {
                                e.stopPropagation();
                                play('start');
                                setActiveProject(meeting.projectId);
                                setActiveMeeting(meeting.id);
                                navigate('/pipeline');
                              }}
                            >
                              Обработать
                            </GlassButton>
                          ) : meeting.status === 'error' ? (
                            <span className="text-xs text-error">Ошибка</span>
                          ) : (
                            <span className="text-xs text-primary">Обработка...</span>
                          )}
                        </div>
                      </div>
                    </GlassCard>
                  </motion.div>
                );
              })}
            </div>
          </div>
        )}

        {/* Quick links when no meetings */}
        {recentMeetings.length === 0 && projects.length > 0 && (
          <div className="text-center">
            <p className="text-sm text-text-muted mb-3">
              Нет записей встреч.{' '}
              <button
                className="text-primary hover:underline"
                onClick={() => navigate('/projects')}
              >
                Перейти к проектам
              </button>
            </p>
          </div>
        )}
      </div>

      {/* Модалка выбора проекта (при наличии проектов) */}
      <SelectProjectModal
        open={showSelectProject}
        files={pendingRawFiles}
        onSelect={handleProjectSelected}
        onClose={() => { setShowSelectProject(false); setPendingRawFiles([]); }}
      />

      {/* Модалка создания нового проекта (нет проектов или кнопка "Новый") */}
      <NewProjectModal
        open={showNewProject}
        onClose={() => { setShowNewProject(false); setInitialFile(null); setPendingFiles([]); }}
        initialFile={initialFile}
        initialFiles={pendingFiles}
      />
    </AnimatedPage>
  );
}
