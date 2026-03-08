"use client";

import { useMemo } from "react";
import { motion } from "framer-motion";
import {
  AreaChart,
  Area,
  XAxis,
  YAxis,
  Tooltip,
  ResponsiveContainer,
} from "recharts";
import { Skeleton } from "@/components/ui/skeleton";
import type { CallEntry } from "@/lib/types";

interface CallsByHourChartProps {
  calls: CallEntry[];
  loading?: boolean;
}

export function CallsByHourChart({ calls, loading }: CallsByHourChartProps) {
  const data = useMemo(() => {
    const buckets: Record<string, number> = {};
    for (const call of calls) {
      const d = new Date(call.created_at);
      const key = `${String(d.getMonth() + 1).padStart(2, "0")}/${String(d.getDate()).padStart(2, "0")} ${String(d.getHours()).padStart(2, "0")}:00`;
      buckets[key] = (buckets[key] ?? 0) + 1;
    }
    return Object.entries(buckets)
      .sort(([a], [b]) => a.localeCompare(b))
      .map(([time, count]) => ({ time, count }));
  }, [calls]);

  return (
    <motion.div
      initial={{ opacity: 0, y: 20 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ duration: 0.5, delay: 0.2 }}
      className="glass rounded-2xl border-gradient p-5"
    >
      <h3 className="text-xs uppercase tracking-wider text-muted-foreground font-medium mb-4">
        {"\u0414\u0438\u043d\u0430\u043c\u0438\u043a\u0430 \u0437\u0432\u043e\u043d\u043a\u043e\u0432"}
      </h3>
      {loading ? (
        <Skeleton className="h-[200px] w-full rounded-xl" />
      ) : data.length === 0 ? (
        <div className="flex h-[200px] items-center justify-center text-muted-foreground text-sm">
          {"\u041d\u0435\u0442 \u0434\u0430\u043d\u043d\u044b\u0445"}
        </div>
      ) : (
        <ResponsiveContainer width="100%" height={200}>
          <AreaChart data={data}>
            <defs>
              <linearGradient id="gradientCyan" x1="0" y1="0" x2="0" y2="1">
                <stop offset="0%" stopColor="oklch(0.72 0.19 200)" stopOpacity={0.35} />
                <stop offset="100%" stopColor="oklch(0.72 0.19 200)" stopOpacity={0} />
              </linearGradient>
            </defs>
            <XAxis
              dataKey="time"
              tick={{ fontSize: 10, fill: "oklch(0.6 0.01 260)" }}
              interval="preserveStartEnd"
              axisLine={false}
              tickLine={false}
            />
            <YAxis
              tick={{ fontSize: 11, fill: "oklch(0.6 0.01 260)" }}
              allowDecimals={false}
              axisLine={false}
              tickLine={false}
            />
            <Tooltip
              contentStyle={{
                background: "oklch(0.12 0.025 270 / 0.9)",
                backdropFilter: "blur(20px)",
                border: "1px solid oklch(0.5 0.05 270 / 0.15)",
                borderRadius: "12px",
                color: "oklch(0.93 0.005 260)",
                fontSize: "12px",
              }}
            />
            <Area
              type="monotone"
              dataKey="count"
              stroke="oklch(0.72 0.19 200)"
              fill="url(#gradientCyan)"
              strokeWidth={2}
            />
          </AreaChart>
        </ResponsiveContainer>
      )}
    </motion.div>
  );
}
