"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import {
  LayoutDashboard,
  Phone,
  Radio,
  Settings,
} from "lucide-react";
import { cn } from "@/lib/utils";

const NAV_ITEMS = [
  { href: "/", icon: LayoutDashboard, label: "Панель" },
  { href: "/calls", icon: Phone, label: "Звонки" },
  { href: "/live", icon: Radio, label: "Онлайн" },
  { href: "/settings", icon: Settings, label: "Настройки" },
];

export function Sidebar() {
  const pathname = usePathname();

  return (
    <aside className="fixed left-0 top-0 z-40 flex h-screen w-16 flex-col items-center border-r border-border-subtle bg-void-900 py-6">
      {/* Logo — InterSoft */}
      <div className="mb-8 flex h-10 w-10 items-center justify-center rounded-xl bg-gradient-to-br from-brand-500 to-accent-500">
        <span className="text-sm font-bold text-white tracking-tight">ИС</span>
      </div>

      {/* Navigation */}
      <nav className="flex flex-1 flex-col items-center gap-2">
        {NAV_ITEMS.map((item) => {
          const isActive =
            item.href === "/"
              ? pathname === "/"
              : pathname.startsWith(item.href);

          return (
            <Link
              key={item.href}
              href={item.href}
              className={cn(
                "group relative flex h-11 w-11 items-center justify-center rounded-xl transition-all duration-200",
                isActive
                  ? "bg-brand-500/15 text-brand-400"
                  : "text-text-muted hover:bg-surface-2 hover:text-text-secondary"
              )}
              title={item.label}
            >
              <item.icon className="h-5 w-5" />
              {isActive && (
                <span className="absolute left-0 top-1/2 h-5 w-0.5 -translate-y-1/2 rounded-r bg-brand-500" />
              )}
              {/* Tooltip */}
              <span className="pointer-events-none absolute left-14 whitespace-nowrap rounded-lg bg-void-600 px-3 py-1.5 text-xs text-text-primary opacity-0 shadow-lg transition-opacity group-hover:opacity-100">
                {item.label}
              </span>
            </Link>
          );
        })}
      </nav>

      {/* Connection status */}
      <div className="mt-auto flex flex-col items-center gap-3">
        <div className="flex items-center gap-1.5" title="Подключено">
          <span className="pulse-live h-2 w-2 rounded-full bg-success" />
        </div>
      </div>
    </aside>
  );
}
