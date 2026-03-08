"use client";

import { useState } from "react";
import { useRouter } from "next/navigation";
import { motion } from "framer-motion";
import { PhoneCall, Filter, ChevronLeft, ChevronRight } from "lucide-react";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
import { PeriodSelector } from "@/components/period-selector";
import { CallsTable } from "@/components/calls-table";
import { useDashboardCalls } from "@/hooks/use-dashboard";
import { DEPARTMENT_LABELS, PRIORITY_LABELS } from "@/lib/constants";

const PAGE_SIZE = 50;

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

export default function CallsPage() {
  const [period, setPeriod] = useState(7);
  const [offset, setOffset] = useState(0);
  const [departmentFilter, setDepartmentFilter] = useState<string>("all");
  const [priorityFilter, setPriorityFilter] = useState<string>("all");
  const router = useRouter();

  const { data, isLoading } = useDashboardCalls({
    period,
    limit: PAGE_SIZE,
    offset,
  });

  const filteredCalls = (data?.calls ?? []).filter((call) => {
    if (departmentFilter !== "all" && call.department !== departmentFilter)
      return false;
    if (priorityFilter !== "all" && call.priority !== priorityFilter)
      return false;
    return true;
  });

  const hasNext = (data?.calls.length ?? 0) === PAGE_SIZE;
  const hasPrev = offset > 0;
  const currentPage = Math.floor(offset / PAGE_SIZE) + 1;

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
          <div className="rounded-xl bg-[oklch(0.68_0.22_280_/_0.12)] p-2.5">
            <PhoneCall className="h-6 w-6 text-[oklch(0.68_0.22_280)]" />
          </div>
          <div>
            <h1 className="text-2xl font-bold text-gradient">{"Журнал звонков"}</h1>
            <p className="text-xs text-muted-foreground">{"Полный список обработанных вызовов"}</p>
          </div>
        </div>
        <PeriodSelector value={period} onChange={(v) => { setPeriod(v); setOffset(0); }} />
      </motion.div>

      {/* Filters */}
      <motion.div variants={itemVariants} className="flex items-center gap-3">
        <div className="rounded-lg bg-[oklch(0.72_0.19_200_/_0.08)] p-1.5">
          <Filter className="h-4 w-4 text-[oklch(0.72_0.19_200)]" />
        </div>
        <Select value={departmentFilter} onValueChange={setDepartmentFilter}>
          <SelectTrigger className="w-[160px] glass rounded-xl border-0">
            <SelectValue placeholder={"Отдел"} />
          </SelectTrigger>
          <SelectContent className="glass-strong rounded-xl border-0">
            <SelectItem value="all">{"Все отделы"}</SelectItem>
            {Object.entries(DEPARTMENT_LABELS).map(([key, label]) => (
              <SelectItem key={key} value={key}>
                {label}
              </SelectItem>
            ))}
          </SelectContent>
        </Select>

        <Select value={priorityFilter} onValueChange={setPriorityFilter}>
          <SelectTrigger className="w-[160px] glass rounded-xl border-0">
            <SelectValue placeholder={"Срочность"} />
          </SelectTrigger>
          <SelectContent className="glass-strong rounded-xl border-0">
            <SelectItem value="all">{"Все уровни"}</SelectItem>
            {Object.entries(PRIORITY_LABELS).map(([key, label]) => (
              <SelectItem key={key} value={key}>
                {label}
              </SelectItem>
            ))}
          </SelectContent>
        </Select>

        {(departmentFilter !== "all" || priorityFilter !== "all") && (
          <button
            onClick={() => { setDepartmentFilter("all"); setPriorityFilter("all"); }}
            className="text-xs text-[oklch(0.72_0.19_200)] hover:text-[oklch(0.82_0.19_200)] transition-colors"
          >
            {"Сбросить"}
          </button>
        )}
      </motion.div>

      {/* Table */}
      <motion.div variants={itemVariants} className="glass rounded-2xl border-gradient p-5">
        <div className="mb-4 flex items-center justify-between">
          <div className="flex items-center gap-2">
            <div className="h-0.5 w-8 rounded-full bg-gradient-to-r from-[oklch(0.68_0.22_280)] to-[oklch(0.68_0.22_280_/_0.2)]" />
            <span className="text-sm font-medium uppercase tracking-wider text-muted-foreground">
              {data ? `Показано: ${filteredCalls.length}` : "Загрузка..."}
            </span>
          </div>
        </div>

        <CallsTable
          calls={filteredCalls}
          loading={isLoading}
          onRowClick={(id) => router.push(`/calls/${id}`)}
        />

        {/* Pagination */}
        <div className="mt-5 flex items-center justify-between">
          <button
            disabled={!hasPrev}
            onClick={() => setOffset(Math.max(0, offset - PAGE_SIZE))}
            className="flex items-center gap-1.5 rounded-xl px-4 py-2 text-sm font-medium glass hover:bg-[oklch(0.72_0.19_200_/_0.1)] transition-all disabled:opacity-30 disabled:cursor-not-allowed"
          >
            <ChevronLeft className="h-4 w-4" />
            {"Назад"}
          </button>
          <span className="text-xs text-muted-foreground font-mono">
            {`Страница ${currentPage}`}
          </span>
          <button
            disabled={!hasNext}
            onClick={() => setOffset(offset + PAGE_SIZE)}
            className="flex items-center gap-1.5 rounded-xl px-4 py-2 text-sm font-medium glass hover:bg-[oklch(0.72_0.19_200_/_0.1)] transition-all disabled:opacity-30 disabled:cursor-not-allowed"
          >
            {"Вперёд"}
            <ChevronRight className="h-4 w-4" />
          </button>
        </div>
      </motion.div>
    </motion.div>
  );
}
