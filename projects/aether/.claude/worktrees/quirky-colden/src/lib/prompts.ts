/**
 * AI-промпты для извлечения артефактов из стенограмм.
 * Источник: docs/plans/stenograph-prompts.md
 */

import type { ArtifactType } from '@/types/artifact.types';

export interface PromptContext {
  meetingType: string;
  projectName: string;
  meetingDate: string;
  transcript: string;
  previousArtifacts?: Record<string, string>;
}

const SYSTEM_PROMPT = `Ты — опытный аналитик IT-проектов, специализирующийся на внедрении корпоративных систем (1С, ERP, CRM).
Ты анализируешь стенограммы рабочих встреч и извлекаешь структурированную информацию.

Правила:
- Извлекай ТОЛЬКО то, что явно сказано на встрече. Не додумывай.
- Если информация неоднозначна — отмечай как "требует уточнения".
- Сохраняй терминологию заказчика (как они называют вещи).
- Для каждого извлечённого элемента указывай таймкод источника.
- Ответ строго в JSON-формате, без markdown-обёрток.`;

const MEETING_TYPE_MODIFIERS: Record<string, string> = {
  'обследование': `Фокус: процессы AS-IS, боли, требования, терминология.
Повышенное внимание: глоссарий, business_rules, process_description.
Типичные паттерны: "сейчас мы делаем так...", "проблема в том, что...", "хотелось бы..."`,
  'рабочая': `Фокус: задачи, статусы, блокеры, решения.
Повышенное внимание: action_items, decisions, deadlines.
Типичные паттерны: "нужно сделать...", "готово на X%", "заблокировано из-за..."`,
  'демонстрация': `Фокус: замечания, доработки, приёмка.
Повышенное внимание: open_questions (замечания), decisions (принято/отклонено).
Типичные паттерны: "это не так работает", "добавьте ещё...", "это ОК, принято"`,
  'приёмка': `Фокус: формальная приёмка, перечень доработок, подтверждение.
Повышенное внимание: decisions (принято/на доработку), action_items (доработки).
Типичные паттерны: "этап принят с замечаниями", "доработать до...", "подтверждаю"`,
};

function buildSystemPrompt(meetingType: string): string {
  const modifier = MEETING_TYPE_MODIFIERS[meetingType];
  if (modifier) {
    return `${SYSTEM_PROMPT}\n\nТип встречи: ${meetingType}\n${modifier}`;
  }
  return SYSTEM_PROMPT;
}

const PROMPT_TEMPLATES: Record<ArtifactType, (ctx: PromptContext) => string> = {
  protocol: (ctx) => `Проанализируй стенограмму рабочей встречи и составь формальный протокол.

Тип встречи: ${ctx.meetingType}
Проект: ${ctx.projectName}
Дата: ${ctx.meetingDate}

Стенограмма:
${ctx.transcript}

Извлеки и верни JSON:
{
  "title": "Автоматически сгенерированное название встречи",
  "meeting_type": "${ctx.meetingType}",
  "date": "${ctx.meetingDate}",
  "duration_minutes": null,
  "participants": [{"name": "ФИО", "role": "должность", "organization": "компания", "first_mention_at": "MM:SS"}],
  "agenda": [{"topic": "Тема", "discussed_from": "MM:SS", "discussed_to": "MM:SS"}],
  "decisions": [{"id": "D-001", "description": "Что решили", "rationale": "Почему", "responsible": "Кто", "deadline": null, "timestamp": "MM:SS", "confidence": "high|medium|low"}],
  "action_items": [{"id": "AI-001", "description": "Что сделать", "responsible": "Кто", "deadline": null, "priority": "high|medium|low", "timestamp": "MM:SS"}],
  "key_statements": [{"speaker": "Кто", "quote": "Цитата", "context": "Контекст", "timestamp": "MM:SS", "importance": "high|medium"}],
  "next_steps": {"next_meeting_date": null, "next_meeting_topics": [], "homework": []}
}

Правила:
- decisions.confidence = "high" если решение чётко подтверждено, "low" если предварительно.
- Если участник не представился — используй "Участник 1", "Участник 2".
- key_statements — только важные высказывания, не более 10.
- Если deadline не назван — пиши null.`,

  requirements: (ctx) => `Проанализируй стенограмму встречи и извлеки функциональные и нефункциональные требования.

Тип встречи: ${ctx.meetingType}
Проект: ${ctx.projectName}

Стенограмма:
${ctx.transcript}
${ctx.previousArtifacts?.requirements ? `\nТребования из предыдущих встреч:\n${ctx.previousArtifacts.requirements}` : ''}

Извлеки и верни JSON:
{
  "functional_requirements": [{"id": "FR-001", "title": "Название", "description": "Описание", "user_story": "Как [роль]...", "acceptance_criteria": [], "priority": "must|should|could|wont", "source_quote": "Цитата", "timestamp": "MM:SS", "status": "new|changed|confirmed|contradicts", "notes": ""}],
  "non_functional_requirements": [{"id": "NFR-001", "category": "performance|security|usability|reliability|scalability|integration", "title": "Название", "description": "Описание", "measurable_criteria": "", "timestamp": "MM:SS", "priority": "must|should|could"}],
  "business_rules": [{"id": "BR-001", "rule": "Правило", "condition": "Условие", "action": "Действие", "exceptions": [], "timestamp": "MM:SS"}],
  "integrations": [{"id": "INT-001", "system": "Система", "direction": "inbound|outbound|bidirectional", "data": "Данные", "frequency": "", "timestamp": "MM:SS"}],
  "constraints": [{"type": "technical|business|regulatory|timeline", "description": "Описание", "timestamp": "MM:SS"}],
  "process_description": {"as_is": "", "pain_points": [], "to_be_hints": ""}
}

Правила:
- Приоритеты по MoSCoW.
- Если есть previous_requirements — сравни: confirmed/changed/contradicts.
- user_story только при явном пользовательском контексте.`,

  risks: (ctx) => `Проанализируй стенограмму встречи и выяви проектные риски, неопределённости и противоречия.

Проект: ${ctx.projectName}

Стенограмма:
${ctx.transcript}
${ctx.previousArtifacts?.risks ? `\nРанее выявленные риски:\n${ctx.previousArtifacts.risks}` : ''}

Извлеки и верни JSON:
{
  "risks": [{"id": "RISK-001", "category": "scope|technical|organizational|timeline|budget|integration|data", "title": "Название", "description": "Описание", "trigger": "Триггер", "impact": "high|medium|low", "probability": "high|medium|low", "mitigation_hint": "", "source_quote": "Цитата", "timestamp": "MM:SS", "status": "new|persists|resolved|escalated"}],
  "uncertainties": [{"id": "UNC-001", "topic": "Тема", "what_is_unknown": "Что неясно", "who_can_clarify": "", "impact_if_unresolved": "", "timestamp": "MM:SS"}],
  "contradictions": [{"id": "CONTR-001", "statement_a": {"speaker": "", "position": "", "timestamp": "MM:SS"}, "statement_b": {"speaker": "", "position": "", "timestamp": "MM:SS"}, "resolution": null, "severity": "high|medium|low"}],
  "assumptions": [{"id": "ASM-001", "assumption": "Предположение", "stated_by": "", "needs_validation": true, "timestamp": "MM:SS"}]
}

Правила:
- Ищи НЕЯВНЫЕ риски: "ну, это мы потом решим" → риск откладывания.
- Ищи противоречия между участниками.
- Ищи допущения без подтверждения.`,

  glossary: (ctx) => `Проанализируй стенограмму встречи и извлеки термины предметной области.

Проект: ${ctx.projectName}

Стенограмма:
${ctx.transcript}
${ctx.previousArtifacts?.glossary ? `\nСуществующий глоссарий:\n${ctx.previousArtifacts.glossary}` : ''}

Извлеки и верни JSON:
{
  "terms": [{"id": "TERM-001", "term": "Термин", "aliases": [], "definition": "Определение", "domain": "logistics|finance|hr|production|sales|it|other", "usage_example": "Пример", "related_terms": [], "first_mention": "MM:SS", "mentioned_by": "", "confidence": "high|medium|low", "status": "new|updated|confirmed"}],
  "abbreviations": [{"abbreviation": "ТМЦ", "full_form": "Расшифровка", "context": "Контекст", "timestamp": "MM:SS"}],
  "entity_mapping": [{"business_name": "Как называет заказчик", "system_name": "Как в системе", "notes": ""}]
}

Правила:
- Только СПЕЦИФИЧНЫЕ термины предметной области.
- entity_mapping — критично для 1С: заказчик говорит "накладная", в 1С это "Реализация товаров".
- confidence = "low" если термин использовался один раз без объяснения.`,

  questions: (ctx) => `Проанализируй стенограмму встречи и выяви все вопросы без ответа и темы для проработки.

Проект: ${ctx.projectName}

Стенограмма:
${ctx.transcript}
${ctx.previousArtifacts?.questions ? `\nРанее открытые вопросы:\n${ctx.previousArtifacts.questions}` : ''}

Извлеки и верни JSON:
{
  "open_questions": [{"id": "Q-001", "question": "Формулировка", "context": "Контекст", "asked_by": "", "directed_to": "", "category": "requirements|technical|organizational|process|data|access", "urgency": "blocking|important|nice_to_have", "related_requirement": null, "timestamp": "MM:SS", "status": "open|answered_partially|deferred"}],
  "deferred_topics": [{"id": "DEF-001", "topic": "Что отложили", "reason": "Почему", "deferred_to": "", "timestamp": "MM:SS"}],
  "information_gaps": [{"id": "GAP-001", "area": "Область", "what_is_needed": "Что нужно", "who_might_know": "", "impact": "На что влияет"}],
  "next_meeting_agenda_suggestions": []
}

Правила:
- urgency = "blocking" если без ответа нельзя продолжать.
- Ищи НЕЯВНЫЕ вопросы: "надо бы уточнить" → вопрос.
- deferred_topics: "давайте потом обсудим" → фиксируй.`,

  transcript: (ctx) => `Отформатируй сырую стенограмму в читаемый документ.

Сырая стенограмма с таймкодами:
${ctx.transcript}

Обработай и верни JSON:
{
  "formatted_transcript": [{"timestamp": "00:00:15", "speaker": "Иванов И.И.", "text": "Отформатированный текст", "topics": []}],
  "chapters": [{"title": "Название раздела", "start": "00:00:00", "end": "00:15:30", "summary": "Краткое содержание"}],
  "statistics": {"total_duration_minutes": 0, "speakers_count": 0, "speaker_time": {}, "topics_discussed": [], "dominant_speaker": ""}
}

Правила:
- Разбей на chapters по темам обсуждения.
- Исправь очевидные ошибки распознавания.
- НЕ меняй смысл — только форматирование.
- speaker_time — в процентах от общего времени.`,
};

export interface BuiltPrompt {
  system: string;
  user: string;
  artifactType: ArtifactType;
  temperature: number;
  maxTokens: number;
}

export function buildPrompt(
  artifactType: ArtifactType,
  context: PromptContext
): BuiltPrompt {
  const template = PROMPT_TEMPLATES[artifactType];
  return {
    system: buildSystemPrompt(context.meetingType),
    user: template(context),
    artifactType,
    temperature: artifactType === 'transcript' ? 0.3 : 0.1,
    maxTokens: 8192,
  };
}

export function buildAllPrompts(
  types: ArtifactType[],
  context: PromptContext
): BuiltPrompt[] {
  return types.map((type) => buildPrompt(type, context));
}
