"use client";

import { motion } from "framer-motion";
import type { DemoPhase } from "./demo-ai-panel";

const PHASE_META: Record<DemoPhase, { step: number; label: string }> = {
  idle:              { step: 0,  label: "Ожидание запуска" },
  ringing:           { step: 1,  label: "Входящий звонок..." },
  greeting:          { step: 2,  label: "Оператор приветствует клиента" },
  client_problem:    { step: 3,  label: "Клиент описывает проблему" },
  ai_scanning:       { step: 4,  label: "AI анализирует эмоции и контекст" },
  ai_classifying:    { step: 5,  label: "AI классифицирует обращение" },
  operator_clarifies:{ step: 6,  label: "Оператор уточняет детали" },
  client_details:    { step: 7,  label: "Клиент предоставляет информацию" },
  ai_deep_analysis:  { step: 8,  label: "AI глубокий анализ проблемы" },
  ai_kb_search:      { step: 9,  label: "Поиск в базе знаний" },
  ai_suggests:       { step: 10, label: "AI формирует решение" },
  operator_resolves: { step: 11, label: "Оператор озвучивает решение" },
  task_creating:     { step: 12, label: "Создание задачи в CRM" },
  client_confirms:   { step: 13, label: "Клиент подтверждает решение" },
  summary:           { step: 14, label: "Демонстрация завершена" },
};

const TOTAL_STEPS = 14;

interface DemoProgressProps {
  phase: DemoPhase;
}

export function DemoProgress({ phase }: DemoProgressProps) {
  const meta = PHASE_META[phase];
  const percent = (meta.step / TOTAL_STEPS) * 100;

  return (
    <div className="space-y-1.5">
      <div className="demo-progress-bar">
        <motion.div
          className="demo-progress-fill"
          animate={{ width: `${percent}%` }}
          transition={{ type: "spring", stiffness: 150, damping: 22 }}
        />
      </div>
      <div className="flex items-center justify-between text-[11px]">
        <span className="text-text-muted">{meta.label}</span>
        <span className="font-mono text-text-secondary">
          {meta.step}/{TOTAL_STEPS}
        </span>
      </div>
    </div>
  );
}
