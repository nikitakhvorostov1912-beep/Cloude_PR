"use client";

import { motion, AnimatePresence } from "framer-motion";
import {
  BarChart3,
  Route,
  Lightbulb,
  CheckCircle2,
  Loader2,
  Brain,
  Search,
  Shield,
  Heart,
  Zap,
  Clock,
  TrendingUp,
} from "lucide-react";

export type DemoPhase =
  | "idle"
  | "ringing"
  | "greeting"
  | "client_problem"
  | "ai_scanning"
  | "ai_classifying"
  | "operator_clarifies"
  | "client_details"
  | "ai_deep_analysis"
  | "ai_kb_search"
  | "ai_suggests"
  | "operator_resolves"
  | "task_creating"
  | "client_confirms"
  | "summary";

interface ClassificationData {
  department: { label: string; confidence: number };
  taskType: { label: string; confidence: number };
  priority: { label: string; confidence: number };
  product: { label: string; confidence: number };
}

interface SentimentData {
  label: string;
  emoji: string;
  value: number; // 0-100 where 0=negative, 100=positive
  color: string;
}

interface KBResult {
  id: string;
  title: string;
  relevance: number;
}

interface DemoAIPanelProps {
  phase: DemoPhase;
  classification: ClassificationData;
  sentiment: SentimentData;
  kbResults: KBResult[];
}

const PHASE_ORDER: DemoPhase[] = [
  "idle", "ringing", "greeting", "client_problem",
  "ai_scanning", "ai_classifying", "operator_clarifies",
  "client_details", "ai_deep_analysis", "ai_kb_search",
  "ai_suggests", "operator_resolves", "task_creating",
  "client_confirms", "summary",
];

function isAtLeast(current: DemoPhase, target: DemoPhase): boolean {
  return PHASE_ORDER.indexOf(current) >= PHASE_ORDER.indexOf(target);
}

const cardIn = {
  initial: { opacity: 0, y: 16, scale: 0.97 },
  animate: { opacity: 1, y: 0, scale: 1 },
  transition: { type: "spring" as const, stiffness: 350, damping: 28 },
};

function ConfidenceBar({
  label,
  value,
  displayValue,
  animate,
  icon: Icon,
}: {
  label: string;
  value: string;
  displayValue: number;
  animate: boolean;
  icon?: React.ElementType;
}) {
  const barColor = displayValue > 85
    ? "from-is-blue to-success"
    : displayValue > 70
      ? "from-is-blue to-warning"
      : "from-is-blue to-is-red";

  return (
    <div className="space-y-1">
      <div className="flex items-center justify-between text-xs">
        <span className="flex items-center gap-1.5 text-text-muted">
          {Icon && <Icon className="h-3 w-3" />}
          {label}
        </span>
        <span className="font-mono text-text-secondary">{value}</span>
      </div>
      <div className="h-1.5 w-full rounded-full bg-bg-elevated overflow-hidden">
        <motion.div
          className={`h-full rounded-full bg-gradient-to-r ${barColor}`}
          initial={{ width: 0 }}
          animate={{ width: animate ? `${displayValue}%` : "0%" }}
          transition={{ type: "spring", stiffness: 80, damping: 18, delay: 0.1 }}
        />
      </div>
    </div>
  );
}

export function DemoAIPanel({
  phase,
  classification,
  sentiment,
  kbResults,
}: DemoAIPanelProps) {
  const showSentiment = isAtLeast(phase, "ai_scanning");
  const showClassification = isAtLeast(phase, "ai_classifying");
  const showRouting = isAtLeast(phase, "operator_clarifies");
  const showKB = isAtLeast(phase, "ai_kb_search");
  const showSuggestion = isAtLeast(phase, "ai_suggests");
  const showTask = isAtLeast(phase, "task_creating");

  return (
    <div className="flex h-full flex-col gap-3 overflow-y-auto pr-1">
      <h3 className="text-sm font-semibold uppercase tracking-wide text-text-secondary flex items-center gap-2">
        <Brain className="h-4 w-4 text-aurora-purple" />
        AI-Суфлёр
      </h3>

      {/* Sentiment Analysis */}
      <AnimatePresence>
        {showSentiment && (
          <motion.div {...cardIn} className="glass-card p-3">
            <div className="flex items-center justify-between mb-2">
              <span className="flex items-center gap-1.5 text-[10px] font-semibold uppercase tracking-wider text-text-muted">
                <Heart className="h-3 w-3 text-is-red" />
                Эмоция клиента
              </span>
              <span className="text-sm">{sentiment.emoji}</span>
            </div>
            <div className="flex items-center gap-2">
              <div className="flex-1 h-1.5 rounded-full bg-bg-elevated overflow-hidden">
                <motion.div
                  className={`h-full rounded-full ${sentiment.color}`}
                  initial={{ width: 0 }}
                  animate={{ width: `${sentiment.value}%` }}
                  transition={{ type: "spring", stiffness: 80, damping: 20 }}
                />
              </div>
              <span className="text-xs font-medium text-text-secondary min-w-fit">
                {sentiment.label}
              </span>
            </div>
          </motion.div>
        )}
      </AnimatePresence>

      {/* AI Classification */}
      <AnimatePresence>
        {isAtLeast(phase, "ai_scanning") && (
          <motion.div {...cardIn} className="glass-card p-3">
            <div className="mb-2.5 flex items-center gap-2">
              <BarChart3 className="h-3.5 w-3.5 text-is-blue" />
              <span className="text-[10px] font-semibold uppercase tracking-wider text-text-muted">
                Классификация
              </span>
              {!showClassification && (
                <Loader2 className="ml-auto h-3 w-3 animate-spin text-is-blue" />
              )}
              {showClassification && (
                <Zap className="ml-auto h-3 w-3 text-success" />
              )}
            </div>
            <div className="space-y-2">
              <ConfidenceBar
                label="Отдел"
                value={showClassification ? `${classification.department.label} ${classification.department.confidence}%` : "анализ..."}
                displayValue={classification.department.confidence}
                animate={showClassification}
                icon={Route}
              />
              <ConfidenceBar
                label="Тип"
                value={showClassification ? `${classification.taskType.label} ${classification.taskType.confidence}%` : "анализ..."}
                displayValue={classification.taskType.confidence}
                animate={showClassification}
                icon={Shield}
              />
              <ConfidenceBar
                label="Приоритет"
                value={showClassification ? `${classification.priority.label} ${classification.priority.confidence}%` : "анализ..."}
                displayValue={classification.priority.confidence}
                animate={showClassification}
                icon={TrendingUp}
              />
              <ConfidenceBar
                label="Продукт"
                value={showClassification ? `${classification.product.label} ${classification.product.confidence}%` : "анализ..."}
                displayValue={classification.product.confidence}
                animate={showClassification}
              />
            </div>
          </motion.div>
        )}
      </AnimatePresence>

      {/* Routing Decision */}
      <AnimatePresence>
        {showRouting && (
          <motion.div {...cardIn} className="glass-card p-3">
            <div className="mb-2 flex items-center gap-2">
              <Route className="h-3.5 w-3.5 text-aurora-purple" />
              <span className="text-[10px] font-semibold uppercase tracking-wider text-text-muted">
                Маршрутизация
              </span>
            </div>
            <div className="space-y-1.5 text-xs">
              <div className="flex justify-between">
                <span className="text-text-muted">Отдел:</span>
                <span className="font-medium text-is-blue">Поддержка / ЗУП</span>
              </div>
              <div className="flex justify-between">
                <span className="text-text-muted">Правило:</span>
                <span className="font-mono text-[10px] text-aurora-purple">error_after_update</span>
              </div>
              <div className="flex justify-between items-center">
                <span className="text-text-muted">SLA:</span>
                <span className="flex items-center gap-1 text-warning font-medium">
                  <Clock className="h-3 w-3" />
                  4 часа (высокий)
                </span>
              </div>
            </div>
          </motion.div>
        )}
      </AnimatePresence>

      {/* Knowledge Base Search */}
      <AnimatePresence>
        {showKB && (
          <motion.div {...cardIn} className="glass-card p-3">
            <div className="mb-2 flex items-center gap-2">
              <Search className="h-3.5 w-3.5 text-success" />
              <span className="text-[10px] font-semibold uppercase tracking-wider text-text-muted">
                База знаний
              </span>
            </div>
            <div className="space-y-1.5">
              {kbResults.map((kb, i) => (
                <motion.div
                  key={kb.id}
                  initial={{ opacity: 0, x: -10 }}
                  animate={{ opacity: 1, x: 0 }}
                  transition={{ delay: i * 0.15 }}
                  className="flex items-center gap-2 rounded-lg bg-success/5 border border-success/10 px-2.5 py-1.5"
                >
                  <span className="text-[10px] font-mono text-success">{kb.relevance}%</span>
                  <span className="text-[11px] text-text-secondary truncate">{kb.title}</span>
                  <span className="ml-auto text-[9px] font-mono text-text-muted">{kb.id}</span>
                </motion.div>
              ))}
            </div>
          </motion.div>
        )}
      </AnimatePresence>

      {/* AI Suggestion */}
      <AnimatePresence>
        {showSuggestion && (
          <motion.div {...cardIn} className="glass-card p-3 border-warning/20">
            <div className="mb-2 flex items-center gap-2">
              <Lightbulb className="h-3.5 w-3.5 text-warning" />
              <span className="text-[10px] font-semibold uppercase tracking-wider text-warning">
                Подсказка оператору
              </span>
            </div>
            <div className="rounded-lg bg-warning/5 border border-warning/10 p-2.5">
              <p className="text-xs leading-relaxed text-text-primary mb-2">
                Известная проблема обновления ЗУП 3.1.28. Решение:
              </p>
              <ol className="space-y-1 text-[11px] text-text-secondary list-decimal list-inside">
                <li>Открыть «Настройки расчёта зарплаты»</li>
                <li>Установить расчётный период вручную</li>
                <li>Обновить регламентный отчёт через «Сервис»</li>
              </ol>
              <p className="mt-2 text-[10px] text-text-muted flex items-center gap-1">
                <Search className="h-2.5 w-2.5" />
                Источник: KB-2024-0089 (совпадение 97%)
              </p>
            </div>
          </motion.div>
        )}
      </AnimatePresence>

      {/* Task Created */}
      <AnimatePresence>
        {showTask && (
          <motion.div
            initial={{ opacity: 0, scale: 0.9 }}
            animate={{ opacity: 1, scale: 1 }}
            transition={{ type: "spring", stiffness: 400, damping: 25 }}
            className="glass-card p-3 border-success/20"
          >
            <div className="mb-2 flex items-center gap-2">
              <CheckCircle2 className="h-3.5 w-3.5 text-success" />
              <span className="text-[10px] font-semibold uppercase tracking-wider text-success">
                Задача создана
              </span>
            </div>
            <div className="space-y-1.5 text-xs">
              <div className="flex justify-between">
                <span className="text-text-muted">ID:</span>
                <span className="font-mono text-is-blue">#T-2024-0147</span>
              </div>
              <div className="flex justify-between">
                <span className="text-text-muted">CRM:</span>
                <span className="text-text-secondary">Sakura CRM</span>
              </div>
              <div className="flex justify-between">
                <span className="text-text-muted">Приоритет:</span>
                <span className="text-warning font-medium">Высокий</span>
              </div>
              <div className="flex justify-between">
                <span className="text-text-muted">Исполнитель:</span>
                <span className="text-text-secondary">Группа ЗУП</span>
              </div>
              <div className="flex justify-between">
                <span className="text-text-muted">SLA до:</span>
                <span className="text-success font-medium">14:30 сегодня</span>
              </div>
            </div>
          </motion.div>
        )}
      </AnimatePresence>
    </div>
  );
}
