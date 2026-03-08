"use client";

import { useState } from "react";
import { motion } from "framer-motion";
import { Phone, Clock, User, Package } from "lucide-react";
import { ConfidenceBadge } from "@/components/confidence-badge";
import {
  TranscriptViewer,
  type TranscriptMessage,
} from "@/components/transcript-viewer";
import { GlowCard } from "@/components/glow-card";
import { MagneticButton } from "@/components/magnetic-button";
import { PageWrapper } from "@/components/page-wrapper";
import { staggerContainer, staggerItem } from "@/lib/motion";
import { toast } from "sonner";

// Demo transcript
const DEMO_MESSAGES: TranscriptMessage[] = [
  {
    id: "1",
    speaker: "operator",
    text: "Здравствуйте! Вы позвонили в службу технической поддержки. Чем могу помочь?",
    timestamp: "10:30:05",
  },
  {
    id: "2",
    speaker: "client",
    text: "Здравствуйте, у нас ошибка при формировании отчёта по зарплате в ЗУП. Пишет что-то про неверный период.",
    timestamp: "10:30:15",
    tags: ["ошибка", "ЗУП"],
  },
  {
    id: "3",
    speaker: "operator",
    text: "Понял, ошибка в отчёте по зарплате. Подскажите, какую версию ЗУП вы используете?",
    timestamp: "10:30:25",
  },
  {
    id: "4",
    speaker: "client",
    text: "Версия 3.1.28. Ошибка появилась после обновления на прошлой неделе. До этого всё работало нормально.",
    timestamp: "10:30:40",
    tags: ["обновление", "версия"],
  },
];

const DEMO_CLASSIFICATION = {
  department: "Поддержка",
  department_confidence: 0.92,
  task_type: "error",
  task_type_confidence: 0.88,
  priority: "high",
  priority_confidence: 0.85,
  product: "ЗУП",
  product_confidence: 0.95,
};

export default function LivePage() {
  const [messages] = useState<TranscriptMessage[]>(DEMO_MESSAGES);
  const classification = DEMO_CLASSIFICATION;

  const [taskForm, setTaskForm] = useState({
    department: "support",
    priority: "high",
    product: "ЗУП",
    description:
      "Ошибка при формировании отчёта по зарплате после обновления до версии 3.1.28. Клиент сообщает о сообщении 'неверный период'.",
  });

  const handleCreateTask = () => {
    toast.success("Задача создана", {
      description: `${taskForm.description.slice(0, 60)}...`,
    });
  };

  return (
    <PageWrapper>
      <div className="flex h-[calc(100vh-3.5rem)] flex-col">
        {/* Top bar — client info */}
        <motion.header
          initial={{ opacity: 0, y: -20 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ type: "spring", stiffness: 300, damping: 24 }}
          className="glass-card mx-4 mt-4 flex items-center gap-6 rounded-2xl px-6 py-3"
        >
          <div className="flex items-center gap-2">
            <User className="h-4 w-4 text-is-blue" />
            <span className="text-sm font-medium text-text-primary">
              ООО Ромашка
            </span>
          </div>
          <div className="flex items-center gap-2">
            <Package className="h-4 w-4 text-text-muted" />
            <span className="text-sm text-text-secondary">ЗУП 3.1.28</span>
          </div>
          <div className="flex items-center gap-2">
            <Phone className="h-4 w-4 text-text-muted" />
            <span className="font-mono text-sm text-text-secondary">
              +7 (495) 123-45-67
            </span>
          </div>
          <div className="ml-auto flex items-center gap-2">
            <span className="pulse-live h-2 w-2 rounded-full bg-success" />
            <Clock className="h-4 w-4 text-text-muted" />
            <span className="font-mono text-sm text-text-secondary">04:25</span>
          </div>
        </motion.header>

        {/* Split view */}
        <div className="flex flex-1 overflow-hidden p-4 gap-4">
          {/* Left — Transcript (60%) */}
          <motion.div
            initial={{ opacity: 0, x: -20 }}
            animate={{ opacity: 1, x: 0 }}
            transition={{ type: "spring", stiffness: 300, damping: 24, delay: 0.1 }}
            className="glass-card flex-[3] overflow-hidden p-5"
          >
            <TranscriptViewer messages={messages} />
          </motion.div>

          {/* Right — AI Panel (40%) */}
          <motion.div
            variants={staggerContainer}
            initial="hidden"
            animate="show"
            className="flex flex-[2] flex-col gap-4 overflow-y-auto"
          >
            {/* Classification */}
            <motion.div variants={staggerItem}>
              <GlowCard className="p-4">
                <h3 className="mb-3 text-sm font-semibold text-text-secondary uppercase tracking-wide">
                  Классификация AI
                </h3>
                <div className="space-y-2.5">
                  <ConfidenceBadge label="Отдел" value={classification.department_confidence} />
                  <ConfidenceBadge label="Тип" value={classification.task_type_confidence} />
                  <ConfidenceBadge label="Приоритет" value={classification.priority_confidence} />
                  <ConfidenceBadge label="Продукт" value={classification.product_confidence} />
                </div>
              </GlowCard>
            </motion.div>

            {/* Routing decision */}
            <motion.div variants={staggerItem}>
              <GlowCard className="p-4">
                <h3 className="mb-3 text-sm font-semibold text-text-secondary uppercase tracking-wide">
                  Маршрутизация
                </h3>
                <div className="space-y-2 text-sm">
                  <div className="flex justify-between">
                    <span className="text-text-muted">Правило:</span>
                    <span className="text-is-blue font-medium font-mono">deterministic_error</span>
                  </div>
                  <div className="flex justify-between">
                    <span className="text-text-muted">LLM пропущен:</span>
                    <span className="text-success font-medium">Да</span>
                  </div>
                </div>
              </GlowCard>
            </motion.div>

            {/* Recommended actions */}
            <motion.div variants={staggerItem}>
              <GlowCard className="p-4">
                <h3 className="mb-3 text-sm font-semibold text-text-secondary uppercase tracking-wide">
                  Рекомендации
                </h3>
                <div className="space-y-2">
                  <div className="flex items-center justify-between rounded-xl bg-is-blue/10 px-3 py-2">
                    <span className="text-sm text-is-blue">Создать задачу</span>
                    <span className="font-mono text-sm font-semibold text-is-blue">94%</span>
                  </div>
                  <div className="flex items-center justify-between rounded-xl bg-bg-elevated px-3 py-2">
                    <span className="text-sm text-text-secondary">Эскалация</span>
                    <span className="font-mono text-sm text-text-muted">6%</span>
                  </div>
                </div>
              </GlowCard>
            </motion.div>

            {/* Task form */}
            <motion.div variants={staggerItem} className="mt-auto">
              <GlowCard glowColor="red" className="p-4">
                <h3 className="mb-3 text-sm font-semibold text-text-secondary uppercase tracking-wide">
                  Создание задачи
                </h3>

                <div className="space-y-3">
                  <div className="grid grid-cols-2 gap-3">
                    <select
                      value={taskForm.department}
                      onChange={(e) =>
                        setTaskForm({ ...taskForm, department: e.target.value })
                      }
                      className="h-9 rounded-xl border border-border-subtle bg-surface-1 px-3 text-sm text-text-primary outline-none focus:border-is-blue/30 focus:shadow-[0_0_15px_rgba(125,190,244,0.06)]"
                    >
                      <option value="support">Поддержка</option>
                      <option value="development">Разработка</option>
                      <option value="implementation">Внедрение</option>
                      <option value="presale">Пресейл</option>
                    </select>

                    <select
                      value={taskForm.priority}
                      onChange={(e) =>
                        setTaskForm({ ...taskForm, priority: e.target.value })
                      }
                      className="h-9 rounded-xl border border-border-subtle bg-surface-1 px-3 text-sm text-text-primary outline-none focus:border-is-blue/30 focus:shadow-[0_0_15px_rgba(125,190,244,0.06)]"
                    >
                      <option value="critical">Критичный</option>
                      <option value="high">Высокий</option>
                      <option value="normal">Обычный</option>
                      <option value="low">Низкий</option>
                    </select>
                  </div>

                  <textarea
                    value={taskForm.description}
                    onChange={(e) =>
                      setTaskForm({ ...taskForm, description: e.target.value })
                    }
                    rows={3}
                    className="w-full rounded-xl border border-border-subtle bg-surface-1 px-3 py-2 text-sm text-text-primary outline-none resize-none placeholder:text-text-muted focus:border-is-blue/30 focus:shadow-[0_0_15px_rgba(125,190,244,0.06)]"
                    placeholder="Описание задачи..."
                  />

                  <MagneticButton
                    onClick={handleCreateTask}
                    className="glow-red w-full bg-gradient-to-r from-is-red to-is-red-hover px-4 py-2.5 text-sm text-white"
                  >
                    Создать задачу
                  </MagneticButton>
                </div>
              </GlowCard>
            </motion.div>
          </motion.div>
        </div>
      </div>
    </PageWrapper>
  );
}
