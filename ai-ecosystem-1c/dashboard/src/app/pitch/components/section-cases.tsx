"use client";

import { useRef } from "react";
import { motion, useInView } from "framer-motion";
import { Building2, TrendingUp } from "lucide-react";
import { GlowCard } from "@/components/glow-card";
import { staggerContainer, staggerItem } from "@/lib/motion";

const CASES = [
  {
    company: "Сбер",
    metric: "1.3 трлн",
    metricLabel: "руб экономия за 5 лет",
    description:
      "AI-контактный центр на базе собственных LLM. Автоматизация 70% обращений, снижение AHT на 40%.",
    color: "text-success",
    bg: "bg-success/5",
  },
  {
    company: "Тинькофф",
    metric: "50M",
    metricLabel: "руб/мес экономия",
    description:
      "80% входящих обращений обрабатываются AI без участия оператора. NPS вырос на 12 пунктов.",
    color: "text-warning",
    bg: "bg-warning/5",
  },
  {
    company: "Ростелеком",
    metric: "7x",
    metricLabel: "ускорение обработки",
    description:
      "Внедрение AI-маршрутизации и автоклассификации. NPS +15 пунктов, FCR вырос на 20%.",
    color: "text-is-blue",
    bg: "bg-is-blue/5",
  },
  {
    company: "МТС",
    metric: "30%",
    metricLabel: "сокращение AHT",
    description:
      "AI-подсказки оператору в реальном времени. 25% рост first-call resolution, снижение эскалаций на 35%.",
    color: "text-aurora-purple",
    bg: "bg-aurora-purple/5",
  },
];

export function SectionCases() {
  const ref = useRef(null);
  const isInView = useInView(ref, { once: true, margin: "-100px" });

  return (
    <section id="cases" className="pitch-section">
      <div ref={ref} className="pitch-section-inner">
        <motion.div
          initial={{ opacity: 0, y: 30 }}
          animate={isInView ? { opacity: 1, y: 0 } : {}}
          transition={{ type: "spring", stiffness: 300, damping: 24 }}
          className="mb-12 text-center"
        >
          <h2 className="mb-3 text-4xl font-bold text-text-primary">
            Кейсы рынка
          </h2>
          <p className="mx-auto max-w-2xl text-lg text-text-muted">
            Российские компании уже внедрили AI в контактные центры
          </p>
        </motion.div>

        <motion.div
          variants={staggerContainer}
          initial="hidden"
          animate={isInView ? "show" : "hidden"}
          className="grid grid-cols-1 gap-6 sm:grid-cols-2"
        >
          {CASES.map((c) => (
            <motion.div key={c.company} variants={staggerItem}>
              <GlowCard className="p-6 h-full">
                <div className="mb-4 flex items-center gap-3">
                  <div className={`flex h-12 w-12 items-center justify-center rounded-xl ${c.bg}`}>
                    <Building2 className={`h-6 w-6 ${c.color}`} />
                  </div>
                  <h3 className="text-lg font-bold text-text-primary">
                    {c.company}
                  </h3>
                </div>

                {/* Key metric */}
                <div className="mb-4 flex items-baseline gap-2">
                  <TrendingUp className={`h-4 w-4 ${c.color}`} />
                  <span className={`text-2xl font-bold ${c.color}`}>
                    {c.metric}
                  </span>
                  <span className="text-sm text-text-muted">
                    {c.metricLabel}
                  </span>
                </div>

                <p className="text-sm leading-relaxed text-text-secondary">
                  {c.description}
                </p>
              </GlowCard>
            </motion.div>
          ))}
        </motion.div>

        <motion.p
          initial={{ opacity: 0 }}
          animate={isInView ? { opacity: 1 } : {}}
          transition={{ delay: 0.8 }}
          className="mt-8 text-center text-sm text-text-muted"
        >
          Аврора адаптирует проверенные подходы лидеров рынка для масштаба 1С-франчайзи
        </motion.p>
      </div>
    </section>
  );
}
