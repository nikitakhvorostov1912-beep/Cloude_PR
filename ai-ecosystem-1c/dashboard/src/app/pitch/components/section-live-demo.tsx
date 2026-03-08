"use client";

import { useRef } from "react";
import { motion, useInView } from "framer-motion";
import { AnimatedGradientText } from "@/components/animated-gradient-text";
import { DemoSimulator } from "./demo-simulator";

export function SectionLiveDemo() {
  const ref = useRef(null);
  const isInView = useInView(ref, { once: true, margin: "-50px" });

  return (
    <section id="live-demo" className="pitch-section">
      <div ref={ref} className="pitch-section-inner">
        <motion.div
          initial={{ opacity: 0, y: 30 }}
          animate={isInView ? { opacity: 1, y: 0 } : {}}
          transition={{ type: "spring", stiffness: 300, damping: 24 }}
          className="mb-6 text-center"
        >
          <p className="mb-2 text-xs font-bold uppercase tracking-[0.2em] text-is-blue">
            Интерактивная демонстрация
          </p>
          <h2 className="mb-3 text-4xl font-bold">
            <AnimatedGradientText>Live Demo</AnimatedGradientText>
          </h2>
          <p className="mx-auto max-w-2xl text-base text-text-muted leading-relaxed">
            Полная симуляция звонка в техподдержку — от первого слова клиента
            до решения проблемы. AI-суфлёр работает в реальном времени.
          </p>
        </motion.div>

        <motion.div
          initial={{ opacity: 0, y: 40, scale: 0.97 }}
          animate={isInView ? { opacity: 1, y: 0, scale: 1 } : {}}
          transition={{ type: "spring", stiffness: 180, damping: 20, delay: 0.15 }}
        >
          <DemoSimulator />
        </motion.div>
      </div>
    </section>
  );
}
