"use client";

import { useState, useCallback, useRef, useEffect } from "react";
import { motion, AnimatePresence } from "framer-motion";
import {
  Phone,
  PhoneOff,
  Clock,
  RotateCcw,
  Play,
  Volume2,
  VolumeX,
  TrendingDown,
  Timer,
  Zap,
  CheckCircle2,
  Star,
} from "lucide-react";
import { DemoTranscript, type TranscriptEntry } from "./demo-transcript";
import { DemoAIPanel, type DemoPhase } from "./demo-ai-panel";
import { DemoProgress } from "./demo-progress";
import {
  unlockAudio,
  playRingSound,
  startAmbient,
  stopAmbient,
  playWhoosh,
  playScanSound,
  playClassifyChime,
  playNotificationDing,
  playSuccessSound,
  playVoice,
  stopAllAudio,
} from "./demo-audio";

// ═══════════════════════════════════════════════════════════
//  SCRIPT — 6 realistic dialogue turns
// ═══════════════════════════════════════════════════════════

const SCRIPT: {
  id: string;
  speaker: "operator" | "client";
  text: string;
  tags?: string[];
  speakerLabel?: string;
}[] = [
  {
    id: "op-1",
    speaker: "operator",
    text: "Добрый день! Вас приветствует Аврора — AI-ассистент компании ИнтерСофт. Расскажите, что у вас случилось, я помогу разобраться.",
    speakerLabel: "Аврора",
  },
  {
    id: "cl-1",
    speaker: "client",
    text: "Добрый день! У нас тут всё встало. Программа ЗУП — после вчерашнего обновления не можем сформировать расчёт зарплаты. Пишет «Неверный расчётный период». Завтра выплата, 150 человек ждут зарплату!",
    tags: ["ЗУП", "обновление", "ошибка", "зарплата", "срочно"],
    speakerLabel: "Клиент (Сергей)",
  },
  {
    id: "op-2",
    speaker: "operator",
    text: "Понимаю, ситуация срочная — сейчас разберёмся. Подскажите, какая у вас версия ЗУП? И обновление было плановым или автоматическим?",
    speakerLabel: "Аврора",
  },
  {
    id: "cl-2",
    speaker: "client",
    text: "Версия 3.1.28, обновление прилетело автоматически вчера вечером. С утра при открытии расчёта — ошибка. Пробовали перезапускать сервер — не помогает.",
    tags: ["3.1.28", "авто-обновление", "перезапуск"],
    speakerLabel: "Клиент (Сергей)",
  },
  {
    id: "op-3",
    speaker: "operator",
    text: "Нашла решение! Это известная проблема обновления 3.1.28. Откройте «Настройки расчёта зарплаты», в поле «Расчётный период» установите текущий месяц вручную, затем через «Сервис» обновите регламентный отчёт. После этого расчёт должен пройти.",
    speakerLabel: "Аврора",
  },
  {
    id: "cl-3",
    speaker: "client",
    text: "Сейчас попробую... Да! Заработало! Вот это скорость! Спасибо огромное, я думал, придётся вызывать программиста.",
    tags: ["решено"],
    speakerLabel: "Клиент (Сергей)",
  },
];

const CLASSIFICATION = {
  department: { label: "Поддержка", confidence: 94 },
  taskType: { label: "Ошибка ПО", confidence: 91 },
  priority: { label: "Критический", confidence: 96 },
  product: { label: "ЗУП 3.1.28", confidence: 97 },
};

const SENTIMENTS = {
  stressed: { label: "Стресс", emoji: "😰", value: 25, color: "bg-gradient-to-r from-is-red to-warning" },
  worried: { label: "Тревога", emoji: "😟", value: 35, color: "bg-gradient-to-r from-is-red to-warning" },
  hopeful: { label: "Надежда", emoji: "🙂", value: 60, color: "bg-gradient-to-r from-warning to-is-blue" },
  relieved: { label: "Облегчение", emoji: "😊", value: 90, color: "bg-gradient-to-r from-is-blue to-success" },
};

const KB_RESULTS = [
  { id: "KB-0089", title: "Ошибка расчётного периода после обновления 3.1.28", relevance: 97 },
  { id: "KB-0045", title: "Сброс параметров при обновлении ЗУП", relevance: 72 },
  { id: "KB-0112", title: "Регламентные отчёты — общее руководство", relevance: 58 },
];

const CHAR_DELAY = 30;

// ═══════════════════════════════════════════════════════════

export function DemoSimulator() {
  const [phase, setPhase] = useState<DemoPhase>("idle");
  const [entries, setEntries] = useState<TranscriptEntry[]>([]);
  const [activeEntryIndex, setActiveEntryIndex] = useState(-1);
  const [revealedChars, setRevealedChars] = useState(0);
  const [isTyping, setIsTyping] = useState(false);
  const [elapsed, setElapsed] = useState(0);
  const [muted, setMuted] = useState(false);
  const [sentiment, setSentiment] = useState(SENTIMENTS.stressed);

  const timerRef = useRef<ReturnType<typeof setInterval> | null>(null);
  const typewriterRef = useRef<ReturnType<typeof setInterval> | null>(null);
  const abortRef = useRef(false);

  // Timer
  useEffect(() => {
    if (phase !== "idle" && phase !== "summary") {
      timerRef.current = setInterval(() => setElapsed((p) => p + 1), 1000);
    }
    return () => { if (timerRef.current) clearInterval(timerRef.current); };
  }, [phase]);

  const fmt = (s: number) => {
    const m = Math.floor(s / 60);
    const sec = s % 60;
    return `${m.toString().padStart(2, "0")}:${sec.toString().padStart(2, "0")}`;
  };

  // Typewriter
  const typeEntry = useCallback(
    (entry: TranscriptEntry): Promise<void> =>
      new Promise((resolve) => {
        setEntries((prev) => [...prev, entry]);
        setActiveEntryIndex((prev) => prev + 1);
        setRevealedChars(0);
        setIsTyping(true);
        let ci = 0;
        typewriterRef.current = setInterval(() => {
          if (abortRef.current) {
            if (typewriterRef.current) clearInterval(typewriterRef.current);
            resolve();
            return;
          }
          ci++;
          setRevealedChars(ci);
          if (ci >= entry.text.length) {
            if (typewriterRef.current) clearInterval(typewriterRef.current);
            setIsTyping(false);
            resolve();
          }
        }, CHAR_DELAY);
      }),
    []
  );

  // Wait
  const wait = (ms: number): Promise<void> =>
    new Promise((resolve) => {
      const t = setTimeout(resolve, ms);
      const chk = setInterval(() => {
        if (abortRef.current) { clearInterval(chk); clearTimeout(t); resolve(); }
      }, 80);
      setTimeout(() => clearInterval(chk), ms + 100);
    });

  // ─── Main Orchestration ───────────────────────────────────
  const runDemo = useCallback(async () => {
    abortRef.current = false;
    setEntries([]);
    setActiveEntryIndex(-1);
    setRevealedChars(0);
    setElapsed(0);
    setSentiment(SENTIMENTS.stressed);

    const stopped = () => abortRef.current;

    // ▸ Phase 1: Ringing
    setPhase("ringing");
    if (!muted) await playRingSound();
    if (stopped()) return;
    await wait(400);
    if (stopped()) return;

    // ▸ Phase 2: Greeting — start ambient + voice
    setPhase("greeting");
    if (!muted) startAmbient();
    {
      const voiceP = playVoice("op-1", muted);
      await typeEntry({ ...SCRIPT[0] });
      await voiceP; // wait for voice to finish too
    }
    if (stopped()) return;
    await wait(300);
    if (stopped()) return;

    // ▸ Phase 3: Client describes problem + voice
    setPhase("client_problem");
    setSentiment(SENTIMENTS.stressed);
    {
      const voiceP = playVoice("cl-1", muted);
      await typeEntry({ ...SCRIPT[1] });
      await voiceP;
    }
    if (stopped()) return;
    await wait(300);
    if (stopped()) return;

    // ▸ Phase 4: AI scanning (sentiment + entity detection)
    setPhase("ai_scanning");
    if (!muted) playScanSound();
    await wait(1800);
    if (stopped()) return;

    // ▸ Phase 5: AI classifying
    setPhase("ai_classifying");
    if (!muted) playWhoosh();
    await wait(2200);
    if (stopped()) return;
    if (!muted) playClassifyChime();
    await wait(600);
    if (stopped()) return;

    // ▸ Phase 6: Operator clarifies (reading AI hint) + voice
    setPhase("operator_clarifies");
    setSentiment(SENTIMENTS.worried);
    {
      const voiceP = playVoice("op-2", muted);
      await typeEntry({ ...SCRIPT[2] });
      await voiceP;
    }
    if (stopped()) return;
    await wait(300);
    if (stopped()) return;

    // ▸ Phase 7: Client provides details + voice
    setPhase("client_details");
    {
      const voiceP = playVoice("cl-2", muted);
      await typeEntry({ ...SCRIPT[3] });
      await voiceP;
    }
    if (stopped()) return;
    await wait(300);
    if (stopped()) return;

    // ▸ Phase 8: Deep analysis
    setPhase("ai_deep_analysis");
    if (!muted) playScanSound();
    await wait(1500);
    if (stopped()) return;

    // ▸ Phase 9: KB search
    setPhase("ai_kb_search");
    if (!muted) playWhoosh();
    setSentiment(SENTIMENTS.hopeful);
    await wait(2000);
    if (stopped()) return;

    // ▸ Phase 10: AI suggests solution
    setPhase("ai_suggests");
    if (!muted) playClassifyChime();
    await wait(1200);
    if (stopped()) return;

    // ▸ Phase 11: Operator resolves (reads AI suggestion) + voice
    setPhase("operator_resolves");
    {
      const voiceP = playVoice("op-3", muted);
      await typeEntry({ ...SCRIPT[4] });
      await voiceP;
    }
    if (stopped()) return;
    await wait(300);
    if (stopped()) return;

    // ▸ Phase 12: Task creating
    setPhase("task_creating");
    if (!muted) playNotificationDing();
    await wait(2000);
    if (stopped()) return;

    // ▸ Phase 13: Client confirms + voice
    setPhase("client_confirms");
    setSentiment(SENTIMENTS.relieved);
    {
      const voiceP = playVoice("cl-3", muted);
      await typeEntry({ ...SCRIPT[5] });
      await voiceP;
    }
    if (stopped()) return;
    await wait(500);
    if (stopped()) return;

    // ▸ Phase 14: Summary
    setPhase("summary");
    stopAmbient();
    if (!muted) playSuccessSound();
  }, [typeEntry, muted]);

  const stopDemo = useCallback(() => {
    abortRef.current = true;
    stopAllAudio();
    if (typewriterRef.current) clearInterval(typewriterRef.current);
    if (timerRef.current) clearInterval(timerRef.current);
    setPhase("idle");
    setIsTyping(false);
  }, []);

  const resetDemo = useCallback(() => {
    stopDemo();
    setEntries([]);
    setActiveEntryIndex(-1);
    setRevealedChars(0);
    setElapsed(0);
    setSentiment(SENTIMENTS.stressed);
  }, [stopDemo]);

  const startDemo = useCallback(async () => {
    // Unlock AudioContext directly from user gesture (click) — no setTimeout!
    await unlockAudio();
    resetDemo();
    await runDemo();
  }, [runDemo, resetDemo]);

  const isRunning = phase !== "idle" && phase !== "summary";

  // ─── Render ───────────────────────────────────────────────
  return (
    <div className="demo-panel w-full">
      {/* Header */}
      <div className="demo-header">
        <div className="flex items-center gap-3">
          {isRunning && (
            <span className="flex items-center gap-1.5">
              <span className="pulse-live h-2 w-2 rounded-full bg-is-red" />
              <span className="text-[10px] font-bold uppercase tracking-widest text-is-red">
                LIVE
              </span>
            </span>
          )}
          <span className="text-sm font-medium text-text-primary">
            {phase === "idle"
              ? "Симуляция звонка"
              : phase === "summary"
                ? "Демонстрация завершена"
                : "Входящий звонок — ИнтерСофт"}
          </span>
        </div>
        <div className="flex items-center gap-2">
          {/* Mute toggle */}
          <button
            onClick={() => setMuted((p) => !p)}
            className="rounded-lg p-1.5 text-text-muted transition-colors hover:bg-bg-elevated hover:text-text-primary"
            title={muted ? "Включить звук" : "Выключить звук"}
          >
            {muted ? <VolumeX className="h-3.5 w-3.5" /> : <Volume2 className="h-3.5 w-3.5" />}
          </button>
          <div className="flex items-center gap-1.5 text-text-muted">
            <Clock className="h-3 w-3" />
            <span className="font-mono text-[11px]">{fmt(elapsed)}</span>
          </div>
          {isRunning && (
            <button
              onClick={stopDemo}
              className="flex items-center gap-1 rounded-lg bg-is-red/10 px-2.5 py-1 text-[11px] font-medium text-is-red transition-colors hover:bg-is-red/20"
            >
              <PhoneOff className="h-3 w-3" />
              Стоп
            </button>
          )}
        </div>
      </div>

      {/* Body */}
      <AnimatePresence mode="wait">
        {phase === "idle" ? (
          <IdleScreen key="idle" onStart={startDemo} />
        ) : phase === "summary" ? (
          <SummaryScreen key="summary" elapsed={elapsed} fmt={fmt} onRestart={startDemo} />
        ) : (
          <motion.div
            key="running"
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            exit={{ opacity: 0 }}
            className="flex flex-col"
          >
            <div className="grid min-h-[480px] grid-cols-1 gap-0 lg:grid-cols-[1fr_340px]">
              {/* Left — Transcript */}
              <div className="border-b border-border-subtle p-4 lg:border-b-0 lg:border-r">
                <DemoTranscript
                  entries={entries}
                  activeEntryIndex={activeEntryIndex}
                  revealedChars={revealedChars}
                  isTyping={isTyping}
                />
              </div>
              {/* Right — AI Panel */}
              <div className="p-4">
                <DemoAIPanel
                  phase={phase}
                  classification={CLASSIFICATION}
                  sentiment={sentiment}
                  kbResults={KB_RESULTS}
                />
              </div>
            </div>
            <div className="border-t border-border-subtle px-4 py-2.5">
              <DemoProgress phase={phase} />
            </div>
          </motion.div>
        )}
      </AnimatePresence>
    </div>
  );
}

// ═══════════════════════════════════════════════════════════
//  Idle Screen
// ═══════════════════════════════════════════════════════════

function IdleScreen({ onStart }: { onStart: () => void }) {
  return (
    <motion.div
      initial={{ opacity: 0 }}
      animate={{ opacity: 1 }}
      exit={{ opacity: 0 }}
      className="flex flex-col items-center justify-center px-8 py-16"
    >
      {/* Animated phone icon */}
      <motion.div
        className="relative mb-8"
        animate={{ scale: [1, 1.05, 1] }}
        transition={{ duration: 2, repeat: Infinity }}
      >
        <div className="flex h-24 w-24 items-center justify-center rounded-full bg-gradient-to-br from-is-blue/20 to-aurora-purple/20 border border-is-blue/20">
          <Phone className="h-10 w-10 text-is-blue" />
        </div>
        {/* Pulse rings */}
        <motion.div
          className="absolute inset-0 rounded-full border border-is-blue/30"
          animate={{ scale: [1, 1.6], opacity: [0.5, 0] }}
          transition={{ duration: 2, repeat: Infinity }}
        />
        <motion.div
          className="absolute inset-0 rounded-full border border-aurora-purple/20"
          animate={{ scale: [1, 1.8], opacity: [0.3, 0] }}
          transition={{ duration: 2, repeat: Infinity, delay: 0.5 }}
        />
      </motion.div>

      <h3 className="mb-2 text-xl font-bold text-text-primary">
        Интерактивная демонстрация
      </h3>
      <p className="mb-2 max-w-lg text-center text-sm text-text-muted leading-relaxed">
        Полная симуляция реального звонка в поддержку. Вы увидите как AI-суфлёр
        Аврора анализирует проблему, ищет решение в базе знаний и помогает
        оператору решить проблему клиента за минуты.
      </p>
      <p className="mb-8 text-xs text-text-muted">
        6 реплик диалога • AI-классификация • Поиск в базе знаний • Создание задачи
      </p>

      <button
        onClick={onStart}
        className="group flex items-center gap-2.5 rounded-2xl bg-gradient-to-r from-is-blue to-aurora-purple px-10 py-4 text-base font-bold text-white shadow-lg shadow-is-blue/20 transition-all hover:shadow-xl hover:shadow-is-blue/30 hover:scale-[1.02] active:scale-[0.98]"
      >
        <Play className="h-5 w-5 transition-transform group-hover:scale-110" />
        Запустить демо
      </button>
    </motion.div>
  );
}

// ═══════════════════════════════════════════════════════════
//  Summary Screen
// ═══════════════════════════════════════════════════════════

function SummaryScreen({
  elapsed,
  fmt,
  onRestart,
}: {
  elapsed: number;
  fmt: (s: number) => string;
  onRestart: () => void;
}) {
  return (
    <motion.div
      initial={{ opacity: 0 }}
      animate={{ opacity: 1 }}
      exit={{ opacity: 0 }}
      className="p-6 lg:p-8"
    >
      <div className="mb-6 text-center">
        <motion.div
          initial={{ scale: 0 }}
          animate={{ scale: 1 }}
          transition={{ type: "spring", stiffness: 300, delay: 0.1 }}
          className="mx-auto mb-3 flex h-14 w-14 items-center justify-center rounded-full bg-success/15"
        >
          <CheckCircle2 className="h-7 w-7 text-success" />
        </motion.div>
        <h3 className="text-lg font-bold text-text-primary">
          Проблема решена за {fmt(elapsed)}
        </h3>
        <p className="text-sm text-text-muted mt-1">
          Без Авроры этот звонок занял бы 12+ минут
        </p>
      </div>

      {/* Comparison: Without vs With Aurora */}
      <div className="mx-auto mb-6 grid max-w-2xl grid-cols-2 gap-4">
        {/* WITHOUT */}
        <div className="rounded-xl border border-is-red/20 bg-is-red/5 p-4">
          <p className="mb-3 text-xs font-bold uppercase tracking-wider text-is-red flex items-center gap-1.5">
            <TrendingDown className="h-3.5 w-3.5" />
            Без Авроры
          </p>
          <div className="space-y-2">
            <MetricRow label="Время звонка" value="12+ мин" bad />
            <MetricRow label="Поиск решения" value="Вручную" bad />
            <MetricRow label="Классификация" value="Ручная" bad />
            <MetricRow label="Создание задачи" value="Вручную" bad />
            <MetricRow label="NPS клиента" value="~6/10" bad />
          </div>
        </div>

        {/* WITH */}
        <div className="rounded-xl border border-success/20 bg-success/5 p-4">
          <p className="mb-3 text-xs font-bold uppercase tracking-wider text-success flex items-center gap-1.5">
            <Zap className="h-3.5 w-3.5" />
            С Авророй
          </p>
          <div className="space-y-2">
            <MetricRow label="Время звонка" value={fmt(elapsed)} good />
            <MetricRow label="Поиск решения" value="AI (2 сек)" good />
            <MetricRow label="Классификация" value="Авто 94%" good />
            <MetricRow label="Создание задачи" value="Авто" good />
            <MetricRow label="NPS клиента" value="9/10" good />
          </div>
        </div>
      </div>

      {/* Key metrics */}
      <div className="mx-auto mb-6 grid max-w-xl grid-cols-4 gap-3">
        <SummaryCard icon={Timer} value="6" label="Реплик" color="text-is-blue" />
        <SummaryCard icon={Zap} value="94%" label="Точность" color="text-success" />
        <SummaryCard icon={Star} value="97%" label="KB Match" color="text-aurora-purple" />
        <SummaryCard icon={CheckCircle2} value="1" label="Задача" color="text-warning" />
      </div>

      <div className="flex justify-center">
        <button
          onClick={onRestart}
          className="flex items-center gap-2 rounded-xl bg-is-blue/10 px-6 py-2.5 text-sm font-medium text-is-blue transition-all hover:bg-is-blue/20 hover:scale-[1.02]"
        >
          <RotateCcw className="h-4 w-4" />
          Повторить демо
        </button>
      </div>
    </motion.div>
  );
}

function MetricRow({
  label,
  value,
  good,
  bad,
}: {
  label: string;
  value: string;
  good?: boolean;
  bad?: boolean;
}) {
  return (
    <div className="flex items-center justify-between text-xs">
      <span className="text-text-muted">{label}</span>
      <span className={`font-medium ${good ? "text-success" : bad ? "text-is-red" : "text-text-secondary"}`}>
        {value}
      </span>
    </div>
  );
}

function SummaryCard({
  icon: Icon,
  value,
  label,
  color,
}: {
  icon: React.ElementType;
  value: string;
  label: string;
  color: string;
}) {
  return (
    <motion.div
      initial={{ opacity: 0, y: 10 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ type: "spring", delay: 0.2 }}
      className="glass-card p-3 text-center"
    >
      <Icon className={`mx-auto mb-1 h-4 w-4 ${color}`} />
      <p className={`text-lg font-bold ${color}`}>{value}</p>
      <p className="text-[10px] text-text-muted">{label}</p>
    </motion.div>
  );
}
