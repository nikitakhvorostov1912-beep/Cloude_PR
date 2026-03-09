"use client";

import { useEffect, useRef } from "react";
import { motion, AnimatePresence } from "framer-motion";
import { Headphones, User } from "lucide-react";

export interface TranscriptEntry {
  id: string;
  speaker: "operator" | "client";
  text: string;
  tags?: string[];
  /** Label displayed next to speaker name */
  speakerLabel?: string;
}

interface DemoTranscriptProps {
  entries: TranscriptEntry[];
  activeEntryIndex: number;
  revealedChars: number;
  isTyping: boolean;
}

export function DemoTranscript({
  entries,
  activeEntryIndex,
  revealedChars,
  isTyping,
}: DemoTranscriptProps) {
  const scrollRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    if (scrollRef.current) {
      scrollRef.current.scrollTop = scrollRef.current.scrollHeight;
    }
  }, [activeEntryIndex, revealedChars]);

  return (
    <div className="flex h-full flex-col">
      <div className="mb-3 flex items-center justify-between">
        <h3 className="text-sm font-semibold uppercase tracking-wide text-text-secondary">
          Транскрипт звонка
        </h3>
        {isTyping && <WaveformIndicator />}
      </div>
      <div
        ref={scrollRef}
        className="flex-1 space-y-3 overflow-y-auto pr-2"
        style={{ maxHeight: "500px" }}
      >
        <AnimatePresence>
          {entries.slice(0, activeEntryIndex + 1).map((entry, i) => {
            const isActive = i === activeEntryIndex;
            const displayText = isActive
              ? entry.text.slice(0, revealedChars)
              : entry.text;
            const isOp = entry.speaker === "operator";
            const label = entry.speakerLabel ?? (isOp ? "Аврора" : "Клиент");

            return (
              <motion.div
                key={entry.id}
                initial={{ opacity: 0, x: isOp ? -20 : 20 }}
                animate={{ opacity: 1, x: 0 }}
                transition={{ type: "spring", stiffness: 400, damping: 30 }}
                className="flex gap-2.5"
              >
                {/* Avatar */}
                <div
                  className={`mt-1 flex h-7 w-7 shrink-0 items-center justify-center rounded-full ${
                    isOp
                      ? "bg-is-blue/15 text-is-blue"
                      : "bg-aurora-purple/15 text-aurora-purple"
                  }`}
                >
                  {isOp ? (
                    <Headphones className="h-3.5 w-3.5" />
                  ) : (
                    <User className="h-3.5 w-3.5" />
                  )}
                </div>

                {/* Bubble */}
                <div className="flex-1 min-w-0">
                  <p className={`mb-0.5 text-[10px] font-semibold uppercase tracking-wider ${
                    isOp ? "text-is-blue" : "text-aurora-purple"
                  }`}>
                    {label}
                  </p>
                  <div
                    className={`rounded-xl px-3.5 py-2.5 text-[13px] leading-relaxed ${
                      isOp
                        ? "bg-is-blue/8 text-text-primary border border-is-blue/10"
                        : "bg-aurora-purple/8 text-text-primary border border-aurora-purple/10"
                    }`}
                  >
                    <span>{highlightKeywords(displayText, isActive ? [] : (entry.tags ?? []))}</span>
                    {isActive && isTyping && <span className="typewriter-cursor" />}
                  </div>

                  {/* Tags after typing */}
                  {!isActive && entry.tags && entry.tags.length > 0 && (
                    <div className="mt-1.5 flex flex-wrap gap-1">
                      {entry.tags.map((tag, ti) => (
                        <motion.span
                          key={tag}
                          initial={{ opacity: 0, scale: 0.7, y: 5 }}
                          animate={{ opacity: 1, scale: 1, y: 0 }}
                          transition={{ delay: ti * 0.08 }}
                          className="demo-tag"
                        >
                          {tag}
                        </motion.span>
                      ))}
                    </div>
                  )}
                </div>
              </motion.div>
            );
          })}
        </AnimatePresence>
      </div>
    </div>
  );
}

/** Highlight matching keywords in text */
function highlightKeywords(text: string, tags: string[]): React.ReactNode {
  if (tags.length === 0) return text;

  // Build regex from tags
  const escaped = tags.map((t) => t.replace(/[.*+?^${}()|[\]\\]/g, "\\$&"));
  const regex = new RegExp(`(${escaped.join("|")})`, "gi");
  const parts = text.split(regex);

  return parts.map((part, i) => {
    const isMatch = tags.some((t) => t.toLowerCase() === part.toLowerCase());
    if (isMatch) {
      return (
        <span key={i} className="rounded bg-is-blue/15 px-0.5 text-is-blue-light font-medium">
          {part}
        </span>
      );
    }
    return part;
  });
}

/** Small animated waveform bars */
function WaveformIndicator() {
  return (
    <div className="flex items-end gap-[2px] h-4">
      {[0, 1, 2, 3, 4].map((i) => (
        <motion.div
          key={i}
          className="w-[2px] rounded-full bg-is-blue"
          animate={{
            height: ["4px", `${8 + Math.random() * 8}px`, "4px"],
          }}
          transition={{
            duration: 0.4 + Math.random() * 0.3,
            repeat: Infinity,
            delay: i * 0.07,
          }}
        />
      ))}
    </div>
  );
}
