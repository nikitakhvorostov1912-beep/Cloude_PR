import { useState } from 'react';
import { GlassButton, GlassInput, GlassModal, GlassCard } from '@/components/glass';
import { useProjectsStore } from '@/stores/projects.store';
import { useSound } from '@/hooks/useSound';

interface SelectProjectModalProps {
  open: boolean;
  files: File[];
  onSelect: (projectId: string, meetingId: string) => void;
  onClose: () => void;
}

export function SelectProjectModal({ open, files, onSelect, onClose }: SelectProjectModalProps) {
  const projects = useProjectsStore((s) => s.projects);
  const meetings = useProjectsStore((s) => s.meetings);
  const addProject = useProjectsStore((s) => s.addProject);
  const createMeeting = useProjectsStore((s) => s.createMeeting);
  const { play } = useSound();

  const [mode, setMode] = useState<'select' | 'create'>('select');
  const [newName, setNewName] = useState('');
  const [newDesc, setNewDesc] = useState('');

  const handleSelectProject = (projectId: string) => {
    play('navigate');
    if (files.length === 0) return;
    const meetingId = createMeeting(projectId, files[0]);
    // Загружаем остальные файлы как отдельные встречи
    for (let i = 1; i < files.length; i++) {
      createMeeting(projectId, files[i]);
    }
    onSelect(projectId, meetingId);
    handleClose();
  };

  const handleCreateProject = () => {
    if (!newName.trim()) return;
    play('success');
    const projectId = crypto.randomUUID();
    const now = new Date().toISOString();
    addProject({
      id: projectId,
      name: newName.trim(),
      description: newDesc.trim(),
      folder: '',
      meetingIds: [],
      createdAt: now,
      updatedAt: now,
    });
    handleSelectProject(projectId);
  };

  const handleClose = () => {
    setMode('select');
    setNewName('');
    setNewDesc('');
    onClose();
  };

  const fileNames = files.map((f) => f.name).join(', ');
  const filesLabel = files.length === 1
    ? files[0].name
    : `${files.length} файлов`;

  return (
    <GlassModal
      open={open}
      onClose={handleClose}
      title="Добавить запись в проект"
      footer={
        mode === 'create' ? (
          <>
            <GlassButton variant="ghost" onClick={() => setMode('select')}>Назад</GlassButton>
            <GlassButton disabled={!newName.trim()} onClick={handleCreateProject}>
              Создать и добавить
            </GlassButton>
          </>
        ) : (
          <GlassButton variant="ghost" onClick={handleClose}>Отмена</GlassButton>
        )
      }
    >
      <div className="flex flex-col gap-4">
        {/* Информация о файлах */}
        <div className="glass-subtle rounded-xl px-3 py-2">
          <p className="text-xs text-text-muted">Файлы:</p>
          <p className="text-sm text-text truncate" title={fileNames}>{filesLabel}</p>
        </div>

        {mode === 'select' ? (
          <>
            {/* Существующие проекты */}
            {projects.length > 0 && (
              <div className="flex flex-col gap-2">
                <p className="text-xs font-medium text-text-secondary">Выберите проект</p>
                <div className="flex flex-col gap-1.5 max-h-60 overflow-y-auto">
                  {projects.map((project) => {
                    const count = meetings.filter((m) => m.projectId === project.id).length;
                    return (
                      <GlassCard
                        key={project.id}
                        variant="subtle"
                        padding="sm"
                        hoverable
                        className="cursor-pointer"
                        onClick={() => handleSelectProject(project.id)}
                      >
                        <div className="flex items-center justify-between">
                          <div className="min-w-0 flex-1">
                            <p className="text-sm font-medium text-text truncate">{project.name}</p>
                            {project.description && (
                              <p className="text-xs text-text-muted truncate">{project.description}</p>
                            )}
                          </div>
                          <span className="text-xs text-text-muted ml-2 flex-shrink-0">
                            {count} запис{count === 1 ? 'ь' : count < 5 ? 'и' : 'ей'}
                          </span>
                        </div>
                      </GlassCard>
                    );
                  })}
                </div>
              </div>
            )}

            {/* Кнопка создать новый */}
            <GlassButton
              variant="secondary"
              onClick={() => {
                play('click');
                setNewName(files[0]?.name.replace(/\.[^/.]+$/, '') ?? '');
                setMode('create');
              }}
            >
              <svg width="14" height="14" viewBox="0 0 14 14" fill="none">
                <path d="M7 2V12M2 7H12" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round" />
              </svg>
              Новый проект
            </GlassButton>
          </>
        ) : (
          <>
            {/* Форма нового проекта */}
            <GlassInput
              label="Название проекта"
              placeholder="Например: Обследование бухгалтерии"
              value={newName}
              onChange={(e) => setNewName(e.target.value)}
              autoFocus
            />
            <GlassInput
              label="Описание (необязательно)"
              placeholder="Краткое описание"
              value={newDesc}
              onChange={(e) => setNewDesc(e.target.value)}
            />
          </>
        )}
      </div>
    </GlassModal>
  );
}
