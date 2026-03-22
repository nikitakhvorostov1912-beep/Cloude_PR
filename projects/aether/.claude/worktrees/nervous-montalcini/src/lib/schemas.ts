/**
 * Zod-схемы для валидации входных данных.
 * Используется в pipeline.service.ts и UI-компонентах.
 */

import { z } from 'zod';

// ─── API ключи ────────────────────────────────────────────────────────────────

export const OpenAIKeySchema = z
  .string()
  .min(1, 'API-ключ OpenAI обязателен')
  .startsWith('sk-', 'Ключ OpenAI должен начинаться с "sk-"')
  .min(20, 'Ключ OpenAI слишком короткий');

export const ClaudeKeySchema = z
  .string()
  .min(1, 'API-ключ Claude обязателен')
  .startsWith('sk-ant-', 'Ключ Claude должен начинаться с "sk-ant-"')
  .min(20, 'Ключ Claude слишком короткий');

// ─── LLM параметры ────────────────────────────────────────────────────────────

export const LLMParamsSchema = z.object({
  temperature: z.number().min(0).max(2).default(0.3),
  maxTokens: z.number().int().min(100).max(32_000).default(4096),
});

export type LLMParams = z.infer<typeof LLMParamsSchema>;

// ─── Pipeline конфиг ──────────────────────────────────────────────────────────

const ArtifactTypeSchema = z.enum([
  'protocol',
  'requirements',
  'risks',
  'glossary',
  'questions',
  'transcript',
]);

const LLMProviderSchema = z.enum(['openai', 'claude']);

export const PipelineConfigSchema = z.object({
  meetingId: z.string().min(1, 'ID встречи обязателен'),
  projectName: z
    .string()
    .min(1, 'Название проекта обязательно')
    .max(200, 'Название проекта слишком длинное'),
  meetingDate: z.string().min(1, 'Дата встречи обязательна'),
  meetingType: z.string().min(1, 'Тип встречи обязателен'),
  artifactTypes: z
    .array(ArtifactTypeSchema)
    .min(1, 'Выберите хотя бы один тип артефакта')
    .max(6),
  provider: LLMProviderSchema,
  apiKeys: z.object({
    openaiKey: OpenAIKeySchema,
    claudeKey: z.string().optional().default(''),
  }),
  previousArtifacts: z.record(z.string()).optional(),
});

export type ValidatedPipelineConfig = z.infer<typeof PipelineConfigSchema>;

// ─── Файл для транскрипции ────────────────────────────────────────────────────

const SUPPORTED_AUDIO_TYPES = [
  'audio/mpeg', 'audio/mp3', 'audio/wav', 'audio/ogg', 'audio/flac',
  'audio/mp4', 'audio/m4a', 'video/mp4', 'video/mpeg', 'video/webm',
  'video/quicktime',
] as const;

export const AudioFileSchema = z.object({
  size: z
    .number()
    .max(25 * 1024 * 1024, 'Файл превышает 25 МБ — максимум Whisper API'),
  type: z
    .string()
    .refine(
      (t) => SUPPORTED_AUDIO_TYPES.some((s) => t.startsWith(s.split('/')[0])),
      'Неподдерживаемый формат файла. Поддерживаются: MP3, WAV, OGG, FLAC, MP4, MOV, WEBM',
    ),
});

/** Валидирует и возвращает ошибки в читаемом виде. */
export function validatePipelineConfig(config: unknown): {
  success: boolean;
  data?: ValidatedPipelineConfig;
  errors?: string[];
} {
  const result = PipelineConfigSchema.safeParse(config);
  if (result.success) {
    return { success: true, data: result.data };
  }
  const errors = result.error.errors.map((e) => `${e.path.join('.')}: ${e.message}`);
  return { success: false, errors };
}

/** Валидирует аудиофайл перед отправкой в pipeline. */
export function validateAudioFile(file: File): { valid: boolean; error?: string } {
  const result = AudioFileSchema.safeParse(file);
  if (result.success) return { valid: true };
  return { valid: false, error: result.error.errors[0]?.message };
}
