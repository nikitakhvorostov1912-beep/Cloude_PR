/**
 * Рендер артефакта «Глоссарий».
 */

import { Section, Timestamp, safeArray, safeStr } from './shared';

interface GlossaryViewProps {
  data: Record<string, unknown>;
  onTimestampClick?: (seconds: number) => void;
}

export function GlossaryView({ data, onTimestampClick }: GlossaryViewProps) {
  const terms = safeArray<Record<string, unknown>>(data.terms);
  const abbreviations = safeArray<Record<string, unknown>>(data.abbreviations);
  const entityMapping = safeArray<Record<string, unknown>>(data.entity_mapping);

  return (
    <div className="glass rounded-2xl p-6 space-y-1">
      {/* Термины */}
      {terms.length > 0 && (
        <Section title="Термины предметной области" icon="📖" count={terms.length}>
          <div className="space-y-3">
            {terms.map((term, i) => (
              <div key={i} className="glass-subtle rounded-xl p-4">
                <div className="flex items-start justify-between gap-2 mb-1">
                  <div>
                    <h4 className="text-sm font-bold text-text">{safeStr(term.term)}</h4>
                    {safeArray<string>(term.aliases).length > 0 && (
                      <span className="text-xs text-text-muted">
                        Синонимы: {safeArray<string>(term.aliases).join(', ')}
                      </span>
                    )}
                  </div>
                  <div className="flex items-center gap-1.5 flex-shrink-0">
                    <span className="text-[10px] px-1.5 py-0.5 rounded bg-secondary/10 text-secondary font-medium">
                      {safeStr(term.domain, 'other')}
                    </span>
                    {!!term.confidence && safeStr(term.confidence) === 'low' && (
                      <span className="text-[10px] px-1.5 py-0.5 rounded bg-warning/10 text-warning">
                        Не подтверждён
                      </span>
                    )}
                  </div>
                </div>

                <p className="text-sm text-text-secondary mt-1">{safeStr(term.definition)}</p>

                {!!term.usage_example && (
                  <p className="text-xs text-text-muted mt-2 italic">
                    Пример: «{safeStr(term.usage_example)}»
                  </p>
                )}

                <div className="flex items-center gap-2 mt-2">
                  {!!term.mentioned_by && (
                    <span className="text-xs text-text-muted">👤 {safeStr(term.mentioned_by)}</span>
                  )}
                  <Timestamp time={safeStr(term.first_mention)} onClick={onTimestampClick} />
                </div>
              </div>
            ))}
          </div>
        </Section>
      )}

      {/* Аббревиатуры */}
      {abbreviations.length > 0 && (
        <Section title="Аббревиатуры" icon="🔤" count={abbreviations.length}>
          <div className="overflow-x-auto">
            <table className="w-full text-sm">
              <thead>
                <tr className="text-left text-xs text-text-muted">
                  <th className="pb-2 pr-4">Сокращение</th>
                  <th className="pb-2 pr-4">Расшифровка</th>
                  <th className="pb-2 pr-4">Контекст</th>
                  <th className="pb-2">Источник</th>
                </tr>
              </thead>
              <tbody>
                {abbreviations.map((abbr, i) => (
                  <tr key={i} className="border-t border-border/30">
                    <td className="py-2 pr-4 font-mono font-bold text-text">{safeStr(abbr.abbreviation)}</td>
                    <td className="py-2 pr-4 text-text-secondary">{safeStr(abbr.full_form)}</td>
                    <td className="py-2 pr-4 text-text-muted text-xs">{safeStr(abbr.context)}</td>
                    <td className="py-2">
                      <Timestamp time={safeStr(abbr.timestamp)} onClick={onTimestampClick} />
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </Section>
      )}

      {/* Маппинг терминов */}
      {entityMapping.length > 0 && (
        <Section title="Маппинг терминов" icon="🔄" count={entityMapping.length}>
          <p className="text-xs text-text-muted mb-2">Соответствие терминов заказчика и системы</p>
          <div className="overflow-x-auto">
            <table className="w-full text-sm">
              <thead>
                <tr className="text-left text-xs text-text-muted">
                  <th className="pb-2 pr-4">Термин заказчика</th>
                  <th className="pb-2 pr-4">В системе</th>
                  <th className="pb-2">Примечание</th>
                </tr>
              </thead>
              <tbody>
                {entityMapping.map((em, i) => (
                  <tr key={i} className="border-t border-border/30">
                    <td className="py-2 pr-4 text-text">{safeStr(em.business_name)}</td>
                    <td className="py-2 pr-4 font-mono text-primary text-xs">{safeStr(em.system_name)}</td>
                    <td className="py-2 text-text-muted text-xs">{safeStr(em.notes)}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </Section>
      )}
    </div>
  );
}
