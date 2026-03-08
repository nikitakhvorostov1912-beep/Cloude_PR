"use client";

import { useRef, useState } from "react";
import { motion, useInView, AnimatePresence } from "framer-motion";
import {
  HelpCircle,
  Bug,
  MessageSquare,
  AlertTriangle,
  ChevronDown,
} from "lucide-react";
import { GlowCard } from "@/components/glow-card";
import { staggerContainer, staggerItem } from "@/lib/motion";

const SCENARIOS = [
  {
    id: "faq",
    icon: HelpCircle,
    title: "Простой вопрос",
    percent: 40,
    color: "text-success",
    borderColor: "border-success/20",
    bgColor: "bg-success/5",
    description: "Ответ из базы знаний без участия эксперта",
    steps: [
      "Распознавание ключевых слов в запросе",
      "Поиск в базе знаний (RAG) — совпадение > 90%",
      "Отображение готового ответа оператору",
      "Оператор зачитывает ответ клиенту",
      "Звонок закрывается автоматически",
    ],
    example: "«Как настроить учётную политику в БП 3.0?»",
  },
  {
    id: "error",
    icon: Bug,
    title: "Ошибка ПО",
    percent: 30,
    color: "text-warning",
    borderColor: "border-warning/20",
    bgColor: "bg-warning/5",
    description: "Классификация ошибки и создание задачи",
    steps: [
      "AI определяет: тип = ошибка, продукт = ЗУП/БП/УТ",
      "Поиск в KB — есть ли решение для этой ошибки",
      "Если найдено — подсказка оператору с пошаговым решением",
      "Создание задачи в Sakura CRM с логами и контекстом",
      "Назначение на профильную группу",
    ],
    example: "«После обновления не формируется отчёт по зарплате»",
  },
  {
    id: "consulting",
    icon: MessageSquare,
    title: "Консультация",
    percent: 20,
    color: "text-is-blue",
    borderColor: "border-is-blue/20",
    bgColor: "bg-is-blue/5",
    description: "AI подбирает контекст для оператора",
    steps: [
      "Определение продукта и модуля (ЗУП, БП, УТ, ERP)",
      "Анализ истории обращений клиента",
      "Подбор релевантной документации",
      "AI формирует набор подсказок по теме",
      "Оператор консультирует с поддержкой AI",
    ],
    example: "«Нужно настроить обмен между БП и ЗУП»",
  },
  {
    id: "escalation",
    icon: AlertTriangle,
    title: "Эскалация",
    percent: 10,
    color: "text-is-red",
    borderColor: "border-is-red/20",
    bgColor: "bg-is-red/5",
    description: "Сложный кейс → переключение на эксперта",
    steps: [
      "AI определяет: confidence < 60% или критичная ошибка",
      "Автоматический поиск свободного эксперта",
      "Переключение звонка с полным контекстом",
      "Уведомление менеджера в Telegram",
      "Создание задачи с пометкой «Эскалация»",
    ],
    example: "«Данные бухгалтерского учёта расходятся с налоговым»",
  },
];

function ScenarioCard({
  scenario,
}: {
  scenario: (typeof SCENARIOS)[number];
}) {
  const [isOpen, setIsOpen] = useState(false);

  return (
    <GlowCard className="p-0 overflow-hidden">
      <button
        onClick={() => setIsOpen(!isOpen)}
        className="flex w-full items-center gap-4 p-5 text-left transition-colors hover:bg-bg-elevated/30"
      >
        <div
          className={`flex h-12 w-12 shrink-0 items-center justify-center rounded-xl ${scenario.bgColor}`}
        >
          <scenario.icon className={`h-6 w-6 ${scenario.color}`} />
        </div>
        <div className="flex-1">
          <div className="flex items-center gap-2">
            <h4 className="text-sm font-semibold text-text-primary">
              {scenario.title}
            </h4>
            <span
              className={`rounded-full px-2 py-0.5 text-xs font-medium ${scenario.bgColor} ${scenario.color}`}
            >
              {scenario.percent}%
            </span>
          </div>
          <p className="text-xs text-text-muted">{scenario.description}</p>
        </div>
        <motion.div
          animate={{ rotate: isOpen ? 180 : 0 }}
          transition={{ duration: 0.2 }}
        >
          <ChevronDown className="h-5 w-5 text-text-muted" />
        </motion.div>
      </button>

      <AnimatePresence>
        {isOpen && (
          <motion.div
            initial={{ height: 0, opacity: 0 }}
            animate={{ height: "auto", opacity: 1 }}
            exit={{ height: 0, opacity: 0 }}
            transition={{ type: "spring", stiffness: 300, damping: 30 }}
            className="overflow-hidden"
          >
            <div
              className={`border-t ${scenario.borderColor} px-5 pb-5 pt-4`}
            >
              {/* Example */}
              <div className="mb-4 rounded-xl bg-bg-elevated/50 px-4 py-3">
                <p className="text-xs text-text-muted">Пример обращения:</p>
                <p className="text-sm italic text-text-secondary">
                  {scenario.example}
                </p>
              </div>

              {/* Steps */}
              <div className="space-y-2">
                {scenario.steps.map((step, i) => (
                  <motion.div
                    key={i}
                    initial={{ opacity: 0, x: -10 }}
                    animate={{ opacity: 1, x: 0 }}
                    transition={{ delay: i * 0.1 }}
                    className="flex items-start gap-3"
                  >
                    <span
                      className={`mt-0.5 flex h-5 w-5 shrink-0 items-center justify-center rounded-full text-[10px] font-bold ${scenario.bgColor} ${scenario.color}`}
                    >
                      {i + 1}
                    </span>
                    <p className="text-sm text-text-secondary">{step}</p>
                  </motion.div>
                ))}
              </div>
            </div>
          </motion.div>
        )}
      </AnimatePresence>
    </GlowCard>
  );
}

export function SectionScenarios() {
  const ref = useRef(null);
  const isInView = useInView(ref, { once: true, margin: "-100px" });

  return (
    <section id="scenarios" className="pitch-section">
      <div ref={ref} className="pitch-section-inner">
        <motion.div
          initial={{ opacity: 0, y: 30 }}
          animate={isInView ? { opacity: 1, y: 0 } : {}}
          transition={{ type: "spring", stiffness: 300, damping: 24 }}
          className="mb-12 text-center"
        >
          <h2 className="mb-3 text-4xl font-bold text-text-primary">
            Сценарии обработки
          </h2>
          <p className="mx-auto max-w-2xl text-lg text-text-muted">
            4 типа обращений — каждый с оптимальным маршрутом обработки
          </p>
        </motion.div>

        <motion.div
          variants={staggerContainer}
          initial="hidden"
          animate={isInView ? "show" : "hidden"}
          className="mx-auto max-w-3xl space-y-4"
        >
          {SCENARIOS.map((scenario) => (
            <motion.div key={scenario.id} variants={staggerItem}>
              <ScenarioCard scenario={scenario} />
            </motion.div>
          ))}
        </motion.div>
      </div>
    </section>
  );
}
