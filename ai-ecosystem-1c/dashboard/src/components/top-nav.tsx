"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import { motion } from "framer-motion";
import {
  LayoutDashboard,
  Phone,
  Radio,
  Settings,
  Search,
  type LucideIcon,
} from "lucide-react";
import { cn } from "@/lib/utils";
import { AuroraLogo } from "@/components/aurora-logo";

interface NavItem {
  href: string;
  icon: LucideIcon;
  label: string;
}

const NAV_ITEMS: NavItem[] = [
  { href: "/", icon: LayoutDashboard, label: "Панель" },
  { href: "/calls", icon: Phone, label: "Звонки" },
  { href: "/live", icon: Radio, label: "Онлайн" },
  { href: "/settings", icon: Settings, label: "Настройки" },
];

interface TopNavProps {
  onCommandOpen: () => void;
}

export function TopNav({ onCommandOpen }: TopNavProps) {
  const pathname = usePathname();

  return (
    <motion.nav
      initial={{ y: -60, opacity: 0 }}
      animate={{ y: 0, opacity: 1 }}
      transition={{ type: "spring", stiffness: 300, damping: 25 }}
      className="top-nav fixed top-0 left-0 right-0 z-50 flex h-14 items-center px-6"
    >
      {/* Left — Logo */}
      <div className="flex items-center gap-3">
        <AuroraLogo size="sm" />
      </div>

      {/* Center — Navigation */}
      <div className="ml-8 flex items-center gap-1">
        {NAV_ITEMS.map((item) => {
          const isActive =
            item.href === "/"
              ? pathname === "/"
              : pathname.startsWith(item.href);
          const Icon = item.icon;

          return (
            <Link key={item.href} href={item.href}>
              <motion.div
                className={cn(
                  "relative flex items-center gap-2 rounded-lg px-3 py-1.5 text-sm transition-colors",
                  isActive
                    ? "text-text-primary"
                    : "text-text-muted hover:text-text-secondary"
                )}
                whileHover={{ scale: 1.04 }}
                whileTap={{ scale: 0.97 }}
                transition={{ type: "spring", stiffness: 400, damping: 25 }}
              >
                {isActive && (
                  <motion.div
                    layoutId="nav-active"
                    className="absolute inset-0 rounded-lg bg-bg-elevated"
                    style={{ borderRadius: 8 }}
                    transition={{ type: "spring", stiffness: 400, damping: 30 }}
                  />
                )}
                <span className="relative z-10 flex items-center gap-2">
                  <Icon className="h-4 w-4" />
                  <span className="font-medium">{item.label}</span>
                </span>
              </motion.div>
            </Link>
          );
        })}
      </div>

      {/* Right — Command palette trigger */}
      <div className="ml-auto">
        <motion.button
          onClick={onCommandOpen}
          whileHover={{ scale: 1.05 }}
          whileTap={{ scale: 0.95 }}
          transition={{ type: "spring", stiffness: 400, damping: 25 }}
          className="flex items-center gap-2 rounded-lg border border-border-subtle bg-surface-1 px-3 py-1.5 text-xs text-text-muted transition-colors hover:border-border-default hover:text-text-secondary"
        >
          <Search className="h-3.5 w-3.5" />
          <span>Поиск</span>
          <kbd className="ml-1 rounded bg-bg-elevated px-1.5 py-0.5 text-[10px] font-mono">
            Ctrl+K
          </kbd>
        </motion.button>
      </div>
    </motion.nav>
  );
}
