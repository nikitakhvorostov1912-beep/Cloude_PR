"use client";

import { useRef } from "react";
import { motion, useInView } from "framer-motion";
import {
  Monitor,
  Server,
  Cpu,
  Mic,
  Brain,
  BookOpen,
  MessageCircle,
  Phone,
  Database,
  Cloud,
  Bell,
  Building2,
} from "lucide-react";
import { staggerContainer, staggerItem } from "@/lib/motion";

const LAYERS = [
  {
    title: "Клиентский уровень",
    color: "border-is-blue/20",
    items: [
      { icon: Monitor, name: "Dashboard", detail: "Next.js / React", color: "text-is-blue" },
      { icon: Phone, name: "Телефония", detail: "Mango Office API", color: "text-is-blue-light" },
    ],
  },
  {
    title: "Оркестратор",
    color: "border-aurora-purple/20",
    items: [
      { icon: Server, name: "API Gateway", detail: "FastAPI + WebSocket", color: "text-aurora-purple" },
      { icon: Cpu, name: "Call Handler", detail: "Сессии + Routing", color: "text-aurora-purple" },
    ],
  },
  {
    title: "AI-агенты",
    color: "border-warning/20",
    items: [
      { icon: Mic, name: "Voice Agent", detail: "STT + VAD + TTS", color: "text-warning" },
      { icon: Brain, name: "Classifier", detail: "RuBERT / Claude", color: "text-warning" },
      { icon: BookOpen, name: "RAG Agent", detail: "Vector Search + KB", color: "text-warning" },
      { icon: MessageCircle, name: "Advisor", detail: "Подсказки оператору", color: "text-warning" },
    ],
  },
  {
    title: "Интеграции",
    color: "border-success/20",
    items: [
      { icon: Cloud, name: "Yandex STT/TTS", detail: "Распознавание речи", color: "text-success" },
      { icon: Building2, name: "1С HTTP", detail: "Данные конфигураций", color: "text-success" },
      { icon: Database, name: "Sakura CRM", detail: "Задачи и клиенты", color: "text-success" },
      { icon: Bell, name: "Telegram/SMS", detail: "Уведомления", color: "text-success" },
    ],
  },
];

export function SectionArchitecture() {
  const ref = useRef(null);
  const isInView = useInView(ref, { once: true, margin: "-100px" });

  return (
    <section id="architecture" className="pitch-section">
      <div ref={ref} className="pitch-section-inner">
        <motion.div
          initial={{ opacity: 0, y: 30 }}
          animate={isInView ? { opacity: 1, y: 0 } : {}}
          transition={{ type: "spring", stiffness: 300, damping: 24 }}
          className="mb-12 text-center"
        >
          <h2 className="mb-3 text-4xl font-bold text-text-primary">
            Архитектура системы
          </h2>
          <p className="mx-auto max-w-2xl text-lg text-text-muted">
            Модульная микросервисная архитектура с AI-агентами
          </p>
        </motion.div>

        <motion.div
          variants={staggerContainer}
          initial="hidden"
          animate={isInView ? "show" : "hidden"}
          className="space-y-6"
        >
          {LAYERS.map((layer, layerIndex) => (
            <motion.div key={layer.title} variants={staggerItem}>
              <div className={`rounded-2xl border ${layer.color} bg-bg-surface/30 p-5`}>
                <h3 className="mb-4 text-xs font-semibold uppercase tracking-wide text-text-muted">
                  {layer.title}
                </h3>
                <div className="grid grid-cols-2 gap-3 lg:grid-cols-4">
                  {layer.items.map((item) => (
                    <motion.div
                      key={item.name}
                      whileHover={{ scale: 1.03, y: -2 }}
                      transition={{ type: "spring", stiffness: 400, damping: 25 }}
                      className="glass-card flex items-center gap-3 p-3 cursor-default"
                    >
                      <div className="flex h-10 w-10 shrink-0 items-center justify-center rounded-xl bg-bg-elevated">
                        <item.icon className={`h-5 w-5 ${item.color}`} />
                      </div>
                      <div>
                        <p className="text-sm font-medium text-text-primary">
                          {item.name}
                        </p>
                        <p className="text-xs text-text-muted">{item.detail}</p>
                      </div>
                    </motion.div>
                  ))}
                </div>
              </div>

              {/* Connection arrow between layers */}
              {layerIndex < LAYERS.length - 1 && (
                <div className="flex justify-center py-2">
                  <svg width="24" height="24" viewBox="0 0 24 24" fill="none">
                    <path
                      d="M12 4V16M12 16L7 11M12 16L17 11"
                      stroke="rgba(125, 190, 244, 0.3)"
                      strokeWidth="2"
                      strokeLinecap="round"
                    />
                  </svg>
                </div>
              )}
            </motion.div>
          ))}
        </motion.div>
      </div>
    </section>
  );
}
