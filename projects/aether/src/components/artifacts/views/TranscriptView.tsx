/**
 * Рендер артефакта «Стенограмма».
 */

import { Section, Timestamp, safeArray, safeStr, safeNum } from './shared';

interface TranscriptViewProps {
  data: Record<string, unknown>;
  onTimestampClick?: (seconds: number) => void;
}

export function TranscriptView({ data, onTimestampClick }: TranscriptViewProps) {
  const entries = safeArray<Record<string, unknown>>(data.formatted_transcript);
  const chapters = safeArray<Record<string, unknown>>(data.chapters);
  const stats = data.statistics as Record<string, unknown> | undefined;

  return (
    <div className="glass rounded-2xl p-6 space-y-1">
      {/* Статистика */}
      {!!stats && (
        <div className="flex flex-wrap gap-4 mb-4 pb-4 border-b border-border text-sm">
          {safeNum(stats.total_duration_minutes) > 0 && (
            <div>
              <span className="text-text-muted">Длительность: </span>
              <strong className="text-text">{safeNum(stats.total_duration_minutes)} мин</strong>
            </div>
          )}
          {safeNum(stats.speakers_count) > 0 && (
            <div>
              <span className="text-text-muted">Участников: </span>
              <strong className="text-text">{safeNum(stats.speakers_count)}</strong>
            </div>
          )}
          {!!stats.dominant_speaker && (
            <div>
              <span className="text-text-muted">Основной: </span>
              <strong className="text-text">{safeStr(stats.dominant_speaker)}</strong>
            </div>
          )}
        </div>
      )}

      {/* Статистика по участникам */}
      {!!stats?.speaker_time && typeof stats.speaker_time === 'object' && (
        <Section title="Время участников" icon="👥">
          <div className="space-y-2">
            {Object.entries(stats.speaker_time as Record<string, unknown>).map(([speaker, percent]) => (
              <div key={speaker} className="flex items-center gap-3">
                <span className="text-sm text-text w-32 truncate">{speaker}</span>
                <div className="flex-1 h-2 rounded-full bg-text-muted/10 overflow-hidden">
                  <div
                    className="h-full rounded-full bg-primary/40"
                    style={{ width: `${safeNum(percent)}%` }}
                  />
                </div>
                <span className="text-xs text-text-muted w-10 text-right">{safeNum(percent)}%</span>
              </div>
            ))}
          </div>
        </Section>
      )}

      {/* Содержание (главы) */}
      {chapters.length > 0 && (
        <Section title="Содержание" icon="📑" count={chapters.length}>
          <div className="space-y-1">
            {chapters.map((ch, i) => (
              <div key={i} className="flex items-center gap-3 py-1.5 text-sm">
                <span className="text-xs text-text-muted w-6">{i + 1}.</span>
                <span className="flex-1 text-text">{safeStr(ch.title)}</span>
                <button
                  onClick={() => {
                    if (!onTimestampClick) return;
                    const parts = safeStr(ch.start).split(':').map(Number);
                    const seconds = parts.length === 3
                      ? parts[0] * 3600 + parts[1] * 60 + parts[2]
                      : parts.length === 2
                        ? parts[0] * 60 + parts[1]
                        : parts[0];
                    onTimestampClick(seconds);
                  }}
                  className="text-xs font-mono text-primary hover:text-primary/80"
                >
                  {safeStr(ch.start)}
                </button>
              </div>
            ))}
          </div>
        </Section>
      )}

      {/* Стенограмма */}
      {entries.length > 0 && (
        <Section title="Стенограмма" icon="🎙️" count={entries.length}>
          <div className="space-y-0">
            {entries.map((entry, i) => {
              const prevEntry = i > 0 ? entries[i - 1] : null;
              const isSameSpeaker = prevEntry && safeStr(prevEntry.speaker) === safeStr(entry.speaker);

              return (
                <div
                  key={i}
                  className={`flex gap-3 py-2 ${!isSameSpeaker ? 'border-t border-border/20 mt-1' : ''}`}
                >
                  {/* Таймкод */}
                  <div className="flex-shrink-0 w-16">
                    <Timestamp time={safeStr(entry.timestamp)} onClick={onTimestampClick} />
                  </div>

                  {/* Контент */}
                  <div className="flex-1 min-w-0">
                    {!isSameSpeaker && (
                      <span className="text-xs font-bold text-primary block mb-0.5">
                        {safeStr(entry.speaker, 'Участник')}
                      </span>
                    )}
                    <p className="text-sm text-text leading-relaxed">{safeStr(entry.text)}</p>
                    {safeArray<string>(entry.topics).length > 0 && (
                      <div className="flex flex-wrap gap-1 mt-1">
                        {safeArray<string>(entry.topics).map((topic, j) => (
                          <span
                            key={j}
                            className="text-[10px] px-1.5 py-0.5 rounded bg-secondary/10 text-secondary"
                          >
                            {topic}
                          </span>
                        ))}
                      </div>
                    )}
                  </div>
                </div>
              );
            })}
          </div>
        </Section>
      )}
    </div>
  );
}
