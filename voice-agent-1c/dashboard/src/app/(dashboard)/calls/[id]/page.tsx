"use client";

import { use } from "react";
import Link from "next/link";
import { motion } from "framer-motion";
import { ArrowLeft, Phone, Tag, MessageSquare, Database, User, Volume2 } from "lucide-react";
import { Skeleton } from "@/components/ui/skeleton";
import { DepartmentBadge, PriorityBadge } from "@/components/call-status-badge";
import { useCallDetail } from "@/hooks/use-dashboard";
import { formatDateTime, formatDuration, formatPhoneNumber } from "@/lib/format";
import { PRODUCT_LABELS, TASK_TYPE_LABELS } from "@/lib/constants";
import { voicesApi } from "@/lib/api";

const containerVariants = {
  hidden: { opacity: 0 },
  visible: {
    opacity: 1,
    transition: { staggerChildren: 0.1 },
  },
};

const itemVariants = {
  hidden: { opacity: 0, y: 20 },
  visible: { opacity: 1, y: 0, transition: { duration: 0.5, ease: [0.23, 1, 0.32, 1] as const } },
};

export default function CallDetailPage({
  params,
}: {
  params: Promise<{ id: string }>;
}) {
  const { id } = use(params);
  const { data: call, isLoading, isError } = useCallDetail(id);

  if (isLoading) {
    return (
      <div className="space-y-4">
        <Skeleton className="h-8 w-48 rounded-xl" />
        <div className="grid gap-4 md:grid-cols-2">
          <Skeleton className="h-64 rounded-2xl" />
          <Skeleton className="h-64 rounded-2xl" />
        </div>
        <Skeleton className="h-48 rounded-2xl" />
      </div>
    );
  }

  if (isError || !call) {
    return (
      <div className="space-y-4">
        <Link
          href="/calls"
          className="inline-flex items-center gap-2 text-sm text-muted-foreground hover:text-foreground transition-colors"
        >
          <ArrowLeft className="h-4 w-4" />
          {"Назад к журналу"}
        </Link>
        <div className="glass rounded-2xl border border-[oklch(0.65_0.22_25_/_0.3)] p-8 text-center">
          <p className="text-[oklch(0.65_0.22_25)]">{"Звонок не найден"}</p>
        </div>
      </div>
    );
  }

  const transcript = call.transcript;
  const classification = transcript?.classification;

  return (
    <motion.div
      className="space-y-6"
      variants={containerVariants}
      initial="hidden"
      animate="visible"
    >
      {/* Back */}
      <motion.div variants={itemVariants}>
        <Link
          href="/calls"
          className="inline-flex items-center gap-2 text-sm text-muted-foreground hover:text-[oklch(0.72_0.19_200)] transition-colors"
        >
          <ArrowLeft className="h-4 w-4" />
          {"Назад к журналу"}
        </Link>
      </motion.div>

      {/* Header */}
      <motion.div variants={itemVariants} className="flex flex-wrap items-center gap-3">
        <div className="rounded-xl bg-[oklch(0.72_0.19_200_/_0.12)] p-2.5">
          <Phone className="h-6 w-6 text-[oklch(0.72_0.19_200)]" />
        </div>
        <h1 className="text-xl font-bold">
          {"Звонок"} {formatPhoneNumber(call.caller_number)}
        </h1>
        <DepartmentBadge department={call.department} />
        <PriorityBadge priority={call.priority} />
        {call.is_known_client && (
          <span className="inline-flex items-center gap-1.5 rounded-full bg-[oklch(0.75_0.18_160_/_0.12)] px-3 py-1 text-xs font-medium text-[oklch(0.75_0.18_160)]">
            <User className="h-3 w-3" />
            {"Известный клиент"}
          </span>
        )}
      </motion.div>

      {/* Audio Player */}
      <motion.div variants={itemVariants} className="glass rounded-2xl border-gradient p-5">
        <div className="mb-3 flex items-center gap-2">
          <Volume2 className="h-4 w-4 text-[oklch(0.72_0.16_50)]" />
          <h2 className="text-sm font-medium uppercase tracking-wider text-muted-foreground">
            {"Запись звонка"}
          </h2>
        </div>
        <audio
          controls
          className="w-full h-10 rounded-lg"
          src={voicesApi.audioUrl(call.mango_call_id)}
          preload="none"
        >
          {"Ваш браузер не поддерживает воспроизведение аудио"}
        </audio>
        <p className="text-[10px] text-muted-foreground mt-2">
          {"Если запись недоступна, файл ещё не создан для этого звонка."}
        </p>
      </motion.div>

      <div className="grid gap-4 md:grid-cols-2">
        {/* Call Info */}
        <motion.div variants={itemVariants} className="glass rounded-2xl border-gradient p-5">
          <div className="mb-4 flex items-center gap-2">
            <Phone className="h-4 w-4 text-[oklch(0.72_0.19_200)]" />
            <h2 className="text-sm font-medium uppercase tracking-wider text-muted-foreground">
              {"Информация о звонке"}
            </h2>
          </div>
          <div className="space-y-3 text-sm">
            <InfoRow label={"Номер"} value={formatPhoneNumber(call.caller_number)} />
            <InfoRow label={"Клиент"} value={call.client_name ?? "Неизвестный"} />
            <InfoRow label={"Длительность"} value={formatDuration(call.duration_seconds)} />
            <InfoRow
              label={"Начало"}
              value={call.call_started_at ? formatDateTime(call.call_started_at) : "\u2014"}
            />
            <InfoRow
              label={"Окончание"}
              value={call.call_ended_at ? formatDateTime(call.call_ended_at) : "\u2014"}
            />
            {call.task_id && (
              <InfoRow label={"Задача"} value={`#${call.task_id}`} />
            )}
          </div>
        </motion.div>

        {/* Classification */}
        <motion.div variants={itemVariants} className="glass rounded-2xl border-gradient p-5">
          <div className="mb-4 flex items-center gap-2">
            <Tag className="h-4 w-4 text-[oklch(0.68_0.22_280)]" />
            <h2 className="text-sm font-medium uppercase tracking-wider text-muted-foreground">
              {"Классификация"}
            </h2>
          </div>
          <div className="space-y-3 text-sm">
            {classification ? (
              <>
                <InfoRow
                  label={"Продукт 1С"}
                  value={PRODUCT_LABELS[classification.product] ?? classification.product}
                />
                <InfoRow
                  label={"Тип обращения"}
                  value={TASK_TYPE_LABELS[classification.task_type] ?? classification.task_type}
                />
                <InfoRow
                  label={"Уверенность"}
                  value={`${(classification.confidence * 100).toFixed(0)}%`}
                />
                {classification.summary && (
                  <div className="pt-2 border-t border-[oklch(1_0_0_/_0.06)]">
                    <span className="text-xs text-muted-foreground block mb-1">{"Описание"}</span>
                    <p className="text-foreground/90 leading-relaxed">{classification.summary}</p>
                  </div>
                )}
              </>
            ) : (
              <p className="text-muted-foreground py-4 text-center">
                {"Классификация недоступна"}
              </p>
            )}
          </div>
        </motion.div>
      </div>

      {/* Transcript */}
      <motion.div variants={itemVariants} className="glass rounded-2xl border-gradient p-5">
        <div className="mb-4 flex items-center gap-2">
          <MessageSquare className="h-4 w-4 text-[oklch(0.75_0.18_160)]" />
          <h2 className="text-sm font-medium uppercase tracking-wider text-muted-foreground">
            {"Транскрипция"}
          </h2>
        </div>
        {transcript?.segments && transcript.segments.length > 0 ? (
          <div className="space-y-2 max-h-96 overflow-y-auto pr-2 scrollbar-thin">
            {transcript.segments.map((seg, i) => (
              <motion.div
                key={i}
                initial={{ opacity: 0, x: seg.speaker === "agent" ? -10 : 10 }}
                animate={{ opacity: 1, x: 0 }}
                transition={{ delay: i * 0.03, duration: 0.3 }}
                className={`flex gap-3 text-sm rounded-xl p-2.5 ${
                  seg.speaker === "agent"
                    ? "bg-[oklch(0.72_0.19_200_/_0.06)]"
                    : "bg-[oklch(0.68_0.22_280_/_0.06)]"
                }`}
              >
                <span className="font-mono text-[10px] text-muted-foreground min-w-[44px] pt-0.5">
                  {formatDuration(Math.floor(seg.start_time))}
                </span>
                <span className={`font-medium min-w-[72px] text-xs pt-0.5 ${
                  seg.speaker === "agent"
                    ? "text-[oklch(0.72_0.19_200)]"
                    : "text-[oklch(0.68_0.22_280)]"
                }`}>
                  {seg.speaker === "agent" ? "Агент" : "Клиент"}
                </span>
                <span className="text-foreground/90 leading-relaxed">{seg.text}</span>
              </motion.div>
            ))}
          </div>
        ) : transcript?.full_text ? (
          <p className="whitespace-pre-wrap text-sm text-foreground/90 leading-relaxed">
            {transcript.full_text}
          </p>
        ) : (
          <p className="text-muted-foreground text-sm py-4 text-center">
            {"Транскрипция недоступна"}
          </p>
        )}
      </motion.div>

      {/* Metadata */}
      <motion.div variants={itemVariants} className="glass rounded-2xl border-gradient p-5">
        <div className="mb-4 flex items-center gap-2">
          <Database className="h-4 w-4 text-[oklch(0.72_0.16_50)]" />
          <h2 className="text-sm font-medium uppercase tracking-wider text-muted-foreground">
            {"Служебные данные"}
          </h2>
        </div>
        <div className="space-y-3 text-sm">
          <InfoRow label="Mango ID" value={call.mango_call_id} />
          <InfoRow
            label={"Направление"}
            value={call.direction === "incoming" ? "Входящий" : "Исходящий"}
          />
          <InfoRow label={"Событие"} value={call.event_type} />
          {call.call_state && <InfoRow label={"Состояние"} value={call.call_state} />}
          {call.called_number && (
            <InfoRow label={"Вызываемый"} value={formatPhoneNumber(call.called_number)} />
          )}
        </div>
      </motion.div>
    </motion.div>
  );
}

function InfoRow({ label, value }: { label: string; value: string }) {
  return (
    <div className="flex justify-between items-center py-1">
      <span className="text-muted-foreground">{label}</span>
      <span className="font-medium text-foreground/90 font-mono text-xs">{value}</span>
    </div>
  );
}
