"use client";

import { useQuery } from "@tanstack/react-query";
import { motion } from "framer-motion";
import {
  Phone,
  Brain,
  Clock,
  Users,
} from "lucide-react";
import {
  AreaChart,
  Area,
  BarChart,
  Bar,
  RadialBarChart,
  RadialBar,
  XAxis,
  YAxis,
  Tooltip,
  ResponsiveContainer,
} from "recharts";
import { KPICard } from "@/components/kpi-card";
import { ActivityFeed } from "@/components/activity-feed";
import { GlowCard } from "@/components/glow-card";
import { AnimatedCounter } from "@/components/animated-counter";
import { AnimatedGradientText } from "@/components/animated-gradient-text";
import { PageWrapper } from "@/components/page-wrapper";
import { staggerContainer, staggerItem } from "@/lib/motion";
import { api, type KPIData } from "@/lib/api";

const DEFAULT_KPIS: KPIData = {
  active_calls: 3,
  ai_accuracy: 0.87,
  avg_handle_time_sec: 245,
  queue_size: 1,
  calls_today: 47,
  tasks_created_today: 38,
  escalations_today: 4,
};

// Sparkline data for each KPI
const SPARK_DATA = {
  calls: [1, 2, 3, 2, 4, 3, 5, 4, 3],
  accuracy: [82, 84, 86, 85, 87, 86, 88, 87, 87],
  time: [280, 260, 270, 250, 255, 248, 245, 250, 245],
  queue: [2, 1, 3, 2, 1, 0, 1, 2, 1],
};

// Demo chart data
const CALLS_PER_HOUR = [
  { hour: "08:00", calls: 2 },
  { hour: "09:00", calls: 5 },
  { hour: "10:00", calls: 8 },
  { hour: "11:00", calls: 12 },
  { hour: "12:00", calls: 7 },
  { hour: "13:00", calls: 4 },
  { hour: "14:00", calls: 9 },
  { hour: "15:00", calls: 11 },
  { hour: "16:00", calls: 14 },
  { hour: "17:00", calls: 10 },
  { hour: "18:00", calls: 6 },
  { hour: "19:00", calls: 3 },
];

const DEPT_DATA = [
  { name: "Поддержка", value: 62, fill: "#6366F1" },
  { name: "Разработка", value: 18, fill: "#7DBEF4" },
  { name: "Внедрение", value: 12, fill: "#FF4547" },
  { name: "Пресейл", value: 8, fill: "#8B5CF6" },
];

const CustomTooltip = ({ active, payload, label }: { active?: boolean; payload?: Array<{ value: number }>; label?: string }) => {
  if (!active || !payload?.length) return null;
  return (
    <div className="glass-card px-3 py-2 text-xs">
      <p className="text-text-muted">{label}</p>
      <p className="font-semibold text-is-blue">{payload[0].value} звонков</p>
    </div>
  );
};

export default function DashboardPage() {
  const { data: kpis } = useQuery({
    queryKey: ["kpis"],
    queryFn: async () => {
      try {
        return await api.getKPIs();
      } catch {
        return DEFAULT_KPIS;
      }
    },
    initialData: DEFAULT_KPIS,
  });

  const data = kpis ?? DEFAULT_KPIS;
  const accuracyRadial = [{ name: "AI", value: Math.round(data.ai_accuracy * 100), fill: "url(#radialGradient)" }];

  return (
    <PageWrapper>
      <div className="flex h-[calc(100vh-3.5rem)]">
        {/* Main content */}
        <div className="flex-1 overflow-y-auto p-6">
          {/* Header */}
          <motion.div
            initial={{ opacity: 0, y: -20 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ type: "spring", stiffness: 300, damping: 24 }}
            className="mb-8"
          >
            <h1 className="text-3xl font-bold">
              <AnimatedGradientText>Аврора</AnimatedGradientText>
            </h1>
            <p className="mt-1 text-sm text-text-muted">
              Панель управления &bull; Суфлёр
            </p>
          </motion.div>

          {/* KPI Grid */}
          <motion.div
            variants={staggerContainer}
            initial="hidden"
            animate="show"
            className="mb-8 grid grid-cols-1 gap-4 sm:grid-cols-2 xl:grid-cols-4"
          >
            <motion.div variants={staggerItem}>
              <KPICard
                title="Активные звонки"
                value={data.active_calls}
                icon={Phone}
                accent="navy"
                trend={12}
                sparkData={SPARK_DATA.calls}
              />
            </motion.div>
            <motion.div variants={staggerItem}>
              <KPICard
                title="Точность AI"
                value={data.ai_accuracy}
                format="percent"
                icon={Brain}
                accent="blue"
                trend={3}
                sparkData={SPARK_DATA.accuracy}
              />
            </motion.div>
            <motion.div variants={staggerItem}>
              <KPICard
                title="Ср. время"
                value={data.avg_handle_time_sec}
                format="duration"
                icon={Clock}
                accent="gradient"
                trend={-5}
                sparkData={SPARK_DATA.time}
              />
            </motion.div>
            <motion.div variants={staggerItem}>
              <KPICard
                title="В очереди"
                value={data.queue_size}
                icon={Users}
                accent="red"
                trend={0}
                sparkData={SPARK_DATA.queue}
              />
            </motion.div>
          </motion.div>

          {/* Bento Grid */}
          <motion.div
            variants={staggerContainer}
            initial="hidden"
            animate="show"
            className="grid grid-cols-1 gap-4 lg:grid-cols-2 xl:grid-cols-3"
          >
            {/* Calls chart (span 2) */}
            <motion.div variants={staggerItem} className="xl:col-span-2">
              <GlowCard className="p-5">
                <h3 className="mb-4 text-sm font-semibold text-text-secondary uppercase tracking-wide">
                  Звонки за сегодня
                </h3>
                <ResponsiveContainer width="100%" height={220}>
                  <AreaChart data={CALLS_PER_HOUR}>
                    <defs>
                      <linearGradient id="callsGradient" x1="0" y1="0" x2="0" y2="1">
                        <stop offset="0%" stopColor="#7DBEF4" stopOpacity={0.3} />
                        <stop offset="100%" stopColor="#7DBEF4" stopOpacity={0} />
                      </linearGradient>
                    </defs>
                    <XAxis
                      dataKey="hour"
                      axisLine={false}
                      tickLine={false}
                      tick={{ fill: "#64748B", fontSize: 11 }}
                    />
                    <YAxis
                      axisLine={false}
                      tickLine={false}
                      tick={{ fill: "#64748B", fontSize: 11 }}
                      width={30}
                    />
                    <Tooltip content={<CustomTooltip />} />
                    <Area
                      type="monotone"
                      dataKey="calls"
                      stroke="#7DBEF4"
                      strokeWidth={2}
                      fill="url(#callsGradient)"
                      animationDuration={1500}
                      animationEasing="ease-out"
                    />
                  </AreaChart>
                </ResponsiveContainer>
              </GlowCard>
            </motion.div>

            {/* Today stats */}
            <motion.div variants={staggerItem}>
              <GlowCard className="p-5">
                <h3 className="mb-4 text-sm font-semibold text-text-secondary uppercase tracking-wide">
                  Сегодня
                </h3>
                <div className="grid grid-cols-3 gap-4">
                  <div>
                    <AnimatedCounter
                      value={data.calls_today}
                      className="text-2xl font-bold text-text-primary"
                    />
                    <p className="text-xs text-text-muted">Звонков</p>
                  </div>
                  <div>
                    <AnimatedCounter
                      value={data.tasks_created_today}
                      className="text-2xl font-bold text-success"
                    />
                    <p className="text-xs text-text-muted">Задач</p>
                  </div>
                  <div>
                    <AnimatedCounter
                      value={data.escalations_today}
                      className="text-2xl font-bold text-warning"
                    />
                    <p className="text-xs text-text-muted">Эскалаций</p>
                  </div>
                </div>
              </GlowCard>
            </motion.div>

            {/* Department chart */}
            <motion.div variants={staggerItem}>
              <GlowCard className="p-5">
                <h3 className="mb-4 text-sm font-semibold text-text-secondary uppercase tracking-wide">
                  По отделам
                </h3>
                <ResponsiveContainer width="100%" height={180}>
                  <BarChart data={DEPT_DATA} layout="vertical" barSize={14}>
                    <XAxis
                      type="number"
                      domain={[0, 100]}
                      axisLine={false}
                      tickLine={false}
                      tick={{ fill: "#64748B", fontSize: 11 }}
                    />
                    <YAxis
                      type="category"
                      dataKey="name"
                      axisLine={false}
                      tickLine={false}
                      tick={{ fill: "#94A3B8", fontSize: 12 }}
                      width={90}
                    />
                    <Bar
                      dataKey="value"
                      radius={[0, 6, 6, 0]}
                      animationDuration={1200}
                      animationEasing="ease-out"
                    />
                  </BarChart>
                </ResponsiveContainer>
              </GlowCard>
            </motion.div>

            {/* AI Accuracy radial */}
            <motion.div variants={staggerItem}>
              <GlowCard className="flex flex-col items-center justify-center p-5">
                <h3 className="mb-2 text-sm font-semibold text-text-secondary uppercase tracking-wide">
                  Точность AI
                </h3>
                <ResponsiveContainer width={160} height={160}>
                  <RadialBarChart
                    cx="50%"
                    cy="50%"
                    innerRadius="70%"
                    outerRadius="100%"
                    barSize={12}
                    data={accuracyRadial}
                    startAngle={90}
                    endAngle={-270}
                  >
                    <defs>
                      <linearGradient id="radialGradient" x1="0" y1="0" x2="1" y2="1">
                        <stop offset="0%" stopColor="#6366F1" />
                        <stop offset="100%" stopColor="#7DBEF4" />
                      </linearGradient>
                    </defs>
                    <RadialBar
                      dataKey="value"
                      cornerRadius={10}
                      background={{ fill: "rgba(20, 24, 73, 0.6)" }}
                      animationDuration={1500}
                      animationEasing="ease-out"
                    />
                  </RadialBarChart>
                </ResponsiveContainer>
                <span className="mt-[-90px] text-2xl font-bold text-text-primary">
                  {Math.round(data.ai_accuracy * 100)}%
                </span>
                <p className="mt-12 text-xs text-text-muted">За последние 24ч</p>
              </GlowCard>
            </motion.div>

            {/* Recent calls mini-table */}
            <motion.div variants={staggerItem}>
              <GlowCard className="p-5">
                <h3 className="mb-3 text-sm font-semibold text-text-secondary uppercase tracking-wide">
                  Последние звонки
                </h3>
                <div className="space-y-2">
                  {[
                    { name: "ООО Ромашка", time: "10:30", status: "Завершён", color: "text-success" },
                    { name: "ИП Петров", time: "10:15", status: "Обработка", color: "text-is-blue" },
                    { name: "ООО ТехноМир", time: "10:05", status: "Активен", color: "text-is-blue-light" },
                    { name: "АО Сервис Плюс", time: "09:45", status: "Завершён", color: "text-success" },
                    { name: "ООО Альфа", time: "09:30", status: "Завершён", color: "text-success" },
                  ].map((call) => (
                    <div
                      key={call.name}
                      className="flex items-center justify-between rounded-xl px-3 py-2 transition-colors hover:bg-bg-elevated/50 cursor-pointer"
                    >
                      <div>
                        <p className="text-sm font-medium text-text-primary">{call.name}</p>
                        <p className="text-xs text-text-muted">{call.time}</p>
                      </div>
                      <span className={`text-xs font-medium ${call.color}`}>{call.status}</span>
                    </div>
                  ))}
                </div>
              </GlowCard>
            </motion.div>
          </motion.div>
        </div>

        {/* Activity feed sidebar */}
        <aside className="hidden w-80 shrink-0 border-l border-border-subtle p-5 xl:block">
          <ActivityFeed />
        </aside>
      </div>
    </PageWrapper>
  );
}
