"use client";

import { useState } from "react";
import { useQuery } from "@tanstack/react-query";
import { motion } from "framer-motion";
import { Search, ChevronLeft, ChevronRight } from "lucide-react";
import { cn } from "@/lib/utils";
import { api } from "@/lib/api";
import { staggerContainer, staggerItem } from "@/lib/motion";
import { PageWrapper } from "@/components/page-wrapper";

const PRIORITY_COLORS: Record<string, string> = {
  critical: "bg-error/20 text-error",
  high: "bg-warning/20 text-warning",
  normal: "bg-is-blue/15 text-is-blue",
  low: "bg-bg-elevated text-text-muted",
};

const STATUS_LABELS: Record<string, string> = {
  active: "Активен",
  classified: "Классифицирован",
  completed: "Завершён",
  escalated: "Эскалация",
};

const DEMO_CALLS = [
  {
    call_id: "call-001",
    phone: "+7 (495) 123-45-67",
    client_name: "ООО Ромашка",
    department: "Поддержка",
    priority: "high",
    status: "completed",
    created_at: "2024-01-15T10:30:00",
    duration_sec: 245,
  },
  {
    call_id: "call-002",
    phone: "+7 (495) 987-65-43",
    client_name: "ИП Петров",
    department: "Разработка",
    priority: "normal",
    status: "classified",
    created_at: "2024-01-15T10:15:00",
    duration_sec: 180,
  },
  {
    call_id: "call-003",
    phone: "+7 (495) 555-12-34",
    client_name: "ООО ТехноМир",
    department: "Поддержка",
    priority: "critical",
    status: "active",
    created_at: "2024-01-15T10:05:00",
    duration_sec: 340,
  },
  {
    call_id: "call-004",
    phone: "+7 (812) 333-22-11",
    client_name: "АО Сервис Плюс",
    department: "Внедрение",
    priority: "low",
    status: "completed",
    created_at: "2024-01-15T09:45:00",
    duration_sec: 120,
  },
];

export default function CallsPage() {
  const [search, setSearch] = useState("");
  const [page, setPage] = useState(1);

  const { data } = useQuery({
    queryKey: ["calls", page],
    queryFn: () => api.getCalls(page),
  });

  const calls = data?.calls?.length ? data.calls : DEMO_CALLS;

  const filtered = calls.filter(
    (c) =>
      c.phone.includes(search) ||
      c.client_name.toLowerCase().includes(search.toLowerCase())
  );

  return (
    <PageWrapper>
      <div className="p-6">
        {/* Header */}
        <motion.div
          initial={{ opacity: 0, y: -20 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ type: "spring", stiffness: 300, damping: 24 }}
          className="mb-6 flex items-center justify-between"
        >
          <div>
            <h1 className="text-xl font-bold text-text-primary">Звонки</h1>
            <p className="text-sm text-text-muted">История обращений</p>
          </div>

          {/* Search */}
          <div className="relative w-72">
            <Search className="absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-text-muted" />
            <input
              type="text"
              value={search}
              onChange={(e) => setSearch(e.target.value)}
              placeholder="Поиск по телефону, клиенту..."
              className="h-10 w-full rounded-xl border border-border-subtle bg-surface-1 pl-10 pr-4 text-sm text-text-primary outline-none transition-all placeholder:text-text-muted focus:border-is-blue/30 focus:shadow-[0_0_20px_rgba(125,190,244,0.08)]"
            />
          </div>
        </motion.div>

        {/* Table */}
        <motion.div
          initial={{ opacity: 0, y: 20 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ type: "spring", stiffness: 300, damping: 24, delay: 0.1 }}
          className="glass-card overflow-hidden"
        >
          <table className="w-full">
            <thead>
              <tr className="border-b border-border-subtle">
                <th className="px-5 py-3 text-left text-xs font-medium text-text-muted uppercase tracking-wide">
                  Клиент
                </th>
                <th className="px-5 py-3 text-left text-xs font-medium text-text-muted uppercase tracking-wide">
                  Телефон
                </th>
                <th className="px-5 py-3 text-left text-xs font-medium text-text-muted uppercase tracking-wide">
                  Отдел
                </th>
                <th className="px-5 py-3 text-left text-xs font-medium text-text-muted uppercase tracking-wide">
                  Приоритет
                </th>
                <th className="px-5 py-3 text-left text-xs font-medium text-text-muted uppercase tracking-wide">
                  Статус
                </th>
                <th className="px-5 py-3 text-left text-xs font-medium text-text-muted uppercase tracking-wide">
                  Длительность
                </th>
              </tr>
            </thead>
            <motion.tbody
              variants={staggerContainer}
              initial="hidden"
              animate="show"
            >
              {filtered.map((call) => (
                <motion.tr
                  key={call.call_id}
                  variants={staggerItem}
                  className="border-b border-border-subtle transition-all cursor-pointer hover:bg-bg-elevated/30 hover:shadow-[inset_0_0_30px_rgba(125,190,244,0.03)]"
                >
                  <td className="px-5 py-4">
                    <p className="text-sm font-medium text-text-primary">
                      {call.client_name}
                    </p>
                  </td>
                  <td className="px-5 py-4 font-mono text-sm text-text-secondary">
                    {call.phone}
                  </td>
                  <td className="px-5 py-4 text-sm text-text-secondary">
                    {call.department}
                  </td>
                  <td className="px-5 py-4">
                    <span
                      className={cn(
                        "inline-block rounded-lg px-2.5 py-1 text-xs font-medium",
                        PRIORITY_COLORS[call.priority] || PRIORITY_COLORS.normal
                      )}
                    >
                      {call.priority}
                    </span>
                  </td>
                  <td className="px-5 py-4 text-sm text-text-secondary">
                    {STATUS_LABELS[call.status] || call.status}
                  </td>
                  <td className="px-5 py-4 font-mono text-sm text-text-secondary">
                    {Math.floor(call.duration_sec / 60)}:{(call.duration_sec % 60)
                      .toString()
                      .padStart(2, "0")}
                  </td>
                </motion.tr>
              ))}
            </motion.tbody>
          </table>
        </motion.div>

        {/* Pagination */}
        <motion.div
          initial={{ opacity: 0 }}
          animate={{ opacity: 1 }}
          transition={{ delay: 0.3 }}
          className="mt-4 flex items-center justify-between"
        >
          <p className="text-sm text-text-muted">
            Показано {filtered.length} записей
          </p>
          <div className="flex gap-2">
            <button
              onClick={() => setPage((p) => Math.max(1, p - 1))}
              disabled={page <= 1}
              className="flex h-9 w-9 items-center justify-center rounded-lg border border-border-subtle text-text-muted transition-all hover:bg-bg-elevated hover:border-is-blue/15 disabled:opacity-30"
            >
              <ChevronLeft className="h-4 w-4" />
            </button>
            <button
              onClick={() => setPage((p) => p + 1)}
              className="flex h-9 w-9 items-center justify-center rounded-lg border border-border-subtle text-text-muted transition-all hover:bg-bg-elevated hover:border-is-blue/15"
            >
              <ChevronRight className="h-4 w-4" />
            </button>
          </div>
        </motion.div>
      </div>
    </PageWrapper>
  );
}
