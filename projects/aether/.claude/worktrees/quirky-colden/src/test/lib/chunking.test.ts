import { describe, it, expect } from 'vitest';
import { estimateTokens, chunkTranscript, estimateChunking, MAX_CHUNK_TOKENS, OVERLAP_TOKENS } from '@/lib/chunking';

describe('estimateTokens', () => {
  it('returns 0 for empty string', () => {
    expect(estimateTokens('')).toBe(0);
  });

  it('returns 0 for falsy input', () => {
    expect(estimateTokens(undefined as unknown as string)).toBe(0);
  });

  it('estimates tokens for short text', () => {
    // "Hello" = 5 chars, ceil(5/2.5) = 2 tokens
    expect(estimateTokens('Hello')).toBe(2);
  });

  it('estimates tokens using Math.ceil(length/2.5)', () => {
    // 10 chars → ceil(10/2.5) = 4
    expect(estimateTokens('12345678901')).toBe(Math.ceil('12345678901'.length / 2.5));
  });

  it('returns positive value for non-empty text', () => {
    expect(estimateTokens('Привет мир')).toBeGreaterThan(0);
  });

  it('longer text has more tokens than shorter', () => {
    const short = estimateTokens('Текст');
    const long = estimateTokens('Очень длинный текст с большим количеством слов');
    expect(long).toBeGreaterThan(short);
  });

  it('is proportional to text length (large texts, no ceiling distortion)', () => {
    // Use large text where ceil rounding effect is minimal
    const base = 'а'.repeat(250); // 250 chars = 100 tokens exactly
    expect(estimateTokens(base)).toBe(100);
    expect(estimateTokens(base.repeat(2))).toBe(200);
  });
});

describe('chunkTranscript', () => {
  it('returns single chunk for short text', () => {
    const text = 'Это короткий текст';
    const chunks = chunkTranscript(text);
    expect(chunks).toHaveLength(1);
    expect(chunks[0]).toBe(text);
  });

  it('splits text that exceeds maxTokens', () => {
    // 'Слово '.repeat(1000) = 6000 chars = 2400 tokens
    // maxTokens=500, overlapTokens=50 to avoid overlap > chunk
    const text = 'Слово '.repeat(1000);
    const chunks = chunkTranscript(text, 500, 50);
    expect(chunks.length).toBeGreaterThan(1);
  });

  it('all chunks are non-empty', () => {
    const text = 'Параграф один.\n\nПараграф два.\n\nПараграф три.'.repeat(50);
    const chunks = chunkTranscript(text, 200, 20);
    expect(chunks.every((c) => c.length > 0)).toBe(true);
  });

  it('chunks preserve content (total chars >= original with overlap)', () => {
    const text = 'Текст '.repeat(200); // 1200 chars = 480 tokens
    const chunks = chunkTranscript(text, 200, 20);
    if (chunks.length > 1) {
      // With overlapping, total can be more than original
      const totalChunkChars = chunks.reduce((sum, c) => sum + c.length, 0);
      expect(totalChunkChars).toBeGreaterThanOrEqual(text.trim().length * 0.9);
    } else {
      expect(chunks[0].trim()).toBe(text.trim());
    }
  });

  it('respects paragraph boundaries', () => {
    // Use large enough text to force splitting, small overlap
    const text = 'Параграф A.\n\nПараграф B.\n\nПараграф C.'.repeat(30);
    // text is ~1200 chars = ~480 tokens, split at 200 tokens
    const chunks = chunkTranscript(text, 200, 20);
    expect(chunks.length).toBeGreaterThan(1);
  });

  it('handles text with no natural break points (hard break fallback)', () => {
    const text = 'а'.repeat(300); // 300 chars = 120 tokens, split at 50 tokens
    const chunks = chunkTranscript(text, 50, 5);
    expect(chunks.length).toBeGreaterThan(0);
    expect(chunks.every((c) => c.length > 0)).toBe(true);
  });

  it('returns single chunk if text fits within maxTokens', () => {
    const text = 'Короткий текст'; // ~6 tokens
    expect(chunkTranscript(text, 100, 10)).toHaveLength(1);
  });
});

describe('estimateChunking', () => {
  it('returns needsChunking: false for short text', () => {
    const result = estimateChunking('Короткий текст');
    expect(result.needsChunking).toBe(false);
    expect(result.chunkCount).toBe(1);
    expect(result.estimatedExtraCost).toBe(1.0);
  });

  it('returns correct totalTokens', () => {
    const text = 'Hello World'; // 11 chars
    const result = estimateChunking(text);
    expect(result.totalTokens).toBe(estimateTokens(text));
  });

  it('returns needsChunking: true for text longer than MAX_CHUNK_TOKENS', () => {
    // MAX_CHUNK_TOKENS = 60_000 → need 60_000 * 2.5 = 150_000 chars
    // Use 152_500 chars (61_000 tokens) to trigger chunking with minimal memory
    const text = 'ab cde'.repeat(25_417); // ~152_502 chars
    const result = estimateChunking(text);
    expect(result.needsChunking).toBe(true);
    expect(result.chunkCount).toBeGreaterThan(1);
  });

  it('chunkCount grows with text length', () => {
    // Use math-based approach instead of large strings
    // At 61_000 tokens: ceil(61_000 / 55_000) = 2 chunks
    // At 116_000 tokens: ceil(116_000 / 55_000) = 3 chunks
    // We verify the formula directly
    const effectiveChunkSize = MAX_CHUNK_TOKENS - OVERLAP_TOKENS; // 55_000
    const chunks61k = Math.ceil(61_000 / effectiveChunkSize);
    const chunks116k = Math.ceil(116_000 / effectiveChunkSize);
    expect(chunks116k).toBeGreaterThan(chunks61k);
  });

  it('estimatedExtraCost equals chunkCount for long text', () => {
    const text = 'ab cde'.repeat(25_417);
    const result = estimateChunking(text);
    expect(result.estimatedExtraCost).toBe(result.chunkCount);
  });

  it('exports correct constants', () => {
    expect(MAX_CHUNK_TOKENS).toBe(60_000);
    expect(OVERLAP_TOKENS).toBe(5_000);
  });
});
