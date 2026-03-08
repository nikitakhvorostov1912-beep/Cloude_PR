"use client";

import { cn } from "@/lib/utils";
import { TrendingUp, TrendingDown, Minus, type LucideIcon } from "lucide-react";
import { GlowCard } from "@/components/glow-card";
import { AnimatedCounter } from "@/components/animated-counter";
import {
  LineChart,
  Line,
  ResponsiveContainer,
} from "recharts";

interface KPICardProps {
  title: string;
  value: number;
  format?: "number" | "percent" | "duration";
  trend?: number;
  icon: LucideIcon;
  accent?: "navy" | "blue" | "red" | "gradient";
  sparkData?: number[];
}

const ACCENT_COLORS = {
  navy: {
    icon: "from-navy-light/20 to-navy/10 text-is-blue",
    glow: "navy" as const,
    sparkColor: "#6366F1",
  },
  blue: {
    icon: "from-is-blue/20 to-is-blue/10 text-is-blue",
    glow: "blue" as const,
    sparkColor: "#7DBEF4",
  },
  red: {
    icon: "from-is-red/20 to-is-red/10 text-is-red",
    glow: "red" as const,
    sparkColor: "#FF4547",
  },
  gradient: {
    icon: "from-is-blue/15 to-navy/10 text-is-blue-light",
    glow: "navy" as const,
    sparkColor: "#A8D4F7",
  },
};

export function KPICard({
  title,
  value,
  format = "number",
  trend,
  icon: Icon,
  accent = "navy",
  sparkData,
}: KPICardProps) {
  const colors = ACCENT_COLORS[accent];

  const TrendIcon =
    trend === undefined || trend === 0
      ? Minus
      : trend > 0
        ? TrendingUp
        : TrendingDown;

  const trendColor =
    trend === undefined || trend === 0
      ? "text-text-muted"
      : trend > 0
        ? "text-success"
        : "text-error";

  const chartData = sparkData?.map((v, i) => ({ i, v }));

  return (
    <GlowCard tilt glowColor={colors.glow} className="p-5">
      <div className="mb-3 flex items-center justify-between">
        <span className="text-xs font-medium tracking-wide text-text-muted uppercase">
          {title}
        </span>
        <div
          className={cn(
            "flex h-9 w-9 items-center justify-center rounded-xl bg-gradient-to-br",
            colors.icon
          )}
        >
          <Icon className="h-4 w-4" />
        </div>
      </div>

      <div className="mb-2">
        <AnimatedCounter
          value={value}
          format={format}
          className="text-3xl font-bold tracking-tight text-text-primary"
        />
      </div>

      {trend !== undefined && (
        <div className={cn("flex items-center gap-1 text-xs", trendColor)}>
          <TrendIcon className="h-3 w-3" />
          <span>{trend > 0 ? "+" : ""}{trend}% за сегодня</span>
        </div>
      )}

      {chartData && chartData.length > 0 && (
        <div className="mt-3 -mx-1">
          <ResponsiveContainer width="100%" height={32}>
            <LineChart data={chartData}>
              <Line
                type="monotone"
                dataKey="v"
                stroke={colors.sparkColor}
                strokeWidth={1.5}
                dot={false}
                animationDuration={1500}
                animationEasing="ease-out"
              />
            </LineChart>
          </ResponsiveContainer>
        </div>
      )}
    </GlowCard>
  );
}
