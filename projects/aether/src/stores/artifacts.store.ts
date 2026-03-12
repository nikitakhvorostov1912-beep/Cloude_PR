import { create } from 'zustand';
import { persist } from 'zustand/middleware';
import type { Artifact, Template, ArtifactType } from '@/types/artifact.types';

interface ArtifactsState {
  artifacts: Artifact[];
  templates: Template[];
  selectedTemplate: string | null;
  addArtifact: (artifact: Artifact) => void;
  getArtifactsByMeeting: (meetingId: string) => Artifact[];
  getLatestArtifact: (meetingId: string, type: ArtifactType) => Artifact | undefined;
  addTemplate: (template: Template) => void;
  updateTemplate: (id: string, data: Partial<Template>) => void;
  removeTemplate: (id: string) => void;
  setSelectedTemplate: (id: string | null) => void;
}

const PRESET_TEMPLATES: Template[] = [
  {
    id: 'full-package',
    name: 'Полный пакет',
    description: 'Все 6 типов артефактов',
    artifactTypes: ['protocol', 'requirements', 'risks', 'glossary', 'questions', 'transcript'],
    customPrompt: null,
    isPreset: true,
    createdAt: new Date().toISOString(),
  },
  {
    id: 'quick-protocol',
    name: 'Быстрый протокол',
    description: 'Протокол встречи и список задач',
    artifactTypes: ['protocol', 'questions'],
    customPrompt: null,
    isPreset: true,
    createdAt: new Date().toISOString(),
  },
  {
    id: 'survey',
    name: 'Обследование',
    description: 'Требования, глоссарий и карта рисков',
    artifactTypes: ['requirements', 'glossary', 'risks'],
    customPrompt: null,
    isPreset: true,
    createdAt: new Date().toISOString(),
  },
];

export const useArtifactsStore = create<ArtifactsState>()(
  persist(
    (set, get) => ({
      artifacts: [],
      templates: PRESET_TEMPLATES,
      selectedTemplate: 'full-package',
      addArtifact: (artifact) =>
        set((s) => ({ artifacts: [...s.artifacts, artifact] })),
      getArtifactsByMeeting: (meetingId) =>
        get().artifacts.filter((a) => a.meetingId === meetingId),
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
    }),
    {
      name: 'aether-artifacts',
    }
  )
);
