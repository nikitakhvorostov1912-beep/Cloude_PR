import { useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { motion } from 'motion/react';
import { AnimatedPage } from '@/components/shared/AnimatedPage';
import { GlassCard, GlassButton } from '@/components/glass';
import { EmptyState } from '@/components/shared/EmptyState';
import { NewProjectModal } from '@/components/shared/NewProjectModal';
import { useProjectsStore } from '@/stores/projects.store';
import { useArtifactsStore } from '@/stores/artifacts.store';
import { useSound } from '@/hooks/useSound';
import { ARTIFACT_ICONS } from '@/types/artifact.types';
import type { ArtifactType } from '@/types/artifact.types';

export function ProjectsListPage() {
  const projects = useProjectsStore((s) => s.projects);
  const meetings = useProjectsStore((s) => s.meetings);
  const artifacts = useArtifactsStore((s) => s.artifacts);
  const navigate = useNavigate();
  const { play } = useSound();
  const [showNewProject, setShowNewProject] = useState(false);

  return (
    <AnimatedPage>
      <div className="max-w-5xl mx-auto">
        <div className="flex items-center justify-between mb-6">
          <div>
            <h1 className="text-2xl font-bold text-text">Проекты</h1>
            <p className="text-sm text-text-secondary mt-1">
              {projects.length} {projects.length === 1 ? 'проект' : projects.length < 5 ? 'проекта' : 'проектов'}
            </p>
          </div>
          <GlassButton onClick={() => { play('click'); setShowNewProject(true); }}>
            <svg width="16" height="16" viewBox="0 0 16 16" fill="none">
              <path d="M8 3V13M3 8H13" stroke="currentColor" strokeWidth="2" strokeLinecap="round" />
            </svg>
            Новый проект
          </GlassButton>
        </div>

        {projects.length === 0 ? (
          <EmptyState
            title="Нет проектов"
            description="Создайте первый проект для организации записей встреч"
            actionLabel="Создать проект"
            onAction={() => { play('click'); setShowNewProject(true); }}
            icon={
              <svg width="32" height="32" viewBox="0 0 32 32" fill="none">
                <rect x="4" y="4" width="24" height="24" rx="4" stroke="currentColor" strokeWidth="2" />
                <path d="M16 10V22M10 16H22" stroke="currentColor" strokeWidth="2" strokeLinecap="round" />
              </svg>
            }
          />
        ) : (
          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
            {projects.map((project, i) => {
              const projectMeetings = meetings.filter((m) => m.projectId === project.id);
              const completedCount = projectMeetings.filter((m) => m.status === 'completed').length;
              const lastCompleted = projectMeetings
                .filter((m) => m.status === 'completed')
                .sort((a, b) => new Date(b.createdAt).getTime() - new Date(a.createdAt).getTime())[0];
              const artifactTypes: ArtifactType[] = lastCompleted
                ? [...new Set(artifacts.filter((a) => a.meetingId === lastCompleted.id).map((a) => a.type))]
                : [];

              return (
                <motion.div
                  key={project.id}
                  initial={{ opacity: 0, y: 20 }}
                  animate={{ opacity: 1, y: 0 }}
                  transition={{ delay: i * 0.05 }}
                >
                  <GlassCard
                    hoverable
                    padding="md"
                    onClick={() => { play('navigate'); navigate(`/projects/${project.id}`); }}
                  >
                    <h3 className="font-semibold text-text mb-1">{project.name}</h3>
                    {project.description && (
                      <p className="text-xs text-text-secondary mb-2 line-clamp-2">{project.description}</p>
                    )}

                    {/* Artifact badges */}
                    {artifactTypes.length > 0 && (
                      <div className="flex gap-1 mb-2">
                        {artifactTypes.map((type) => (
                          <span key={type} className="text-sm" title={type}>
                            {ARTIFACT_ICONS[type]}
                          </span>
                        ))}
                      </div>
                    )}

                    {/* Stats + date */}
                    <div className="flex items-center justify-between text-xs text-text-muted">
                      <span>
                        {projectMeetings.length} запис{projectMeetings.length === 1 ? 'ь' : projectMeetings.length < 5 ? 'и' : 'ей'}
                        {completedCount > 0 && ` · ${completedCount} обработано`}
                      </span>
                      <span>{new Date(project.createdAt).toLocaleDateString('ru-RU')}</span>
                    </div>

                    {/* Progress bar */}
                    {projectMeetings.length > 0 && (
                      <div className="mt-2 h-1 bg-white/20 rounded-full overflow-hidden">
                        <div
                          className="h-full bg-primary/60 rounded-full transition-all"
                          style={{ width: `${(completedCount / projectMeetings.length) * 100}%` }}
                        />
                      </div>
                    )}
                  </GlassCard>
                </motion.div>
              );
            })}
          </div>
        )}
      </div>

      <NewProjectModal
        open={showNewProject}
        onClose={() => setShowNewProject(false)}
      />
    </AnimatedPage>
  );
}
