/**
 * Валидация JSON-ответов от LLM.
 * Обработка edge cases: EC-11 (невалидный JSON), EC-12 (пустой артефакт).
 */

import type { ArtifactType } from '@/types/artifact.types';

export interface ValidationResult {
  valid: boolean;
  data: Record<string, unknown> | null;
  errors: string[];
  isEmpty: boolean;
}

/**
 * Очищает ответ LLM от markdown-обёрток и мусора.
 * Обрабатывает типичные проблемы:
 * - ```json ... ``` обёртки
 * - Текст до/после JSON
 * - BOM-символы
 * - Незакрытые строки/скобки
 */
export function cleanLLMResponse(text: string): string {
  let cleaned = text.trim();

  // Убираем BOM
  cleaned = cleaned.replace(/^\uFEFF/, '');

  // Убираем markdown-обёртки: ```json ... ```
  const jsonBlockMatch = cleaned.match(/```(?:json)?\s*\n?([\s\S]*?)\n?\s*```/);
  if (jsonBlockMatch) {
    cleaned = jsonBlockMatch[1].trim();
  }

  // Ищем первый { или [ и последний } или ]
  const firstBrace = cleaned.indexOf('{');
  const firstBracket = cleaned.indexOf('[');

  let start = -1;
  if (firstBrace === -1 && firstBracket === -1) {
    return cleaned; // нет JSON-структуры
  } else if (firstBrace === -1) {
    start = firstBracket;
  } else if (firstBracket === -1) {
    start = firstBrace;
  } else {
    start = Math.min(firstBrace, firstBracket);
  }

  const isArray = cleaned[start] === '[';
  const closeChar = isArray ? ']' : '}';
  const lastClose = cleaned.lastIndexOf(closeChar);

  if (lastClose > start) {
    cleaned = cleaned.slice(start, lastClose + 1);
  } else {
    cleaned = cleaned.slice(start);
  }

  return cleaned;
}

/**
 * Попытка парсинга JSON с автоисправлением.
 * Retry-логика: очистка → парсинг → попытка починить → парсинг.
 */
export function tryParseJSON(text: string): { ok: true; data: unknown } | { ok: false; error: string; rawText: string } {
  // Попытка 1: парсим как есть
  try {
    const data = JSON.parse(text);
    return { ok: true, data };
  } catch {
    // продолжаем
  }

  // Попытка 2: очищаем и парсим
  const cleaned = cleanLLMResponse(text);
  try {
    const data = JSON.parse(cleaned);
    return { ok: true, data };
  } catch {
    // продолжаем
  }

  // Попытка 3: пробуем починить распространённые ошибки
  const fixed = attemptJSONFix(cleaned);
  try {
    const data = JSON.parse(fixed);
    return { ok: true, data };
  } catch (e) {
    const error = e instanceof Error ? e.message : 'Unknown parse error';
    return { ok: false, error, rawText: text };
  }
}

/**
 * Попытка исправить распространённые ошибки JSON от LLM.
 */
function attemptJSONFix(text: string): string {
  let fixed = text;

  // Убираем trailing commas: ,} и ,]
  fixed = fixed.replace(/,\s*([\]}])/g, '$1');

  // Закрываем незакрытые скобки
  const openBraces = (fixed.match(/{/g) || []).length;
  const closeBraces = (fixed.match(/}/g) || []).length;
  const openBrackets = (fixed.match(/\[/g) || []).length;
  const closeBrackets = (fixed.match(/]/g) || []).length;

  for (let i = 0; i < openBrackets - closeBrackets; i++) {
    fixed += ']';
  }
  for (let i = 0; i < openBraces - closeBraces; i++) {
    fixed += '}';
  }

  // Заменяем одинарные кавычки на двойные (только в ключах/значениях)
  // Осторожно — не ломаем строки с апострофами
  fixed = fixed.replace(/(\s|[{[,:])'([^']*?)'(\s|[}\],:])/g, '$1"$2"$3');

  return fixed;
}

/**
 * Проверяет, пуст ли артефакт (EC-12).
 * Для каждого типа артефакта проверяет ключевые массивы/поля.
 */
export function isEmptyArtifact(type: ArtifactType, data: Record<string, unknown>): boolean {
  switch (type) {
    case 'protocol':
      return isEmptyArray(data.participants) && isEmptyArray(data.decisions) && isEmptyArray(data.action_items);
    case 'requirements':
      return isEmptyArray(data.functional_requirements) && isEmptyArray(data.non_functional_requirements);
    case 'risks':
      return isEmptyArray(data.risks) && isEmptyArray(data.uncertainties) && isEmptyArray(data.contradictions);
    case 'glossary':
      return isEmptyArray(data.terms) && isEmptyArray(data.abbreviations);
    case 'questions':
      return isEmptyArray(data.open_questions) && isEmptyArray(data.deferred_topics);
    case 'transcript':
      return isEmptyArray(data.formatted_transcript);
    default:
      return false;
  }
}

function isEmptyArray(value: unknown): boolean {
  return !Array.isArray(value) || value.length === 0;
}

/**
 * Валидация схемы артефакта.
 * Проверяет наличие обязательных полей верхнего уровня.
 */
export function validateArtifactSchema(type: ArtifactType, data: unknown): ValidationResult {
  if (!data || typeof data !== 'object') {
    return { valid: false, data: null, errors: ['Ответ не является объектом'], isEmpty: true };
  }

  const obj = data as Record<string, unknown>;
  const errors: string[] = [];

  const requiredFields = REQUIRED_FIELDS[type];
  for (const field of requiredFields) {
    if (!(field in obj)) {
      errors.push(`Отсутствует обязательное поле: ${field}`);
    }
  }

  const isEmpty = isEmptyArtifact(type, obj);

  return {
    valid: errors.length === 0,
    data: errors.length === 0 ? obj : null,
    errors,
    isEmpty,
  };
}

/** Обязательные поля верхнего уровня для каждого типа артефакта */
const REQUIRED_FIELDS: Record<ArtifactType, string[]> = {
  protocol: ['participants', 'decisions', 'action_items'],
  requirements: ['functional_requirements', 'non_functional_requirements'],
  risks: ['risks', 'uncertainties'],
  glossary: ['terms'],
  questions: ['open_questions'],
  transcript: ['formatted_transcript', 'chapters'],
};
