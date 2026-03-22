/**
 * Рендер протокола встречи.
 */

import { Section, ItemCard, Timestamp, PriorityBadge, Quote, safeArray, safeStr } from './shared';

interface ProtocolViewProps {
  data: Record<string, unknown>;
  onTimestampClick?: (seconds: number) => void;
}

export function ProtocolView({ data, onTimestampClick }: ProtocolViewProps) {
  const participants = safeArray<Record<string, unknown>>(data.participants);
  const agenda = safeArray<Record<string, unknown>>(data.agenda);
  const decisions = safeArray<Record<string, unknown>>(data.decisions);
  const actionItems = safeArray<Record<string, unknown>>(data.action_items);
  const keyStatements = safeArray<Record<string, unknown>>(data.key_statements);
  const nextSteps = data.next_steps as Record<string, unknown> | undefined;

  return (
    <div className="glass rounded-2xl p-6 space-y-1">
      {/* Заголовок */}
      <div className="mb-4 pb-4 border-b border-border">
        <h2 className="text-lg font-bold text-text">{safeStr(data.title, 'Протокол встречи')}</h2>
        <div className="flex flex-wrap gap-3 mt-2 text-xs text-text-muted">
          {!!data.date && <span>📅 {safeStr(data.date)}</span>}
          {!!data.meeting_type && <span>📌 {safeStr(data.meeting_type)}</span>}
          {!!data.duration_minutes && <span>⏱ {safeStr(data.duration_minutes)} мин</span>}
        </div>
      </div>

      {/* Участники */}
      {participants.length > 0 && (
        <Section title="Участники" icon="👥" count={participants.length}>
          <div className="overflow-x-auto">
            <table className="w-full text-sm">
              <thead>
                <tr className="text-left text-xs text-text-muted">
                  <th className="pb-2 pr-4">ФИО</th>
                  <th className="pb-2 pr-4">Роль</th>
                  <th className="pb-2">Организация</th>
                </tr>
              </thead>
              <tbody>
                {participants.map((p, i) => (
                  <tr key={i} className="border-t border-border/30">
                    <td className="py-2 pr-4 font-medium text-text">{safeStr(p.name)}</td>
                    <td className="py-2 pr-4 text-text-secondary">{safeStr(p.role)}</td>
                    <td className="py-2 text-text-secondary">{safeStr(p.organization)}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </Section>
      )}

      {/* Повестка */}
      {agenda.length > 0 && (
        <Section title="Повестка" icon="📋" count={agenda.length}>
          {agenda.map((item, i) => (
            <div key={i} className="flex items-center gap-3 py-1.5 text-sm">
              <span className="text-xs text-text-muted w-6">{i + 1}.</span>
              <span className="flex-1 text-text">{safeStr(item.topic)}</span>
              <span className="text-xs text-text-muted font-mono">
                {safeStr(item.discussed_from)}–{safeStr(item.discussed_to)}
              </span>
            </div>
          ))}
        </Section>
      )}

      {/* Решения */}
      {decisions.length > 0 && (
        <Section title="Принятые решения" icon="✅" count={decisions.length}>
          {decisions.map((d, i) => (
            <ItemCard key={i} id={safeStr(d.id)}>
              <div className="flex items-start justify-between gap-2">
                <p className="text-sm font-medium text-text">{safeStr(d.description)}</p>
                <Timestamp time={safeStr(d.timestamp)} onClick={onTimestampClick} />
              </div>
              {!!d.rationale && (
                <p className="text-xs text-text-secondary mt-1">Обоснование: {safeStr(d.rationale)}</p>
              )}
              <div className="flex flex-wrap gap-2 mt-2 text-xs text-text-muted">
                {!!d.responsible && <span>👤 {safeStr(d.responsible)}</span>}
                {!!d.deadline && <span>📅 {safeStr(d.deadline)}</span>}
              </div>
            </ItemCard>
          ))}
        </Section>
      )}

      {/* Задачи */}
      {actionItems.length > 0 && (
        <Section title="Задачи" icon="📌" count={actionItems.length}>
          {actionItems.map((ai, i) => (
            <ItemCard key={i} id={safeStr(ai.id)}>
              <div className="flex items-start justify-between gap-2">
                <p className="text-sm text-text">{safeStr(ai.description)}</p>
                <div className="flex items-center gap-1.5 flex-shrink-0">
                  <PriorityBadge priority={safeStr(ai.priority)} />
                  <Timestamp time={safeStr(ai.timestamp)} onClick={onTimestampClick} />
                </div>
              </div>
              <div className="flex flex-wrap gap-2 mt-2 text-xs text-text-muted">
                {!!ai.responsible && <span>👤 {safeStr(ai.responsible)}</span>}
                {!!ai.deadline && <span>📅 {safeStr(ai.deadline)}</span>}
              </div>
            </ItemCard>
          ))}
        </Section>
      )}

      {/* Ключевые высказывания */}
      {keyStatements.length > 0 && (
        <Section title="Ключевые высказывания" icon="💬" count={keyStatements.length}>
          {keyStatements.map((ks, i) => (
            <Quote
              key={i}
              text={safeStr(ks.quote)}
              speaker={safeStr(ks.speaker)}
              timestamp={safeStr(ks.timestamp)}
              onTimestampClick={onTimestampClick}
            />
          ))}
        </Section>
      )}

      {/* Следующие шаги */}
      {nextSteps && (
        <Section title="Следующие шаги" icon="➡️">
          {!!nextSteps.next_meeting_date && (
            <p className="text-sm text-text mb-2">
              📅 Следующая встреча: <strong>{safeStr(nextSteps.next_meeting_date)}</strong>
            </p>
          )}
          {safeArray<string>(nextSteps.next_meeting_topics).length > 0 && (
            <ul className="list-disc list-inside text-sm text-text-secondary space-y-1">
              {safeArray<string>(nextSteps.next_meeting_topics).map((t, i) => (
                <li key={i}>{t}</li>
              ))}
            </ul>
          )}
        </Section>
      )}
    </div>
  );
}
