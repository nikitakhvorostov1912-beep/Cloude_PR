"use client";

import { type ReactNode } from "react";
import { motion } from "framer-motion";
import Tilt from "react-parallax-tilt";
import { cn } from "@/lib/utils";

interface GlowCardProps {
  children: ReactNode;
  tilt?: boolean;
  className?: string;
  glowColor?: "navy" | "red" | "blue" | "success" | "error";
}

const GLOW_HOVER = {
  navy: "hover:shadow-[0_0_30px_rgba(28,20,117,0.25),0_0_60px_rgba(28,20,117,0.08)]",
  red: "hover:shadow-[0_0_30px_rgba(255,33,36,0.2),0_0_60px_rgba(255,33,36,0.06)]",
  blue: "hover:shadow-[0_0_30px_rgba(125,190,244,0.2),0_0_60px_rgba(125,190,244,0.06)]",
  success: "hover:shadow-[0_0_30px_rgba(34,197,94,0.2),0_0_60px_rgba(34,197,94,0.06)]",
  error: "hover:shadow-[0_0_30px_rgba(239,68,68,0.2),0_0_60px_rgba(239,68,68,0.06)]",
};

/**
 * GlowCard — dark glassmorphism card with rotating gradient borders.
 * The rotating conic-gradient border is handled by .glass-card CSS.
 * Hover intensifies the glow. Optional react-parallax-tilt wrapper.
 */
export function GlowCard({
  children,
  tilt = false,
  className,
  glowColor = "navy",
}: GlowCardProps) {
  const card = (
    <motion.div
      whileHover={{ scale: 1.015 }}
      transition={{ type: "spring", stiffness: 400, damping: 30 }}
      className={cn(
        "glass-card overflow-hidden transition-all duration-300",
        GLOW_HOVER[glowColor],
        className
      )}
    >
      {children}
    </motion.div>
  );

  if (!tilt) return card;

  return (
    <Tilt
      tiltMaxAngleX={8}
      tiltMaxAngleY={8}
      glareEnable
      glareMaxOpacity={0.08}
      glareColor="#7DBEF4"
      glareBorderRadius="16px"
      perspective={1000}
      transitionSpeed={400}
    >
      {card}
    </Tilt>
  );
}
