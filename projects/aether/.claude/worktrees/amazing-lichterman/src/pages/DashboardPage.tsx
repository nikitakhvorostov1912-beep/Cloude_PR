import { useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { motion } from 'motion/react';
import { AnimatedPage } from '@/components/shared/AnimatedPage';
import { GlassCard, GlassButton, GlassInput, GlassModal } from '@/components/glass';
import { EmptyState } from '@/components/shared/EmptyState';
import { DragDropZone } from '@/components/upload/DragDropZone';
import { FileCard } from '@/components/upload/FileCard';
import { useProjectsStore } from '@/stores/projects.store';
import { useUIStore } from '@/stores/ui.store';
import { useShallow } from 'zustand/react/shallow';
import { useSound } from '@/hooks/useSound';
import type { FileInfo } from '@/services/file.service';

export function DashboardPage() {
  const { projects, addProject, addMeeting } = useProjectsStore(
    useShallow((s) => ({ projects: s.projects, addProject: s.addProject, addMeeting: s.addMeeting }))
  );
  const addToast = useUIStore((s) => s.addToast);
  const navigate = useNavigate();
  const { play } = useSound();

  const [showNewProject, setShowNewProject] = useState(false);
  const [projectName, setProjectName] = useState('');
  const [projectDesc, setProjectDesc] = useState('');
  const [uploadedFile, setUploadedFile] = useState<FileInfo | null>(null);

  const handleCreateProject = () => {
    if (!projectName.trim()) return;

    play('success');
    const id = crypto.randomUUID();
    const now = new Date().toISOString();
    addProject({
      id,
      name: projectName.trim(),
      description: projectDesc.trim(),
      folder: '',
      createdAt: now,
      updatedAt: now,
    });

    if (uploadedFile) {
      addMeeting({
        id: crypto.randomUUID(),
        projectId: id,
        title: uploadedFile.name.replace(/\.[^.]+$/, ''),
        filePath: uploadedFile.objectUrl,
        audioPath: uploadedFile.objectUrl,
        durationSeconds: uploadedFile.durationSeconds,
        fileSizeBytes: uploadedFile.sizeBytes,
        qualityScore: 0,
        status: 'uploaded',
        errorMessage: null,
        createdAt: now,
        processedAt: null,
      });
    }

    setShowNewProject(false);
    setProjectName('');
    setProjectDesc('');
    setUploadedFile(null);
    navigate(`/projects/${id}`);
  };

  const handleFileProcessed = (file: FileInfo) => {
    setUploadedFile(file);

    if (projects.length === 0) {
      setProjectName(file.name.replace(/\.[^.]+$/, ''));
      setShowNewProject(true);
    } else {
      const project = projects[0];
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
      addToast('success', `Файл добавлен в проект "${project.name}"`);
      navigate(`/projects/${project.id}`);
    }
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
              Загрузите запись встречи или выберите проект
            </p>
          </div>
          <GlassButton onClick={() => {
            play('click');
            setShowNewProject(true);
          }}>
            <svg width="16" height="16" viewBox="0 0 16 16" fill="none">
              <path d="M8 3V13M3 8H13" stroke="currentColor" strokeWidth="2" strokeLinecap="round" />
            </svg>
            Новый проект
          </GlassButton>
        </div>

        {/* DnD Zone */}
        <div className="mb-8">
          <DragDropZone
            onFileProcessed={handleFileProcessed}
            onError={handleFileError}
          />
        </div>

        {/* Projects */}
        {projects.length === 0 ? (
          <EmptyState
            title="Нет проектов"
            description="Создайте первый проект для организации записей встреч"
            actionLabel="Создать проект"
            onAction={() => {
              play('click');
              setShowNewProject(true);
            }}
            icon={
              <svg width="32" height="32" viewBox="0 0 32 32" fill="none">
                <rect x="4" y="4" width="24" height="24" rx="4" stroke="currentColor" strokeWidth="2" />
                <path d="M16 10V22M10 16H22" stroke="currentColor" strokeWidth="2" strokeLinecap="round" />
              </svg>
            }
          />
        ) : (
          <div>
            <h2 className="text-lg font-semibold text-text mb-4">Проекты</h2>
            <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
              {projects.map((project, i) => (
                <motion.div
                  key={project.id}
                  initial={{ opacity: 0, y: 20 }}
                  animate={{ opacity: 1, y: 0 }}
                  transition={{ delay: i * 0.05 }}
                >
                  <GlassCard
                    hoverable
                    padding="md"
                    onClick={() => {
                      play('navigate');
                      navigate(`/projects/${project.id}`);
                    }}
                  >
                    <h3 className="font-semibold text-text mb-1">{project.name}</h3>
                    {project.description && (
                      <p className="text-xs text-text-secondary mb-2 line-clamp-2">{project.description}</p>
                    )}
                    <p className="text-xs text-text-muted">
                      {new Date(project.createdAt).toLocaleDateString('ru-RU')}
                    </p>
                  </GlassCard>
                </motion.div>
              ))}
            </div>
          </div>
        )}
      </div>

      {/* New Project Modal */}
      <GlassModal
        open={showNewProject}
        onClose={() => {
          setShowNewProject(false);
          setUploadedFile(null);
        }}
        title="Новый проект"
        footer={
          <>
            <GlassButton variant="ghost" onClick={() => {
              setShowNewProject(false);
              setUploadedFile(null);
            }}>
              Отмена
            </GlassButton>
            <GlassButton
              disabled={!projectName.trim()}
              onClick={handleCreateProject}
            >
              Создать
            </GlassButton>
          </>
        }
      >
        <div className="flex flex-col gap-4">
          <GlassInput
            label="Название проекта"
            placeholder="Например: Обследование бухгалтерии"
            value={projectName}
            onChange={(e) => setProjectName(e.target.value)}
          />
          <GlassInput
            label="Описание (необязательно)"
            placeholder="Краткое описание проекта"
            value={projectDesc}
            onChange={(e) => setProjectDesc(e.target.value)}
          />
          {uploadedFile && (
            <div>
              <p className="text-xs font-medium text-text-secondary mb-2">Загруженный файл</p>
              <FileCard file={uploadedFile} onRemove={() => setUploadedFile(null)} />
            </div>
          )}
        </div>
      </GlassModal>
    </AnimatedPage>
  );
}
