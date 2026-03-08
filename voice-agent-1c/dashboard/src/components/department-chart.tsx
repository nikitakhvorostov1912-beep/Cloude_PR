"use client";

import { motion } from "framer-motion";
import {
  BarChart,
  Bar,
  XAxis,
  YAxis,
  Tooltip,
  ResponsiveContainer,
  Cell,
} from "recharts";
import { Skeleton } from "@/components/ui/skeleton";
import type { DepartmentEntry } from "@/lib/types";
import { DEPARTMENT_LABELS, DEPARTMENT_COLORS } from "@/lib/constants";

interface DepartmentChartProps {
  departments: DepartmentEntry[];
  loading?: boolean;
}

export function DepartmentChart({ departments, loading }: DepartmentChartProps) {
  const data = departments.map((d) => ({
    name: DEPARTMENT_LABELS[d.department] ?? d.department,
    count: d.count,
    key: d.department,
  }));

  return (
    <motion.div
      initial={{ opacity: 0, y: 20 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ duration: 0.5, delay: 0.3 }}
      className="glass rounded-2xl border-gradient p-5"
    >
      <h3 className="text-xs uppercase tracking-wider text-muted-foreground font-medium mb-4">
        {"\u041f\u043e \u043e\u0442\u0434\u0435\u043b\u0430\u043c"}
      </h3>
      {loading ? (
        <Skeleton className="h-[200px] w-full rounded-xl" />
      ) : data.length === 0 ? (
        <div className="flex h-[200px] items-center justify-center text-muted-foreground text-sm">
          {"\u041d\u0435\u0442 \u0434\u0430\u043d\u043d\u044b\u0445"}
        </div>
      ) : (
        <ResponsiveContainer width="100%" height={200}>
          <BarChart data={data} layout="vertical" margin={{ left: 10 }}>
            <XAxis type="number" tick={{ fontSize: 11, fill: "oklch(0.6 0.01 260)" }} axisLine={false} tickLine={false} />
            <YAxis
              type="category"
              dataKey="name"
              tick={{ fontSize: 11, fill: "oklch(0.6 0.01 260)" }}
              width={90}
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
            <Bar dataKey="count" radius={[0, 6, 6, 0]} barSize={20}>
              {data.map((entry) => (
                <Cell
                  key={entry.key}
                  fill={DEPARTMENT_COLORS[entry.key] ?? "oklch(0.72 0.19 200)"}
                  fillOpacity={0.8}
                />
              ))}
            </Bar>
          </BarChart>
        </ResponsiveContainer>
      )}
    </motion.div>
  );
}
