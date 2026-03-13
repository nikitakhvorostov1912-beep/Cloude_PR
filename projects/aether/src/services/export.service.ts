/**
 * Сервис экспорта артефактов в DOCX и ZIP.
 * 6 шаблонов по спецификациям stenograph-docx-templates.md.
 */

import {
  Document,
  Packer,
  Paragraph,
  TextRun,
  AlignmentType,
  HeadingLevel,
  Footer,
  PageNumber,
} from 'docx';
import { saveAs } from 'file-saver';
import JSZip from 'jszip';
import type { Artifact, ArtifactType } from '@/types/artifact.types';

// === Стили ===

const COLORS = {
  primary: '6C5CE7',
  secondary: '00CEC9',
  success: '00B894',
  warning: 'FDCB6E',
  error: 'E17055',
  text: '2D3436',
  textSecondary: '636E72',
  textMuted: 'B2BEC3',
  timestamp: '0984E3',
  border: 'DFE6E9',
};

const FONT = { name: 'Arial', size: 22 }; // 11pt = 22 half-points
const FONT_SMALL = { name: 'Arial', size: 18 }; // 9pt
const FONT_MONO = { name: 'Courier New', size: 18 };
const FONT_TITLE = { name: 'Arial', size: 36, bold: true }; // 18pt

function heading(text: string, level: typeof HeadingLevel[keyof typeof HeadingLevel] = HeadingLevel.HEADING_1): Paragraph {
  return new Paragraph({ heading: level, children: [new TextRun({ text, font: 'Arial', bold: true, color: COLORS.text })] });
}

function text(t: string, opts: Partial<{ bold: boolean; italic: boolean; color: string; font: typeof FONT; size: number }> = {}): TextRun {
  return new TextRun({
    text: t,
    font: opts.font?.name || FONT.name,
    size: opts.size || FONT.size,
    bold: opts.bold,
    italics: opts.italic,
    color: opts.color || COLORS.text,
  });
}

function timestamp(time: string): TextRun {
  return new TextRun({
    text: `[${time}]`,
    font: FONT_MONO.name,
    size: FONT_MONO.size,
    color: COLORS.timestamp,
  });
}

function priorityRun(priority: string): TextRun {
  const colorMap: Record<string, string> = {
    must: COLORS.error, high: COLORS.error,
    should: COLORS.warning, medium: COLORS.warning,
    could: COLORS.textMuted, low: COLORS.textMuted,
  };
  return new TextRun({
    text: ` [${priority.toUpperCase()}]`,
    font: FONT.name,
    size: FONT_SMALL.size,
    bold: true,
    color: colorMap[priority.toLowerCase()] || COLORS.textSecondary,
  });
}

function separator(): Paragraph {
  return new Paragraph({
    children: [new TextRun({ text: '─'.repeat(60), color: COLORS.border, font: FONT.name, size: FONT_SMALL.size })],
    spacing: { before: 100, after: 100 },
  });
}

function emptyParagraph(): Paragraph {
  return new Paragraph({ children: [] });
}

// === Утилиты ===

function safeArray<T>(val: unknown): T[] {
  return Array.isArray(val) ? val as T[] : [];
}

function safeStr(val: unknown, fallback = ''): string {
  return typeof val === 'string' ? val : fallback;
}

// === Генерация шапки ===

function createHeader(
  docType: string,
  projectName: string,
  meetingTitle: string,
  date: string,
): Paragraph[] {
  return [
    new Paragraph({
      children: [new TextRun({ ...FONT_TITLE, text: 'AETHER', color: COLORS.primary })],
      alignment: AlignmentType.LEFT,
    }),
    emptyParagraph(),
    new Paragraph({
      children: [new TextRun({ text: docType.toUpperCase(), ...FONT_TITLE, color: COLORS.text })],
    }),
    emptyParagraph(),
    new Paragraph({ children: [text(`Проект: ${projectName}`, { bold: true })] }),
    meetingTitle ? new Paragraph({ children: [text(`Встреча: ${meetingTitle}`)] }) : emptyParagraph(),
    new Paragraph({ children: [text(`Дата: ${date}`)] }),
    new Paragraph({
      children: [text('Сгенерировано: Aether', { color: COLORS.textMuted, size: FONT_SMALL.size })],
    }),
    separator(),
  ];
}

function createFooter(projectName: string): Footer {
  return new Footer({
    children: [
      new Paragraph({
        alignment: AlignmentType.CENTER,
        children: [
          text(`Aether · ${projectName} · `, { color: COLORS.textMuted, size: FONT_SMALL.size }),
          new TextRun({
            children: ['Стр. ', PageNumber.CURRENT, ' из ', PageNumber.TOTAL_PAGES],
            font: FONT_SMALL.name,
            size: FONT_SMALL.size,
            color: COLORS.textMuted,
          }),
        ],
      }),
    ],
  });
}

// === Генераторы по типам ===

function generateProtocolContent(data: Record<string, unknown>): Paragraph[] {
  const paragraphs: Paragraph[] = [];

  // Участники
  const participants = safeArray<Record<string, unknown>>(data.participants);
  if (participants.length > 0) {
    paragraphs.push(heading('1. Участники', HeadingLevel.HEADING_2));
    participants.forEach((p, i) => {
      paragraphs.push(new Paragraph({
        children: [
          text(`${i + 1}. `, { bold: true }),
          text(safeStr(p.name), { bold: true }),
          text(` — ${safeStr(p.role)}`, { color: COLORS.textSecondary }),
          p.organization ? text(` (${safeStr(p.organization)})`, { color: COLORS.textMuted }) : text(''),
        ],
      }));
    });
    paragraphs.push(separator());
  }

  // Повестка
  const agenda = safeArray<Record<string, unknown>>(data.agenda);
  if (agenda.length > 0) {
    paragraphs.push(heading('2. Повестка', HeadingLevel.HEADING_2));
    agenda.forEach((item, i) => {
      paragraphs.push(new Paragraph({
        children: [
          text(`${i + 1}. ${safeStr(item.topic)}`),
          text(`  ${safeStr(item.discussed_from)}–${safeStr(item.discussed_to)}`, { color: COLORS.timestamp, font: FONT_MONO }),
        ],
      }));
    });
    paragraphs.push(separator());
  }

  // Решения
  const decisions = safeArray<Record<string, unknown>>(data.decisions);
  if (decisions.length > 0) {
    paragraphs.push(heading('3. Принятые решения', HeadingLevel.HEADING_2));
    decisions.forEach((d) => {
      paragraphs.push(new Paragraph({
        children: [
          text(safeStr(d.id), { bold: true, color: COLORS.textMuted }),
          text(`  ${safeStr(d.description)}`, { bold: true }),
          d.timestamp ? timestamp(safeStr(d.timestamp)) : text(''),
        ],
        spacing: { before: 80 },
      }));
      if (d.responsible) {
        paragraphs.push(new Paragraph({
          children: [text(`     Ответственный: ${safeStr(d.responsible)}`, { color: COLORS.textSecondary })],
        }));
      }
      if (d.deadline) {
        paragraphs.push(new Paragraph({
          children: [text(`     Срок: ${safeStr(d.deadline)}`, { color: COLORS.textSecondary })],
        }));
      }
    });
    paragraphs.push(separator());
  }

  // Задачи
  const actionItems = safeArray<Record<string, unknown>>(data.action_items);
  if (actionItems.length > 0) {
    paragraphs.push(heading('4. Задачи (Action Items)', HeadingLevel.HEADING_2));
    actionItems.forEach((ai) => {
      paragraphs.push(new Paragraph({
        children: [
          text(safeStr(ai.id), { bold: true, color: COLORS.textMuted }),
          text(`  ${safeStr(ai.description)}`),
          priorityRun(safeStr(ai.priority, 'medium')),
        ],
        spacing: { before: 60 },
      }));
      const meta: string[] = [];
      if (ai.responsible) meta.push(`Ответственный: ${safeStr(ai.responsible)}`);
      if (ai.deadline) meta.push(`Срок: ${safeStr(ai.deadline)}`);
      if (meta.length > 0) {
        paragraphs.push(new Paragraph({
          children: [text(`     ${meta.join(' · ')}`, { color: COLORS.textSecondary, size: FONT_SMALL.size })],
        }));
      }
    });
    paragraphs.push(separator());
  }

  // Ключевые высказывания
  const keyStatements = safeArray<Record<string, unknown>>(data.key_statements);
  if (keyStatements.length > 0) {
    paragraphs.push(heading('5. Ключевые высказывания', HeadingLevel.HEADING_2));
    keyStatements.forEach((ks) => {
      paragraphs.push(new Paragraph({
        children: [
          text(`«${safeStr(ks.quote)}»`, { italic: true, color: COLORS.textSecondary }),
        ],
        indent: { left: 360 },
        spacing: { before: 60 },
      }));
      paragraphs.push(new Paragraph({
        children: [
          text(`— ${safeStr(ks.speaker)}`, { color: COLORS.textMuted, size: FONT_SMALL.size }),
          ks.timestamp ? new TextRun({ text: ' ', size: FONT_SMALL.size }) : text(''),
          ks.timestamp ? timestamp(safeStr(ks.timestamp)) : text(''),
        ],
        indent: { left: 360 },
      }));
    });
  }

  return paragraphs;
}

function generateRequirementsContent(data: Record<string, unknown>): Paragraph[] {
  const paragraphs: Paragraph[] = [];

  const funcReqs = safeArray<Record<string, unknown>>(data.functional_requirements);
  if (funcReqs.length > 0) {
    paragraphs.push(heading('1. Функциональные требования', HeadingLevel.HEADING_2));
    funcReqs.forEach((req) => {
      paragraphs.push(new Paragraph({
        children: [
          text(safeStr(req.id), { bold: true, color: COLORS.textMuted }),
          text(`  ${safeStr(req.title)}`, { bold: true }),
          priorityRun(safeStr(req.priority, 'should')),
        ],
        spacing: { before: 100 },
      }));
      paragraphs.push(new Paragraph({
        children: [text(safeStr(req.description), { color: COLORS.textSecondary })],
        indent: { left: 360 },
      }));
      if (req.user_story) {
        paragraphs.push(new Paragraph({
          children: [text(safeStr(req.user_story), { italic: true, color: COLORS.primary })],
          indent: { left: 360 },
        }));
      }
      const criteria = safeArray<string>(req.acceptance_criteria);
      criteria.forEach((c) => {
        paragraphs.push(new Paragraph({
          children: [text(`✓ ${c}`, { color: COLORS.success, size: FONT_SMALL.size })],
          indent: { left: 720 },
        }));
      });
      if (req.timestamp) {
        paragraphs.push(new Paragraph({
          children: [text('Источник: ', { color: COLORS.textMuted, size: FONT_SMALL.size }), timestamp(safeStr(req.timestamp))],
          indent: { left: 360 },
        }));
      }
    });
    paragraphs.push(separator());
  }

  const nfReqs = safeArray<Record<string, unknown>>(data.non_functional_requirements);
  if (nfReqs.length > 0) {
    paragraphs.push(heading('2. Нефункциональные требования', HeadingLevel.HEADING_2));
    nfReqs.forEach((req) => {
      paragraphs.push(new Paragraph({
        children: [
          text(safeStr(req.id), { bold: true, color: COLORS.textMuted }),
          text(`  [${safeStr(req.category).toUpperCase()}] `, { color: COLORS.textSecondary, size: FONT_SMALL.size }),
          text(safeStr(req.title), { bold: true }),
          priorityRun(safeStr(req.priority, 'should')),
        ],
        spacing: { before: 80 },
      }));
      paragraphs.push(new Paragraph({
        children: [text(safeStr(req.description), { color: COLORS.textSecondary })],
        indent: { left: 360 },
      }));
    });
    paragraphs.push(separator());
  }

  const businessRules = safeArray<Record<string, unknown>>(data.business_rules);
  if (businessRules.length > 0) {
    paragraphs.push(heading('3. Бизнес-правила', HeadingLevel.HEADING_2));
    businessRules.forEach((br) => {
      paragraphs.push(new Paragraph({
        children: [text(safeStr(br.id), { bold: true, color: COLORS.textMuted }), text(`  ${safeStr(br.rule)}`)],
        spacing: { before: 80 },
      }));
    });
    paragraphs.push(separator());
  }

  const integrations = safeArray<Record<string, unknown>>(data.integrations);
  if (integrations.length > 0) {
    paragraphs.push(heading('4. Интеграции', HeadingLevel.HEADING_2));
    integrations.forEach((intg) => {
      paragraphs.push(new Paragraph({
        children: [
          text(safeStr(intg.id), { bold: true, color: COLORS.textMuted }),
          text(`  ${safeStr(intg.system)} (${safeStr(intg.direction)})`, { bold: true }),
        ],
        spacing: { before: 80 },
      }));
      paragraphs.push(new Paragraph({
        children: [text(safeStr(intg.data), { color: COLORS.textSecondary })],
        indent: { left: 360 },
      }));
    });
  }

  return paragraphs;
}

function generateRisksContent(data: Record<string, unknown>): Paragraph[] {
  const paragraphs: Paragraph[] = [];
  const risks = safeArray<Record<string, unknown>>(data.risks);

  if (risks.length > 0) {
    paragraphs.push(heading('Детализация рисков', HeadingLevel.HEADING_2));
    risks.forEach((risk) => {
      paragraphs.push(new Paragraph({
        children: [
          text(safeStr(risk.id), { bold: true, color: COLORS.textMuted }),
          text(`  ${safeStr(risk.title)}`, { bold: true }),
          priorityRun(safeStr(risk.impact, 'medium')),
        ],
        spacing: { before: 100 },
      }));
      paragraphs.push(new Paragraph({
        children: [text(`Категория: ${safeStr(risk.category)}`, { color: COLORS.textSecondary, size: FONT_SMALL.size })],
        indent: { left: 360 },
      }));
      paragraphs.push(new Paragraph({
        children: [text(safeStr(risk.description), { color: COLORS.textSecondary })],
        indent: { left: 360 },
      }));
      if (risk.mitigation_hint) {
        paragraphs.push(new Paragraph({
          children: [text(`Смягчение: ${safeStr(risk.mitigation_hint)}`, { color: COLORS.success })],
          indent: { left: 360 },
        }));
      }
    });
    paragraphs.push(separator());
  }

  const contradictions = safeArray<Record<string, unknown>>(data.contradictions);
  if (contradictions.length > 0) {
    paragraphs.push(heading('Противоречия', HeadingLevel.HEADING_2));
    contradictions.forEach((c) => {
      const a = c.statement_a as Record<string, unknown> | undefined;
      const b = c.statement_b as Record<string, unknown> | undefined;
      paragraphs.push(new Paragraph({
        children: [text(safeStr(c.id), { bold: true, color: COLORS.textMuted }), priorityRun(safeStr(c.severity, 'medium'))],
        spacing: { before: 80 },
      }));
      if (a) {
        paragraphs.push(new Paragraph({
          children: [text(`Позиция А: ${safeStr(a.speaker)} — ${safeStr(a.position)}`, { color: COLORS.textSecondary })],
          indent: { left: 360 },
        }));
      }
      if (b) {
        paragraphs.push(new Paragraph({
          children: [text(`Позиция Б: ${safeStr(b.speaker)} — ${safeStr(b.position)}`, { color: COLORS.textSecondary })],
          indent: { left: 360 },
        }));
      }
    });
  }

  return paragraphs;
}

function generateGlossaryContent(data: Record<string, unknown>): Paragraph[] {
  const paragraphs: Paragraph[] = [];
  const terms = safeArray<Record<string, unknown>>(data.terms);

  if (terms.length > 0) {
    paragraphs.push(heading('Термины предметной области', HeadingLevel.HEADING_2));
    terms.forEach((term) => {
      paragraphs.push(new Paragraph({
        children: [
          text(safeStr(term.term).toUpperCase(), { bold: true }),
          text(`  [${safeStr(term.domain)}]`, { color: COLORS.secondary, size: FONT_SMALL.size }),
        ],
        spacing: { before: 100 },
      }));
      paragraphs.push(new Paragraph({
        children: [text(`Определение: ${safeStr(term.definition)}`, { color: COLORS.textSecondary })],
        indent: { left: 360 },
      }));
      const aliases = safeArray<string>(term.aliases);
      if (aliases.length > 0) {
        paragraphs.push(new Paragraph({
          children: [text(`Синонимы: ${aliases.join(', ')}`, { color: COLORS.textMuted, size: FONT_SMALL.size })],
          indent: { left: 360 },
        }));
      }
      if (term.usage_example) {
        paragraphs.push(new Paragraph({
          children: [text(`Пример: «${safeStr(term.usage_example)}»`, { italic: true, color: COLORS.textMuted, size: FONT_SMALL.size })],
          indent: { left: 360 },
        }));
      }
    });
    paragraphs.push(separator());
  }

  const entityMapping = safeArray<Record<string, unknown>>(data.entity_mapping);
  if (entityMapping.length > 0) {
    paragraphs.push(heading('Маппинг терминов', HeadingLevel.HEADING_2));
    entityMapping.forEach((em) => {
      paragraphs.push(new Paragraph({
        children: [
          text(`«${safeStr(em.business_name)}»`, { bold: true }),
          text(' → ', { color: COLORS.textMuted }),
          text(safeStr(em.system_name), { bold: true, color: COLORS.primary }),
          em.notes ? text(`  (${safeStr(em.notes)})`, { color: COLORS.textMuted, size: FONT_SMALL.size }) : text(''),
        ],
        spacing: { before: 40 },
      }));
    });
  }

  return paragraphs;
}

function generateQuestionsContent(data: Record<string, unknown>): Paragraph[] {
  const paragraphs: Paragraph[] = [];
  const questions = safeArray<Record<string, unknown>>(data.open_questions);

  const urgencyLabels: Record<string, string> = {
    blocking: '🔴 БЛОКИРУЮЩИЕ',
    important: '🟡 ВАЖНЫЕ',
    nice_to_have: '🟢 ЖЕЛАТЕЛЬНЫЕ',
  };

  const grouped = new Map<string, Record<string, unknown>[]>();
  questions.forEach((q) => {
    const urgency = safeStr(q.urgency, 'important');
    if (!grouped.has(urgency)) grouped.set(urgency, []);
    grouped.get(urgency)!.push(q);
  });

  for (const [urgency, items] of grouped.entries()) {
    paragraphs.push(heading(urgencyLabels[urgency] || urgency, HeadingLevel.HEADING_2));
    items.forEach((q) => {
      paragraphs.push(new Paragraph({
        children: [
          text(safeStr(q.id), { bold: true, color: COLORS.textMuted }),
          text(`  ${safeStr(q.question)}`, { bold: true }),
        ],
        spacing: { before: 80 },
      }));
      if (q.context) {
        paragraphs.push(new Paragraph({
          children: [text(`Контекст: ${safeStr(q.context)}`, { color: COLORS.textSecondary, size: FONT_SMALL.size })],
          indent: { left: 360 },
        }));
      }
      if (q.directed_to) {
        paragraphs.push(new Paragraph({
          children: [text(`Адресовано: ${safeStr(q.directed_to)}`, { color: COLORS.textMuted, size: FONT_SMALL.size })],
          indent: { left: 360 },
        }));
      }
    });
    paragraphs.push(separator());
  }

  const agendaSuggestions = safeArray<string>(data.next_meeting_agenda_suggestions);
  if (agendaSuggestions.length > 0) {
    paragraphs.push(heading('Рекомендуемая повестка следующей встречи', HeadingLevel.HEADING_2));
    agendaSuggestions.forEach((s, i) => {
      paragraphs.push(new Paragraph({
        children: [text(`${i + 1}. ${s}`)],
      }));
    });
  }

  return paragraphs;
}

function generateTranscriptContent(data: Record<string, unknown>): Paragraph[] {
  const paragraphs: Paragraph[] = [];
  const entries = safeArray<Record<string, unknown>>(data.formatted_transcript);
  const chapters = safeArray<Record<string, unknown>>(data.chapters);

  // Содержание
  if (chapters.length > 0) {
    paragraphs.push(heading('Содержание', HeadingLevel.HEADING_2));
    chapters.forEach((ch, i) => {
      paragraphs.push(new Paragraph({
        children: [
          text(`${i + 1}. ${safeStr(ch.title)}`),
          text(`  ${safeStr(ch.start)}`, { color: COLORS.timestamp, font: FONT_MONO }),
        ],
      }));
    });
    paragraphs.push(separator());
  }

  // Стенограмма
  paragraphs.push(heading('Стенограмма', HeadingLevel.HEADING_2));
  let lastSpeaker = '';

  entries.forEach((entry) => {
    const speaker = safeStr(entry.speaker, 'Участник');
    const isSameSpeaker = speaker === lastSpeaker;
    lastSpeaker = speaker;

    if (!isSameSpeaker) {
      paragraphs.push(emptyParagraph());
      paragraphs.push(new Paragraph({
        children: [
          timestamp(safeStr(entry.timestamp)),
          text(` ${speaker}:`, { bold: true, color: COLORS.primary }),
        ],
        spacing: { before: 80 },
      }));
    }

    paragraphs.push(new Paragraph({
      children: [
        isSameSpeaker ? timestamp(safeStr(entry.timestamp)) : text(''),
        isSameSpeaker ? text(' ') : text(''),
        text(safeStr(entry.text), { color: COLORS.textSecondary }),
      ],
      indent: { left: isSameSpeaker ? 0 : 360 },
    }));
  });

  return paragraphs;
}

// === Главная функция генерации ===

const DOC_TYPE_LABELS: Record<ArtifactType, string> = {
  protocol: 'Протокол встречи',
  requirements: 'Техническое задание',
  risks: 'Карта рисков',
  glossary: 'Глоссарий проекта',
  questions: 'Открытые вопросы',
  transcript: 'Стенограмма встречи',
};

const contentGenerators: Record<ArtifactType, (data: Record<string, unknown>) => Paragraph[]> = {
  protocol: generateProtocolContent,
  requirements: generateRequirementsContent,
  risks: generateRisksContent,
  glossary: generateGlossaryContent,
  questions: generateQuestionsContent,
  transcript: generateTranscriptContent,
};

function generateDocx(
  artifact: Artifact,
  projectName: string,
  meetingTitle: string,
): Document {
  const docTypeLabel = DOC_TYPE_LABELS[artifact.type];
  const date = new Date(artifact.createdAt).toLocaleDateString('ru-RU');

  const headerParagraphs = createHeader(docTypeLabel, projectName, meetingTitle, date);
  const contentParagraphs = contentGenerators[artifact.type](artifact.data);

  return new Document({
    styles: {
      default: {
        document: {
          run: { font: FONT.name, size: FONT.size, color: COLORS.text },
        },
      },
    },
    sections: [
      {
        properties: {
          page: {
            margin: { top: 720, right: 720, bottom: 720, left: 720 },
            pageNumbers: { start: 1 },
          },
        },
        footers: { default: createFooter(projectName) },
        children: [...headerParagraphs, ...contentParagraphs],
      },
    ],
  });
}

// === Экспорт API ===

/**
 * Экспортирует один артефакт в DOCX и скачивает файл.
 */
export async function exportArtifactToDocx(
  artifact: Artifact,
  projectName: string,
  meetingTitle: string,
): Promise<void> {
  const doc = generateDocx(artifact, projectName, meetingTitle);
  const blob = await Packer.toBlob(doc);
  const fileName = buildFileName(projectName, artifact.type, artifact.createdAt);
  saveAs(blob, fileName);
}

/**
 * Экспортирует все артефакты встречи в ZIP-архив.
 */
export async function exportAllToZip(
  artifacts: Artifact[],
  projectName: string,
  meetingTitle: string,
): Promise<void> {
  const zip = new JSZip();

  for (const artifact of artifacts) {
    const doc = generateDocx(artifact, projectName, meetingTitle);
    const blob = await Packer.toBlob(doc);
    const fileName = buildFileName(projectName, artifact.type, artifact.createdAt);
    zip.file(fileName, blob);
  }

  const zipBlob = await zip.generateAsync({ type: 'blob' });
  const date = new Date().toISOString().slice(0, 10);
  saveAs(zipBlob, `${sanitizeName(projectName)}_${date}_полный_пакет.zip`);
}

/**
 * Генерирует DOCX как Blob (без скачивания).
 */
export async function generateDocxBlob(
  artifact: Artifact,
  projectName: string,
  meetingTitle: string,
): Promise<Blob> {
  const doc = generateDocx(artifact, projectName, meetingTitle);
  return Packer.toBlob(doc);
}

// === Утилиты именования ===

const ARTIFACT_FILE_NAMES: Record<ArtifactType, string> = {
  protocol: 'протокол',
  requirements: 'требования',
  risks: 'риски',
  glossary: 'глоссарий',
  questions: 'вопросы',
  transcript: 'стенограмма',
};

function buildFileName(projectName: string, type: ArtifactType, createdAt: string): string {
  const date = new Date(createdAt).toISOString().slice(0, 10);
  return `${sanitizeName(projectName)}_${date}_${ARTIFACT_FILE_NAMES[type]}.docx`;
}

function sanitizeName(name: string): string {
  return name.replace(/[<>:"/\\|?*]/g, '_').replace(/\s+/g, '_').slice(0, 50);
}
