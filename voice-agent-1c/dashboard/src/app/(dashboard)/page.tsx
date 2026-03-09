"use client";

import { useState } from "react";
import { useRouter } from "next/navigation";
import { motion } from "framer-motion";
import { Phone, Clock, CheckCircle, AlertTriangle, Activity } from "lucide-react";
import { KpiCard } from "@/components/kpi-card";
import { PeriodSelector } from "@/components/period-selector";
import { DepartmentChart } from "@/components/department-chart";
import { CallsByHourChart } from "@/components/calls-by-hour-chart";
import { CallsTable } from "@/components/calls-table";
import {
  useDashboardSummary,
  useDashboardDepartments,
  useDashboardCalls,
} from "@/hooks/use-dashboard";
import { formatDuration, formatPercent } from "@/lib/format";

const containerVariants = {
  hidden: { opacity: 0 },
  visible: {
    opacity: 1,
    transition: { staggerChildren: 0.08 },
  },
};

const itemVariants = {
  hidden: { opacity: 0, y: 20 },
  visible: { opacity: 1, y: 0, transition: { duration: 0.5, ease: [0.23, 1, 0.32, 1] as const } },
};

export default function DashboardPage() {
  const [period, setPeriod] = useState(7);
  const router = useRouter();

  const summary = useDashboardSummary(period);
  const departments = useDashboardDepartments(period);
  const calls = useDashboardCalls({ period, limit: 200, offset: 0 });

  const recentCalls = (calls.data?.calls ?? []).slice(0, 10);

  return (
    <motion.div
      className="space-y-6"
      variants={containerVariants}
      initial="hidden"
      animate="visible"
    >
      {/* Header */}
      <motion.div variants={itemVariants} className="flex items-center justify-between">
        <div className="flex items-center gap-3">
          <div className="rounded-xl bg-[oklch(0.72_0.19_200_/_0.12)] p-2.5">
            <Activity className="h-6 w-6 text-[oklch(0.72_0.19_200)]" />
          </div>
          <div>
            <h1 className="text-2xl font-bold text-gradient">{"Панель управления"}</h1>
            <p className="text-xs text-muted-foreground">{"Обзор активности голосового агента"}</p>
          </div>
        </div>
        <PeriodSelector value={period} onChange={setPeriod} />
      </motion.div>

      {/* KPI Cards */}
      <motion.div variants={itemVariants} className="grid gap-4 sm:grid-cols-2 lg:grid-cols-4">
        <KpiCard
          title={"Всего звонков"}
          value={summary.data?.total_calls ?? 0}
          icon={Phone}
          loading={summary.isLoading}
          description={`За ${period} дн.`}
          accentColor="cyan"
          index={0}
        />
        <KpiCard
          title={"Средняя длительность"}
          value={formatDuration(summary.data?.avg_duration_seconds ?? null)}
          icon={Clock}
          loading={summary.isLoading}
          accentColor="violet"
          index={1}
        />
        <KpiCard
          title={"Успешность"}
          value={formatPercent(summary.data?.success_rate ?? 0)}
          icon={CheckCircle}
          loading={summary.isLoading}
          description={`${summary.data?.successful_calls ?? 0} успешных`}
          accentColor="green"
          index={2}
        />
        <KpiCard
          title={"Эскалации"}
          value={summary.data?.escalation_count ?? 0}
          icon={AlertTriangle}
          loading={summary.isLoading}
          description={
            summary.data
              ? `${formatPercent(summary.data.escalation_rate)} от всех`
              : undefined
          }
          accentColor="amber"
          index={3}
        />
      </motion.div>

      {/* Error state */}
      {summary.isError && (
        <motion.div
          variants={itemVariants}
          className="glass rounded-2xl border border-[oklch(0.65_0.22_25_/_0.3)] p-4"
        >
          <p className="text-sm text-[oklch(0.65_0.22_25)]">
            {"Ошибка загрузки данных. Проверьте подключение к серверу."}
          </p>
        </motion.div>
      )}

      {/* Charts Row */}
      <motion.div variants={itemVariants} className="grid gap-4 md:grid-cols-2">
        <CallsByHourChart
          calls={calls.data?.calls ?? []}
          loading={calls.isLoading}
        />
        <DepartmentChart
          departments={departments.data?.departments ?? []}
          loading={departments.isLoading}
        />
      </motion.div>

      {/* Recent Calls */}
      <motion.div variants={itemVariants} className="glass rounded-2xl border-gradient p-5">
        <div className="mb-4 flex items-center gap-2">
          <div className="h-0.5 w-8 rounded-full bg-gradient-to-r from-[oklch(0.72_0.19_200)] to-[oklch(0.72_0.19_200_/_0.2)]" />
          <h2 className="text-sm font-medium uppercase tracking-wider text-muted-foreground">
            {"Последние звонки"}
          </h2>
        </div>
        <CallsTable
          calls={recentCalls}
          loading={calls.isLoading}
          onRowClick={(id) => router.push(`/calls/${id}`)}
          compact
        />
      </motion.div>
    </motion.div>
  );
}
