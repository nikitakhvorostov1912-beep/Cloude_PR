"use client";

import { motion } from "framer-motion";
import { AuroraLogo } from "@/components/aurora-logo";
import { AnimatedGradientText } from "@/components/animated-gradient-text";
import { MagneticButton } from "@/components/magnetic-button";
import { staggerContainer, staggerItem } from "@/lib/motion";
import { ChevronDown } from "lucide-react";

export function SectionHero() {
  const scrollToDemo = () => {
    const el = document.getElementById("live-demo");
    if (el) el.scrollIntoView({ behavior: "smooth" });
  };

  return (
    <section id="hero" className="pitch-section">
      <motion.div
        variants={staggerContainer}
        initial="hidden"
        animate="show"
        className="pitch-section-inner flex flex-col items-center text-center"
      >
        <motion.div variants={staggerItem} className="mb-8">
          <AuroraLogo size="lg" />
        </motion.div>

        <motion.h1
          variants={staggerItem}
          className="mb-4 text-6xl font-bold tracking-tight md:text-7xl"
        >
          <AnimatedGradientText>Аврора</AnimatedGradientText>
        </motion.h1>

        <motion.p
          variants={staggerItem}
          className="mb-3 text-xl text-text-secondary md:text-2xl"
        >
          AI-суфлёр для 1С-франчайзи
        </motion.p>

        <motion.p
          variants={staggerItem}
          className="mb-12 max-w-xl text-lg text-text-muted"
        >
          Каждый звонок — точное решение. Распознавание речи, мгновенная
          классификация и подсказки оператору в реальном времени.
        </motion.p>

        <motion.div variants={staggerItem}>
          <MagneticButton
            onClick={scrollToDemo}
            className="glow-blue bg-gradient-to-r from-is-blue to-aurora-purple px-8 py-4 text-lg font-semibold text-white"
          >
            Смотреть демо
          </MagneticButton>
        </motion.div>

        {/* Scroll indicator */}
        <motion.div
          initial={{ opacity: 0 }}
          animate={{ opacity: 1 }}
          transition={{ delay: 1.5 }}
          className="absolute bottom-8"
        >
          <motion.div
            animate={{ y: [0, 8, 0] }}
            transition={{ duration: 2, repeat: Infinity, ease: "easeInOut" }}
          >
            <ChevronDown className="h-6 w-6 text-text-muted" />
          </motion.div>
        </motion.div>
      </motion.div>
    </section>
  );
}
