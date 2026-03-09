"use client";

import { motion } from "framer-motion";
import { cn } from "@/lib/utils";

interface ConfidenceBadgeProps {
  label: string;
  value: number;
  size?: "sm" | "md";
}

export function ConfidenceBadge({
  label,
  value,
  size = "md",
}: ConfidenceBadgeProps) {
  const percent = Math.round(value * 100);
  const color =
    percent >= 85
      ? "text-success"
      : percent >= 60
        ? "text-warning"
        : "text-error";

  const barColor =
    percent >= 85 ? "bg-success" : percent >= 60 ? "bg-warning" : "bg-error";

  return (
    <div className={cn("flex items-center gap-3", size === "sm" ? "text-xs" : "text-sm")}>
      <span className="min-w-[100px] text-text-secondary">{label}</span>
      <div className="flex-1">
        <div className="h-1.5 overflow-hidden rounded-full bg-bg-elevated">
          <motion.div
            initial={{ width: 0 }}
            animate={{ width: `${percent}%` }}
            transition={{ type: "spring", stiffness: 200, damping: 20, delay: 0.2 }}
            className={cn("h-full rounded-full", barColor)}
            style={{ opacity: 0.8 }}
          />
        </div>
      </div>
      <span className={cn("min-w-[36px] text-right font-mono font-semibold", color)}>
        {percent}%
      </span>
    </div>
  );
}
