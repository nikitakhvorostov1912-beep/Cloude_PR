/**
 * Рендер артефакта «Карта рисков».
 */

import { Section, ItemCard, Timestamp, PriorityBadge, StatusBadge, Quote, safeArray, safeStr } from './shared';

interface RisksViewProps {
  data: Record<string, unknown>;
  onTimestampClick?: (seconds: number) => void;
}

export function RisksView({ data, onTimestampClick }: RisksViewProps) {
  const risks = safeArray<Record<string, unknown>>(data.risks);
  const uncertainties = safeArray<Record<string, unknown>>(data.uncertainties);
  const contradictions = safeArray<Record<string, unknown>>(data.contradictions);
  const assumptions = safeArray<Record<string, unknown>>(data.assumptions);

  return (
    <div className="glass rounded-2xl p-6 space-y-1">
      {/* Матрица рисков (визуальная) */}
      {risks.length > 0 && (
        <Section title="Риски" icon="⚠️" count={risks.length}>
          {/* Мини-матрица */}
          <div className="grid grid-cols-3 gap-1 mb-4 p-3 rounded-lg bg-text/3">
            {['high', 'medium', 'low'].map((impact) => (
              ['high', 'medium', 'low'].map((prob) => {
                const matching = risks.filter(
                  (r) => safeStr(r.impact).toLowerCase() === impact && safeStr(r.probability).toLowerCase() === prob
                );
                const severity =
                  (impact === 'high' && prob === 'high') ? 'bg-error/20 text-error' :
                  (impact === 'high' || prob === 'high') ? 'bg-warning/20 text-warning' :
                  'bg-text-muted/10 text-text-muted';

                return (
                  <div
                    key={`${impact}-${prob}`}
                    className={`rounded p-1.5 text-center text-[10px] ${severity}`}
                    title={`Влияние: ${impact}, Вероятность: ${prob}`}
                  >
                    {matching.length > 0
                      ? matching.map((r) => safeStr(r.id)).join(', ')
                      : '—'
                    }
                  </div>
                );
              })
            ))}
          </div>

          {/* Детализация */}
          {risks.map((risk, i) => (
            <ItemCard key={i} id={safeStr(risk.id)}>
              <div className="flex items-start justify-between gap-2 mb-1">
                <h4 className="text-sm font-semibold text-text">{safeStr(risk.title)}</h4>
                <div className="flex items-center gap-1.5 flex-shrink-0">
                  <PriorityBadge priority={safeStr(risk.impact)} />
                  <StatusBadge status={safeStr(risk.status)} />
                </div>
              </div>
              <span className="text-[10px] text-text-muted uppercase">{safeStr(risk.category)}</span>
              <p className="text-sm text-text-secondary mt-1">{safeStr(risk.description)}</p>
              {!!risk.trigger && (
                <p className="text-xs text-text-muted mt-1">🎯 Триггер: {safeStr(risk.trigger)}</p>
              )}
              {!!risk.mitigation_hint && (
                <p className="text-xs text-success/80 mt-1">🛡 Смягчение: {safeStr(risk.mitigation_hint)}</p>
              )}
              {!!risk.source_quote && (
                <Quote
                  text={safeStr(risk.source_quote)}
                  timestamp={safeStr(risk.timestamp)}
                  onTimestampClick={onTimestampClick}
                />
              )}
              {!risk.source_quote && (
                <Timestamp time={safeStr(risk.timestamp)} onClick={onTimestampClick} />
              )}
            </ItemCard>
          ))}
        </Section>
      )}

      {/* Неопределённости */}
      {uncertainties.length > 0 && (
        <Section title="Неопределённости" icon="❓" count={uncertainties.length}>
          {uncertainties.map((unc, i) => (
            <ItemCard key={i} id={safeStr(unc.id)}>
              <h4 className="text-sm font-semibold text-text">{safeStr(unc.topic)}</h4>
              <p className="text-sm text-text-secondary mt-1">{safeStr(unc.what_is_unknown)}</p>
              {!!unc.who_can_clarify && (
                <p className="text-xs text-text-muted mt-1">👤 Кто уточнит: {safeStr(unc.who_can_clarify)}</p>
              )}
              {!!unc.impact_if_unresolved && (
                <p className="text-xs text-warning mt-1">⚡ Если не решить: {safeStr(unc.impact_if_unresolved)}</p>
              )}
              <Timestamp time={safeStr(unc.timestamp)} onClick={onTimestampClick} />
            </ItemCard>
          ))}
        </Section>
      )}

      {/* Противоречия */}
      {contradictions.length > 0 && (
        <Section title="Противоречия" icon="⚡" count={contradictions.length}>
          {contradictions.map((c, i) => {
            const a = c.statement_a as Record<string, unknown> | undefined;
            const b = c.statement_b as Record<string, unknown> | undefined;

            return (
              <ItemCard key={i} id={safeStr(c.id)}>
                <div className="flex items-center gap-2 mb-2">
                  <PriorityBadge priority={safeStr(c.severity)} />
                  {c.resolution ? (
                    <StatusBadge status="resolved" />
                  ) : (
                    <StatusBadge status="open" />
                  )}
                </div>
                {a && (
                  <div className="border-l-2 border-primary/30 pl-3 mb-2">
                    <p className="text-xs text-text-muted">{safeStr(a.speaker)}</p>
                    <p className="text-sm text-text-secondary">{safeStr(a.position)}</p>
                    <Timestamp time={safeStr(a.timestamp)} onClick={onTimestampClick} />
                  </div>
                )}
                {b && (
                  <div className="border-l-2 border-error/30 pl-3">
                    <p className="text-xs text-text-muted">{safeStr(b.speaker)}</p>
                    <p className="text-sm text-text-secondary">{safeStr(b.position)}</p>
                    <Timestamp time={safeStr(b.timestamp)} onClick={onTimestampClick} />
                  </div>
                )}
              </ItemCard>
            );
          })}
        </Section>
      )}

      {/* Допущения */}
      {assumptions.length > 0 && (
        <Section title="Допущения" icon="💭" count={assumptions.length}>
          {assumptions.map((a, i) => (
            <div key={i} className="flex items-start gap-2 py-1.5 text-sm">
              <span className={`text-xs mt-0.5 ${a.needs_validation ? 'text-warning' : 'text-success'}`}>
                {a.needs_validation ? '⚠' : '✓'}
              </span>
              <div className="flex-1">
                <span className="text-text">{safeStr(a.assumption)}</span>
                {!!a.stated_by && <span className="text-text-muted text-xs ml-2">— {safeStr(a.stated_by)}</span>}
              </div>
              <Timestamp time={safeStr(a.timestamp)} onClick={onTimestampClick} />
            </div>
          ))}
        </Section>
      )}
    </div>
  );
}
