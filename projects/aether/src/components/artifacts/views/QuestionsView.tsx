/**
 * Рендер артефакта «Открытые вопросы».
 */

import { Section, ItemCard, Timestamp, StatusBadge, safeArray, safeStr } from './shared';

interface QuestionsViewProps {
  data: Record<string, unknown>;
  onTimestampClick?: (seconds: number) => void;
}

const urgencyConfig: Record<string, { icon: string; label: string }> = {
  blocking: { icon: '🔴', label: 'Блокирующий' },
  important: { icon: '🟡', label: 'Важный' },
  nice_to_have: { icon: '🟢', label: 'Желательный' },
};

export function QuestionsView({ data, onTimestampClick }: QuestionsViewProps) {
  const openQuestions = safeArray<Record<string, unknown>>(data.open_questions);
  const deferredTopics = safeArray<Record<string, unknown>>(data.deferred_topics);
  const infoGaps = safeArray<Record<string, unknown>>(data.information_gaps);
  const agendaSuggestions = safeArray<string>(data.next_meeting_agenda_suggestions);

  // Группируем вопросы по urgency
  const blocking = openQuestions.filter((q) => safeStr(q.urgency) === 'blocking');
  const important = openQuestions.filter((q) => safeStr(q.urgency) === 'important');
  const niceToHave = openQuestions.filter((q) => safeStr(q.urgency) === 'nice_to_have');
  const other = openQuestions.filter(
    (q) => !['blocking', 'important', 'nice_to_have'].includes(safeStr(q.urgency)),
  );

  const renderQuestionGroup = (questions: Record<string, unknown>[], urgency: string) => {
    if (questions.length === 0) return null;
    const config = urgencyConfig[urgency] || { icon: '❓', label: urgency };

    return (
      <div className="mb-4">
        <div className="flex items-center gap-2 mb-2">
          <span>{config.icon}</span>
          <span className="text-xs font-bold text-text-muted uppercase">{config.label}</span>
          <span className="text-xs text-text-muted">({questions.length})</span>
        </div>
        {questions.map((q, i) => (
          <ItemCard key={i} id={safeStr(q.id)}>
            <p className="text-sm font-medium text-text">{safeStr(q.question)}</p>
            {!!q.context && (
              <p className="text-xs text-text-secondary mt-1">{safeStr(q.context)}</p>
            )}
            <div className="flex flex-wrap items-center gap-2 mt-2 text-xs text-text-muted">
              {!!q.category && (
                <span className="px-1.5 py-0.5 rounded bg-text-muted/10">{safeStr(q.category)}</span>
              )}
              {!!q.directed_to && <span>👤 {safeStr(q.directed_to)}</span>}
              {!!q.related_requirement && <span>📝 {safeStr(q.related_requirement)}</span>}
              <StatusBadge status={safeStr(q.status, 'open')} />
              <Timestamp time={safeStr(q.timestamp)} onClick={onTimestampClick} />
            </div>
          </ItemCard>
        ))}
      </div>
    );
  };

  return (
    <div className="glass rounded-2xl p-6 space-y-1">
      {/* Статистика */}
      <div className="flex gap-4 mb-4 text-sm">
        <div className="flex items-center gap-1.5">
          <span className="text-error font-bold">{blocking.length}</span>
          <span className="text-text-muted">блокирующих</span>
        </div>
        <div className="flex items-center gap-1.5">
          <span className="text-warning font-bold">{important.length}</span>
          <span className="text-text-muted">важных</span>
        </div>
        <div className="flex items-center gap-1.5">
          <span className="text-success font-bold">{niceToHave.length + other.length}</span>
          <span className="text-text-muted">прочих</span>
        </div>
      </div>

      {/* Открытые вопросы */}
      {openQuestions.length > 0 && (
        <Section title="Открытые вопросы" icon="❓" count={openQuestions.length}>
          {renderQuestionGroup(blocking, 'blocking')}
          {renderQuestionGroup(important, 'important')}
          {renderQuestionGroup(niceToHave, 'nice_to_have')}
          {renderQuestionGroup(other, 'other')}
        </Section>
      )}

      {/* Отложенные темы */}
      {deferredTopics.length > 0 && (
        <Section title="Отложенные темы" icon="📋" count={deferredTopics.length}>
          {deferredTopics.map((dt, i) => (
            <ItemCard key={i} id={safeStr(dt.id)}>
              <p className="text-sm font-medium text-text">{safeStr(dt.topic)}</p>
              {!!dt.reason && (
                <p className="text-xs text-text-secondary mt-1">Причина: {safeStr(dt.reason)}</p>
              )}
              {!!dt.deferred_to && (
                <p className="text-xs text-text-muted mt-1">Вернуться: {safeStr(dt.deferred_to)}</p>
              )}
              <Timestamp time={safeStr(dt.timestamp)} onClick={onTimestampClick} />
            </ItemCard>
          ))}
        </Section>
      )}

      {/* Информационные пробелы */}
      {infoGaps.length > 0 && (
        <Section title="Информационные пробелы" icon="🕳️" count={infoGaps.length}>
          {infoGaps.map((gap, i) => (
            <ItemCard key={i} id={safeStr(gap.id)}>
              <h4 className="text-sm font-semibold text-text">{safeStr(gap.area)}</h4>
              <p className="text-sm text-text-secondary mt-1">{safeStr(gap.what_is_needed)}</p>
              <div className="flex flex-wrap gap-2 mt-2 text-xs text-text-muted">
                {!!gap.who_might_know && <span>👤 {safeStr(gap.who_might_know)}</span>}
                {!!gap.impact && <span>⚡ {safeStr(gap.impact)}</span>}
              </div>
            </ItemCard>
          ))}
        </Section>
      )}

      {/* Рекомендации для следующей встречи */}
      {agendaSuggestions.length > 0 && (
        <Section title="Рекомендуемая повестка следующей встречи" icon="📌">
          <ol className="list-decimal list-inside space-y-1.5">
            {agendaSuggestions.map((suggestion, i) => (
              <li key={i} className="text-sm text-text-secondary">{suggestion}</li>
            ))}
          </ol>
        </Section>
      )}
    </div>
  );
}
