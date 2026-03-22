import { describe, it, expect } from 'vitest';
import { cleanLLMResponse, tryParseJSON, isEmptyArtifact, validateArtifactSchema } from '@/lib/validators';

describe('cleanLLMResponse', () => {
  it('returns plain JSON unchanged', () => {
    const json = '{"key": "value"}';
    expect(cleanLLMResponse(json)).toBe(json);
  });

  it('strips ```json``` markdown wrapper', () => {
    const input = '```json\n{"key": "value"}\n```';
    const result = cleanLLMResponse(input);
    expect(result).toBe('{"key": "value"}');
  });

  it('strips ``` markdown wrapper without json tag', () => {
    const input = '```\n{"key": "value"}\n```';
    const result = cleanLLMResponse(input);
    expect(result).toBe('{"key": "value"}');
  });

  it('removes BOM character', () => {
    const input = '\uFEFF{"key": "value"}';
    const result = cleanLLMResponse(input);
    expect(result).toBe('{"key": "value"}');
  });

  it('extracts JSON from text with prefix', () => {
    const input = 'Вот результат:\n{"key": "value"}';
    const result = cleanLLMResponse(input);
    expect(result).toBe('{"key": "value"}');
  });

  it('extracts JSON from text with suffix', () => {
    const input = '{"key": "value"}\nЗдесь текст после JSON';
    const result = cleanLLMResponse(input);
    expect(result).toBe('{"key": "value"}');
  });

  it('handles array JSON', () => {
    const input = 'Some text [1, 2, 3]';
    const result = cleanLLMResponse(input);
    expect(result).toBe('[1, 2, 3]');
  });

  it('returns trimmed text when no JSON structure found', () => {
    const input = 'Просто текст без JSON';
    const result = cleanLLMResponse(input);
    expect(result).toBe('Просто текст без JSON');
  });
});

describe('tryParseJSON', () => {
  it('parses valid JSON', () => {
    const result = tryParseJSON('{"name": "test"}');
    expect(result.ok).toBe(true);
    if (result.ok) expect(result.data).toEqual({ name: 'test' });
  });

  it('parses JSON wrapped in markdown', () => {
    const result = tryParseJSON('```json\n{"name": "test"}\n```');
    expect(result.ok).toBe(true);
    if (result.ok) expect(result.data).toEqual({ name: 'test' });
  });

  it('parses JSON with trailing comma (auto-fix)', () => {
    const result = tryParseJSON('{"name": "test",}');
    expect(result.ok).toBe(true);
    if (result.ok) expect((result.data as Record<string, unknown>).name).toBe('test');
  });

  it('parses JSON with unclosed brackets (auto-fix)', () => {
    const result = tryParseJSON('{"items": [1, 2, 3');
    expect(result.ok).toBe(true);
  });

  it('fails gracefully on completely invalid input', () => {
    const result = tryParseJSON('totally not json at all !!!');
    expect(result.ok).toBe(false);
    if (!result.ok) expect(result.error).toBeTruthy();
  });

  it('returns rawText on failure', () => {
    const result = tryParseJSON('not json');
    if (!result.ok) expect(result.rawText).toBe('not json');
  });

  it('parses empty object', () => {
    const result = tryParseJSON('{}');
    expect(result.ok).toBe(true);
  });
});

describe('isEmptyArtifact', () => {
  describe('protocol', () => {
    it('empty when all arrays empty', () => {
      expect(isEmptyArtifact('protocol', { participants: [], decisions: [], action_items: [] })).toBe(true);
    });

    it('not empty when participants has items', () => {
      expect(isEmptyArtifact('protocol', { participants: ['Иван'], decisions: [], action_items: [] })).toBe(false);
    });

    it('not empty when decisions has items', () => {
      expect(isEmptyArtifact('protocol', { participants: [], decisions: ['Решение 1'], action_items: [] })).toBe(false);
    });
  });

  describe('requirements', () => {
    it('empty when all arrays empty', () => {
      expect(isEmptyArtifact('requirements', { functional_requirements: [], non_functional_requirements: [] })).toBe(true);
    });

    it('not empty when functional_requirements has items', () => {
      expect(isEmptyArtifact('requirements', { functional_requirements: ['REQ-001'], non_functional_requirements: [] })).toBe(false);
    });
  });

  describe('risks', () => {
    it('empty when all arrays empty', () => {
      expect(isEmptyArtifact('risks', { risks: [], uncertainties: [], contradictions: [] })).toBe(true);
    });

    it('not empty when risks has items', () => {
      expect(isEmptyArtifact('risks', { risks: ['Риск 1'], uncertainties: [], contradictions: [] })).toBe(false);
    });
  });

  describe('glossary', () => {
    it('empty when terms empty', () => {
      expect(isEmptyArtifact('glossary', { terms: [], abbreviations: [] })).toBe(true);
    });

    it('not empty when has terms', () => {
      expect(isEmptyArtifact('glossary', { terms: [{ term: 'API', definition: '...' }], abbreviations: [] })).toBe(false);
    });
  });

  describe('questions', () => {
    it('empty when no questions', () => {
      expect(isEmptyArtifact('questions', { open_questions: [], deferred_topics: [] })).toBe(true);
    });

    it('not empty when has open questions', () => {
      expect(isEmptyArtifact('questions', { open_questions: ['Вопрос 1?'], deferred_topics: [] })).toBe(false);
    });
  });

  describe('transcript', () => {
    it('empty when no formatted_transcript', () => {
      expect(isEmptyArtifact('transcript', { formatted_transcript: [] })).toBe(true);
    });

    it('not empty when has transcript', () => {
      expect(isEmptyArtifact('transcript', { formatted_transcript: ['00:00 Начало'] })).toBe(false);
    });
  });
});

describe('validateArtifactSchema', () => {
  it('validates protocol with all required fields', () => {
    const data = {
      participants: ['Иван', 'Мария'],
      decisions: ['Принято решение'],
      action_items: [],
    };
    const result = validateArtifactSchema('protocol', data);
    expect(result.valid).toBe(true);
    expect(result.errors).toHaveLength(0);
  });

  it('reports missing required fields', () => {
    const data = { participants: ['Иван'] }; // missing decisions, action_items
    const result = validateArtifactSchema('protocol', data);
    expect(result.valid).toBe(false);
    expect(result.errors.length).toBeGreaterThan(0);
  });

  it('returns invalid for non-object data', () => {
    const result = validateArtifactSchema('protocol', null);
    expect(result.valid).toBe(false);
    expect(result.isEmpty).toBe(true);
  });

  it('returns invalid for string data', () => {
    const result = validateArtifactSchema('requirements', 'just a string');
    expect(result.valid).toBe(false);
  });

  it('validates requirements schema', () => {
    const data = {
      functional_requirements: ['REQ-001'],
      non_functional_requirements: [],
    };
    const result = validateArtifactSchema('requirements', data);
    expect(result.valid).toBe(true);
  });

  it('validates glossary schema', () => {
    const data = { terms: [{ term: 'API', definition: 'Application Programming Interface' }] };
    const result = validateArtifactSchema('glossary', data);
    expect(result.valid).toBe(true);
  });

  it('indicates isEmpty correctly', () => {
    const data = { participants: [], decisions: [], action_items: [] };
    const result = validateArtifactSchema('protocol', data);
    expect(result.valid).toBe(true);
    expect(result.isEmpty).toBe(true);
  });
});
