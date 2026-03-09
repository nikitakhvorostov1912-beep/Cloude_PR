"use client";

import { useState } from "react";
import { motion, AnimatePresence } from "framer-motion";
import { Phone, CheckCircle, AlertTriangle, ArrowUpRight } from "lucide-react";
import { cn } from "@/lib/utils";

interface ActivityItem {
  id: string;
  type: "call_in" | "task_created" | "escalation" | "classified";
  title: string;
  description: string;
  time: string;
}

const DEMO_ITEMS: ActivityItem[] = [
  {
    id: "1",
    type: "call_in",
    title: "Входящий звонок",
    description: "+7 (495) 123-45-67 — ООО Ромашка",
    time: "только что",
  },
  {
    id: "2",
    type: "classified",
    title: "Классификация AI",
    description: "Ошибка БП → Отдел поддержки (92%)",
    time: "30 сек назад",
  },
  {
    id: "3",
    type: "task_created",
    title: "Задача создана",
    description: "SAK-4521 — Ошибка при формировании отчёта",
    time: "1 мин назад",
  },
  {
    id: "4",
    type: "escalation",
    title: "Эскалация",
    description: "Клиент запросил оператора",
    time: "3 мин назад",
  },
];

const ICON_MAP = {
  call_in: Phone,
  task_created: CheckCircle,
  escalation: AlertTriangle,
  classified: ArrowUpRight,
};

const COLOR_MAP = {
  call_in: "text-is-blue bg-is-blue/10",
  task_created: "text-success bg-success/10",
  escalation: "text-warning bg-warning/10",
  classified: "text-is-blue-light bg-is-blue-light/10",
};

export function ActivityFeed() {
  const [items] = useState<ActivityItem[]>(DEMO_ITEMS);

  return (
    <div className="flex h-full flex-col">
      <h3 className="mb-4 text-sm font-semibold text-text-secondary uppercase tracking-wide">
        Активность
      </h3>

      <div className="flex-1 space-y-1 overflow-y-auto">
        <AnimatePresence initial={false}>
          {items.map((item) => {
            const Icon = ICON_MAP[item.type];
            return (
              <motion.div
                key={item.id}
                initial={{ opacity: 0, y: -20, scale: 0.95 }}
                animate={{ opacity: 1, y: 0, scale: 1 }}
                exit={{ opacity: 0, height: 0 }}
                transition={{ type: "spring", stiffness: 300, damping: 25 }}
                className="flex gap-3 rounded-xl p-3 transition-colors hover:bg-bg-elevated/50"
              >
                <div
                  className={cn(
                    "flex h-8 w-8 shrink-0 items-center justify-center rounded-lg",
                    COLOR_MAP[item.type]
                  )}
                >
                  <Icon className="h-4 w-4" />
                </div>
                <div className="min-w-0 flex-1">
                  <p className="text-sm font-medium text-text-primary truncate">
                    {item.title}
                  </p>
                  <p className="text-xs text-text-muted truncate">
                    {item.description}
                  </p>
                </div>
                <span className="shrink-0 text-xs text-text-muted whitespace-nowrap">
                  {item.time}
                </span>
              </motion.div>
            );
          })}
        </AnimatePresence>
      </div>
    </div>
  );
}
