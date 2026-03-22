/**
 * Aether — standalone pipeline runner (Node.js 22, no browser/Tauri)
 * Whisper API → GPT-4 → 6 artifacts per meeting
 */

import fs from 'fs';
import path from 'path';

const OPENAI_API_KEY = process.env.OPENAI_API_KEY;
if (!OPENAI_API_KEY) {
  console.error('❌ Укажи ключ: OPENAI_API_KEY=sk-... node scripts/run_pipeline.mjs');
  process.exit(1);
}

const AUDIO_FILES = [
  {
    path: 'C:\\Users\\nikit\\Downloads\\aether_audio\\meeting_2026-03-17.mp3',
    date: '2026-03-17',
    name: 'Встреча 17 марта 2026',
  },
  {
    path: 'C:\\Users\\nikit\\Downloads\\aether_audio\\meeting_2026-01-30.mp3',
    date: '2026-01-30',
    name: 'Встреча 30 января 2026',
  },
];

const OUTPUT_DIR = 'C:\\Users\\nikit\\Downloads\\aether_results';
fs.mkdirSync(OUTPUT_DIR, { recursive: true });

// ─── Artifact types ───────────────────────────────────────────────────────────

const ARTIFACT_TYPES = ['protocol', 'requirements', 'risks', 'glossary', 'questions', 'transcript'];

// ─── Prompts (ported from src/lib/prompts.ts) ─────────────────────────────────

const SYSTEM_PROMPT = `Ты — опытный аналитик IT-проектов, специализирующийся на внедрении корпоративных систем (1С, ERP, CRM).
Ты анализируешь стенограммы рабочих встреч и извлекаешь структурированную информацию.

Правила:
- Извлекай ТОЛЬКО то, что явно сказано на встрече. Не додумывай.
- Если информация неоднозначна — отмечай как "требует уточнения".
- Сохраняй терминологию заказчика (как они называют вещи).
- Для каждого извлечённого элемента указывай таймкод источника.
- Ответ строго в JSON-формате, без markdown-обёрток.`;

function buildPrompts(transcript, meta) {
  const ctx = {
    meetingType: 'рабочая',
    projectName: meta.name,
    meetingDate: meta.date,
    transcript,
  };

  return {
    protocol: {
      system: SYSTEM_PROMPT,
      user: `Проанализируй стенограмму рабочей встречи и составь формальный протокол.

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
}`,
    },

    requirements: {
      system: SYSTEM_PROMPT,
      user: `Проанализируй стенограмму встречи и извлеки функциональные и нефункциональные требования.

Тип встречи: ${ctx.meetingType}
Проект: ${ctx.projectName}

Стенограмма:
${ctx.transcript}

Извлеки и верни JSON:
{
  "functional_requirements": [{"id": "FR-001", "title": "Название", "description": "Описание", "user_story": "Как [роль]...", "acceptance_criteria": [], "priority": "must|should|could|wont", "source_quote": "Цитата", "timestamp": "MM:SS", "status": "new|changed|confirmed|contradicts", "notes": ""}],
  "non_functional_requirements": [{"id": "NFR-001", "category": "performance|security|usability|reliability|scalability|integration", "title": "Название", "description": "Описание", "measurable_criteria": "", "timestamp": "MM:SS", "priority": "must|should|could"}],
  "business_rules": [{"id": "BR-001", "rule": "Правило", "condition": "Условие", "action": "Действие", "exceptions": [], "timestamp": "MM:SS"}],
  "integrations": [{"id": "INT-001", "system": "Система", "direction": "inbound|outbound|bidirectional", "data": "Данные", "frequency": "", "timestamp": "MM:SS"}],
  "constraints": [{"type": "technical|business|regulatory|timeline", "description": "Описание", "timestamp": "MM:SS"}],
  "process_description": {"as_is": "", "pain_points": [], "to_be_hints": ""}
}`,
    },

    risks: {
      system: SYSTEM_PROMPT,
      user: `Проанализируй стенограмму встречи и выяви проектные риски, неопределённости и противоречия.

Проект: ${ctx.projectName}

Стенограмма:
${ctx.transcript}

Извлеки и верни JSON:
{
  "risks": [{"id": "RISK-001", "category": "scope|technical|organizational|timeline|budget|integration|data", "title": "Название", "description": "Описание", "trigger": "Триггер", "impact": "high|medium|low", "probability": "high|medium|low", "mitigation_hint": "", "source_quote": "Цитата", "timestamp": "MM:SS", "status": "new|persists|resolved|escalated"}],
  "uncertainties": [{"id": "UNC-001", "topic": "Тема", "what_is_unknown": "Что неясно", "who_can_clarify": "", "impact_if_unresolved": "", "timestamp": "MM:SS"}],
  "contradictions": [{"id": "CONTR-001", "statement_a": {"speaker": "", "position": "", "timestamp": "MM:SS"}, "statement_b": {"speaker": "", "position": "", "timestamp": "MM:SS"}, "resolution": null, "severity": "high|medium|low"}],
  "assumptions": [{"id": "ASM-001", "assumption": "Предположение", "stated_by": "", "needs_validation": true, "timestamp": "MM:SS"}]
}`,
    },

    glossary: {
      system: SYSTEM_PROMPT,
      user: `Проанализируй стенограмму встречи и извлеки термины предметной области.

Проект: ${ctx.projectName}

Стенограмма:
${ctx.transcript}

Извлеки и верни JSON:
{
  "terms": [{"id": "TERM-001", "term": "Термин", "aliases": [], "definition": "Определение", "domain": "logistics|finance|hr|production|sales|it|other", "usage_example": "Пример", "related_terms": [], "first_mention": "MM:SS", "mentioned_by": "", "confidence": "high|medium|low", "status": "new|updated|confirmed"}],
  "abbreviations": [{"abbreviation": "ТМЦ", "full_form": "Расшифровка", "context": "Контекст", "timestamp": "MM:SS"}],
  "entity_mapping": [{"business_name": "Как называет заказчик", "system_name": "Как в системе", "notes": ""}]
}`,
    },

    questions: {
      system: SYSTEM_PROMPT,
      user: `Проанализируй стенограмму встречи и выяви все вопросы без ответа и темы для проработки.

Проект: ${ctx.projectName}

Стенограмма:
${ctx.transcript}

Извлеки и верни JSON:
{
  "open_questions": [{"id": "Q-001", "question": "Формулировка", "context": "Контекст", "asked_by": "", "directed_to": "", "category": "requirements|technical|organizational|process|data|access", "urgency": "blocking|important|nice_to_have", "related_requirement": null, "timestamp": "MM:SS", "status": "open|answered_partially|deferred"}],
  "deferred_topics": [{"id": "DEF-001", "topic": "Что отложили", "reason": "Почему", "deferred_to": "", "timestamp": "MM:SS"}],
  "information_gaps": [{"id": "GAP-001", "area": "Область", "what_is_needed": "Что нужно", "who_might_know": "", "impact": "На что влияет"}],
  "next_meeting_agenda_suggestions": []
}`,
    },

    transcript: {
      system: SYSTEM_PROMPT,
      user: `Отформатируй сырую стенограмму в читаемый документ.

Сырая стенограмма с таймкодами:
${ctx.transcript}

Обработай и верни JSON:
{
  "formatted_transcript": [{"timestamp": "00:00:15", "speaker": "Участник", "text": "Отформатированный текст", "topics": []}],
  "chapters": [{"title": "Название раздела", "start": "00:00:00", "end": "00:15:30", "summary": "Краткое содержание"}],
  "statistics": {"total_duration_minutes": 0, "speakers_count": 0, "speaker_time": {}, "topics_discussed": [], "dominant_speaker": ""}
}`,
    },
  };
}

// ─── Whisper API ──────────────────────────────────────────────────────────────

async function transcribeAudio(audioPath) {
  console.log(`  📤 Отправка в Whisper: ${path.basename(audioPath)}`);
  const audioBuffer = fs.readFileSync(audioPath);
  const blob = new Blob([audioBuffer], { type: 'audio/ogg; codecs=opus' });

  const formData = new FormData();
  formData.append('file', blob, path.basename(audioPath));
  formData.append('model', 'whisper-1');
  formData.append('response_format', 'verbose_json');
  formData.append('language', 'ru');
  formData.append('timestamp_granularities[]', 'segment');

  const response = await fetch('https://api.openai.com/v1/audio/transcriptions', {
    method: 'POST',
    headers: { Authorization: `Bearer ${OPENAI_API_KEY}` },
    body: formData,
  });

  if (!response.ok) {
    const err = await response.text();
    throw new Error(`Whisper API error ${response.status}: ${err.slice(0, 300)}`);
  }

  const data = await response.json();
  console.log(`  ✓ Транскрипция: ${data.segments?.length || 0} сегментов, ${Math.round(data.duration / 60)} мин`);
  return data;
}

function segmentsToTranscript(segments) {
  return segments.map((seg) => {
    const mins = Math.floor(seg.start / 60);
    const secs = Math.floor(seg.start % 60);
    const ts = `${String(mins).padStart(2, '0')}:${String(secs).padStart(2, '0')}`;
    return `[${ts}] ${seg.text.trim()}`;
  }).join('\n');
}

// ─── GPT-4 API ────────────────────────────────────────────────────────────────

function sleep(ms) {
  return new Promise((resolve) => setTimeout(resolve, ms));
}

async function generateArtifact(type, prompt) {
  const response = await fetch('https://api.openai.com/v1/chat/completions', {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
      Authorization: `Bearer ${OPENAI_API_KEY}`,
    },
    body: JSON.stringify({
      model: 'gpt-4o',
      messages: [
        { role: 'system', content: prompt.system },
        { role: 'user', content: prompt.user },
      ],
      temperature: type === 'transcript' ? 0.3 : 0.1,
      max_tokens: 8192,
      response_format: { type: 'json_object' },
    }),
  });

  if (!response.ok) {
    const err = await response.text();
    throw new Error(`GPT-4 API error ${response.status}: ${err.slice(0, 500)}`);
  }

  const data = await response.json();
  const text = data.choices?.[0]?.message?.content || '';
  const usage = data.usage || {};
  const tokens = (usage.prompt_tokens || 0) + (usage.completion_tokens || 0);

  let parsed = null;
  let parseError = null;
  try {
    parsed = JSON.parse(text);
  } catch (e) {
    parseError = e.message;
  }

  return { type, text, data: parsed, parseError, tokens, model: data.model };
}

/** Генерация с автоматическим ожиданием при rate limit 429. */
async function generateArtifactWithRateLimit(type, prompt, maxRetries = 6) {
  for (let attempt = 0; attempt < maxRetries; attempt++) {
    try {
      return await generateArtifact(type, prompt);
    } catch (err) {
      if (err.message.includes('429')) {
        const match = err.message.match(/Please try again in (\d+\.?\d*)s/);
        const waitSec = match ? Math.ceil(parseFloat(match[1])) + 5 : 70;
        console.log(`  ⏳ Rate limit (попытка ${attempt + 1}/${maxRetries}), жду ${waitSec} сек...`);
        await sleep(waitSec * 1000);
      } else {
        throw err;
      }
    }
  }
  throw new Error(`Превышено число попыток для артефакта ${type}`);
}

// ─── Main pipeline ────────────────────────────────────────────────────────────

async function processMeeting(meta) {
  const safeName = meta.date;
  console.log(`\n${'═'.repeat(60)}`);
  console.log(`▶ Обработка: ${meta.name}`);
  console.log(`${'═'.repeat(60)}`);

  // Stage 1: Transcribe
  console.log('\n[1/3] Транскрипция через Whisper...');
  const whisperResult = await transcribeAudio(meta.path);
  const transcriptText = segmentsToTranscript(whisperResult.segments || []);

  // Save raw transcript
  const transcriptPath = path.join(OUTPUT_DIR, `${safeName}_transcript_raw.txt`);
  fs.writeFileSync(transcriptPath, transcriptText, 'utf8');
  console.log(`  💾 Сохранено: ${transcriptPath}`);

  // Stage 2: Generate artifacts
  console.log('\n[2/3] Генерация артефактов через GPT-4...');
  const prompts = buildPrompts(transcriptText, meta);
  const artifacts = {};
  let totalTokens = 0;

  // Process sequentially to respect TPM limits (~28K tokens per request, limit 30K/min)
  for (const type of ARTIFACT_TYPES) {
    console.log(`  ▶ ${type}...`);
    try {
      const result = await generateArtifactWithRateLimit(type, prompts[type]);
      console.log(`  ✓ ${type} (${result.tokens} токенов)${result.parseError ? ' ⚠ parse error' : ''}`);
      artifacts[type] = result;
      totalTokens += result.tokens || 0;
    } catch (err) {
      console.error(`  ✗ ${type}: ${err.message.slice(0, 120)}`);
      artifacts[type] = { type, error: err.message, data: null, tokens: 0 };
    }
  }

  // Stage 3: Save results
  console.log('\n[3/3] Сохранение результатов...');
  const summary = {
    meeting: meta.name,
    date: meta.date,
    duration_minutes: Math.round((whisperResult.duration || 0) / 60),
    segments: whisperResult.segments?.length || 0,
    language: whisperResult.language || 'ru',
    total_tokens: totalTokens,
    artifacts: {},
  };

  for (const [type, result] of Object.entries(artifacts)) {
    const outPath = path.join(OUTPUT_DIR, `${safeName}_${type}.json`);
    const content = result.data || { raw: result.text, error: result.error };
    fs.writeFileSync(outPath, JSON.stringify(content, null, 2), 'utf8');
    console.log(`  💾 ${type}: ${outPath}`);
    summary.artifacts[type] = {
      ok: !result.error && !result.parseError,
      tokens: result.tokens || 0,
      error: result.error || result.parseError || null,
    };
  }

  // Save summary
  const summaryPath = path.join(OUTPUT_DIR, `${safeName}_summary.json`);
  fs.writeFileSync(summaryPath, JSON.stringify(summary, null, 2), 'utf8');

  return summary;
}

// ─── Entry point ─────────────────────────────────────────────────────────────

(async () => {
  console.log('🚀 Aether Pipeline Runner');
  console.log(`📁 Результаты: ${OUTPUT_DIR}\n`);

  const allSummaries = [];
  for (const meta of AUDIO_FILES) {
    try {
      const summary = await processMeeting(meta);
      allSummaries.push(summary);
    } catch (err) {
      console.error(`\n❌ Критическая ошибка для ${meta.name}:`, err.message);
    }
  }

  console.log('\n' + '═'.repeat(60));
  console.log('ИТОГ');
  console.log('═'.repeat(60));
  for (const s of allSummaries) {
    console.log(`\n📋 ${s.meeting} (${s.duration_minutes} мин, ${s.segments} сегментов)`);
    console.log(`   Токены: ${s.total_tokens}`);
    for (const [type, info] of Object.entries(s.artifacts)) {
      const status = info.ok ? '✓' : `✗ ${info.error}`;
      console.log(`   ${status} ${type} (${info.tokens} tok)`);
    }
  }

  console.log(`\n✅ Файлы сохранены в: ${OUTPUT_DIR}`);
})();
