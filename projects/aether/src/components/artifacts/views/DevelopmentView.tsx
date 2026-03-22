/**
 * Рендер артефакта «На разработку» — задачи с приоритетами, зависимостями и критериями приёмки.
 */

import { useState, useCallback, useRef, useMemo, memo } from 'react';
import { Section, Quote, PriorityBadge, safeArray, safeStr } from './shared';
import type { DevTask } from '@/types/artifact.types';

interface DevelopmentViewProps {
  data: Record<string, unknown>;
  onTimestampClick?: (seconds: number) => void;
}

/** Цветовая полоса слева по приоритету */
const PRIORITY_BORDER: Record<string, string> = {
  critical: 'border-error',
  high: 'border-warning',
  medium: 'border-primary/40',
  low: 'border-text-muted/20',
};

/** Статусы задач на русском */
const STATUS_CONFIG: Record<string, { bg: string; text: string; label: string }> = {
  ready: { bg: 'bg-success/10', text: 'text-success', label: 'Готова' },
  requires_clarification: { bg: 'bg-warning/10', text: 'text-warning', label: 'Требует уточнения' },
  deferred: { bg: 'bg-text-muted/10', text: 'text-text-muted', label: 'Отложена' },
};

/** Общий статус набора задач */
const OVERALL_STATUS_LABEL: Record<string, string> = {
  ready: 'Все задачи готовы',
  partial: 'Частично готовы',
  requires_clarification: 'Требуется уточнение',
};

function TaskStatusBadge({ status }: { status: string }) {
  const c = STATUS_CONFIG[status] || STATUS_CONFIG.ready;
  return (
    <span className={`inline-flex items-center text-[10px] font-medium px-1.5 py-0.5 rounded ${c.bg} ${c.text}`}>
      {c.label}
    </span>
  );
}

/** Карточка одной задачи */
function TaskCard({
  task,
  isExpanded,
  onToggle,
  onDependencyClick,
  onTimestampClick,
}: {
  task: DevTask;
  isExpanded: boolean;
  onToggle: () => void;
  onDependencyClick: (id: string) => void;
  onTimestampClick?: (seconds: number) => void;
}) {
  const borderColor = PRIORITY_BORDER[task.priority] || PRIORITY_BORDER.medium;
  const dependencies = safeArray<string>(task.dependencies);
  const actions = safeArray<Record<string, unknown>>(task.actions);
  const criteria = safeArray<string>(task.acceptance_criteria);
  const notes = safeArray<Record<string, unknown>>(task.meeting_notes);

  return (
    <div
      id={`task-${task.id}`}
      className={`glass-subtle rounded-2xl overflow-hidden border-l-4 ${borderColor} transition-all duration-200`}
    >
      {/* Свёрнутый заголовок */}
      <button
        onClick={onToggle}
        className="w-full text-left px-4 py-3 hover:bg-white/5 transition-colors"
      >
        <div className="flex items-center gap-3">
          {/* Стрелка раскрытия */}
          <svg
            width="12"
            height="12"
            viewBox="0 0 12 12"
            className={`text-text-muted flex-shrink-0 transition-transform duration-200 ${
              isExpanded ? 'rotate-90' : ''
            }`}
          >
            <path d="M4 2L8 6L4 10" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round" fill="none" />
          </svg>

          {/* ID */}
          <span className="font-mono text-xs font-bold text-primary/70 flex-shrink-0">
            {safeStr(task.id)}
          </span>

          {/* Заголовок */}
          <span className="text-sm font-medium text-text truncate flex-1">
            {safeStr(task.title)}
          </span>

          {/* Бейджи */}
          <div className="flex items-center gap-1.5 flex-shrink-0">
            <PriorityBadge priority={safeStr(task.priority)} />
            <span className="text-[10px] px-1.5 py-0.5 rounded bg-secondary/10 text-secondary font-medium">
              {safeStr(task.group)}
            </span>
            <TaskStatusBadge status={safeStr(task.status)} />
          </div>
        </div>

        {/* Зависимости (всегда видны) */}
        {dependencies.length > 0 && (
          <div className="flex items-center gap-1.5 mt-2 ml-7">
            {dependencies.map((dep) => (
              <span
                key={dep}
                onClick={(e) => {
                  e.stopPropagation();
                  onDependencyClick(dep);
                }}
                className="inline-flex items-center text-[10px] font-mono px-1.5 py-0.5 rounded bg-primary/10 text-primary cursor-pointer hover:bg-primary/20 transition-colors"
              >
                ↗ {dep}
              </span>
            ))}
          </div>
        )}
      </button>

      {/* Развёрнутое содержимое */}
      {isExpanded && (
        <div className="px-4 pb-4 space-y-4 border-t border-white/5">
          {/* Описание */}
          {safeStr(task.description) && (
            <div className="pt-3">
              <span className="text-xs font-bold text-text-muted uppercase tracking-wide">Описание</span>
              <p className="text-sm text-text-secondary mt-1">{safeStr(task.description)}</p>
            </div>
          )}

          {/* Действия (нумерованный список) */}
          {actions.length > 0 && (
            <div>
              <span className="text-xs font-bold text-text-muted uppercase tracking-wide">Действия</span>
              <ol className="mt-1.5 space-y-1.5">
                {actions.map((a, i) => (
                  <li key={i} className="flex items-start gap-2">
                    <span className="text-xs font-mono text-primary/60 mt-0.5 flex-shrink-0">
                      {safeStr(a.step) || i + 1}.
                    </span>
                    <div>
                      <p className="text-sm text-text">{safeStr(a.action)}</p>
                      {safeStr(a.detail) && (
                        <p className="text-xs text-text-muted mt-0.5">{safeStr(a.detail)}</p>
                      )}
                    </div>
                  </li>
                ))}
              </ol>
            </div>
          )}

          {/* Входные данные + Ожидаемый результат */}
          {(safeStr(task.input_data) || safeStr(task.expected_result)) && (
            <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
              {safeStr(task.input_data) && (
                <div className="glass rounded-xl p-3">
                  <span className="text-[10px] font-bold text-text-muted uppercase tracking-wide">Входные данные</span>
                  <p className="text-sm text-text-secondary mt-1">{safeStr(task.input_data)}</p>
                </div>
              )}
              {safeStr(task.expected_result) && (
                <div className="glass rounded-xl p-3">
                  <span className="text-[10px] font-bold text-text-muted uppercase tracking-wide">Ожидаемый результат</span>
                  <p className="text-sm text-text-secondary mt-1">{safeStr(task.expected_result)}</p>
                </div>
              )}
            </div>
          )}

          {/* Критерии приёмки */}
          {criteria.length > 0 && (
            <div>
              <span className="text-xs font-bold text-text-muted uppercase tracking-wide">Критерии приёмки</span>
              <ul className="mt-1.5 space-y-1">
                {criteria.map((c, i) => (
                  <li key={i} className="text-sm text-text-secondary flex items-start gap-2">
                    <span className="text-success mt-0.5 flex-shrink-0">✓</span>
                    {c}
                  </li>
                ))}
              </ul>
            </div>
          )}

          {/* Заметки со встречи (цитаты) */}
          {notes.length > 0 && (
            <div>
              <span className="text-xs font-bold text-text-muted uppercase tracking-wide">Из обсуждения</span>
              {notes.map((note, i) => (
                <Quote
                  key={i}
                  text={safeStr(note.quote)}
                  speaker={safeStr(note.speaker)}
                  timestamp={safeStr(note.timestamp)}
                  onTimestampClick={onTimestampClick}
                />
              ))}
            </div>
          )}
        </div>
      )}
    </div>
  );
}

export const DevelopmentView = memo(function DevelopmentView({ data, onTimestampClick }: DevelopmentViewProps) {
  const metadata = (data.metadata || {}) as Record<string, unknown>;
  const tasks = safeArray<Record<string, unknown>>(data.tasks).map((t) => t as unknown as DevTask);

  const [expandedTasks, setExpandedTasks] = useState<Set<string>>(new Set());
  const containerRef = useRef<HTMLDivElement>(null);

  // Метаданные
  const participants = safeArray<Record<string, unknown>>(metadata.participants);
  const systems = safeArray<string>(metadata.systems);
  const summary = safeStr(metadata.summary);
  const overallStatus = safeStr(metadata.overall_status, 'partial');

  // Статистика
  const stats = useMemo(() => {
    const total = tasks.length;
    const critical = tasks.filter((t) => t.priority === 'critical').length;
    const high = tasks.filter((t) => t.priority === 'high').length;
    const needsClarification = tasks.filter((t) => t.status === 'requires_clarification').length;
    return { total, critical, high, needsClarification };
  }, [tasks]);

  // Группировка задач по group
  const groupedTasks = useMemo(() => {
    const groups = new Map<string, DevTask[]>();
    for (const task of tasks) {
      const group = safeStr(task.group, 'Без группы');
      if (!groups.has(group)) groups.set(group, []);
      groups.get(group)!.push(task);
    }
    return groups;
  }, [tasks]);

  // Управление раскрытием
  const toggleTask = useCallback((id: string) => {
    setExpandedTasks((prev) => {
      const next = new Set(prev);
      if (next.has(id)) next.delete(id);
      else next.add(id);
      return next;
    });
  }, []);

  const expandAll = useCallback(() => {
    setExpandedTasks(new Set(tasks.map((t) => t.id)));
  }, [tasks]);

  const collapseAll = useCallback(() => {
    setExpandedTasks(new Set());
  }, []);

  // Клик по зависимости — прокрутка + раскрытие
  const handleDependencyClick = useCallback((depId: string) => {
    setExpandedTasks((prev) => {
      const next = new Set(prev);
      next.add(depId);
      return next;
    });

    requestAnimationFrame(() => {
      const el = document.getElementById(`task-${depId}`);
      if (el) {
        el.scrollIntoView({ behavior: 'smooth', block: 'center' });
        el.classList.add('ring-2', 'ring-primary/50');
        setTimeout(() => el.classList.remove('ring-2', 'ring-primary/50'), 2000);
      }
    });
  }, []);

  return (
    <div ref={containerRef} className="glass rounded-2xl p-6 space-y-6">
      {/* Шапка с метаданными */}
      <div className="space-y-3">
        {summary && (
          <p className="text-sm text-text-secondary">{summary}</p>
        )}
        <div className="flex flex-wrap items-center gap-3 text-xs text-text-muted">
          {participants.length > 0 && (
            <span>
              👥 {participants.map((p) => safeStr(p.name)).join(', ')}
            </span>
          )}
          {systems.length > 0 && (
            <span>
              🖥️ {systems.join(', ')}
            </span>
          )}
          {overallStatus && (
            <span className={`px-1.5 py-0.5 rounded font-medium ${
              overallStatus === 'ready' ? 'bg-success/10 text-success' :
              overallStatus === 'partial' ? 'bg-warning/10 text-warning' :
              'bg-error/10 text-error'
            }`}>
              {OVERALL_STATUS_LABEL[overallStatus] || overallStatus}
            </span>
          )}
        </div>
      </div>

      {/* Статистика — 4 карточки */}
      <div className="grid grid-cols-2 sm:grid-cols-4 gap-3">
        <div className="glass-subtle rounded-xl p-3 text-center">
          <p className="text-2xl font-bold text-text">{stats.total}</p>
          <p className="text-[10px] text-text-muted uppercase tracking-wide mt-0.5">Всего задач</p>
        </div>
        <div className="glass-subtle rounded-xl p-3 text-center">
          <p className="text-2xl font-bold text-error">{stats.critical}</p>
          <p className="text-[10px] text-text-muted uppercase tracking-wide mt-0.5">Критических</p>
        </div>
        <div className="glass-subtle rounded-xl p-3 text-center">
          <p className="text-2xl font-bold text-warning">{stats.high}</p>
          <p className="text-[10px] text-text-muted uppercase tracking-wide mt-0.5">Высоких</p>
        </div>
        <div className="glass-subtle rounded-xl p-3 text-center">
          <p className="text-2xl font-bold text-primary">{stats.needsClarification}</p>
          <p className="text-[10px] text-text-muted uppercase tracking-wide mt-0.5">Требуют уточнения</p>
        </div>
      </div>

      {/* Кнопки управления */}
      {tasks.length > 0 && (
        <div className="flex items-center gap-2">
          <button
            onClick={expandAll}
            className="text-xs text-primary hover:text-primary-light transition-colors px-2 py-1 rounded hover:bg-primary/5"
          >
            Развернуть все
          </button>
          <span className="text-text-muted/30">|</span>
          <button
            onClick={collapseAll}
            className="text-xs text-primary hover:text-primary-light transition-colors px-2 py-1 rounded hover:bg-primary/5"
          >
            Свернуть все
          </button>
        </div>
      )}

      {/* Задачи, сгруппированные по group */}
      {Array.from(groupedTasks.entries()).map(([group, groupTasks]) => (
        <Section key={group} title={group} icon="📦" count={groupTasks.length}>
          <div className="space-y-2">
            {groupTasks.map((task) => (
              <TaskCard
                key={task.id}
                task={task}
                isExpanded={expandedTasks.has(task.id)}
                onToggle={() => toggleTask(task.id)}
                onDependencyClick={handleDependencyClick}
                onTimestampClick={onTimestampClick}
              />
            ))}
          </div>
        </Section>
      ))}

      {/* Пустое состояние */}
      {tasks.length === 0 && (
        <div className="text-center py-8">
          <p className="text-sm text-text-muted">Задачи на разработку не найдены в стенограмме.</p>
        </div>
      )}
    </div>
  );
});
