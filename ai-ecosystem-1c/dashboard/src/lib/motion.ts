import type { Transition, Variants } from "framer-motion";

/* ── Spring Presets ─────────────────────────────── */
export const SPRING = {
  snappy: { type: "spring", stiffness: 400, damping: 25 } as Transition,
  gentle: { type: "spring", stiffness: 150, damping: 20, mass: 0.8 } as Transition,
  bouncy: { type: "spring", stiffness: 300, damping: 10 } as Transition,
  numeric: { type: "spring", stiffness: 500, damping: 35 } as Transition,
  heavy: { type: "spring", stiffness: 100, damping: 30, mass: 2 } as Transition,
  instant: { type: "spring", stiffness: 500, damping: 30 } as Transition,
};

/* ── Stagger Container ──────────────────────────── */
export const staggerContainer: Variants = {
  hidden: { opacity: 0 },
  show: {
    opacity: 1,
    transition: {
      staggerChildren: 0.08,
      delayChildren: 0.1,
    },
  },
};

/* ── Stagger Item ───────────────────────────────── */
export const staggerItem: Variants = {
  hidden: { opacity: 0, y: 24, scale: 0.96 },
  show: {
    opacity: 1,
    y: 0,
    scale: 1,
    transition: { type: "spring", stiffness: 300, damping: 24 },
  },
};

/* ── Fade In Up ─────────────────────────────────── */
export const fadeInUp: Variants = {
  hidden: { opacity: 0, y: 20 },
  show: {
    opacity: 1,
    y: 0,
    transition: { type: "spring", stiffness: 300, damping: 24 },
  },
};

/* ── Scale In ───────────────────────────────────── */
export const scaleIn: Variants = {
  hidden: { opacity: 0, scale: 0.9 },
  show: {
    opacity: 1,
    scale: 1,
    transition: { type: "spring", stiffness: 400, damping: 25 },
  },
};

/* ── Page Transition ────────────────────────────── */
export const pageTransition: Variants = {
  initial: { opacity: 0, y: 12, filter: "blur(4px)" },
  animate: {
    opacity: 1,
    y: 0,
    filter: "blur(0px)",
    transition: { type: "spring", stiffness: 300, damping: 24, mass: 0.8 },
  },
  exit: {
    opacity: 0,
    y: -8,
    filter: "blur(4px)",
    transition: { duration: 0.15, ease: "easeIn" },
  },
};

/* ── Slide In Variants ──────────────────────────── */
export const slideInLeft: Variants = {
  hidden: { opacity: 0, x: -30 },
  show: {
    opacity: 1,
    x: 0,
    transition: { type: "spring", stiffness: 300, damping: 24 },
  },
};

export const slideInRight: Variants = {
  hidden: { opacity: 0, x: 30 },
  show: {
    opacity: 1,
    x: 0,
    transition: { type: "spring", stiffness: 300, damping: 24 },
  },
};
