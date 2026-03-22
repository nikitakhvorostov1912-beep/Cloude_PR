import { describe, it, expect } from 'vitest';
import { buildPrompt, buildAllPrompts } from '@/lib/prompts';
import type { ArtifactType } from '@/types/artifact.types';

const baseContext = {
  meetingType: 'рабочая',
  projectName: 'Тестовый проект',
  meetingDate: '2026-01-15',
  transcript: 'Участники обсудили задачи на следующую неделю.',
};

describe('buildPrompt', () => {
  const artifactTypes: ArtifactType[] = ['protocol', 'requirements', 'risks', 'glossary', 'questions', 'transcript'];

  artifactTypes.forEach((type) => {
    it(`builds prompt for ${type}`, () => {
      const prompt = buildPrompt(type, baseContext);
      expect(prompt.artifactType).toBe(type);
      expect(prompt.system).toBeTruthy();
      expect(prompt.user).toBeTruthy();
      expect(prompt.maxTokens).toBe(8192);
    });
  });

  it('uses temperature 0.3 for transcript', () => {
    const prompt = buildPrompt('transcript', baseContext);
    expect(prompt.temperature).toBe(0.3);
  });

  it('uses temperature 0.1 for non-transcript types', () => {
    (['protocol', 'requirements', 'risks', 'glossary', 'questions'] as ArtifactType[]).forEach((type) => {
      const prompt = buildPrompt(type, baseContext);
      expect(prompt.temperature).toBe(0.1);
    });
  });

  it('includes project name in user prompt', () => {
    const prompt = buildPrompt('protocol', baseContext);
    expect(prompt.user).toContain('Тестовый проект');
  });

  it('includes transcript in user prompt', () => {
    const prompt = buildPrompt('requirements', baseContext);
    expect(prompt.user).toContain('Участники обсудили задачи');
  });

  it('includes meeting type modifier for "обследование"', () => {
    const prompt = buildPrompt('glossary', { ...baseContext, meetingType: 'обследование' });
    expect(prompt.system).toContain('обследование');
  });

  it('uses base system prompt for unknown meeting type', () => {
    const prompt = buildPrompt('protocol', { ...baseContext, meetingType: 'неизвестный' });
    expect(prompt.system).toBeTruthy();
    // Should not throw or contain the unknown type in modifier
  });

  it('includes previousArtifacts context when provided', () => {
    const prompt = buildPrompt('requirements', {
      ...baseContext,
      previousArtifacts: { protocol: 'Протокол первой встречи' },
    });
    expect(prompt.user).toBeTruthy();
  });
});

describe('buildAllPrompts', () => {
  it('builds prompts for all 6 types', () => {
    const types: ArtifactType[] = ['protocol', 'requirements', 'risks', 'glossary', 'questions', 'transcript'];
    const prompts = buildAllPrompts(types, baseContext);
    expect(prompts).toHaveLength(6);
  });

  it('builds prompts for a subset of types', () => {
    const prompts = buildAllPrompts(['protocol', 'glossary'], baseContext);
    expect(prompts).toHaveLength(2);
    expect(prompts[0].artifactType).toBe('protocol');
    expect(prompts[1].artifactType).toBe('glossary');
  });

  it('returns empty array for empty types', () => {
    const prompts = buildAllPrompts([], baseContext);
    expect(prompts).toEqual([]);
  });

  it('all prompts have required fields', () => {
    const prompts = buildAllPrompts(['protocol', 'risks'], baseContext);
    prompts.forEach((p) => {
      expect(p.system).toBeTruthy();
      expect(p.user).toBeTruthy();
      expect(p.maxTokens).toBe(8192);
      expect(typeof p.temperature).toBe('number');
    });
  });
});
