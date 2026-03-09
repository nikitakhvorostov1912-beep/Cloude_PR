"use client";

import { useRef } from "react";
import { motion, useInView } from "framer-motion";
import { Clock, RotateCcw, Timer, TrendingDown } from "lucide-react";
import { GlowCard } from "@/components/glow-card";
import { AnimatedCounter } from "@/components/animated-counter";
import { staggerContainer, staggerItem } from "@/lib/motion";

const PAIN_POINTS = [
  {
    icon: Clock,
    value: 67,
    suffix: "%",
    label: "времени на поиск",
    description: "Оператор тратит на поиск решения вместо помощи клиенту",
    color: "text-error",
  },
  {
    icon: RotateCcw,
    value: 35,
    suffix: "%",
    label: "повторных звонков",
    description: "Из-за неверной маршрутизации и неточных ответов",
    color: "text-warning",
  },
  {
    icon: Timer,
    value: 12,
    suffix: " мин",
    label: "время обработки",
    description: "Среднее время на один звонок, можно сократить до 4 минут",
    color: "text-is-blue",
  },
  {
    icon: TrendingDown,
    value: 2.8,
    suffix: "M",
    prefix: "₽",
    label: "потери в год",
    description: "На эскалациях, повторных обращениях и простоях",
    color: "text-is-red",
  },
];

export function SectionProblem() {
  const ref = useRef(null);
  const isInView = useInView(ref, { once: true, margin: "-100px" });

  return (
    <section id="problem" className="pitch-section">
      <div ref={ref} className="pitch-section-inner">
        <motion.div
          initial={{ opacity: 0, y: 30 }}
          animate={isInView ? { opacity: 1, y: 0 } : {}}
          transition={{ type: "spring", stiffness: 300, damping: 24 }}
          className="mb-12 text-center"
        >
          <h2 className="mb-3 text-4xl font-bold text-text-primary">
            Проблема
          </h2>
          <p className="mx-auto max-w-2xl text-lg text-text-muted">
            Типичный call-центр 1С-франчайзи теряет до 30% эффективности
            из-за ручной маршрутизации и отсутствия подсказок
          </p>
        </motion.div>

        <motion.div
          variants={staggerContainer}
          initial="hidden"
          animate={isInView ? "show" : "hidden"}
          className="grid grid-cols-1 gap-6 sm:grid-cols-2 lg:grid-cols-4"
        >
          {PAIN_POINTS.map((point) => (
            <motion.div key={point.label} variants={staggerItem}>
              <GlowCard glowColor="error" className="p-6 text-center">
                <point.icon className={`mx-auto mb-4 h-8 w-8 ${point.color}`} />
                <div className="mb-2 flex items-baseline justify-center gap-1">
                  {point.prefix && (
                    <span className="text-3xl font-bold text-text-primary">
                      {point.prefix}
                    </span>
                  )}
                  {isInView && (
                    <AnimatedCounter
                      value={point.value}
                      className="text-3xl font-bold text-text-primary"
                    />
                  )}
                  <span className="text-xl font-semibold text-text-secondary">
                    {point.suffix}
                  </span>
                </div>
                <p className="mb-1 text-sm font-semibold uppercase tracking-wide text-text-secondary">
                  {point.label}
                </p>
                <p className="text-xs text-text-muted">{point.description}</p>
              </GlowCard>
            </motion.div>
          ))}
        </motion.div>
      </div>
    </section>
  );
}
