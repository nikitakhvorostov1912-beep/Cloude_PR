/**
 * Рендер артефакта «Требования».
 */

import { Section, ItemCard, Timestamp, PriorityBadge, StatusBadge, safeArray, safeStr } from './shared';

interface RequirementsViewProps {
  data: Record<string, unknown>;
  onTimestampClick?: (seconds: number) => void;
}

export function RequirementsView({ data, onTimestampClick }: RequirementsViewProps) {
  const funcReqs = safeArray<Record<string, unknown>>(data.functional_requirements);
  const nonFuncReqs = safeArray<Record<string, unknown>>(data.non_functional_requirements);
  const businessRules = safeArray<Record<string, unknown>>(data.business_rules);
  const integrations = safeArray<Record<string, unknown>>(data.integrations);
  const constraints = safeArray<Record<string, unknown>>(data.constraints);
  const processDesc = data.process_description as Record<string, unknown> | undefined;

  return (
    <div className="glass rounded-2xl p-6 space-y-1">
      {/* Функциональные требования */}
      {funcReqs.length > 0 && (
        <Section title="Функциональные требования" icon="📝" count={funcReqs.length}>
          {funcReqs.map((req, i) => (
            <ItemCard key={i} id={safeStr(req.id)}>
              <div className="flex items-start justify-between gap-2 mb-1">
                <h4 className="text-sm font-semibold text-text">{safeStr(req.title)}</h4>
                <div className="flex items-center gap-1.5 flex-shrink-0">
                  <PriorityBadge priority={safeStr(req.priority)} />
                  <StatusBadge status={safeStr(req.status)} />
                </div>
              </div>
              <p className="text-sm text-text-secondary">{safeStr(req.description)}</p>
              {!!req.user_story && (
                <p className="text-xs text-primary/70 mt-1 italic">{safeStr(req.user_story)}</p>
              )}
              {safeArray<string>(req.acceptance_criteria).length > 0 && (
                <div className="mt-2">
                  <span className="text-xs font-medium text-text-muted">Критерии приёмки:</span>
                  <ul className="mt-1 space-y-0.5">
                    {safeArray<string>(req.acceptance_criteria).map((c, j) => (
                      <li key={j} className="text-xs text-text-secondary flex items-start gap-1.5">
                        <span className="text-success mt-0.5">✓</span>
                        {c}
                      </li>
                    ))}
                  </ul>
                </div>
              )}
              <div className="flex items-center gap-2 mt-2">
                <Timestamp time={safeStr(req.timestamp)} onClick={onTimestampClick} />
              </div>
            </ItemCard>
          ))}
        </Section>
      )}

      {/* Нефункциональные требования */}
      {nonFuncReqs.length > 0 && (
        <Section title="Нефункциональные требования" icon="⚙️" count={nonFuncReqs.length}>
          {nonFuncReqs.map((req, i) => (
            <ItemCard key={i} id={safeStr(req.id)}>
              <div className="flex items-start justify-between gap-2">
                <div>
                  <span className="text-[10px] font-medium text-text-muted uppercase">
                    {safeStr(req.category)}
                  </span>
                  <h4 className="text-sm font-semibold text-text">{safeStr(req.title)}</h4>
                </div>
                <PriorityBadge priority={safeStr(req.priority)} />
              </div>
              <p className="text-sm text-text-secondary mt-1">{safeStr(req.description)}</p>
              {!!req.measurable_criteria && (
                <p className="text-xs text-text-muted mt-1">📏 {safeStr(req.measurable_criteria)}</p>
              )}
              <Timestamp time={safeStr(req.timestamp)} onClick={onTimestampClick} />
            </ItemCard>
          ))}
        </Section>
      )}

      {/* Бизнес-правила */}
      {businessRules.length > 0 && (
        <Section title="Бизнес-правила" icon="📜" count={businessRules.length}>
          {businessRules.map((br, i) => (
            <ItemCard key={i} id={safeStr(br.id)}>
              <p className="text-sm font-medium text-text">{safeStr(br.rule)}</p>
              <div className="grid grid-cols-2 gap-2 mt-2 text-xs text-text-secondary">
                {!!br.condition && <div>Условие: {safeStr(br.condition)}</div>}
                {!!br.action && <div>Действие: {safeStr(br.action)}</div>}
              </div>
              {safeArray<string>(br.exceptions).length > 0 && (
                <p className="text-xs text-text-muted mt-1">
                  Исключения: {safeArray<string>(br.exceptions).join(', ')}
                </p>
              )}
              <Timestamp time={safeStr(br.timestamp)} onClick={onTimestampClick} />
            </ItemCard>
          ))}
        </Section>
      )}

      {/* Интеграции */}
      {integrations.length > 0 && (
        <Section title="Интеграции" icon="🔗" count={integrations.length}>
          {integrations.map((intg, i) => (
            <ItemCard key={i} id={safeStr(intg.id)}>
              <div className="flex items-center gap-2 mb-1">
                <h4 className="text-sm font-semibold text-text">{safeStr(intg.system)}</h4>
                <span className="text-[10px] px-1.5 py-0.5 rounded bg-secondary/10 text-secondary font-medium">
                  {safeStr(intg.direction)}
                </span>
              </div>
              <p className="text-sm text-text-secondary">{safeStr(intg.data)}</p>
              {!!intg.frequency && <p className="text-xs text-text-muted mt-1">Частота: {safeStr(intg.frequency)}</p>}
              <Timestamp time={safeStr(intg.timestamp)} onClick={onTimestampClick} />
            </ItemCard>
          ))}
        </Section>
      )}

      {/* Ограничения */}
      {constraints.length > 0 && (
        <Section title="Ограничения" icon="🚫" count={constraints.length}>
          {constraints.map((c, i) => (
            <div key={i} className="flex items-start gap-2 py-1.5 text-sm">
              <span className="text-xs text-text-muted uppercase font-medium">
                [{safeStr(c.type)}]
              </span>
              <span className="text-text-secondary">{safeStr(c.description)}</span>
              <Timestamp time={safeStr(c.timestamp)} onClick={onTimestampClick} />
            </div>
          ))}
        </Section>
      )}

      {/* Описание процесса */}
      {processDesc && (!!processDesc.as_is || safeArray(processDesc.pain_points).length > 0) && (
        <Section title="Описание процесса" icon="🔄">
          {!!processDesc.as_is && (
            <div className="mb-3">
              <span className="text-xs font-bold text-text-muted">AS-IS:</span>
              <p className="text-sm text-text-secondary mt-1">{safeStr(processDesc.as_is)}</p>
            </div>
          )}
          {safeArray<string>(processDesc.pain_points).length > 0 && (
            <div className="mb-3">
              <span className="text-xs font-bold text-text-muted">Проблемы:</span>
              <ul className="mt-1 space-y-1">
                {safeArray<string>(processDesc.pain_points).map((p, i) => (
                  <li key={i} className="text-sm text-error/80 flex items-start gap-1.5">
                    <span>•</span>
                    {p}
                  </li>
                ))}
              </ul>
            </div>
          )}
        </Section>
      )}
    </div>
  );
}
