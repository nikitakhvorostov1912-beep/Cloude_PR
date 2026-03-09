"use client";

import { useRef } from "react";
import { motion, useInView } from "framer-motion";
import { Rocket, Users, Calendar, Banknote } from "lucide-react";
import { AnimatedGradientText } from "@/components/animated-gradient-text";
import { MagneticButton } from "@/components/magnetic-button";
import { GlowCard } from "@/components/glow-card";
import { staggerContainer, staggerItem } from "@/lib/motion";

const BUDGET_ITEMS = [
  {
    icon: Banknote,
    label: "Бюджет MVP",
    value: "от 2.5M руб",
    color: "text-success",
  },
  {
    icon: Calendar,
    label: "Срок",
    value: "8 недель",
    color: "text-is-blue",
  },
  {
    icon: Users,
    label: "Команда",
    value: "4 специалиста",
    color: "text-aurora-purple",
  },
  {
    icon: Rocket,
    label: "Окупаемость",
    value: "4 месяца",
    color: "text-warning",
  },
];

export function SectionCTA() {
  const ref = useRef(null);
  const isInView = useInView(ref, { once: true, margin: "-100px" });

  return (
    <section id="cta" className="pitch-section">
      <div ref={ref} className="pitch-section-inner text-center">
        <motion.div
          variants={staggerContainer}
          initial="hidden"
          animate={isInView ? "show" : "hidden"}
          className="flex flex-col items-center"
        >
          <motion.h2
            variants={staggerItem}
            className="mb-4 text-5xl font-bold"
          >
            <AnimatedGradientText>Готовы начать?</AnimatedGradientText>
          </motion.h2>

          <motion.p
            variants={staggerItem}
            className="mb-10 max-w-xl text-lg text-text-muted"
          >
            Запустите пилотный проект Аврора и увидите результат за 8 недель.
            Без рисков — начинаем с MVP на 5 операторов.
          </motion.p>

          {/* Budget cards */}
          <motion.div
            variants={staggerItem}
            className="mb-10 grid grid-cols-2 gap-4 lg:grid-cols-4"
          >
            {BUDGET_ITEMS.map((item) => (
              <GlowCard key={item.label} className="p-4 text-center">
                <item.icon
                  className={`mx-auto mb-2 h-6 w-6 ${item.color}`}
                />
                <p className="text-sm font-bold text-text-primary">
                  {item.value}
                </p>
                <p className="text-xs text-text-muted">{item.label}</p>
              </GlowCard>
            ))}
          </motion.div>

          {/* Team breakdown */}
          <motion.div
            variants={staggerItem}
            className="mb-10 max-w-lg"
          >
            <GlowCard className="p-5">
              <h3 className="mb-3 text-sm font-semibold uppercase tracking-wide text-text-secondary">
                Состав команды
              </h3>
              <div className="grid grid-cols-2 gap-3 text-sm">
                <div className="flex items-center gap-2">
                  <span className="h-2 w-2 rounded-full bg-is-blue" />
                  <span className="text-text-secondary">
                    2 Backend-разработчика
                  </span>
                </div>
                <div className="flex items-center gap-2">
                  <span className="h-2 w-2 rounded-full bg-aurora-purple" />
                  <span className="text-text-secondary">
                    1 ML-инженер
                  </span>
                </div>
                <div className="flex items-center gap-2">
                  <span className="h-2 w-2 rounded-full bg-warning" />
                  <span className="text-text-secondary">
                    1 Project Manager
                  </span>
                </div>
                <div className="flex items-center gap-2">
                  <span className="h-2 w-2 rounded-full bg-success" />
                  <span className="text-text-secondary">
                    Frontend (имеется)
                  </span>
                </div>
              </div>
            </GlowCard>
          </motion.div>

          {/* CTA Button */}
          <motion.div variants={staggerItem}>
            <MagneticButton
              onClick={() => {
                const el = document.getElementById("hero");
                if (el) el.scrollIntoView({ behavior: "smooth" });
              }}
              className="glow-blue bg-gradient-to-r from-is-blue to-aurora-purple px-10 py-4 text-lg font-bold text-white"
            >
              Запустить пилот
            </MagneticButton>
          </motion.div>

          <motion.p
            variants={staggerItem}
            className="mt-6 text-sm text-text-muted"
          >
            Аврора &bull; AI-суфлёр для 1С-франчайзи &bull; InterSoft
          </motion.p>
        </motion.div>
      </div>
    </section>
  );
}
