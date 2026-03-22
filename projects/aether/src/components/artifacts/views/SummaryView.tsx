/**
 * Сводная панель встречи — агрегирует данные из всех артефактов.
 * Используется как первый таб в ViewerPage.
 */

import { memo } from 'react';
import { GlassCard } from '@/components/glass';
import { Section, ItemCard, PriorityBadge, safeArray, safeStr, safeNum } from './shared';
import { ARTIFACT_ICONS, ARTIFACT_LABELS } from '@/types/artifact.types';
import type { ArtifactType, Artifact } from '@/types/artifact.types';
import type { Meeting } from '@/types/project.types';
import type { Project } from '@/types/project.types';

interface SummaryViewProps {
  artifacts: Artifact[];
  meeting: Meeting;
  project: Project | undefined;
  onNavigateToTab: (type: ArtifactType) => void;
}

export const SummaryView = memo(function SummaryView({ artifacts, meeting, project, onNavigateToTab }: SummaryViewProps) {
  const protocol = artifacts.find((a) => a.type === 'protocol');
  const risks = artifacts.find((a) => a.type === 'risks');
  const questions = artifacts.find((a) => a.type === 'questions');
  const transcript = artifacts.find((a) => a.type === 'transcript');
  const requirements = artifacts.find((a) => a.type === 'requirements');

  const participants = protocol ? safeArray<Record<string, unknown>>(protocol.data.participants) : [];
  const decisions = protocol ? safeArray<Record<string, unknown>>(protocol.data.decisions) : [];
  const actionItems = protocol ? safeArray<Record<string, unknown>>(protocol.data.action_items) : [];
  const allRisks = risks ? safeArray<Record<string, unknown>>(risks.data.risks) : [];
  const openQuestions = questions ? safeArray<Record<string, unknown>>(questions.data.open_questions) : [];
  const statistics = transcript?.data.statistics as Record<string, unknown> | undefined;

  // Топ-3 рисков по impact * probability
  const riskScoreMap: Record<string, number> = { high: 3, medium: 2, low: 1 };
  const topRisks = [...allRisks]
    .sort((a, b) => {
      const scoreA = (riskScoreMap[safeStr(a.impact, 'low')] || 1) * (riskScoreMap[safeStr(a.probability, 'low')] || 1);
      const scoreB = (riskScoreMap[safeStr(b.impact, 'low')] || 1) * (riskScoreMap[safeStr(b.probability, 'low')] || 1);
      return scoreB - scoreA;
    })
    .slice(0, 3);

  // Blocking вопросы
  const blockingQuestions = openQuestions.filter(
    (q) => safeStr(q.urgency, '').toLowerCase() === 'blocking'
  );

  // Стоимость обработки
  const totalTokens = artifacts.reduce((sum, a) => sum + a.tokensUsed, 0);
  const totalCost = artifacts.reduce((sum, a) => sum + a.costUsd, 0);

  const formatDuration = (seconds: number): string => {
    const h = Math.floor(seconds / 3600);
    const m = Math.floor((seconds % 3600) / 60);
    if (h > 0) return `${h}ч ${m}мин`;
    return `${m} мин`;
  };

  return (
    <div className="space-y-6">
      {/* Заголовок встречи */}
      <GlassCard padding="lg">
        <div className="flex items-start justify-between">
          <div>
            <h2 className="text-xl font-bold text-text">
              {meeting.title || 'Без названия'}
            </h2>
            <div className="flex items-center gap-3 mt-2 text-sm text-text-secondary">
              {project && <span>{project.name}</span>}
              <span>·</span>
              <span>{new Date(meeting.createdAt).toLocaleDateString('ru-RU', {
                day: 'numeric', month: 'long', year: 'numeric',
              })}</span>
              <span>·</span>
              <span>{formatDuration(meeting.durationSeconds)}</span>
            </div>
            {safeStr(protocol?.data.meeting_type as unknown) && (
              <span className="inline-flex items-center text-xs bg-primary/10 text-primary px-2 py-0.5 rounded mt-2">
                📌 {safeStr(protocol?.data.meeting_type as unknown)}
              </span>
            )}
          </div>
          <div className="text-right text-xs text-text-muted">
            <p>{artifacts.length} артефактов</p>
            {totalTokens > 0 && <p>{totalTokens.toLocaleString()} токенов</p>}
            {totalCost > 0 && <p>${totalCost.toFixed(4)}</p>}
          </div>
        </div>
      </GlassCard>

      {/* Участники + статистика */}
      {(participants.length > 0 || statistics) && (
        <GlassCard padding="md">
          <Section title="Участники" icon="👥" count={participants.length}>
            {participants.length > 0 ? (
              <div className="grid grid-cols-1 sm:grid-cols-2 gap-2">
                {participants.map((p, i) => (
                  <div key={i} className="flex items-center gap-2 glass-subtle rounded-lg px-3 py-2">
                    <div className="w-8 h-8 rounded-full bg-primary/10 flex items-center justify-center text-xs font-bold text-primary flex-shrink-0">
                      {safeStr(p.name, '?').charAt(0).toUpperCase()}
                    </div>
                    <div className="min-w-0">
                      <p className="text-sm font-medium text-text truncate">{safeStr(p.name)}</p>
                      <p className="text-xs text-text-muted truncate">
                        {safeStr(p.role)}{safeStr(p.organization) ? ` · ${safeStr(p.organization)}` : ''}
                      </p>
                    </div>
                  </div>
                ))}
              </div>
            ) : (
              <p className="text-sm text-text-muted">Нет данных об участниках</p>
            )}
            {statistics && (
              <div className="flex gap-4 mt-3 text-xs text-text-muted">
                {safeNum(statistics.total_duration_minutes as unknown) > 0 && (
                  <span>⏱ {safeNum(statistics.total_duration_minutes as unknown)} мин</span>
                )}
                {safeNum(statistics.total_speakers as unknown) > 0 && (
                  <span>🎤 {safeNum(statistics.total_speakers as unknown)} спикеров</span>
                )}
                {safeNum(statistics.total_segments as unknown) > 0 && (
                  <span>💬 {safeNum(statistics.total_segments as unknown)} сегментов</span>
                )}
              </div>
            )}
          </Section>
        </GlassCard>
      )}

      {/* Ключевые решения */}
      {decisions.length > 0 && (
        <GlassCard padding="md">
          <Section title="Ключевые решения" icon="✅" count={decisions.length}>
            <div className="space-y-2">
              {decisions.slice(0, 5).map((d, i) => (
                <ItemCard key={i}>
                  <p className="text-sm font-medium text-text">{safeStr(d.decision)}</p>
                  {safeStr(d.rationale) && (
                    <p className="text-xs text-text-secondary mt-1">{safeStr(d.rationale)}</p>
                  )}
                  <div className="flex items-center gap-2 mt-1">
                    {safeStr(d.confidence) && (
                      <span className={`text-[10px] px-1.5 py-0.5 rounded ${
                        safeStr(d.confidence) === 'high' ? 'bg-success/10 text-success' :
                        safeStr(d.confidence) === 'medium' ? 'bg-warning/10 text-warning' :
                        'bg-text-muted/10 text-text-muted'
                      }`}>
                        {safeStr(d.confidence) === 'high' ? 'Уверенно' :
                         safeStr(d.confidence) === 'medium' ? 'Предположительно' : 'Неточно'}
                      </span>
                    )}
                  </div>
                </ItemCard>
              ))}
              {decisions.length > 5 && (
                <button
                  onClick={() => onNavigateToTab('protocol')}
                  className="text-xs text-primary hover:text-primary-light transition-colors"
                >
                  Ещё {decisions.length - 5} решений →
                </button>
              )}
            </div>
          </Section>
        </GlassCard>
      )}

      {/* Задачи */}
      {actionItems.length > 0 && (
        <GlassCard padding="md">
          <Section title="Задачи" icon="📌" count={actionItems.length}>
            <div className="space-y-2">
              {actionItems.slice(0, 5).map((item, i) => (
                <ItemCard key={i}>
                  <div className="flex items-start justify-between gap-2">
                    <p className="text-sm text-text">{safeStr(item.task || item.action)}</p>
                    {safeStr(item.priority) && <PriorityBadge priority={safeStr(item.priority)} />}
                  </div>
                  <div className="flex items-center gap-2 mt-1 text-xs text-text-muted">
                    {safeStr(item.assignee || item.responsible) && (
                      <span>👤 {safeStr(item.assignee || item.responsible)}</span>
                    )}
                    {safeStr(item.deadline) && (
                      <span>📅 {safeStr(item.deadline)}</span>
                    )}
                  </div>
                </ItemCard>
              ))}
              {actionItems.length > 5 && (
                <button
                  onClick={() => onNavigateToTab('protocol')}
                  className="text-xs text-primary hover:text-primary-light transition-colors"
                >
                  Ещё {actionItems.length - 5} задач →
                </button>
              )}
            </div>
          </Section>
        </GlassCard>
      )}

      {/* Топ-3 рисков */}
      {topRisks.length > 0 && (
        <GlassCard padding="md">
          <Section title="Топ рисков" icon="⚠️" count={allRisks.length}>
            <div className="space-y-2">
              {topRisks.map((r, i) => (
                <ItemCard key={i}>
                  <p className="text-sm font-medium text-text">{safeStr(r.title || r.description)}</p>
                  {safeStr(r.mitigation) && (
                    <p className="text-xs text-text-secondary mt-1">
                      💡 {safeStr(r.mitigation)}
                    </p>
                  )}
                  <div className="flex items-center gap-2 mt-1">
                    <span className={`text-[10px] px-1.5 py-0.5 rounded ${
                      safeStr(r.impact) === 'high' ? 'bg-error/10 text-error' :
                      safeStr(r.impact) === 'medium' ? 'bg-warning/10 text-warning' :
                      'bg-text-muted/10 text-text-muted'
                    }`}>
                      Влияние: {safeStr(r.impact)}
                    </span>
                    <span className={`text-[10px] px-1.5 py-0.5 rounded ${
                      safeStr(r.probability) === 'high' ? 'bg-error/10 text-error' :
                      safeStr(r.probability) === 'medium' ? 'bg-warning/10 text-warning' :
                      'bg-text-muted/10 text-text-muted'
                    }`}>
                      Вероятность: {safeStr(r.probability)}
                    </span>
                  </div>
                </ItemCard>
              ))}
              {allRisks.length > 3 && (
                <button
                  onClick={() => onNavigateToTab('risks')}
                  className="text-xs text-primary hover:text-primary-light transition-colors"
                >
                  Все {allRisks.length} рисков →
                </button>
              )}
            </div>
          </Section>
        </GlassCard>
      )}

      {/* Блокирующие вопросы */}
      {blockingQuestions.length > 0 && (
        <GlassCard padding="md">
          <Section title="Блокирующие вопросы" icon="🚫" count={blockingQuestions.length}>
            <div className="space-y-2">
              {blockingQuestions.map((q, i) => (
                <ItemCard key={i}>
                  <p className="text-sm text-text">{safeStr(q.question)}</p>
                  <div className="flex items-center gap-2 mt-1 text-xs text-text-muted">
                    {safeStr(q.addressed_to) && <span>👤 {safeStr(q.addressed_to)}</span>}
                    {safeStr(q.category) && <span>📂 {safeStr(q.category)}</span>}
                  </div>
                </ItemCard>
              ))}
              {openQuestions.length > blockingQuestions.length && (
                <button
                  onClick={() => onNavigateToTab('questions')}
                  className="text-xs text-primary hover:text-primary-light transition-colors"
                >
                  Все {openQuestions.length} вопросов →
                </button>
              )}
            </div>
          </Section>
        </GlassCard>
      )}

      {/* Навигация по артефактам */}
      <GlassCard padding="md">
        <Section title="Артефакты" icon="📂">
          <div className="grid grid-cols-2 sm:grid-cols-3 gap-2">
            {artifacts.map((artifact) => (
              <button
                key={artifact.id}
                onClick={() => onNavigateToTab(artifact.type)}
                className="glass-subtle rounded-xl p-3 text-left hover:bg-white/50 transition-colors group"
              >
                <div className="flex items-center gap-2">
                  <span className="text-lg">{ARTIFACT_ICONS[artifact.type]}</span>
                  <div className="min-w-0">
                    <p className="text-sm font-medium text-text truncate">
                      {ARTIFACT_LABELS[artifact.type]}
                    </p>
                    <p className="text-[10px] text-text-muted">
                      v{artifact.version} · {artifact.llmModel}
                    </p>
                  </div>
                </div>
              </button>
            ))}
          </div>
        </Section>
      </GlassCard>

      {/* Пустое состояние — нет данных для сводки */}
      {!protocol && !risks && !questions && !transcript && !requirements && (
        <GlassCard padding="lg">
          <div className="text-center py-6">
            <p className="text-text-muted text-sm">
              Недостаточно данных для сводки. Обработайте запись, чтобы увидеть агрегированный обзор.
            </p>
          </div>
        </GlassCard>
      )}
    </div>
  );
});
