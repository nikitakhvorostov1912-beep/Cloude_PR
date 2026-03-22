/**
 * Общие компоненты для рендеринга артефактов.
 */

import { type ReactNode } from 'react';

/** Кликабельный таймкод */
export function Timestamp({
  time,
  onClick,
}: {
  time: string;
  onClick?: (seconds: number) => void;
}) {
  if (!time) return null;

  const handleClick = () => {
    if (!onClick) return;
    const parts = time.split(':').map(Number);
    let seconds = 0;
    if (parts.length === 3) seconds = parts[0] * 3600 + parts[1] * 60 + parts[2];
    else if (parts.length === 2) seconds = parts[0] * 60 + parts[1];
    else seconds = parts[0];
    onClick(seconds);
  };

  return (
    <button
      onClick={handleClick}
      className={`inline-flex items-center font-mono text-xs px-1.5 py-0.5 rounded bg-primary/5 ${
        onClick ? 'text-primary hover:bg-primary/10 cursor-pointer' : 'text-primary/60'
      }`}
    >
      [{time}]
    </button>
  );
}

/** Бейдж приоритета */
export function PriorityBadge({ priority }: { priority: string }) {
  const config: Record<string, { bg: string; text: string; label: string }> = {
    must: { bg: 'bg-error/10', text: 'text-error', label: 'MUST' },
    high: { bg: 'bg-error/10', text: 'text-error', label: 'Высокий' },
    should: { bg: 'bg-warning/10', text: 'text-warning', label: 'SHOULD' },
    medium: { bg: 'bg-warning/10', text: 'text-warning', label: 'Средний' },
    could: { bg: 'bg-text-muted/10', text: 'text-text-muted', label: 'COULD' },
    low: { bg: 'bg-text-muted/10', text: 'text-text-muted', label: 'Низкий' },
    wont: { bg: 'bg-text-muted/5', text: 'text-text-muted', label: 'WONT' },
  };

  const c = config[priority?.toLowerCase()] || config.medium;

  return (
    <span className={`inline-flex items-center text-[10px] font-bold px-1.5 py-0.5 rounded ${c.bg} ${c.text}`}>
      {c.label}
    </span>
  );
}

/** Бейдж статуса */
export function StatusBadge({ status }: { status: string }) {
  const config: Record<string, { bg: string; text: string; label: string }> = {
    new: { bg: 'bg-success/10', text: 'text-success', label: 'Новое' },
    changed: { bg: 'bg-warning/10', text: 'text-warning', label: 'Изменено' },
    confirmed: { bg: 'bg-primary/10', text: 'text-primary', label: 'Подтверждено' },
    contradicts: { bg: 'bg-error/10', text: 'text-error', label: 'Противоречит' },
    open: { bg: 'bg-warning/10', text: 'text-warning', label: 'Открыт' },
    resolved: { bg: 'bg-success/10', text: 'text-success', label: 'Решён' },
    persists: { bg: 'bg-error/10', text: 'text-error', label: 'Сохраняется' },
    escalated: { bg: 'bg-error/10', text: 'text-error', label: 'Эскалирован' },
  };

  const c = config[status?.toLowerCase()] || { bg: 'bg-text-muted/10', text: 'text-text-muted', label: status };

  return (
    <span className={`inline-flex items-center text-[10px] font-medium px-1.5 py-0.5 rounded ${c.bg} ${c.text}`}>
      {c.label}
    </span>
  );
}

/** Секция с заголовком */
export function Section({ title, icon, children, count }: {
  title: string;
  icon?: string;
  children: ReactNode;
  count?: number;
}) {
  return (
    <div className="mb-6 last:mb-0">
      <div className="flex items-center gap-2 mb-3">
        {icon && <span className="text-base">{icon}</span>}
        <h3 className="text-sm font-bold text-text uppercase tracking-wide">{title}</h3>
        {count !== undefined && (
          <span className="text-xs text-text-muted bg-text-muted/10 px-1.5 py-0.5 rounded">
            {count}
          </span>
        )}
      </div>
      {children}
    </div>
  );
}

/** Карточка элемента списка */
export function ItemCard({ id, children }: { id?: string; children: ReactNode }) {
  return (
    <div className="glass-subtle rounded-xl p-4 mb-2 last:mb-0">
      {id && (
        <span className="inline-flex font-mono text-xs font-bold text-text-muted mb-1">
          {id}
        </span>
      )}
      {children}
    </div>
  );
}

/** Цитата */
export function Quote({ text, speaker, timestamp, onTimestampClick }: {
  text: string;
  speaker?: string;
  timestamp?: string;
  onTimestampClick?: (seconds: number) => void;
}) {
  return (
    <div className="border-l-3 border-secondary/40 pl-3 py-1 my-2">
      <p className="text-sm italic text-text-secondary">«{text}»</p>
      <div className="flex items-center gap-2 mt-1">
        {speaker && <span className="text-xs text-text-muted">— {speaker}</span>}
        {timestamp && <Timestamp time={timestamp} onClick={onTimestampClick} />}
      </div>
    </div>
  );
}

/** Безопасный доступ к массиву */
export function safeArray<T>(data: unknown): T[] {
  if (Array.isArray(data)) return data as T[];
  return [];
}

/** Безопасный доступ к строке */
export function safeStr(value: unknown, fallback = ''): string {
  if (typeof value === 'string') return value;
  if (value === null || value === undefined) return fallback;
  return String(value);
}

/** Безопасный доступ к числу */
export function safeNum(value: unknown, fallback = 0): number {
  if (typeof value === 'number') return value;
  return fallback;
}
