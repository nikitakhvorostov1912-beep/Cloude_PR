"use client";

import { useState, useRef, useCallback } from "react";
import { motion } from "framer-motion";
import {
  Play,
  Square,
  Loader2,
  Mic,
  User,
  CheckCircle2,
  Volume2,
  Gauge,
} from "lucide-react";
import { Skeleton } from "@/components/ui/skeleton";
import { useVoices } from "@/hooks/use-dashboard";
import { voicesApi } from "@/lib/api";
import type { VoiceInfo } from "@/lib/types";

const containerVariants = {
  hidden: { opacity: 0 },
  visible: { opacity: 1, transition: { staggerChildren: 0.06 } },
};

const cardVariants = {
  hidden: { opacity: 0, y: 20, scale: 0.95 },
  visible: {
    opacity: 1,
    y: 0,
    scale: 1,
    transition: { duration: 0.4, ease: [0.23, 1, 0.32, 1] as const },
  },
};

const EMOTIONS_LABELS: Record<string, string> = {
  neutral: "Нейтральный",
  good: "Добрый",
  evil: "Строгий",
  friendly: "Дружелюбный",
  strict: "Формальный",
};

export default function VoicesPage() {
  const { data, isLoading, isError } = useVoices();
  const [playingId, setPlayingId] = useState<string | null>(null);
  const [loadingId, setLoadingId] = useState<string | null>(null);
  const [customText, setCustomText] = useState("");
  const [speed, setSpeed] = useState(1.0);
  const [selectedEmotion, setSelectedEmotion] = useState("neutral");
  const audioRef = useRef<HTMLAudioElement | null>(null);
  const objectUrlRef = useRef<string | null>(null);

  const cleanup = useCallback(() => {
    if (audioRef.current) {
      audioRef.current.pause();
      audioRef.current = null;
    }
    if (objectUrlRef.current) {
      URL.revokeObjectURL(objectUrlRef.current);
      objectUrlRef.current = null;
    }
    setPlayingId(null);
  }, []);

  const handlePlay = useCallback(
    async (voice: VoiceInfo) => {
      // Stop if already playing this voice
      if (playingId === voice.id) {
        cleanup();
        return;
      }

      cleanup();
      setLoadingId(voice.id);

      try {
        const url = await voicesApi.preview(
          voice.id,
          customText || voice.sample_text,
          speed,
          selectedEmotion,
        );
        objectUrlRef.current = url;

        const audio = new Audio(url);
        audioRef.current = audio;

        audio.onended = () => {
          setPlayingId(null);
        };
        audio.onerror = () => {
          setPlayingId(null);
          setLoadingId(null);
        };

        await audio.play();
        setPlayingId(voice.id);
      } catch {
        // silently handle
      } finally {
        setLoadingId(null);
      }
    },
    [playingId, customText, speed, selectedEmotion, cleanup],
  );

  if (isLoading) {
    return (
      <div className="space-y-6">
        <Skeleton className="h-8 w-64 rounded-xl" />
        <Skeleton className="h-16 rounded-2xl" />
        <div className="grid gap-4 md:grid-cols-2 lg:grid-cols-3">
          {Array.from({ length: 6 }).map((_, i) => (
            <Skeleton key={i} className="h-48 rounded-2xl" />
          ))}
        </div>
      </div>
    );
  }

  if (isError || !data) {
    return (
      <div className="glass rounded-2xl border border-[oklch(0.65_0.22_25_/_0.3)] p-8 text-center">
        <p className="text-[oklch(0.65_0.22_25)]">
          {"Не удалось загрузить список голосов. Проверьте подключение к серверу."}
        </p>
      </div>
    );
  }

  const { voices, active_voice, mode } = data;

  return (
    <motion.div
      className="space-y-6"
      variants={containerVariants}
      initial="hidden"
      animate="visible"
    >
      {/* Header */}
      <motion.div variants={cardVariants} className="flex items-center gap-3">
        <div className="rounded-xl bg-[oklch(0.68_0.22_280_/_0.12)] p-2.5">
          <Mic className="h-6 w-6 text-[oklch(0.68_0.22_280)]" />
        </div>
        <div>
          <h1 className="text-xl font-bold">{"Тестирование голосов"}</h1>
          <p className="text-xs text-muted-foreground">
            {mode === "yandex"
              ? "Yandex SpeechKit"
              : "Демо-режим (без API ключей)"}
          </p>
        </div>
      </motion.div>

      {/* Controls */}
      <motion.div
        variants={cardVariants}
        className="glass rounded-2xl border-gradient p-5 space-y-4"
      >
        {/* Custom text */}
        <div>
          <label className="text-xs text-muted-foreground uppercase tracking-wider font-medium block mb-2">
            {"Текст для озвучки"}
          </label>
          <textarea
            value={customText}
            onChange={(e) => setCustomText(e.target.value)}
            placeholder="Оставьте пустым для стандартной фразы..."
            maxLength={500}
            rows={2}
            className="w-full rounded-xl bg-[oklch(0.15_0_0)] border border-[oklch(1_0_0_/_0.08)] px-4 py-3 text-sm text-foreground placeholder:text-muted-foreground focus:outline-none focus:ring-1 focus:ring-[oklch(0.72_0.19_200_/_0.4)] resize-none"
          />
        </div>

        <div className="flex flex-wrap gap-6">
          {/* Speed */}
          <div className="flex-1 min-w-[200px]">
            <label className="text-xs text-muted-foreground uppercase tracking-wider font-medium flex items-center gap-2 mb-2">
              <Gauge className="h-3 w-3" />
              {"Скорость"}: {speed.toFixed(1)}x
            </label>
            <input
              type="range"
              min="0.5"
              max="2.0"
              step="0.1"
              value={speed}
              onChange={(e) => setSpeed(parseFloat(e.target.value))}
              className="w-full accent-[oklch(0.72_0.19_200)]"
            />
            <div className="flex justify-between text-[10px] text-muted-foreground mt-1">
              <span>0.5x</span>
              <span>1.0x</span>
              <span>2.0x</span>
            </div>
          </div>

          {/* Emotion */}
          <div className="flex-1 min-w-[200px]">
            <label className="text-xs text-muted-foreground uppercase tracking-wider font-medium flex items-center gap-2 mb-2">
              <Volume2 className="h-3 w-3" />
              {"Эмоция"}
            </label>
            <div className="flex flex-wrap gap-2">
              {["neutral", "good", "friendly", "strict"].map((emo) => (
                <button
                  key={emo}
                  onClick={() => setSelectedEmotion(emo)}
                  className={`px-3 py-1.5 rounded-lg text-xs font-medium transition-all ${
                    selectedEmotion === emo
                      ? "bg-[oklch(0.72_0.19_200_/_0.2)] text-[oklch(0.72_0.19_200)] ring-1 ring-[oklch(0.72_0.19_200_/_0.3)]"
                      : "bg-[oklch(1_0_0_/_0.04)] text-muted-foreground hover:bg-[oklch(1_0_0_/_0.08)]"
                  }`}
                >
                  {EMOTIONS_LABELS[emo] ?? emo}
                </button>
              ))}
            </div>
          </div>
        </div>
      </motion.div>

      {/* Voice Grid */}
      <motion.div
        variants={containerVariants}
        className="grid gap-4 md:grid-cols-2 lg:grid-cols-3"
      >
        {voices.map((voice) => (
          <VoiceCard
            key={voice.id}
            voice={voice}
            isActive={voice.id === active_voice}
            isPlaying={playingId === voice.id}
            isLoading={loadingId === voice.id}
            onPlay={() => handlePlay(voice)}
          />
        ))}
      </motion.div>

      {/* Mode info */}
      {mode === "demo" && (
        <motion.div
          variants={cardVariants}
          className="glass rounded-2xl border border-[oklch(0.72_0.16_50_/_0.2)] p-4 text-center"
        >
          <p className="text-xs text-muted-foreground">
            {"Демо-режим: голоса воспроизводятся как тональные сигналы. "}
            {"Для реальных голосов укажите YANDEX_API_KEY и YANDEX_FOLDER_ID в .env"}
          </p>
        </motion.div>
      )}
    </motion.div>
  );
}

function VoiceCard({
  voice,
  isActive,
  isPlaying,
  isLoading,
  onPlay,
}: {
  voice: VoiceInfo;
  isActive: boolean;
  isPlaying: boolean;
  isLoading: boolean;
  onPlay: () => void;
}) {
  const genderColor =
    voice.gender === "female"
      ? "oklch(0.68_0.22_280)"
      : "oklch(0.72_0.19_200)";

  return (
    <motion.div
      variants={cardVariants}
      className={`glass rounded-2xl border p-5 transition-all relative group ${
        isActive
          ? "border-[oklch(0.75_0.18_160_/_0.4)] ring-1 ring-[oklch(0.75_0.18_160_/_0.2)]"
          : "border-gradient hover:border-[oklch(0.72_0.19_200_/_0.2)]"
      }`}
    >
      {/* Active badge */}
      {isActive && (
        <div className="absolute top-3 right-3">
          <span className="inline-flex items-center gap-1 rounded-full bg-[oklch(0.75_0.18_160_/_0.12)] px-2.5 py-1 text-[10px] font-medium text-[oklch(0.75_0.18_160)]">
            <CheckCircle2 className="h-3 w-3" />
            {"Активный"}
          </span>
        </div>
      )}

      {/* Header */}
      <div className="flex items-center gap-3 mb-3">
        <div
          className="rounded-xl p-2"
          style={{ backgroundColor: `${genderColor} / 0.12` }}
        >
          {voice.gender === "female" ? (
            <User className="h-5 w-5" style={{ color: genderColor }} />
          ) : (
            <User className="h-5 w-5" style={{ color: genderColor }} />
          )}
        </div>
        <div>
          <h3 className="font-bold text-sm">{voice.name}</h3>
          <span className="text-[10px] text-muted-foreground uppercase tracking-wider">
            {voice.id} &middot;{" "}
            {voice.gender === "female" ? "Женский" : "Мужской"}
          </span>
        </div>
      </div>

      {/* Description */}
      <p className="text-xs text-foreground/70 mb-3 leading-relaxed">
        {voice.description}
      </p>

      {/* Emotions */}
      <div className="flex flex-wrap gap-1.5 mb-4">
        {voice.emotions.map((emo) => (
          <span
            key={emo}
            className="rounded-md bg-[oklch(1_0_0_/_0.04)] px-2 py-0.5 text-[10px] text-muted-foreground"
          >
            {EMOTIONS_LABELS[emo] ?? emo}
          </span>
        ))}
      </div>

      {/* Play button */}
      <button
        onClick={onPlay}
        disabled={isLoading}
        className={`w-full flex items-center justify-center gap-2 rounded-xl px-4 py-2.5 text-sm font-medium transition-all ${
          isPlaying
            ? "bg-[oklch(0.65_0.22_25_/_0.15)] text-[oklch(0.65_0.22_25)] hover:bg-[oklch(0.65_0.22_25_/_0.25)]"
            : "bg-[oklch(0.72_0.19_200_/_0.1)] text-[oklch(0.72_0.19_200)] hover:bg-[oklch(0.72_0.19_200_/_0.2)]"
        } disabled:opacity-50`}
      >
        {isLoading ? (
          <Loader2 className="h-4 w-4 animate-spin" />
        ) : isPlaying ? (
          <Square className="h-4 w-4" />
        ) : (
          <Play className="h-4 w-4" />
        )}
        {isLoading
          ? "Синтез..."
          : isPlaying
            ? "Остановить"
            : "Прослушать"}
      </button>

      {/* Waveform animation when playing */}
      {isPlaying && (
        <div className="flex items-center justify-center gap-[3px] mt-3 h-5">
          {Array.from({ length: 12 }).map((_, i) => (
            <motion.div
              key={i}
              className="w-[3px] rounded-full"
              style={{ backgroundColor: genderColor }}
              animate={{
                height: [4, 16, 8, 20, 6, 14],
              }}
              transition={{
                duration: 0.8,
                repeat: Infinity,
                delay: i * 0.05,
                ease: "easeInOut",
              }}
            />
          ))}
        </div>
      )}
    </motion.div>
  );
}
