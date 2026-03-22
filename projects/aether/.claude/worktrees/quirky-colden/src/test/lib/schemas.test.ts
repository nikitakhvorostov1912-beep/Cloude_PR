import { describe, it, expect } from 'vitest';
import {
  OpenAIKeySchema,
  ClaudeKeySchema,
  LLMParamsSchema,
  PipelineConfigSchema,
  AudioFileSchema,
  validatePipelineConfig,
  validateAudioFile,
} from '@/lib/schemas';

describe('OpenAIKeySchema', () => {
  it('accepts valid key', () => {
    expect(OpenAIKeySchema.safeParse('sk-proj-abcdefghij1234567890').success).toBe(true);
  });

  it('rejects empty string', () => {
    expect(OpenAIKeySchema.safeParse('').success).toBe(false);
  });

  it('rejects key not starting with sk-', () => {
    expect(OpenAIKeySchema.safeParse('invalid-key-12345678901234').success).toBe(false);
  });

  it('rejects key shorter than 20 chars', () => {
    expect(OpenAIKeySchema.safeParse('sk-short').success).toBe(false);
  });
});

describe('ClaudeKeySchema', () => {
  it('accepts valid claude key', () => {
    expect(ClaudeKeySchema.safeParse('sk-ant-api03-abcdefghij1234567890').success).toBe(true);
  });

  it('rejects key not starting with sk-ant-', () => {
    expect(ClaudeKeySchema.safeParse('sk-openai-key-12345678901234').success).toBe(false);
  });

  it('rejects short claude key', () => {
    expect(ClaudeKeySchema.safeParse('sk-ant-').success).toBe(false);
  });
});

describe('LLMParamsSchema', () => {
  it('validates with defaults', () => {
    const result = LLMParamsSchema.safeParse({});
    expect(result.success).toBe(true);
    expect(result.data?.temperature).toBe(0.3);
    expect(result.data?.maxTokens).toBe(4096);
  });

  it('accepts valid temperature', () => {
    expect(LLMParamsSchema.safeParse({ temperature: 1.5, maxTokens: 1000 }).success).toBe(true);
  });

  it('rejects temperature > 2', () => {
    expect(LLMParamsSchema.safeParse({ temperature: 2.5, maxTokens: 1000 }).success).toBe(false);
  });

  it('rejects temperature < 0', () => {
    expect(LLMParamsSchema.safeParse({ temperature: -0.1, maxTokens: 1000 }).success).toBe(false);
  });

  it('rejects maxTokens > 32000', () => {
    expect(LLMParamsSchema.safeParse({ temperature: 0.5, maxTokens: 33000 }).success).toBe(false);
  });

  it('rejects maxTokens < 100', () => {
    expect(LLMParamsSchema.safeParse({ temperature: 0.5, maxTokens: 50 }).success).toBe(false);
  });

  it('rejects non-integer maxTokens', () => {
    expect(LLMParamsSchema.safeParse({ temperature: 0.5, maxTokens: 1000.5 }).success).toBe(false);
  });
});

describe('PipelineConfigSchema', () => {
  const validConfig = {
    meetingId: 'meeting-1',
    projectName: 'Тестовый проект',
    meetingDate: '2026-01-15',
    meetingType: 'Обследование',
    artifactTypes: ['protocol', 'requirements'],
    provider: 'openai',
    apiKeys: { openaiKey: 'sk-valid-openai-key-1234567890123456' },
  };

  it('validates correct config', () => {
    expect(PipelineConfigSchema.safeParse(validConfig).success).toBe(true);
  });

  it('rejects empty meetingId', () => {
    expect(PipelineConfigSchema.safeParse({ ...validConfig, meetingId: '' }).success).toBe(false);
  });

  it('rejects empty artifactTypes array', () => {
    expect(PipelineConfigSchema.safeParse({ ...validConfig, artifactTypes: [] }).success).toBe(false);
  });

  it('rejects more than 6 artifact types', () => {
    expect(
      PipelineConfigSchema.safeParse({
        ...validConfig,
        artifactTypes: ['protocol', 'requirements', 'risks', 'glossary', 'questions', 'transcript', 'protocol'],
      }).success,
    ).toBe(false);
  });

  it('rejects invalid provider', () => {
    expect(PipelineConfigSchema.safeParse({ ...validConfig, provider: 'gemini' }).success).toBe(false);
  });

  it('accepts all 6 artifact types', () => {
    expect(
      PipelineConfigSchema.safeParse({
        ...validConfig,
        artifactTypes: ['protocol', 'requirements', 'risks', 'glossary', 'questions', 'transcript'],
      }).success,
    ).toBe(true);
  });

  it('rejects project name longer than 200 chars', () => {
    expect(
      PipelineConfigSchema.safeParse({ ...validConfig, projectName: 'A'.repeat(201) }).success,
    ).toBe(false);
  });
});

describe('AudioFileSchema', () => {
  it('accepts valid audio file', () => {
    const file = { size: 1024 * 1024, type: 'audio/mpeg' }; // 1 MB mp3
    expect(AudioFileSchema.safeParse(file).success).toBe(true);
  });

  it('rejects file larger than 25 MB', () => {
    const file = { size: 26 * 1024 * 1024, type: 'audio/mpeg' };
    expect(AudioFileSchema.safeParse(file).success).toBe(false);
  });

  it('accepts video/mp4', () => {
    const file = { size: 10 * 1024 * 1024, type: 'video/mp4' };
    expect(AudioFileSchema.safeParse(file).success).toBe(true);
  });
});

describe('validatePipelineConfig', () => {
  it('returns success: true for valid config', () => {
    const config = {
      meetingId: 'meeting-1',
      projectName: 'Проект',
      meetingDate: '2026-01-15',
      meetingType: 'Рабочая',
      artifactTypes: ['protocol'],
      provider: 'openai',
      apiKeys: { openaiKey: 'sk-valid-openai-key-1234567890123456' },
    };
    const result = validatePipelineConfig(config);
    expect(result.success).toBe(true);
    expect(result.data).toBeDefined();
    expect(result.errors).toBeUndefined();
  });

  it('returns errors for invalid config', () => {
    const result = validatePipelineConfig({ meetingId: '' });
    expect(result.success).toBe(false);
    expect(result.errors).toBeDefined();
    expect(result.errors!.length).toBeGreaterThan(0);
  });

  it('returns errors with field paths', () => {
    const result = validatePipelineConfig({ meetingId: '' });
    expect(result.errors![0]).toContain('meetingId');
  });
});

describe('validateAudioFile', () => {
  it('returns valid: true for good file', () => {
    const file = { size: 1024, type: 'audio/wav', name: 'test.wav' } as unknown as File;
    const result = validateAudioFile(file);
    expect(result.valid).toBe(true);
  });

  it('returns error for too-large file', () => {
    const file = { size: 30 * 1024 * 1024, type: 'audio/mp3', name: 'big.mp3' } as unknown as File;
    const result = validateAudioFile(file);
    expect(result.valid).toBe(false);
    expect(result.error).toBeDefined();
  });
});
