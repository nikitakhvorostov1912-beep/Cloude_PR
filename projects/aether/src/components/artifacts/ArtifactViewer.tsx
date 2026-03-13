/**
 * Универсальный просмотрщик артефактов.
 * Рендерит данные в зависимости от типа артефакта.
 */

import type { ArtifactType } from '@/types/artifact.types';
import { ProtocolView } from './views/ProtocolView';
import { RequirementsView } from './views/RequirementsView';
import { RisksView } from './views/RisksView';
import { GlossaryView } from './views/GlossaryView';
import { QuestionsView } from './views/QuestionsView';
import { TranscriptView } from './views/TranscriptView';
import { RawTextView } from './views/RawTextView';

interface ArtifactViewerProps {
  type: ArtifactType;
  data: Record<string, unknown> | null;
  rawText?: string;
  isEmpty?: boolean;
  error?: string | null;
  onTimestampClick?: (seconds: number) => void;
}

export function ArtifactViewer({
  type,
  data,
  rawText,
  isEmpty,
  error,
  onTimestampClick,
}: ArtifactViewerProps) {
  // Ошибка генерации
  if (error && !data) {
    return (
      <div className="glass rounded-2xl p-6">
        <div className="flex items-start gap-3">
          <div className="w-8 h-8 rounded-full bg-error/10 flex items-center justify-center flex-shrink-0">
            <svg width="16" height="16" viewBox="0 0 16 16" fill="none">
              <path d="M4 4L12 12M4 12L12 4" stroke="currentColor" strokeWidth="2" strokeLinecap="round" className="text-error" />
            </svg>
          </div>
          <div>
            <h3 className="font-semibold text-error mb-1">Ошибка генерации</h3>
            <p className="text-sm text-text-secondary">{error}</p>
            {rawText && (
              <details className="mt-3">
                <summary className="text-xs text-text-muted cursor-pointer hover:text-text-secondary">
                  Показать сырой текст
                </summary>
                <RawTextView text={rawText} />
              </details>
            )}
          </div>
        </div>
      </div>
    );
  }

  // Пустой артефакт
  if (isEmpty || !data) {
    return (
      <div className="glass rounded-2xl p-8 text-center">
        <div className="w-12 h-12 mx-auto mb-3 rounded-full bg-warning/10 flex items-center justify-center">
          <span className="text-xl">○</span>
        </div>
        <h3 className="font-semibold text-text-secondary mb-1">Нет данных</h3>
        <p className="text-sm text-text-muted">
          На этой встрече не обсуждались темы, относящиеся к данному типу артефакта.
        </p>
      </div>
    );
  }

  // Рендер по типу
  const viewProps = { data, onTimestampClick };

  switch (type) {
    case 'protocol':
      return <ProtocolView {...viewProps} />;
    case 'requirements':
      return <RequirementsView {...viewProps} />;
    case 'risks':
      return <RisksView {...viewProps} />;
    case 'glossary':
      return <GlossaryView {...viewProps} />;
    case 'questions':
      return <QuestionsView {...viewProps} />;
    case 'transcript':
      return <TranscriptView {...viewProps} />;
    default:
      return <RawTextView text={JSON.stringify(data, null, 2)} />;
  }
}
