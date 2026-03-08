"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import { LayoutDashboard, Phone, Headphones, Activity, Mic } from "lucide-react";
import {
  Sidebar,
  SidebarContent,
  SidebarFooter,
  SidebarGroup,
  SidebarGroupContent,
  SidebarHeader,
  SidebarMenu,
  SidebarMenuButton,
  SidebarMenuItem,
} from "@/components/ui/sidebar";
import { ConnectionIndicator } from "./connection-indicator";

const NAV_ITEMS = [
  { title: "\u0413\u043b\u0430\u0432\u043d\u0430\u044f", href: "/", icon: LayoutDashboard },
  { title: "\u0417\u0432\u043e\u043d\u043a\u0438", href: "/calls", icon: Phone },
  { title: "\u0413\u043e\u043b\u043e\u0441\u0430", href: "/voices", icon: Mic },
];

export function AppSidebar() {
  const pathname = usePathname();

  return (
    <Sidebar className="border-r-0">
      <SidebarHeader className="px-4 py-4">
        <div className="flex items-center gap-3">
          <div className="rounded-xl bg-[oklch(0.72_0.19_200_/_0.15)] p-2 glow-cyan">
            <Headphones className="h-5 w-5 text-[oklch(0.72_0.19_200)]" />
          </div>
          <div>
            <span className="font-bold text-sm text-gradient">Voice Agent</span>
            <p className="text-[10px] text-muted-foreground uppercase tracking-widest">1C</p>
          </div>
        </div>
      </SidebarHeader>

      <SidebarContent className="px-2">
        <SidebarGroup>
          <SidebarGroupContent>
            <SidebarMenu>
              {NAV_ITEMS.map((item) => {
                const isActive =
                  item.href === "/"
                    ? pathname === "/"
                    : pathname.startsWith(item.href);
                return (
                  <SidebarMenuItem key={item.href}>
                    <SidebarMenuButton
                      asChild
                      isActive={isActive}
                      className={isActive ? "glass glow-cyan" : ""}
                    >
                      <Link href={item.href}>
                        <item.icon className="h-4 w-4" />
                        <span>{item.title}</span>
                      </Link>
                    </SidebarMenuButton>
                  </SidebarMenuItem>
                );
              })}
            </SidebarMenu>
          </SidebarGroupContent>
        </SidebarGroup>
      </SidebarContent>

      <SidebarFooter className="px-4 pb-4">
        <div className="glass rounded-xl p-3">
          <div className="flex items-center gap-2 mb-2">
            <Activity className="h-3 w-3 text-muted-foreground" />
            <span className="text-[10px] uppercase tracking-wider text-muted-foreground font-medium">
              {"\u0421\u0442\u0430\u0442\u0443\u0441"}
            </span>
          </div>
          <ConnectionIndicator />
        </div>
      </SidebarFooter>
    </Sidebar>
  );
}
