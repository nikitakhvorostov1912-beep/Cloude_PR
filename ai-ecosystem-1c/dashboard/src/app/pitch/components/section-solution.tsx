"use client";

import { useRef } from "react";
import { motion, useInView } from "framer-motion";
import { Mic, Brain, Zap } from "lucide-react";
import { GlowCard } from "@/components/glow-card";
import { staggerContainer, staggerItem } from "@/lib/motion";

const FEATURES = [
  {
    icon: Mic,
    title: "Распознавание речи",
    description:
      "Real-time транскрипция через Yandex SpeechKit. Автоматическое определение тем, продуктов и тегов из разговора.",
    detail: "Точность 95%+ для русского языка",
    color: "text-is-blue",
    glow: "navy" as const,
  },
  {
    icon: Brain,
    title: "AI-классификация",
    description:
      "Мгновенное определение отдела, продукта, приоритета и типа обращения. Маршрутизация по правилам + LLM.",
    detail: "< 2 секунды на классификацию",
    color: "text-aurora-purple",
    glow: "blue" as const,
  },
  {
    icon: Zap,
    title: "Автоматизация",
    description:
      "Создание задач в Sakura CRM, подсказки оператору из базы знаний, автоматическая эскалация критичных кейсов.",
    detail: "80% задач создаются автоматически",
    color: "text-success",
    glow: "success" as const,
  },
];

export function SectionSolution() {
  const ref = useRef(null);
  const isInView = useInView(ref, { once: true, margin: "-100px" });

  return (
    <section id="solution" className="pitch-section">
      <div ref={ref} className="pitch-section-inner">
        <motion.div
          initial={{ opacity: 0, y: 30 }}
          animate={isInView ? { opacity: 1, y: 0 } : {}}
          transition={{ type: "spring", stiffness: 300, damping: 24 }}
          className="mb-12 text-center"
        >
          <h2 className="mb-3 text-4xl font-bold text-text-primary">
            Решение
          </h2>
          <p className="mx-auto max-w-2xl text-lg text-text-muted">
            Аврора — AI-суфлёр, который слушает, понимает и подсказывает
            оператору в реальном времени
          </p>
        </motion.div>

        <motion.div
          variants={staggerContainer}
          initial="hidden"
          animate={isInView ? "show" : "hidden"}
          className="grid grid-cols-1 gap-6 lg:grid-cols-3"
        >
          {FEATURES.map((feature) => (
            <motion.div key={feature.title} variants={staggerItem}>
              <GlowCard glowColor={feature.glow} className="p-6 h-full">
                <div className="mb-4 flex items-center gap-3">
                  <div className="flex h-12 w-12 items-center justify-center rounded-xl bg-bg-elevated">
                    <feature.icon className={`h-6 w-6 ${feature.color}`} />
                  </div>
                  <h3 className="text-lg font-semibold text-text-primary">
                    {feature.title}
                  </h3>
                </div>
                <p className="mb-4 text-sm leading-relaxed text-text-secondary">
                  {feature.description}
                </p>
                <div className="rounded-lg bg-bg-elevated/50 px-3 py-2">
                  <p className="text-xs font-medium text-is-blue">
                    {feature.detail}
                  </p>
                </div>
              </GlowCard>
            </motion.div>
          ))}
        </motion.div>
      </div>
    </section>
  );
}
