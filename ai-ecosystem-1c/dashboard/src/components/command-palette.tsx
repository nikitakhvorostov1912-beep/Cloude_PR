"use client";

import { useEffect, useState, useCallback } from "react";
import { useRouter } from "next/navigation";
import { motion, AnimatePresence } from "framer-motion";
import { Command } from "cmdk";
import { Search, Phone, FileText, Zap, Radio, Settings, LayoutDashboard, X } from "lucide-react";

export function CommandPalette() {
  const [open, setOpen] = useState(false);
  const router = useRouter();

  const handleKeyDown = useCallback((e: KeyboardEvent) => {
    if ((e.metaKey || e.ctrlKey) && e.key === "k") {
      e.preventDefault();
      setOpen((prev) => !prev);
    }
    if (e.key === "Escape") {
      setOpen(false);
    }
  }, []);

  useEffect(() => {
    document.addEventListener("keydown", handleKeyDown);
    return () => document.removeEventListener("keydown", handleKeyDown);
  }, [handleKeyDown]);

  // Listen for external open event (from TopNav button)
  useEffect(() => {
    const handler = () => setOpen(true);
    window.addEventListener("command-palette:open", handler);
    return () => window.removeEventListener("command-palette:open", handler);
  }, []);

  const navigate = (path: string) => {
    router.push(path);
    setOpen(false);
  };

  return (
    <AnimatePresence>
      {open && (
        <div className="fixed inset-0 z-[60] flex items-start justify-center pt-[20vh]">
          {/* Backdrop */}
          <motion.div
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            exit={{ opacity: 0 }}
            transition={{ duration: 0.15 }}
            className="absolute inset-0 bg-bg-deepest/60 backdrop-blur-sm"
            onClick={() => setOpen(false)}
          />

          {/* Dialog */}
          <motion.div
            initial={{ opacity: 0, scale: 0.95, y: -10 }}
            animate={{ opacity: 1, scale: 1, y: 0 }}
            exit={{ opacity: 0, scale: 0.95, y: -10 }}
            transition={{ type: "spring", stiffness: 400, damping: 30 }}
            className="glass-card relative w-full max-w-lg overflow-hidden"
          >
            <Command className="flex flex-col">
              {/* Input */}
              <div className="flex items-center gap-3 border-b border-border-subtle px-4">
                <Search className="h-4 w-4 text-is-blue" />
                <Command.Input
                  placeholder="Поиск звонков, клиентов, действий..."
                  className="h-12 flex-1 bg-transparent text-sm text-text-primary outline-none placeholder:text-text-muted"
                  autoFocus
                />
                <button
                  onClick={() => setOpen(false)}
                  className="rounded-lg p-1 text-text-muted hover:bg-bg-elevated hover:text-text-secondary"
                >
                  <X className="h-4 w-4" />
                </button>
              </div>

              {/* Results */}
              <Command.List className="max-h-72 overflow-y-auto p-2">
                <Command.Empty className="py-6 text-center text-sm text-text-muted">
                  Ничего не найдено
                </Command.Empty>

                <Command.Group
                  heading="Навигация"
                  className="px-2 py-1.5 text-xs font-medium text-text-muted"
                >
                  <CommandItem icon={LayoutDashboard} label="Панель" shortcut="⌘1" onSelect={() => navigate("/")} />
                  <CommandItem icon={Phone} label="Звонки" shortcut="⌘2" onSelect={() => navigate("/calls")} />
                  <CommandItem icon={Radio} label="Онлайн" shortcut="⌘3" onSelect={() => navigate("/live")} />
                  <CommandItem icon={Settings} label="Настройки" shortcut="⌘4" onSelect={() => navigate("/settings")} />
                </Command.Group>

                <Command.Group
                  heading="Быстрые действия"
                  className="px-2 py-1.5 text-xs font-medium text-text-muted"
                >
                  <CommandItem icon={FileText} label="Недавние задачи" shortcut="⌘T" onSelect={() => navigate("/calls")} />
                  <CommandItem icon={Zap} label="Эскалации" shortcut="⌘E" onSelect={() => navigate("/calls")} />
                </Command.Group>
              </Command.List>

              {/* Footer */}
              <div className="flex items-center justify-between border-t border-border-subtle px-4 py-2">
                <span className="text-xs text-text-muted">
                  Навигация: ↑↓ &bull; Выбор: Enter &bull; Закрыть: Esc
                </span>
                <kbd className="rounded bg-bg-elevated px-1.5 py-0.5 text-xs text-text-muted font-mono">
                  Ctrl+K
                </kbd>
              </div>
            </Command>
          </motion.div>
        </div>
      )}
    </AnimatePresence>
  );
}

function CommandItem({
  icon: Icon,
  label,
  shortcut,
  onSelect,
}: {
  icon: React.ComponentType<{ className?: string }>;
  label: string;
  shortcut: string;
  onSelect: () => void;
}) {
  return (
    <Command.Item
      onSelect={onSelect}
      className="flex cursor-pointer items-center gap-3 rounded-xl px-3 py-2.5 text-sm text-text-secondary transition-colors hover:bg-bg-elevated hover:text-text-primary data-[selected=true]:bg-bg-elevated data-[selected=true]:text-text-primary"
    >
      <Icon className="h-4 w-4 text-text-muted" />
      <span className="flex-1">{label}</span>
      <kbd className="rounded bg-bg-surface px-1.5 py-0.5 text-xs text-text-muted font-mono">
        {shortcut}
      </kbd>
    </Command.Item>
  );
}
