"use client";

import { useEffect, useRef } from "react";
import { motion, useMotionValue, useSpring, useTransform } from "framer-motion";

interface AnimatedCounterProps {
  value: number;
  format?: "number" | "percent" | "duration";
  className?: string;
}

function formatDisplay(value: number, format: string): string {
  switch (format) {
    case "percent":
      return `${Math.round(value * 100)}%`;
    case "duration": {
      const m = Math.floor(value / 60);
      const s = Math.round(value % 60);
      return `${m}:${s.toString().padStart(2, "0")}`;
    }
    default:
      return Math.round(value).toLocaleString("ru-RU");
  }
}

export function AnimatedCounter({
  value,
  format = "number",
  className,
}: AnimatedCounterProps) {
  const motionValue = useMotionValue(0);
  const spring = useSpring(motionValue, { stiffness: 500, damping: 35 });
  const display = useTransform(spring, (v) => formatDisplay(v, format));
  const ref = useRef<HTMLSpanElement>(null);

  useEffect(() => {
    motionValue.set(value);
  }, [value, motionValue]);

  useEffect(() => {
    const unsubscribe = display.on("change", (v) => {
      if (ref.current) {
        ref.current.textContent = v;
      }
    });
    return unsubscribe;
  }, [display]);

  return (
    <motion.span
      ref={ref}
      className={className}
      initial={{ opacity: 0, y: 8 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ type: "spring", stiffness: 300, damping: 24 }}
    >
      {formatDisplay(value, format)}
    </motion.span>
  );
}
