import { describe, it, expect, beforeEach } from 'vitest';
import { useArtifactsStore } from '@/stores/artifacts.store';
import type { Artifact, Template } from '@/types/artifact.types';

const makeArtifact = (override: Partial<Artifact> = {}): Artifact => ({
  id: 'artifact-1',
  meetingId: 'meeting-1',
  type: 'protocol',
  version: 1,
  data: { participants: ['Иван', 'Мария'], decisions: [], action_items: [] },
  llmProvider: 'claude',
  llmModel: 'claude-sonnet-4-6',
  tokensUsed: 1500,
  costUsd: 0.02,
  createdAt: '2026-01-01T00:00:00.000Z',
  ...override,
});

const makeTemplate = (override: Partial<Template> = {}): Template => ({
  id: 'custom-template',
  name: 'Мой шаблон',
  description: 'Описание шаблона',
  artifactTypes: ['protocol', 'requirements'],
  customPrompt: null,
  isPreset: false,
  createdAt: '2026-01-01T00:00:00.000Z',
  ...override,
});

describe('useArtifactsStore', () => {
  beforeEach(() => {
    // Reset to initial state (keep preset templates)
    useArtifactsStore.setState({
      artifacts: [],
      templates: [
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
      ],
      selectedTemplate: 'full-package',
    });
  });

  describe('initial state', () => {
    it('has 3 preset templates', () => {
      expect(useArtifactsStore.getState().templates).toHaveLength(3);
    });

    it('has full-package selected by default', () => {
      expect(useArtifactsStore.getState().selectedTemplate).toBe('full-package');
    });

    it('starts with empty artifacts', () => {
      expect(useArtifactsStore.getState().artifacts).toHaveLength(0);
    });
  });

  describe('addArtifact', () => {
    it('adds an artifact', () => {
      useArtifactsStore.getState().addArtifact(makeArtifact());
      expect(useArtifactsStore.getState().artifacts).toHaveLength(1);
    });

    it('adds multiple artifacts', () => {
      useArtifactsStore.getState().addArtifact(makeArtifact({ id: 'a1', type: 'protocol' }));
      useArtifactsStore.getState().addArtifact(makeArtifact({ id: 'a2', type: 'requirements' }));
      expect(useArtifactsStore.getState().artifacts).toHaveLength(2);
    });
  });

  describe('getArtifactsByMeeting', () => {
    it('returns artifacts for specific meeting', () => {
      useArtifactsStore.getState().addArtifact(makeArtifact({ id: 'a1', meetingId: 'm1' }));
      useArtifactsStore.getState().addArtifact(makeArtifact({ id: 'a2', meetingId: 'm1' }));
      useArtifactsStore.getState().addArtifact(makeArtifact({ id: 'a3', meetingId: 'm2' }));
      const artifacts = useArtifactsStore.getState().getArtifactsByMeeting('m1');
      expect(artifacts).toHaveLength(2);
    });

    it('returns empty array for unknown meeting', () => {
      expect(useArtifactsStore.getState().getArtifactsByMeeting('unknown')).toEqual([]);
    });
  });

  describe('getLatestArtifact', () => {
    it('returns highest version artifact', () => {
      useArtifactsStore.getState().addArtifact(makeArtifact({ id: 'a1', meetingId: 'm1', type: 'protocol', version: 1 }));
      useArtifactsStore.getState().addArtifact(makeArtifact({ id: 'a2', meetingId: 'm1', type: 'protocol', version: 3 }));
      useArtifactsStore.getState().addArtifact(makeArtifact({ id: 'a3', meetingId: 'm1', type: 'protocol', version: 2 }));
      const latest = useArtifactsStore.getState().getLatestArtifact('m1', 'protocol');
      expect(latest?.id).toBe('a2');
    });

    it('returns undefined for non-existent meeting/type', () => {
      expect(useArtifactsStore.getState().getLatestArtifact('m-none', 'risks')).toBeUndefined();
    });
  });

  describe('template management', () => {
    it('adds a custom template', () => {
      useArtifactsStore.getState().addTemplate(makeTemplate());
      expect(useArtifactsStore.getState().templates).toHaveLength(4);
    });

    it('updates a template', () => {
      useArtifactsStore.getState().addTemplate(makeTemplate({ id: 't1', name: 'Старое имя' }));
      useArtifactsStore.getState().updateTemplate('t1', { name: 'Новое имя' });
      const t = useArtifactsStore.getState().templates.find((t) => t.id === 't1');
      expect(t?.name).toBe('Новое имя');
    });

    it('removes a template', () => {
      useArtifactsStore.getState().addTemplate(makeTemplate({ id: 't1' }));
      useArtifactsStore.getState().removeTemplate('t1');
      expect(useArtifactsStore.getState().templates).toHaveLength(3); // only presets
    });

    it('clears selectedTemplate when removing selected', () => {
      useArtifactsStore.getState().addTemplate(makeTemplate({ id: 't1' }));
      useArtifactsStore.getState().setSelectedTemplate('t1');
      useArtifactsStore.getState().removeTemplate('t1');
      expect(useArtifactsStore.getState().selectedTemplate).toBeNull();
    });

    it('preserves selectedTemplate when removing different template', () => {
      useArtifactsStore.getState().addTemplate(makeTemplate({ id: 't1' }));
      useArtifactsStore.getState().addTemplate(makeTemplate({ id: 't2' }));
      useArtifactsStore.getState().setSelectedTemplate('t1');
      useArtifactsStore.getState().removeTemplate('t2');
      expect(useArtifactsStore.getState().selectedTemplate).toBe('t1');
    });
  });

  describe('setSelectedTemplate', () => {
    it('sets selected template', () => {
      useArtifactsStore.getState().setSelectedTemplate('quick-protocol');
      expect(useArtifactsStore.getState().selectedTemplate).toBe('quick-protocol');
    });

    it('clears selection with null', () => {
      useArtifactsStore.getState().setSelectedTemplate(null);
      expect(useArtifactsStore.getState().selectedTemplate).toBeNull();
    });
  });
});
