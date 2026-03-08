"use client";

import { useState } from "react";
import { motion } from "framer-motion";
import { useQuery } from "@tanstack/react-query";
import { Wifi, WifiOff, Monitor, Info } from "lucide-react";
import { GlowCard } from "@/components/glow-card";
import { PageWrapper } from "@/components/page-wrapper";
import { staggerContainer, staggerItem } from "@/lib/motion";
import { api } from "@/lib/api";

export default function SettingsPage() {
  const [apiUrl] = useState(
    process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000"
  );

  const { data: health, isError } = useQuery({
    queryKey: ["health"],
    queryFn: () => api.getHealth(),
    retry: 1,
    refetchInterval: 10000,
  });

  const isConnected = !!health && !isError;

  return (
    <PageWrapper>
      <div className="mx-auto max-w-2xl p-6">
        <motion.div
          initial={{ opacity: 0, y: -20 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ type: "spring", stiffness: 300, damping: 24 }}
          className="mb-8"
        >
          <h1 className="text-xl font-bold text-text-primary">Настройки</h1>
          <p className="text-sm text-text-muted">Конфигурация системы</p>
        </motion.div>

        <motion.div
          variants={staggerContainer}
          initial="hidden"
          animate="show"
          className="space-y-4"
        >
          {/* Connection */}
          <motion.div variants={staggerItem}>
            <GlowCard glowColor={isConnected ? "success" : "error"} className="p-5">
              <div className="mb-4 flex items-center gap-3">
                {isConnected ? (
                  <Wifi className="h-5 w-5 text-success" />
                ) : (
                  <WifiOff className="h-5 w-5 text-error" />
                )}
                <h3 className="text-sm font-semibold text-text-secondary uppercase tracking-wide">
                  Подключение
                </h3>
              </div>
              <div className="space-y-3">
                <div className="flex items-center justify-between">
                  <span className="text-sm text-text-muted">API URL</span>
                  <span className="font-mono text-sm text-text-secondary">{apiUrl}</span>
                </div>
                <div className="flex items-center justify-between">
                  <span className="text-sm text-text-muted">Статус</span>
                  <span className={`text-sm font-medium ${isConnected ? "text-success" : "text-error"}`}>
                    {isConnected ? "Подключено" : "Не доступен"}
                  </span>
                </div>
                {health && (
                  <>
                    <div className="flex items-center justify-between">
                      <span className="text-sm text-text-muted">Окружение</span>
                      <span className="text-sm text-text-secondary">{health.env}</span>
                    </div>
                    <div className="flex items-center justify-between">
                      <span className="text-sm text-text-muted">Uptime</span>
                      <span className="font-mono text-sm text-text-secondary">
                        {Math.floor(health.uptime_seconds / 60)} мин
                      </span>
                    </div>
                  </>
                )}
              </div>
            </GlowCard>
          </motion.div>

          {/* Interface */}
          <motion.div variants={staggerItem}>
            <GlowCard className="p-5">
              <div className="mb-4 flex items-center gap-3">
                <Monitor className="h-5 w-5 text-is-blue" />
                <h3 className="text-sm font-semibold text-text-secondary uppercase tracking-wide">
                  Интерфейс
                </h3>
              </div>
              <div className="space-y-3">
                <div className="flex items-center justify-between">
                  <span className="text-sm text-text-muted">Тема</span>
                  <span className="text-sm text-text-secondary">Deep Navy Aurora</span>
                </div>
                <div className="flex items-center justify-between">
                  <span className="text-sm text-text-muted">Обновление KPI</span>
                  <span className="font-mono text-sm text-text-secondary">5 сек</span>
                </div>
                <div className="flex items-center justify-between">
                  <span className="text-sm text-text-muted">Команды</span>
                  <kbd className="rounded bg-bg-elevated px-2 py-0.5 text-xs text-text-muted font-mono">
                    Ctrl+K
                  </kbd>
                </div>
              </div>
            </GlowCard>
          </motion.div>

          {/* About */}
          <motion.div variants={staggerItem}>
            <GlowCard className="p-5">
              <div className="mb-4 flex items-center gap-3">
                <Info className="h-5 w-5 text-is-blue" />
                <h3 className="text-sm font-semibold text-text-secondary uppercase tracking-wide">
                  О системе
                </h3>
              </div>
              <div className="space-y-3">
                <div className="flex items-center justify-between">
                  <span className="text-sm text-text-muted">Версия</span>
                  <span className="font-mono text-sm text-text-secondary">
                    {health?.version || "0.1.0"}
                  </span>
                </div>
                <div className="flex items-center justify-between">
                  <span className="text-sm text-text-muted">Продукт</span>
                  <span className="text-sm text-is-blue font-medium">Аврора Суфлёр</span>
                </div>
                <div className="flex items-center justify-between">
                  <span className="text-sm text-text-muted">Фаза</span>
                  <span className="text-sm text-text-secondary">Phase 1 — MVP</span>
                </div>
              </div>
            </GlowCard>
          </motion.div>
        </motion.div>
      </div>
    </PageWrapper>
  );
}
