"use client";

import { useRef } from "react";
import { motion, useInView } from "framer-motion";
import { Rocket, Cog, Sparkles } from "lucide-react";
import { GlowCard } from "@/components/glow-card";
import { staggerContainer, staggerItem } from "@/lib/motion";

const PHASES = [
  {
    phase: 1,
    icon: Rocket,
    title: "MVP",
    weeks: "1-8 неделя",
    status: "active" as const,
    color: "text-is-blue",
    deliverables: [
      "Интеграция Mango Office (входящие звонки)",
      "Yandex STT — real-time транскрипция",
      "Базовая классификация (отдел + продукт)",
      "Маршрутизация по правилам (Rules Engine)",
      "Dashboard — KPI, звонки, live-панель",
      "Развёртывание на тестовом контуре",
    ],
    metric: "Proof of Concept для 5 операторов",
  },
  {
    phase: 2,
    icon: Cog,
    title: "Автоматизация",
    weeks: "9-16 неделя",
    status: "pending" as const,
    color: "text-aurora-purple",
    deliverables: [
      "RAG Agent — база знаний + vector search",
      "Авто-создание задач в Sakura CRM",
      "LLM-классификация (Claude / GigaChat)",
      "Интеграция с 1С HTTP-сервисами",
      "Telegram/SMS уведомления",
      "Обучение модели на реальных данных",
    ],
    metric: "50% задач создаются автоматически",
  },
  {
    phase: 3,
    icon: Sparkles,
    title: "AI-суфлёр",
    weeks: "17-24 неделя",
    status: "pending" as const,
    color: "text-warning",
    deliverables: [
      "Real-time подсказки оператору из KB + RAG",
      "Advisor Agent — контекстные рекомендации",
      "Memory Agent — история взаимодействий",
      "Мониторинг качества (Monitoring Agent)",
      "Аналитика и отчёты для руководства",
      "Масштабирование на весь call-центр",
    ],
    metric: "Полноценный AI-суфлёр для 15+ операторов",
  },
];

export function SectionRoadmap() {
  const ref = useRef(null);
  const isInView = useInView(ref, { once: true, margin: "-100px" });

  return (
    <section id="roadmap" className="pitch-section">
      <div ref={ref} className="pitch-section-inner">
        <motion.div
          initial={{ opacity: 0, y: 30 }}
          animate={isInView ? { opacity: 1, y: 0 } : {}}
          transition={{ type: "spring", stiffness: 300, damping: 24 }}
          className="mb-12 text-center"
        >
          <h2 className="mb-3 text-4xl font-bold text-text-primary">
            Дорожная карта
          </h2>
          <p className="mx-auto max-w-2xl text-lg text-text-muted">
            3 фазы, 24 недели — от MVP до полноценного AI-суфлёра
          </p>
        </motion.div>

        {/* Timeline */}
        <motion.div
          variants={staggerContainer}
          initial="hidden"
          animate={isInView ? "show" : "hidden"}
          className="relative mx-auto max-w-4xl"
        >
          {/* Vertical line */}
          <div className="absolute left-6 top-0 bottom-0 w-0.5 bg-gradient-to-b from-is-blue/30 via-aurora-purple/30 to-warning/30 lg:left-1/2 lg:-translate-x-px" />

          <div className="space-y-8">
            {PHASES.map((phase, i) => (
              <motion.div
                key={phase.phase}
                variants={staggerItem}
                className={`relative flex gap-6 lg:gap-12 ${
                  i % 2 === 1 ? "lg:flex-row-reverse" : ""
                }`}
              >
                {/* Dot on timeline */}
                <div className="absolute left-6 lg:left-1/2 lg:-translate-x-1/2 z-10">
                  <div
                    className={`timeline-dot ${
                      phase.status === "active" ? "active" : ""
                    }`}
                  />
                </div>

                {/* Spacer for mobile */}
                <div className="w-12 shrink-0 lg:hidden" />

                {/* Card */}
                <div className="flex-1 lg:w-[calc(50%-3rem)]">
                  <GlowCard
                    glowColor={phase.status === "active" ? "blue" : undefined}
                    className="p-5"
                  >
                    <div className="mb-3 flex items-center gap-3">
                      <div className="flex h-10 w-10 items-center justify-center rounded-xl bg-bg-elevated">
                        <phase.icon className={`h-5 w-5 ${phase.color}`} />
                      </div>
                      <div>
                        <h4 className="text-sm font-semibold text-text-primary">
                          Фаза {phase.phase} — {phase.title}
                        </h4>
                        <p className="text-xs text-text-muted">{phase.weeks}</p>
                      </div>
                      {phase.status === "active" && (
                        <span className="ml-auto rounded-full bg-is-blue/10 px-2.5 py-0.5 text-xs font-medium text-is-blue">
                          Текущая
                        </span>
                      )}
                    </div>

                    <ul className="mb-3 space-y-1.5">
                      {phase.deliverables.map((d) => (
                        <li
                          key={d}
                          className="flex items-start gap-2 text-sm text-text-secondary"
                        >
                          <span className={`mt-1.5 h-1.5 w-1.5 shrink-0 rounded-full ${
                            phase.status === "active" ? "bg-is-blue" : "bg-text-muted"
                          }`} />
                          {d}
                        </li>
                      ))}
                    </ul>

                    <div className="rounded-lg bg-bg-elevated/50 px-3 py-2">
                      <p className="text-xs font-medium text-is-blue">
                        {phase.metric}
                      </p>
                    </div>
                  </GlowCard>
                </div>

                {/* Spacer for desktop alignment */}
                <div className="hidden flex-1 lg:block lg:w-[calc(50%-3rem)]" />
              </motion.div>
            ))}
          </div>
        </motion.div>
      </div>
    </section>
  );
}
