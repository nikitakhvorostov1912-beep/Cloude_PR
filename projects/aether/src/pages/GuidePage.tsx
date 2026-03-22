/**
 * Страница справки и руководства по Aether.
 * Секции: обзор, типы артефактов, лучшие практики, рабочий процесс, ссылки.
 */

import { useState } from 'react';
import { motion, AnimatePresence } from 'motion/react';
import { AnimatedPage } from '@/components/shared/AnimatedPage';
import { GlassCard } from '@/components/glass';
import {
  ARTIFACT_LABELS,
  ARTIFACT_ICONS,
  ARTIFACT_DESCRIPTIONS,
  type ArtifactType,
} from '@/types/artifact.types';

const ALL_TYPES: ArtifactType[] = [
  'protocol', 'requirements', 'risks', 'glossary', 'questions', 'transcript', 'development',
];

/** Раскрываемая карточка артефакта */
function ArtifactCard({ type }: { type: ArtifactType }) {
  const [expanded, setExpanded] = useState(false);
  const desc = ARTIFACT_DESCRIPTIONS[type];

  return (
    <GlassCard
      hoverable
      padding="md"
      className="cursor-pointer"
      onClick={() => setExpanded(!expanded)}
    >
      {/* Заголовок */}
      <div className="flex items-start justify-between">
        <div className="flex items-center gap-3">
          <span className="text-2xl">{ARTIFACT_ICONS[type]}</span>
          <div>
            <h3 className="font-semibold text-text">{ARTIFACT_LABELS[type]}</h3>
            <p className="text-xs text-text-secondary mt-0.5">{desc.summary}</p>
          </div>
        </div>
        <motion.svg
          width="16" height="16" viewBox="0 0 16 16" fill="none"
          className="text-text-muted mt-1 flex-shrink-0"
          animate={{ rotate: expanded ? 180 : 0 }}
          transition={{ duration: 0.2 }}
        >
          <path d="M4 6L8 10L12 6" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round" />
        </motion.svg>
      </div>

      {/* Развёрнутое содержимое */}
      <AnimatePresence>
        {expanded && (
          <motion.div
            initial={{ height: 0, opacity: 0 }}
            animate={{ height: 'auto', opacity: 1 }}
            exit={{ height: 0, opacity: 0 }}
            transition={{ duration: 0.25, ease: [0.4, 0, 0.2, 1] }}
            className="overflow-hidden"
          >
            <div className="mt-4 pt-4 border-t border-white/15 space-y-4">
              {/* Полное описание */}
              <p className="text-sm text-text-secondary leading-relaxed">
                {desc.fullDescription}
              </p>

              {/* Что извлекает */}
              <div>
                <h4 className="text-xs font-semibold text-text-muted uppercase tracking-wider mb-2">
                  Что извлекает из записи
                </h4>
                <ul className="space-y-1.5">
                  {desc.extracts.map((item, i) => (
                    <li key={i} className="flex items-start gap-2 text-sm text-text-secondary">
                      <span className="text-primary mt-0.5 flex-shrink-0">•</span>
                      {item}
                    </li>
                  ))}
                </ul>
              </div>

              {/* Структура результата */}
              <div>
                <h4 className="text-xs font-semibold text-text-muted uppercase tracking-wider mb-2">
                  Структура результата
                </h4>
                <div className="flex flex-wrap gap-1.5">
                  {desc.outputStructure.map((section) => (
                    <span
                      key={section}
                      className="text-[11px] px-2.5 py-1 rounded-lg bg-primary/10 text-primary font-mono"
                    >
                      {section}
                    </span>
                  ))}
                </div>
              </div>

              {/* Когда полезен + Качество */}
              <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
                <div className="rounded-xl bg-white/20 p-3">
                  <h4 className="text-[10px] font-semibold text-text-muted uppercase tracking-wider mb-1">
                    Когда полезен
                  </h4>
                  <p className="text-xs text-text-secondary leading-relaxed">{desc.bestFor}</p>
                </div>
                <div className="rounded-xl bg-white/20 p-3">
                  <h4 className="text-[10px] font-semibold text-text-muted uppercase tracking-wider mb-1">
                    Качество
                  </h4>
                  <p className="text-xs text-text-secondary leading-relaxed">{desc.qualityNote}</p>
                </div>
              </div>
            </div>
          </motion.div>
        )}
      </AnimatePresence>
    </GlassCard>
  );
}

/** Шаг рабочего процесса */
function WorkflowStep({ step, title, description, icon }: {
  step: number;
  title: string;
  description: string;
  icon: string;
}) {
  return (
    <motion.div
      className="flex items-start gap-4"
      initial={{ opacity: 0, x: -10 }}
      animate={{ opacity: 1, x: 0 }}
      transition={{ delay: step * 0.08 }}
    >
      <div className="flex-shrink-0 w-10 h-10 rounded-xl bg-primary/15 flex items-center justify-center">
        <span className="text-lg">{icon}</span>
      </div>
      <div className="flex-1 min-w-0">
        <div className="flex items-center gap-2 mb-0.5">
          <span className="text-[10px] font-bold text-primary bg-primary/10 rounded px-1.5 py-0.5">
            {step}
          </span>
          <h4 className="text-sm font-semibold text-text">{title}</h4>
        </div>
        <p className="text-xs text-text-secondary leading-relaxed">{description}</p>
      </div>
    </motion.div>
  );
}

/** Совет */
function TipCard({ icon, title, tips }: {
  icon: string;
  title: string;
  tips: string[];
}) {
  return (
    <GlassCard variant="subtle" padding="md">
      <div className="flex items-center gap-2 mb-3">
        <span className="text-lg">{icon}</span>
        <h3 className="text-sm font-semibold text-text">{title}</h3>
      </div>
      <ul className="space-y-1.5">
        {tips.map((tip, i) => (
          <li key={i} className="flex items-start gap-2 text-xs text-text-secondary">
            <span className="text-primary/60 mt-0.5 flex-shrink-0">•</span>
            {tip}
          </li>
        ))}
      </ul>
    </GlassCard>
  );
}

export function GuidePage() {
  return (
    <AnimatedPage>
      <div className="max-w-4xl mx-auto pb-8">
        {/* === Секция 1: Что такое Aether === */}
        <div className="mb-10">
          <h1 className="text-2xl font-bold text-text mb-2">Справка</h1>
          <GlassCard padding="lg">
            <div className="flex items-start gap-4">
              <div className="w-12 h-12 rounded-2xl bg-gradient-to-br from-primary to-primary-light flex items-center justify-center flex-shrink-0">
                <span className="text-white font-bold text-lg">AE</span>
              </div>
              <div>
                <h2 className="text-lg font-semibold text-text mb-2">
                  Aether — ваш AI-ассистент для обработки встреч
                </h2>
                <p className="text-sm text-text-secondary leading-relaxed">
                  Aether автоматически превращает аудио и видеозаписи встреч в 6 типов структурированных проектных
                  артефактов. Загрузите запись, выберите шаблон, запустите обработку — и через несколько минут
                  получите готовый протокол, требования, карту рисков, глоссарий, открытые вопросы и форматированную
                  стенограмму. Всё это без ручной расшифровки и структуризации.
                </p>
                <div className="flex flex-wrap gap-3 mt-4">
                  <div className="flex items-center gap-1.5 text-xs text-text-muted">
                    <span className="w-2 h-2 rounded-full bg-primary/50" />
                    OpenAI Whisper для транскрипции
                  </div>
                  <div className="flex items-center gap-1.5 text-xs text-text-muted">
                    <span className="w-2 h-2 rounded-full bg-secondary/50" />
                    Claude / GPT-4 для анализа
                  </div>
                  <div className="flex items-center gap-1.5 text-xs text-text-muted">
                    <span className="w-2 h-2 rounded-full bg-success/50" />
                    Экспорт в DOCX и ZIP
                  </div>
                </div>
              </div>
            </div>
          </GlassCard>
        </div>

        {/* === Секция 2: Типы артефактов === */}
        <div className="mb-10">
          <h2 className="text-lg font-semibold text-text mb-1">Типы артефактов</h2>
          <p className="text-sm text-text-secondary mb-4">
            Нажмите на карточку, чтобы увидеть подробное описание и структуру результата
          </p>
          <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
            {ALL_TYPES.map((type) => (
              <ArtifactCard key={type} type={type} />
            ))}
          </div>
        </div>

        {/* === Секция 3: Как получить лучший результат === */}
        <div className="mb-10">
          <h2 className="text-lg font-semibold text-text mb-1">Как получить лучший результат</h2>
          <p className="text-sm text-text-secondary mb-4">
            Советы для максимального качества артефактов
          </p>
          <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
            <TipCard
              icon="🎙️"
              title="Качество аудио"
              tips={[
                'Используйте внешний микрофон или гарнитуру',
                'Записывайте в WAV или высоком битрейте MP3 (192+ kbps)',
                'Минимизируйте фоновый шум, эхо и музыку',
                'Говорите чётко, не перебивайте друг друга',
                'При онлайн-встречах записывайте системный звук, а не микрофон',
              ]}
            />
            <TipCard
              icon="📋"
              title="Выбор шаблона"
              tips={[
                '«Полный пакет» — для обследований (все 6 артефактов)',
                '«Быстрый протокол» — для рабочих встреч и стендапов',
                '«Обследование» — для сбора требований (без стенограммы)',
                'Создайте свой шаблон с нужным набором артефактов',
              ]}
            />
            <TipCard
              icon="🤖"
              title="Выбор AI-провайдера"
              tips={[
                'Claude (Sonnet 4.6) — точнее для русскоязычных текстов',
                'GPT-4 — хорош для технической терминологии',
                'Оба провайдера используют одинаковые промпты',
                'Whisper (OpenAI) всегда используется для транскрипции',
              ]}
            />
            <TipCard
              icon="📝"
              title="Подготовка встречи"
              tips={[
                'В начале встречи представьтесь — AI определит спикеров',
                'Формулируйте решения явно: «Решили, что...»',
                'Подводите итоги в конце каждого блока',
                'Используйте терминологию, принятую в проекте',
                'Фиксируйте тип встречи (обследование, демо, приёмка)',
              ]}
            />
          </div>
        </div>

        {/* === Секция 4: Рабочий процесс === */}
        <div className="mb-10">
          <h2 className="text-lg font-semibold text-text mb-1">Рабочий процесс</h2>
          <p className="text-sm text-text-secondary mb-4">
            6 шагов от записи до готового документа
          </p>
          <GlassCard padding="lg">
            <div className="space-y-5">
              <WorkflowStep
                step={1}
                icon="📂"
                title="Создайте проект"
                description="Организуйте встречи по проектам. При серии встреч AI использует контекст предыдущих для связности артефактов."
              />
              <WorkflowStep
                step={2}
                icon="⬆️"
                title="Загрузите запись"
                description="Перетащите файл или выберите через диалог. Поддерживается 10+ форматов: MP3, WAV, M4A, MP4, MKV, WEBM, MOV, OGG, FLAC, AAC."
              />
              <WorkflowStep
                step={3}
                icon="🎯"
                title="Выберите шаблон"
                description="Используйте встроенный шаблон или создайте свой с нужным набором артефактов и кастомным промптом."
              />
              <WorkflowStep
                step={4}
                icon="⚡"
                title="Запустите обработку"
                description="Aether оценит стоимость, транскрибирует запись через Whisper и сгенерирует артефакты через Claude или GPT-4."
              />
              <WorkflowStep
                step={5}
                icon="👁️"
                title="Просмотрите артефакты"
                description="Каждый артефакт отображается с таймкодами. Кликните по таймкоду, чтобы перейти к нужному моменту в записи."
              />
              <WorkflowStep
                step={6}
                icon="📤"
                title="Экспортируйте результат"
                description="Сохраните артефакты в DOCX по шаблону или скачайте ZIP-архив со всеми документами для отправки заказчику."
              />
            </div>
          </GlassCard>
        </div>

        {/* === Секция 5: Кумулятивный контекст === */}
        <div className="mb-10">
          <h2 className="text-lg font-semibold text-text mb-1">Кумулятивный контекст</h2>
          <p className="text-sm text-text-secondary mb-4">
            Как Aether накапливает знания по серии встреч в рамках одного проекта
          </p>

          <GlassCard padding="lg" className="mb-4">
            <div className="flex items-start gap-3 mb-4">
              <div className="w-10 h-10 rounded-xl bg-secondary/15 flex items-center justify-center flex-shrink-0">
                <span className="text-lg">🔗</span>
              </div>
              <div>
                <h3 className="text-sm font-semibold text-text mb-1">Что это такое</h3>
                <p className="text-sm text-text-secondary leading-relaxed">
                  Когда вы обрабатываете несколько встреч в одном проекте, Aether автоматически передаёт результаты
                  предыдущих встреч в контекст AI. Это позволяет отслеживать эволюцию требований, закрывать ранее
                  открытые вопросы, замечать новые риски и пополнять глоссарий — без ручного сравнения документов.
                </p>
              </div>
            </div>

            <div className="border-t border-white/15 pt-4">
              <h4 className="text-xs font-semibold text-text-muted uppercase tracking-wider mb-3">
                Какие артефакты поддерживают накопление
              </h4>
              <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
                <div className="rounded-xl bg-white/20 p-3">
                  <div className="flex items-center gap-2 mb-2">
                    <span>📝</span>
                    <h5 className="text-xs font-semibold text-text">Требования</h5>
                  </div>
                  <div className="flex flex-wrap gap-1.5 mb-2">
                    <span className="text-[10px] px-2 py-0.5 rounded bg-success/10 text-success font-medium">Новое</span>
                    <span className="text-[10px] px-2 py-0.5 rounded bg-warning/10 text-warning font-medium">Изменено</span>
                    <span className="text-[10px] px-2 py-0.5 rounded bg-primary/10 text-primary font-medium">Подтверждено</span>
                    <span className="text-[10px] px-2 py-0.5 rounded bg-error/10 text-error font-medium">Противоречит</span>
                  </div>
                  <p className="text-[11px] text-text-muted leading-relaxed">
                    AI сравнивает новые требования с ранее собранными и отмечает статус каждого
                  </p>
                </div>

                <div className="rounded-xl bg-white/20 p-3">
                  <div className="flex items-center gap-2 mb-2">
                    <span>⚠️</span>
                    <h5 className="text-xs font-semibold text-text">Риски</h5>
                  </div>
                  <div className="flex flex-wrap gap-1.5 mb-2">
                    <span className="text-[10px] px-2 py-0.5 rounded bg-success/10 text-success font-medium">Новый</span>
                    <span className="text-[10px] px-2 py-0.5 rounded bg-error/10 text-error font-medium">Сохраняется</span>
                    <span className="text-[10px] px-2 py-0.5 rounded bg-success/10 text-success font-medium">Решён</span>
                    <span className="text-[10px] px-2 py-0.5 rounded bg-error/10 text-error font-medium">Эскалирован</span>
                  </div>
                  <p className="text-[11px] text-text-muted leading-relaxed">
                    Отслеживает эволюцию рисков: какие сняты, какие обострились
                  </p>
                </div>

                <div className="rounded-xl bg-white/20 p-3">
                  <div className="flex items-center gap-2 mb-2">
                    <span>📖</span>
                    <h5 className="text-xs font-semibold text-text">Глоссарий</h5>
                  </div>
                  <div className="flex flex-wrap gap-1.5 mb-2">
                    <span className="text-[10px] px-2 py-0.5 rounded bg-success/10 text-success font-medium">Новый</span>
                    <span className="text-[10px] px-2 py-0.5 rounded bg-warning/10 text-warning font-medium">Обновлён</span>
                    <span className="text-[10px] px-2 py-0.5 rounded bg-primary/10 text-primary font-medium">Подтверждён</span>
                  </div>
                  <p className="text-[11px] text-text-muted leading-relaxed">
                    Расширяет словарь новыми терминами, уточняет определения
                  </p>
                </div>

                <div className="rounded-xl bg-white/20 p-3">
                  <div className="flex items-center gap-2 mb-2">
                    <span>❓</span>
                    <h5 className="text-xs font-semibold text-text">Вопросы</h5>
                  </div>
                  <div className="flex flex-wrap gap-1.5 mb-2">
                    <span className="text-[10px] px-2 py-0.5 rounded bg-warning/10 text-warning font-medium">Открыт</span>
                    <span className="text-[10px] px-2 py-0.5 rounded bg-success/10 text-success font-medium">Решён</span>
                  </div>
                  <p className="text-[11px] text-text-muted leading-relaxed">
                    Закрывает решённые вопросы, выявляет новые информационные пробелы
                  </p>
                </div>
              </div>
            </div>

            <div className="border-t border-white/15 pt-4 mt-4">
              <h4 className="text-xs font-semibold text-text-muted uppercase tracking-wider mb-2">
                Как это работает
              </h4>
              <div className="space-y-2">
                <div className="flex items-start gap-3">
                  <span className="text-[10px] font-bold text-primary bg-primary/10 rounded px-1.5 py-0.5 mt-0.5">1</span>
                  <p className="text-xs text-text-secondary">Обработайте первую встречу в проекте — получите базовые артефакты</p>
                </div>
                <div className="flex items-start gap-3">
                  <span className="text-[10px] font-bold text-primary bg-primary/10 rounded px-1.5 py-0.5 mt-0.5">2</span>
                  <p className="text-xs text-text-secondary">Загрузите следующую встречу <strong className="text-text">в тот же проект</strong> — Aether автоматически подтянет результаты предыдущих</p>
                </div>
                <div className="flex items-start gap-3">
                  <span className="text-[10px] font-bold text-primary bg-primary/10 rounded px-1.5 py-0.5 mt-0.5">3</span>
                  <p className="text-xs text-text-secondary">AI сравнит новую информацию с прошлой и расставит статусы: что нового, что изменилось, что подтвердилось</p>
                </div>
              </div>
            </div>
          </GlassCard>

          <GlassCard variant="subtle" padding="sm">
            <div className="flex items-start gap-2">
              <span className="text-sm mt-0.5">💡</span>
              <p className="text-xs text-text-secondary leading-relaxed">
                <strong className="text-text">Совет:</strong> для максимальной пользы от кумулятивного контекста
                объединяйте все встречи по одному проекту в одну папку. Протокол генерируется для каждой встречи
                отдельно, а требования, риски, глоссарий и вопросы — накапливаются.
              </p>
            </div>
          </GlassCard>
        </div>

        {/* === Секция 6: Ссылки === */}
        <div>
          <h2 className="text-lg font-semibold text-text mb-4">Ссылки</h2>
          <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
            <GlassCard variant="subtle" padding="md" hoverable>
              <a
                href="https://github.com/nikitakhvorostov1912-beep/aether"
                target="_blank"
                rel="noopener noreferrer"
                className="flex items-center gap-3"
              >
                <div className="w-9 h-9 rounded-xl bg-text/10 flex items-center justify-center flex-shrink-0">
                  <svg width="18" height="18" viewBox="0 0 16 16" fill="currentColor" className="text-text">
                    <path d="M8 0C3.58 0 0 3.58 0 8c0 3.54 2.29 6.53 5.47 7.59.4.07.55-.17.55-.38 0-.19-.01-.82-.01-1.49-2.01.37-2.53-.49-2.69-.94-.09-.23-.48-.94-.82-1.13-.28-.15-.68-.52-.01-.53.63-.01 1.08.58 1.23.82.72 1.21 1.87.87 2.33.66.07-.52.28-.87.51-1.07-1.78-.2-3.64-.89-3.64-3.95 0-.87.31-1.59.82-2.15-.08-.2-.36-1.02.08-2.12 0 0 .67-.21 2.2.82.64-.18 1.32-.27 2-.27.68 0 1.36.09 2 .27 1.53-1.04 2.2-.82 2.2-.82.44 1.1.16 1.92.08 2.12.51.56.82 1.27.82 2.15 0 3.07-1.87 3.75-3.65 3.95.29.25.54.73.54 1.48 0 1.07-.01 1.93-.01 2.2 0 .21.15.46.55.38A8.013 8.013 0 0016 8c0-4.42-3.58-8-8-8z" />
                  </svg>
                </div>
                <div>
                  <p className="text-sm font-medium text-text">GitHub</p>
                  <p className="text-xs text-text-secondary">Исходный код и PRD</p>
                </div>
                <svg width="14" height="14" viewBox="0 0 14 14" fill="none" className="ml-auto text-text-muted">
                  <path d="M5 3H11V9M11 3L3 11" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round" />
                </svg>
              </a>
            </GlassCard>

            <GlassCard variant="subtle" padding="md">
              <div className="flex items-center gap-3">
                <div className="w-9 h-9 rounded-xl bg-primary/15 flex items-center justify-center flex-shrink-0">
                  <span className="text-primary font-bold text-xs">v0.1</span>
                </div>
                <div>
                  <p className="text-sm font-medium text-text">Aether v0.1.0</p>
                  <p className="text-xs text-text-secondary">
                    Tauri 2.x • React 19 • TypeScript • Tailwind 4
                  </p>
                </div>
              </div>
            </GlassCard>
          </div>
        </div>
      </div>
    </AnimatedPage>
  );
}
