/**
 * Модалка генерации нового/кастомного артефакта.
 * Позволяет выбрать тип, написать промпт, улучшить его через AI.
 */

import { useState, useMemo } from 'react';
import { GlassModal, GlassButton, GlassInput } from '@/components/glass';
import { useArtifactsStore } from '@/stores/artifacts.store';
import { useSettingsStore } from '@/stores/settings.store';
import { MODEL_COSTS } from '@/lib/constants';
import { useUIStore } from '@/stores/ui.store';
import { useSound } from '@/hooks/useSound';
import { generateArtifact } from '@/services/llm.service';
import {
  buildPrompt,
  buildCustomPrompt,
  buildImprovePromptRequest,
  CUSTOM_PROMPT_PRESETS,
} from '@/lib/prompts';
import { LLM_KEY_MAP } from '@/lib/provider-router';
import {
  STANDARD_ARTIFACT_TYPES,
  ARTIFACT_LABELS,
  ARTIFACT_ICONS,
} from '@/types/artifact.types';
import type { ArtifactType, Artifact } from '@/types/artifact.types';
import type { BuiltPrompt } from '@/lib/prompts';

interface GenerateArtifactPanelProps {
  open: boolean;
  onClose: () => void;
  meetingId: string;
  projectName: string;
  meetingDate: string;
  /** Существующие артефакты для данной встречи */
  existingArtifacts: Artifact[];
  /** Вызывается после успешной генерации */
  onGenerated?: (type: ArtifactType) => void;
}

type Mode = 'standard' | 'custom';

export function GenerateArtifactPanel({
  open,
  onClose,
  meetingId,
  projectName,
  meetingDate,
  existingArtifacts,
  onGenerated,
}: GenerateArtifactPanelProps) {
  const { play } = useSound();
  const addToast = useUIStore((s) => s.addToast);
  const addArtifact = useArtifactsStore((s) => s.addArtifact);
  const apiKeys = useSettingsStore((s) => s.apiKeys);
  const llmProvider = useSettingsStore((s) => s.llmProvider);

  const [mode, setMode] = useState<Mode>('standard');
  const [selectedType, setSelectedType] = useState<ArtifactType>('protocol');
  const [customPrompt, setCustomPrompt] = useState('');
  const [customTitle, setCustomTitle] = useState('');
  const [generating, setGenerating] = useState(false);
  const [improving, setImproving] = useState(false);
  const [progress, setProgress] = useState('');

  // Получаем транскрипцию из существующих артефактов
  const transcript = useMemo(() => {
    const transcriptArtifact = existingArtifacts.find((a) => a.type === 'transcript');
    if (!transcriptArtifact) return null;
    const data = transcriptArtifact.data;
    if (typeof data.formatted_transcript === 'string') return data.formatted_transcript;
    // Fallback: собираем из реплик
    const entries = Array.isArray(data.formatted_transcript) ? data.formatted_transcript : [];
    return entries.map((e: Record<string, unknown>) =>
      `[${e.timestamp || ''}] ${e.speaker || ''}: ${e.text || ''}`
    ).join('\n');
  }, [existingArtifacts]);

  const apiKeyField = LLM_KEY_MAP[llmProvider];
  const apiKey = apiKeyField ? apiKeys[apiKeyField] : '';
  const hasKey = apiKey.length > 10;

  const handleGenerate = async () => {
    if (!transcript) {
      addToast('error', 'Нет транскрипции. Сначала обработайте запись.');
      return;
    }
    if (!hasKey) {
      addToast('error', 'Настройте API-ключ в разделе Настройки');
      return;
    }
    if (mode === 'custom' && !customPrompt.trim()) {
      addToast('error', 'Введите промпт для кастомного артефакта');
      return;
    }

    setGenerating(true);
    setProgress('Подготовка промпта...');
    play('start');

    try {
      let prompt: BuiltPrompt;
      const artifactType = mode === 'custom' ? 'custom' as ArtifactType : selectedType;

      if (mode === 'custom') {
        prompt = buildCustomPrompt(customPrompt.trim(), {
          meetingType: 'рабочая',
          projectName,
          meetingDate,
          transcript,
        });
      } else {
        prompt = buildPrompt(selectedType, {
          meetingType: 'рабочая',
          projectName,
          meetingDate,
          transcript,
        });
      }

      setProgress('Генерация артефакта...');

      const result = await generateArtifact(prompt, apiKey, llmProvider, {
        onProgress: (msg) => setProgress(msg),
      });

      // Определяем версию
      const existingOfType = existingArtifacts.filter((a) => a.type === artifactType);
      const maxVersion = existingOfType.reduce((max, a) => Math.max(max, a.version), 0);

      const artifactData = result.data || { raw_text: result.text };

      // Добавляем метаданные кастомного промпта
      if (mode === 'custom') {
        (artifactData as Record<string, unknown>)._customPrompt = customPrompt.trim();
        (artifactData as Record<string, unknown>)._customTitle = customTitle.trim() || 'Кастомный артефакт';
      }

      const artifact: Artifact = {
        id: crypto.randomUUID(),
        meetingId,
        type: artifactType,
        version: maxVersion + 1,
        data: artifactData,
        llmProvider: result.provider,
        llmModel: result.model,
        tokensUsed: result.tokensUsed.total,
        costUsd: estimateCost(result.tokensUsed.total, result.provider, result.model),
        createdAt: new Date().toISOString(),
      };

      addArtifact(artifact);
      play('success');
      addToast('success', `Артефакт «${ARTIFACT_LABELS[artifactType]}» создан`);
      onGenerated?.(artifactType);
      onClose();
    } catch (err) {
      play('error');
      const msg = err instanceof Error ? err.message : 'Ошибка генерации';
      addToast('error', msg);
    } finally {
      setGenerating(false);
      setProgress('');
    }
  };

  const handleImprovePrompt = async () => {
    if (!customPrompt.trim()) {
      addToast('error', 'Введите промпт для улучшения');
      return;
    }
    if (!hasKey) {
      addToast('error', 'Настройте API-ключ в разделе Настройки');
      return;
    }

    setImproving(true);
    try {
      const prompt = buildImprovePromptRequest(customPrompt.trim());
      const result = await generateArtifact(prompt, apiKey, llmProvider);
      setCustomPrompt(result.text.trim());
      play('success');
      addToast('success', 'Промпт улучшен');
    } catch (err) {
      play('error');
      const msg = err instanceof Error ? err.message : 'Ошибка улучшения промпта';
      addToast('error', msg);
    } finally {
      setImproving(false);
    }
  };

  return (
    <GlassModal
      open={open}
      onClose={onClose}
      title="Создать артефакт"
      footer={
        <>
          <GlassButton variant="ghost" onClick={onClose} disabled={generating}>
            Отмена
          </GlassButton>
          <GlassButton
            onClick={handleGenerate}
            disabled={generating || improving || !hasKey || !transcript}
          >
            {generating ? progress || 'Генерация...' : 'Создать артефакт'}
          </GlassButton>
        </>
      }
    >
      <div className="flex flex-col gap-4">
        {/* Предупреждение если нет транскрипции */}
        {!transcript && (
          <div className="glass-subtle rounded-xl p-3 text-sm text-warning">
            Нет транскрипции для этой встречи. Сначала обработайте запись через пайплайн.
          </div>
        )}

        {/* Переключатель режима */}
        <div className="flex gap-2">
          <button
            onClick={() => setMode('standard')}
            className={`flex-1 py-2 px-3 rounded-xl text-sm font-medium transition-colors ${
              mode === 'standard'
                ? 'bg-primary/10 text-primary'
                : 'text-text-secondary hover:bg-white/40'
            }`}
          >
            Стандартный тип
          </button>
          <button
            onClick={() => setMode('custom')}
            className={`flex-1 py-2 px-3 rounded-xl text-sm font-medium transition-colors ${
              mode === 'custom'
                ? 'bg-primary/10 text-primary'
                : 'text-text-secondary hover:bg-white/40'
            }`}
          >
            Кастомный промпт
          </button>
        </div>

        {/* Стандартный режим — выбор типа */}
        {mode === 'standard' && (
          <div>
            <p className="text-xs text-text-muted mb-2">Выберите тип артефакта:</p>
            <div className="grid grid-cols-2 gap-2">
              {STANDARD_ARTIFACT_TYPES.map((type) => {
                const exists = existingArtifacts.some((a) => a.type === type);
                return (
                  <button
                    key={type}
                    onClick={() => setSelectedType(type)}
                    className={`flex items-center gap-2 p-2.5 rounded-xl text-left text-sm transition-colors ${
                      selectedType === type
                        ? 'bg-primary/10 text-primary ring-1 ring-primary/30'
                        : 'glass-subtle text-text-secondary hover:bg-white/50'
                    }`}
                  >
                    <span className="text-base">{ARTIFACT_ICONS[type]}</span>
                    <div className="min-w-0">
                      <p className="font-medium truncate">{ARTIFACT_LABELS[type]}</p>
                      {exists && (
                        <p className="text-[10px] text-text-muted">Перегенерация</p>
                      )}
                    </div>
                  </button>
                );
              })}
            </div>
          </div>
        )}

        {/* Кастомный режим */}
        {mode === 'custom' && (
          <>
            <GlassInput
              label="Название (необязательно)"
              value={customTitle}
              onChange={(e) => setCustomTitle(e.target.value)}
              placeholder="Матрица RACI"
            />

            {/* Пресеты */}
            <div>
              <p className="text-xs text-text-muted mb-2">Примеры промптов:</p>
              <div className="flex flex-wrap gap-1.5">
                {CUSTOM_PROMPT_PRESETS.map((preset) => (
                  <button
                    key={preset.label}
                    onClick={() => {
                      setCustomPrompt(preset.prompt);
                      setCustomTitle(preset.label);
                      play('click');
                    }}
                    className="text-xs px-2.5 py-1 rounded-lg glass-subtle text-text-secondary hover:text-text hover:bg-white/50 transition-colors"
                  >
                    {preset.label}
                  </button>
                ))}
              </div>
            </div>

            {/* Textarea для промпта */}
            <div>
              <label className="block text-xs text-text-secondary mb-1">Промпт</label>
              <textarea
                value={customPrompt}
                onChange={(e) => setCustomPrompt(e.target.value)}
                placeholder="Проанализируй стенограмму и составь..."
                rows={5}
                className="w-full glass-subtle rounded-xl p-3 text-sm text-text placeholder-text-muted resize-y focus:outline-none focus:ring-1 focus:ring-primary/30"
              />
            </div>

            {/* Кнопка улучшения промпта */}
            <GlassButton
              variant="ghost"
              size="sm"
              onClick={handleImprovePrompt}
              disabled={improving || !customPrompt.trim() || !hasKey}
            >
              {improving ? 'Улучшаю...' : '✨ Улучшить промпт через AI'}
            </GlassButton>
          </>
        )}

        {/* Не настроен ключ */}
        {!hasKey && (
          <div className="glass-subtle rounded-xl p-3 text-sm text-error">
            API-ключ не настроен. Перейдите в Настройки → API-ключи.
          </div>
        )}
      </div>
    </GlassModal>
  );
}

/** Грубая оценка стоимости */
function estimateCost(tokens: number, _provider: string, model: string): number {
  const rate = MODEL_COSTS[model] || 5.0;
  return (tokens / 1_000_000) * rate;
}
