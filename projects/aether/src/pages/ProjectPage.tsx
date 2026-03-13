import { useState } from 'react';
import { useParams, useNavigate } from 'react-router-dom';
import { motion } from 'motion/react';
import { AnimatedPage } from '@/components/shared/AnimatedPage';
import { GlassCard, GlassButton, GlassInput, GlassModal } from '@/components/glass';
import { EmptyState } from '@/components/shared/EmptyState';
import { DragDropZone } from '@/components/upload/DragDropZone';
import { WaveformPlayer } from '@/components/audio/WaveformPlayer';
import { useProjectsStore } from '@/stores/projects.store';
import { useUIStore } from '@/stores/ui.store';
import { useShallow } from 'zustand/react/shallow';
import { useSound } from '@/hooks/useSound';
import { formatDuration } from '@/services/file.service';
import type { FileInfo } from '@/services/file.service';

export function ProjectPage() {
  const { id } = useParams<{ id: string }>();
  const navigate = useNavigate();
  const { play } = useSound();
  const addToast = useUIStore((s) => s.addToast);

  const project = useProjectsStore((s) => s.projects.find((p) => p.id === id));
  const allMeetings = useProjectsStore((s) => s.meetings);
  const meetings = allMeetings.filter((m) => m.projectId === id);
  const { addMeeting, updateProject, removeProject, removeMeeting } = useProjectsStore(
    useShallow((s) => ({
      addMeeting: s.addMeeting,
      updateProject: s.updateProject,
      removeProject: s.removeProject,
      removeMeeting: s.removeMeeting,
    }))
  );

  const [showEdit, setShowEdit] = useState(false);
  const [editName, setEditName] = useState('');
  const [editDesc, setEditDesc] = useState('');
  const [showDeleteConfirm, setShowDeleteConfirm] = useState(false);
  const [expandedMeeting, setExpandedMeeting] = useState<string | null>(null);

  if (!project) {
    return (
      <AnimatedPage>
        <EmptyState
          title="Проект не найден"
          description="Возможно он был удалён"
          actionLabel="На главную"
          onAction={() => navigate('/')}
        />
      </AnimatedPage>
    );
  }

  const handleEditOpen = () => {
    play('click');
    setEditName(project.name);
    setEditDesc(project.description);
    setShowEdit(true);
  };

  const handleEditSave = () => {
    if (!editName.trim()) return;
    updateProject(project.id, { name: editName.trim(), description: editDesc.trim() });
    play('success');
    setShowEdit(false);
    addToast('success', 'Проект обновлён');
  };

  const handleDelete = () => {
    play('error');
    removeProject(project.id);
    navigate('/');
    addToast('info', `Проект "${project.name}" удалён`);
  };

  const handleFileProcessed = (file: FileInfo) => {
    const now = new Date().toISOString();
    addMeeting({
      id: crypto.randomUUID(),
      projectId: project.id,
      title: file.name.replace(/\.[^.]+$/, ''),
      filePath: file.objectUrl,
      audioPath: file.objectUrl,
      durationSeconds: file.durationSeconds,
      fileSizeBytes: file.sizeBytes,
      qualityScore: 0,
      status: 'uploaded',
      errorMessage: null,
      createdAt: now,
      processedAt: null,
    });
    addToast('success', `Файл "${file.name}" загружен`);
  };

  const handleFileError = (message: string) => {
    addToast('error', message);
  };

  const formatSize = (bytes: number): string => {
    if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(1)} КБ`;
    return `${(bytes / (1024 * 1024)).toFixed(1)} МБ`;
  };

  return (
    <AnimatedPage>
      <div className="max-w-4xl mx-auto">
        {/* Header */}
        <div className="flex items-start justify-between mb-6">
          <div className="flex items-center gap-3">
            <GlassButton variant="ghost" size="sm" onClick={() => navigate('/')}>
              <svg width="16" height="16" viewBox="0 0 16 16" fill="none">
                <path d="M10 4L6 8L10 12" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round" />
              </svg>
            </GlassButton>
            <div>
              <h1 className="text-2xl font-bold text-text">{project.name}</h1>
              {project.description && (
                <p className="text-sm text-text-secondary mt-0.5">{project.description}</p>
              )}
              <p className="text-xs text-text-muted mt-1">
                Создан {new Date(project.createdAt).toLocaleDateString('ru-RU')} · {meetings.length} запис{meetings.length === 1 ? 'ь' : meetings.length < 5 ? 'и' : 'ей'}
              </p>
            </div>
          </div>
          <div className="flex gap-2">
            <GlassButton variant="ghost" size="sm" onClick={handleEditOpen}>
              <svg width="14" height="14" viewBox="0 0 14 14" fill="none">
                <path d="M10.5 1.5L12.5 3.5L4.5 11.5L1.5 12.5L2.5 9.5L10.5 1.5Z" stroke="currentColor" strokeWidth="1.5" strokeLinejoin="round" />
              </svg>
            </GlassButton>
            <GlassButton variant="ghost" size="sm" onClick={() => { play('click'); setShowDeleteConfirm(true); }}>
              <svg width="14" height="14" viewBox="0 0 14 14" fill="none">
                <path d="M2 4H12M5 4V2H9V4M3 4V12C3 12.6 3.4 13 4 13H10C10.6 13 11 12.6 11 12V4" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round" />
              </svg>
            </GlassButton>
          </div>
        </div>

        {/* Upload zone */}
        <div className="mb-6">
          <DragDropZone
            compact
            onFileProcessed={handleFileProcessed}
            onError={handleFileError}
          />
        </div>

        {/* Meetings */}
        <div>
          <h2 className="text-lg font-semibold text-text mb-4">Записи встреч</h2>
          {meetings.length === 0 ? (
            <EmptyState
              title="Нет записей"
              description="Загрузите аудио или видео файл встречи"
              icon={
                <svg width="24" height="24" viewBox="0 0 24 24" fill="none">
                  <path d="M12 4V16M7 9L12 4L17 9" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" />
                </svg>
              }
            />
          ) : (
            <div className="flex flex-col gap-3">
              {meetings.map((meeting, i) => (
                <motion.div
                  key={meeting.id}
                  initial={{ opacity: 0, y: 10 }}
                  animate={{ opacity: 1, y: 0 }}
                  transition={{ delay: i * 0.05 }}
                >
                  <GlassCard
                    hoverable
                    padding="md"
                    onClick={() => {
                      play('click');
                      setExpandedMeeting(expandedMeeting === meeting.id ? null : meeting.id);
                    }}
                  >
                    <div className="flex items-center justify-between">
                      <div className="flex items-center gap-3">
                        <div className="w-10 h-10 rounded-xl bg-primary/10 flex items-center justify-center text-primary flex-shrink-0">
                          <svg width="18" height="18" viewBox="0 0 18 18" fill="none">
                            <path d="M9 2V14M5 8V14M13 5V14M1 9V14M17 7V14" stroke="currentColor" strokeWidth="2" strokeLinecap="round" />
                          </svg>
                        </div>
                        <div>
                          <p className="font-medium text-text">{meeting.title || 'Без названия'}</p>
                          <div className="flex items-center gap-2 mt-0.5">
                            <span className="text-xs text-text-muted">{formatDuration(meeting.durationSeconds)}</span>
                            <span className="text-xs text-text-muted">·</span>
                            <span className="text-xs text-text-muted">{formatSize(meeting.fileSizeBytes)}</span>
                            <span className="text-xs text-text-muted">·</span>
                            <span className="text-xs text-text-muted">
                              {new Date(meeting.createdAt).toLocaleDateString('ru-RU')}
                            </span>
                          </div>
                        </div>
                      </div>
                      <div className="flex items-center gap-2">
                        <span
                          className={`text-xs px-2 py-1 rounded-lg ${
                            meeting.status === 'completed'
                              ? 'bg-success/10 text-success'
                              : meeting.status === 'processing'
                              ? 'bg-primary/10 text-primary'
                              : meeting.status === 'error'
                              ? 'bg-error/10 text-error'
                              : 'bg-secondary/10 text-secondary'
                          }`}
                        >
                          {meeting.status === 'completed' ? 'Готово' :
                           meeting.status === 'processing' ? 'Обработка...' :
                           meeting.status === 'error' ? 'Ошибка' : 'Загружен'}
                        </span>
                        <GlassButton
                          variant="ghost"
                          size="sm"
                          onClick={() => {
                            play('click');
                            removeMeeting(meeting.id);
                            addToast('info', 'Запись удалена');
                          }}
                        >
                          <svg width="12" height="12" viewBox="0 0 12 12" fill="none">
                            <path d="M2 2L10 10M2 10L10 2" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round" />
                          </svg>
                        </GlassButton>
                      </div>
                    </div>

                    {/* Expanded: Waveform + Actions */}
                    {expandedMeeting === meeting.id && meeting.audioPath && (
                      <motion.div
                        className="mt-4 pt-4 border-t border-white/20"
                        initial={{ opacity: 0, height: 0 }}
                        animate={{ opacity: 1, height: 'auto' }}
                      >
                        <WaveformPlayer audioUrl={meeting.audioPath} height={60} />
                        <div className="flex gap-2 mt-3">
                          <GlassButton
                            variant="primary"
                            size="sm"
                            onClick={() => {
                              play('start');
                              navigate('/pipeline');
                            }}
                          >
                            <svg width="14" height="14" viewBox="0 0 14 14" fill="none">
                              <path d="M3 1L13 7L3 13V1Z" fill="currentColor" />
                            </svg>
                            Обработать
                          </GlassButton>
                          {meeting.status === 'completed' && (
                            <GlassButton
                              variant="secondary"
                              size="sm"
                              onClick={() => {
                                play('navigate');
                                navigate(`/viewer?meetingId=${meeting.id}`);
                              }}
                            >
                              <svg width="14" height="14" viewBox="0 0 14 14" fill="none">
                                <path d="M2 2H8L12 6V12H2V2Z" stroke="currentColor" strokeWidth="1.5" strokeLinejoin="round" />
                                <path d="M5 7H9M5 9H9" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round" />
                              </svg>
                              Артефакты
                            </GlassButton>
                          )}
                        </div>
                      </motion.div>
                    )}
                  </GlassCard>
                </motion.div>
              ))}
            </div>
          )}
        </div>
      </div>

      {/* Edit Project Modal */}
      <GlassModal
        open={showEdit}
        onClose={() => setShowEdit(false)}
        title="Редактировать проект"
        footer={
          <>
            <GlassButton variant="ghost" onClick={() => setShowEdit(false)}>Отмена</GlassButton>
            <GlassButton disabled={!editName.trim()} onClick={handleEditSave}>Сохранить</GlassButton>
          </>
        }
      >
        <div className="flex flex-col gap-4">
          <GlassInput
            label="Название"
            value={editName}
            onChange={(e) => setEditName(e.target.value)}
          />
          <GlassInput
            label="Описание"
            value={editDesc}
            onChange={(e) => setEditDesc(e.target.value)}
          />
        </div>
      </GlassModal>

      {/* Delete Confirm Modal */}
      <GlassModal
        open={showDeleteConfirm}
        onClose={() => setShowDeleteConfirm(false)}
        title="Удалить проект?"
        footer={
          <>
            <GlassButton variant="ghost" onClick={() => setShowDeleteConfirm(false)}>Отмена</GlassButton>
            <GlassButton variant="danger" onClick={handleDelete}>Удалить</GlassButton>
          </>
        }
      >
        <p className="text-sm text-text-secondary">
          Проект «{project.name}» и все его записи будут удалены. Это действие нельзя отменить.
        </p>
      </GlassModal>
    </AnimatedPage>
  );
}
