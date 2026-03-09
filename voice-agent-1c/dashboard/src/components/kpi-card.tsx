"use client";

import type { LucideIcon } from "lucide-react";
import { motion } from "framer-motion";
import { Skeleton } from "@/components/ui/skeleton";

interface KpiCardProps {
  title: string;
  value: string | number;
  description?: string;
  icon: LucideIcon;
  loading?: boolean;
  accentColor?: "cyan" | "violet" | "green" | "amber";
  index?: number;
}

const ACCENT_CLASSES = {
  cyan: {
    glow: "glow-cyan",
    icon: "text-[oklch(0.72_0.19_200)]",
    iconBg: "bg-[oklch(0.72_0.19_200_/_0.12)]",
    bar: "from-[oklch(0.72_0.19_200)] to-[oklch(0.72_0.19_200_/_0.2)]",
  },
  violet: {
    glow: "glow-violet",
    icon: "text-[oklch(0.68_0.22_280)]",
    iconBg: "bg-[oklch(0.68_0.22_280_/_0.12)]",
    bar: "from-[oklch(0.68_0.22_280)] to-[oklch(0.68_0.22_280_/_0.2)]",
  },
  green: {
    glow: "glow-green",
    icon: "text-[oklch(0.75_0.18_160)]",
    iconBg: "bg-[oklch(0.75_0.18_160_/_0.12)]",
    bar: "from-[oklch(0.75_0.18_160)] to-[oklch(0.75_0.18_160_/_0.2)]",
  },
  amber: {
    glow: "glow-amber",
    icon: "text-[oklch(0.72_0.16_50)]",
    iconBg: "bg-[oklch(0.72_0.16_50_/_0.12)]",
    bar: "from-[oklch(0.72_0.16_50)] to-[oklch(0.72_0.16_50_/_0.2)]",
  },
};

export function KpiCard({
  title,
  value,
  description,
  icon: Icon,
  loading,
  accentColor = "cyan",
  index = 0,
}: KpiCardProps) {
  const accent = ACCENT_CLASSES[accentColor];

  return (
    <motion.div
      initial={{ opacity: 0, y: 20 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ duration: 0.5, delay: index * 0.1, ease: [0.23, 1, 0.32, 1] }}
      className={`glass rounded-2xl p-5 border-gradient hover:scale-[1.02] transition-transform duration-300 ${accent.glow}`}
    >
      <div className={`h-0.5 w-12 rounded-full bg-gradient-to-r ${accent.bar} mb-4`} />

      <div className="flex items-start justify-between">
        <div className="space-y-1">
          <p className="text-xs uppercase tracking-wider text-muted-foreground font-medium">
            {title}
          </p>
          {loading ? (
            <Skeleton className="h-9 w-24 rounded-lg" />
          ) : (
            <motion.p
              initial={{ opacity: 0, scale: 0.8 }}
              animate={{ opacity: 1, scale: 1 }}
              transition={{ duration: 0.6, delay: index * 0.1 + 0.2 }}
              className="text-3xl font-bold tracking-tight"
            >
              {value}
            </motion.p>
          )}
          {description && (
            <p className="text-[11px] text-muted-foreground">{description}</p>
          )}
        </div>
        <div className={`rounded-xl p-2.5 ${accent.iconBg}`}>
          <Icon className={`h-5 w-5 ${accent.icon}`} />
        </div>
      </div>
    </motion.div>
  );
}
