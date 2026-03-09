"use client";

import { useRef } from "react";
import Link from "next/link";
import { usePathname } from "next/navigation";
import { motion, useMotionValue, useSpring, useTransform } from "framer-motion";
import {
  LayoutDashboard,
  Phone,
  Radio,
  Settings,
  type LucideIcon,
} from "lucide-react";
import { cn } from "@/lib/utils";

interface DockItem {
  href: string;
  icon: LucideIcon;
  label: string;
}

const NAV_ITEMS: DockItem[] = [
  { href: "/", icon: LayoutDashboard, label: "Панель" },
  { href: "/calls", icon: Phone, label: "Звонки" },
  { href: "/live", icon: Radio, label: "Онлайн" },
  { href: "/settings", icon: Settings, label: "Настройки" },
];

export function FloatingDock() {
  const mouseX = useMotionValue(Infinity);

  return (
    <motion.nav
      initial={{ y: 100, opacity: 0 }}
      animate={{ y: 0, opacity: 1 }}
      transition={{ type: "spring", stiffness: 300, damping: 25, delay: 0.5 }}
      onMouseMove={(e) => mouseX.set(e.pageX)}
      onMouseLeave={() => mouseX.set(Infinity)}
      className="floating-dock fixed bottom-5 left-1/2 z-40 flex -translate-x-1/2 items-end gap-2 px-4 py-3"
    >
      {NAV_ITEMS.map((item) => (
        <DockIcon key={item.href} item={item} mouseX={mouseX} />
      ))}
    </motion.nav>
  );
}

function DockIcon({
  item,
  mouseX,
}: {
  item: DockItem;
  mouseX: ReturnType<typeof useMotionValue<number>>;
}) {
  const ref = useRef<HTMLAnchorElement>(null);
  const pathname = usePathname();

  const isActive =
    item.href === "/" ? pathname === "/" : pathname.startsWith(item.href);

  const distance = useTransform(mouseX, (val: number) => {
    const rect = ref.current?.getBoundingClientRect();
    if (!rect) return 200;
    return val - rect.x - rect.width / 2;
  });

  const sizeSpring = useSpring(
    useTransform(distance, [-150, 0, 150], [48, 64, 48]),
    { stiffness: 300, damping: 25, mass: 0.5 }
  );

  const Icon = item.icon;

  return (
    <Link href={item.href} ref={ref} className="group relative">
      <motion.div
        style={{ width: sizeSpring, height: sizeSpring }}
        className={cn(
          "flex items-center justify-center rounded-2xl transition-colors duration-200",
          isActive
            ? "bg-navy/10 text-navy"
            : "bg-bg-section/80 text-text-muted hover:text-text-secondary"
        )}
      >
        <Icon className="h-5 w-5" />
        {isActive && (
          <motion.span
            layoutId="dock-active"
            className="absolute -bottom-1.5 h-1 w-1 rounded-full bg-is-red"
            transition={{ type: "spring", stiffness: 400, damping: 30 }}
          />
        )}
      </motion.div>

      {/* Tooltip */}
      <span className="pointer-events-none absolute -top-9 left-1/2 -translate-x-1/2 whitespace-nowrap rounded-lg bg-white px-3 py-1.5 text-xs text-text-primary opacity-0 shadow-lg border border-border-subtle transition-opacity group-hover:opacity-100">
        {item.label}
      </span>
    </Link>
  );
}
