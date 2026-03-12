/**
 * Разбивка длинных транскриптов на чанки для LLM.
 * Стратегия: 60K токенов максимум + 5K перекрытие.
 */

/** 1 токен ≈ 4 символа для English, ≈ 2 символа для Russian (conservative) */
const CHARS_PER_TOKEN_RU = 2.5;

/** Максимум токенов в одном чанке */
export const MAX_CHUNK_TOKENS = 60_000;

/** Перекрытие между чанками для сохранения контекста */
export const OVERLAP_TOKENS = 5_000;

/**
 * Грубая оценка количества токенов в тексте.
 * Для русского языка: ~2.5 символа на токен.
 */
export function estimateTokens(text: string): number {
  if (!text) return 0;
  return Math.ceil(text.length / CHARS_PER_TOKEN_RU);
}

/**
 * Оценка количества символов для заданного числа токенов.
 */
function tokensToChars(tokens: number): number {
  return Math.floor(tokens * CHARS_PER_TOKEN_RU);
}

/**
 * Разбивает текст на чанки по границам предложений/абзацев.
 * Каждый чанк не превышает maxTokens, с перекрытием overlapTokens.
 */
export function chunkTranscript(
  text: string,
  maxTokens: number = MAX_CHUNK_TOKENS,
  overlapTokens: number = OVERLAP_TOKENS,
): string[] {
  const totalTokens = estimateTokens(text);

  // Если текст помещается в один чанк — возвращаем как есть
  if (totalTokens <= maxTokens) {
    return [text];
  }

  const maxChars = tokensToChars(maxTokens);
  const overlapChars = tokensToChars(overlapTokens);
  const chunks: string[] = [];
  let position = 0;

  while (position < text.length) {
    let end = Math.min(position + maxChars, text.length);

    // Ищем ближайшую границу абзаца или предложения
    if (end < text.length) {
      end = findBreakPoint(text, end, position + maxChars - tokensToChars(2_000));
    }

    chunks.push(text.slice(position, end).trim());

    // Следующий чанк начинается с перекрытием
    position = end - overlapChars;

    // Защита от бесконечного цикла
    if (position <= 0 || position >= text.length) break;
  }

  return chunks.filter((c) => c.length > 0);
}

/**
 * Находит ближайшую точку разрыва (конец абзаца/предложения)
 * в окрестности target, не раньше minPosition.
 */
function findBreakPoint(text: string, target: number, minPosition: number): number {
  // Приоритет 1: двойной перенос строки (абзац)
  const paragraphBreak = text.lastIndexOf('\n\n', target);
  if (paragraphBreak > minPosition) return paragraphBreak + 2;

  // Приоритет 2: одинарный перенос строки
  const lineBreak = text.lastIndexOf('\n', target);
  if (lineBreak > minPosition) return lineBreak + 1;

  // Приоритет 3: конец предложения (. ! ?)
  for (let i = target; i > minPosition; i--) {
    const char = text[i];
    if ((char === '.' || char === '!' || char === '?') && (i + 1 >= text.length || text[i + 1] === ' ' || text[i + 1] === '\n')) {
      return i + 1;
    }
  }

  // Приоритет 4: пробел
  const spaceBreak = text.lastIndexOf(' ', target);
  if (spaceBreak > minPosition) return spaceBreak + 1;

  // Fallback: жёсткий разрыв
  return target;
}

/**
 * Информация о разбивке для отображения пользователю.
 */
export interface ChunkingInfo {
  totalTokens: number;
  chunkCount: number;
  needsChunking: boolean;
  estimatedExtraCost: number; // множитель стоимости (1.0 = без разбивки)
}

/**
 * Оценивает параметры чанкинга без реальной разбивки.
 */
export function estimateChunking(text: string): ChunkingInfo {
  const totalTokens = estimateTokens(text);
  const needsChunking = totalTokens > MAX_CHUNK_TOKENS;

  if (!needsChunking) {
    return { totalTokens, chunkCount: 1, needsChunking: false, estimatedExtraCost: 1.0 };
  }

  // Оценка количества чанков с учётом перекрытия
  const effectiveChunkSize = MAX_CHUNK_TOKENS - OVERLAP_TOKENS;
  const chunkCount = Math.ceil(totalTokens / effectiveChunkSize);
  const estimatedExtraCost = chunkCount;

  return { totalTokens, chunkCount, needsChunking, estimatedExtraCost };
}
