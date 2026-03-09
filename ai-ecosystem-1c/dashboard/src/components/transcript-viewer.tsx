"use client";

import { useRef, useEffect } from "react";
import { motion, AnimatePresence } from "framer-motion";
import { cn } from "@/lib/utils";

export interface TranscriptMessage {
  id: string;
  speaker: "client" | "operator";
  text: string;
  timestamp: string;
  tags?: string[];
}

interface TranscriptViewerProps {
  messages: TranscriptMessage[];
  autoScroll?: boolean;
}

export function TranscriptViewer({
  messages,
  autoScroll = true,
}: TranscriptViewerProps) {
  const bottomRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    if (autoScroll && bottomRef.current) {
      bottomRef.current.scrollIntoView({ behavior: "smooth" });
    }
  }, [messages, autoScroll]);

  return (
    <div className="flex h-full flex-col">
      <h3 className="mb-3 text-sm font-semibold text-text-secondary uppercase tracking-wide">
        Транскрипт
      </h3>
      <div className="flex-1 space-y-3 overflow-y-auto pr-2">
        <AnimatePresence initial={false}>
          {messages.map((msg) => (
            <motion.div
              key={msg.id}
              initial={{ opacity: 0, y: 10, scale: 0.97 }}
              animate={{ opacity: 1, y: 0, scale: 1 }}
              transition={{ type: "spring", stiffness: 300, damping: 25 }}
              className={cn(
                "flex",
                msg.speaker === "operator" ? "justify-end" : "justify-start"
              )}
            >
              <div
                className={cn(
                  "max-w-[80%] rounded-2xl px-4 py-2.5",
                  msg.speaker === "operator"
                    ? "rounded-br-md bg-is-blue/10 text-is-blue-light"
                    : "rounded-bl-md bg-bg-elevated text-text-primary"
                )}
              >
                <p className="text-sm leading-relaxed">{msg.text}</p>
                <div className="mt-1 flex items-center gap-2">
                  <span className="text-xs text-text-muted">{msg.timestamp}</span>
                  {msg.tags?.map((tag) => (
                    <motion.span
                      key={tag}
                      initial={{ opacity: 0, scale: 0.8 }}
                      animate={{ opacity: 1, scale: 1 }}
                      transition={{ type: "spring", stiffness: 400, damping: 25 }}
                      className="rounded-md bg-is-blue/10 px-1.5 py-0.5 text-xs text-is-blue"
                    >
                      {tag}
                    </motion.span>
                  ))}
                </div>
              </div>
            </motion.div>
          ))}
        </AnimatePresence>
        <div ref={bottomRef} />
      </div>
    </div>
  );
}
