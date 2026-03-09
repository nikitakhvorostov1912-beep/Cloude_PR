"use client";

import { useRef } from "react";
import { motion, useInView } from "framer-motion";
import {
  Phone,
  Mic,
  Tags,
  GitBranch,
  Lightbulb,
  ClipboardList,
  CheckCircle,
} from "lucide-react";
import { staggerContainer, staggerItem } from "@/lib/motion";

const FLOW_STEPS = [
  {
    icon: Phone,
    title: "Входящий звонок",
    description: "Mango Office передаёт звонок в систему",
    color: "text-is-blue",
    bg: "bg-is-blue/10",
  },
  {
    icon: Mic,
    title: "Транскрипция",
    description: "Yandex STT — real-time распознавание речи",
    color: "text-aurora-purple",
    bg: "bg-aurora-purple/10",
  },
  {
    icon: Tags,
    title: "Классификация",
    description: "RuBERT / Claude определяют тему и приоритет",
    color: "text-warning",
    bg: "bg-warning/10",
  },
  {
    icon: GitBranch,
    title: "Маршрутизация",
    description: "Rules Engine направляет к нужному отделу",
    color: "text-success",
    bg: "bg-success/10",
  },
  {
    icon: Lightbulb,
    title: "Подсказка",
    description: "RAG + База знаний — рекомендация оператору",
    color: "text-is-blue-light",
    bg: "bg-is-blue-light/10",
  },
  {
    icon: ClipboardList,
    title: "Задача",
    description: "Автоматическое создание задачи в Sakura CRM",
    color: "text-is-red",
    bg: "bg-is-red/10",
  },
  {
    icon: CheckCircle,
    title: "Завершение",
    description: "Обратная связь, обучение модели, аналитика",
    color: "text-success",
    bg: "bg-success/10",
  },
];

export function SectionCallFlow() {
  const ref = useRef(null);
  const isInView = useInView(ref, { once: true, margin: "-100px" });

  return (
    <section id="call-flow" className="pitch-section">
      <div ref={ref} className="pitch-section-inner">
        <motion.div
          initial={{ opacity: 0, y: 30 }}
          animate={isInView ? { opacity: 1, y: 0 } : {}}
          transition={{ type: "spring", stiffness: 300, damping: 24 }}
          className="mb-12 text-center"
        >
          <h2 className="mb-3 text-4xl font-bold text-text-primary">
            Процесс обработки звонка
          </h2>
          <p className="mx-auto max-w-2xl text-lg text-text-muted">
            7 автоматических шагов от момента звонка до закрытия обращения
          </p>
        </motion.div>

        {/* Flow — Horizontal on desktop, vertical on mobile */}
        <motion.div
          variants={staggerContainer}
          initial="hidden"
          animate={isInView ? "show" : "hidden"}
          className="relative"
        >
          {/* Connection line (desktop) */}
          <div className="absolute left-0 right-0 top-[3.5rem] hidden h-0.5 bg-gradient-to-r from-transparent via-is-blue/20 to-transparent lg:block" />

          <div className="grid grid-cols-1 gap-4 sm:grid-cols-2 lg:grid-cols-7">
            {FLOW_STEPS.map((step, i) => (
              <motion.div
                key={step.title}
                variants={staggerItem}
                className="relative flex flex-col items-center text-center"
              >
                {/* Step number + icon */}
                <div
                  className={`relative z-10 mb-3 flex h-16 w-16 items-center justify-center rounded-2xl ${step.bg} border border-border-subtle`}
                >
                  <step.icon className={`h-7 w-7 ${step.color}`} />
                  <span className="absolute -right-1 -top-1 flex h-5 w-5 items-center justify-center rounded-full bg-bg-deepest text-[10px] font-bold text-text-secondary ring-1 ring-border-subtle">
                    {i + 1}
                  </span>
                </div>

                {/* Title */}
                <h4 className="mb-1 text-sm font-semibold text-text-primary">
                  {step.title}
                </h4>

                {/* Description */}
                <p className="text-xs leading-relaxed text-text-muted">
                  {step.description}
                </p>

                {/* Arrow connector (mobile) */}
                {i < FLOW_STEPS.length - 1 && (
                  <div className="my-2 text-text-muted lg:hidden">
                    <svg width="12" height="16" viewBox="0 0 12 16" fill="none">
                      <path d="M6 0V12M6 12L1 7M6 12L11 7" stroke="currentColor" strokeWidth="1.5" />
                    </svg>
                  </div>
                )}
              </motion.div>
            ))}
          </div>
        </motion.div>
      </div>
    </section>
  );
}
