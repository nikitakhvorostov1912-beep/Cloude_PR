import { create } from 'zustand';
import { persist } from 'zustand/middleware';
import type { Artifact, Template, ArtifactType } from '@/types/artifact.types';

interface ArtifactsState {
  artifacts: Artifact[];
  templates: Template[];
  selectedTemplate: string | null;
  /** meetingId последней завершённой обработки — используется для навигации из Sidebar */
  lastMeetingId: string | null;
  addArtifact: (artifact: Artifact) => void;
  getArtifactsByMeeting: (meetingId: string) => Artifact[];
  /** Получить все артефакты проекта (через meetingIds) */
  getArtifactsByProject: (meetingIds: string[]) => Artifact[];
  getLatestArtifact: (meetingId: string, type: ArtifactType) => Artifact | undefined;
  addTemplate: (template: Template) => void;
  updateTemplate: (id: string, data: Partial<Template>) => void;
  removeTemplate: (id: string) => void;
  setSelectedTemplate: (id: string | null) => void;
  setLastMeetingId: (id: string | null) => void;
}

const PRESET_CREATED_AT = '2026-01-01T00:00:00.000Z';

const PRESET_TEMPLATES: Template[] = [
  {
    id: 'full-package',
    name: 'Полный пакет',
    description: 'Все 7 типов артефактов',
    artifactTypes: ['protocol', 'requirements', 'risks', 'glossary', 'questions', 'transcript', 'development'],
    customPrompt: null,
    isPreset: true,
    createdAt: PRESET_CREATED_AT,
  },
  {
    id: 'quick-protocol',
    name: 'Быстрый протокол',
    description: 'Протокол встречи и список задач',
    artifactTypes: ['protocol', 'questions'],
    customPrompt: null,
    isPreset: true,
    createdAt: PRESET_CREATED_AT,
  },
  {
    id: 'survey',
    name: 'Обследование',
    description: 'Требования, глоссарий и карта рисков',
    artifactTypes: ['requirements', 'glossary', 'risks'],
    customPrompt: null,
    isPreset: true,
    createdAt: PRESET_CREATED_AT,
  },
];

export const useArtifactsStore = create<ArtifactsState>()(
  persist(
    (set, get) => ({
      artifacts: [],
      templates: PRESET_TEMPLATES,
      selectedTemplate: 'full-package',
      lastMeetingId: null,
      addArtifact: (artifact) => {
        console.log('[ArtifactsStore] addArtifact called:', { id: artifact.id, type: artifact.type, meetingId: artifact.meetingId, dataKeys: Object.keys(artifact.data) });
        set((s) => {
          const newArtifacts = [...s.artifacts, artifact];
          console.log('[ArtifactsStore] Total artifacts after add:', newArtifacts.length);
          return {
            artifacts: newArtifacts,
            lastMeetingId: artifact.meetingId,
          };
        });
      },
      getArtifactsByMeeting: (meetingId) =>
        get().artifacts.filter((a) => a.meetingId === meetingId),
      getArtifactsByProject: (meetingIds) => {
        const idSet = new Set(meetingIds);
        return get().artifacts.filter((a) => idSet.has(a.meetingId));
      },
      getLatestArtifact: (meetingId, type) =>
        get()
          .artifacts.filter((a) => a.meetingId === meetingId && a.type === type)
          .sort((a, b) => b.version - a.version)[0],
      addTemplate: (template) =>
        set((s) => ({ templates: [...s.templates, template] })),
      updateTemplate: (id, data) =>
        set((s) => ({
          templates: s.templates.map((t) =>
            t.id === id ? { ...t, ...data } : t
          ),
        })),
      removeTemplate: (id) =>
        set((s) => ({
          templates: s.templates.filter((t) => t.id !== id),
          selectedTemplate: s.selectedTemplate === id ? null : s.selectedTemplate,
        })),
      setSelectedTemplate: (id) => set({ selectedTemplate: id }),
      setLastMeetingId: (id) => set({ lastMeetingId: id }),
    }),
    {
      name: 'aether-artifacts',
      version: 2,
      migrate: (persisted: unknown, version: number) => {
        const state = persisted as Record<string, unknown>;
        if (version < 2) {
          // v2: обновляем preset-шаблоны (добавлен тип development), сохраняем кастомные
          const old = (state.templates as Template[]) || [];
          const custom = old.filter((t) => !t.isPreset);
          state.templates = [...PRESET_TEMPLATES, ...custom];
        }
        return state as unknown as ArtifactsState;
      },
    }
  )
);
