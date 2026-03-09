"use client";

import * as React from "react";
import Link from "next/link";
import { usePathname } from "next/navigation";
import {
  BarChart3,
  ClipboardList,
  FileText,
  FolderOpen,
  GitCompareArrows,
  LayoutDashboard,
  ListChecks,
  Upload,
  ChevronDown,
  Workflow,
} from "lucide-react";
import {
  Sidebar,
  SidebarContent,
  SidebarGroup,
  SidebarGroupContent,
  SidebarGroupLabel,
  SidebarHeader,
  SidebarMenu,
  SidebarMenuButton,
  SidebarMenuItem,
  SidebarSeparator,
} from "@/components/ui/sidebar";
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuTrigger,
} from "@/components/ui/dropdown-menu";
import type { Project } from "@/lib/types";

interface AppSidebarProps {
  project?: Project;
  projects?: Project[];
  onProjectSelect?: (id: string) => void;
}

const projectNavItems = [
  {
    label: "Обзор",
    href: "",
    icon: LayoutDashboard,
  },
  {
    label: "Загрузка",
    href: "/upload",
    icon: Upload,
  },
  {
    label: "Транскрипции",
    href: "/transcripts",
    icon: FileText,
  },
  {
    label: "Процессы",
    href: "/processes",
    icon: Workflow,
  },
  {
    label: "GAP-анализ",
    href: "/gaps",
    icon: GitCompareArrows,
  },
  {
    label: "Требования",
    href: "/requirements",
    icon: ListChecks,
  },
  {
    label: "Файлы",
    href: "/files",
    icon: FolderOpen,
  },
];

export function AppSidebar({ project, projects, onProjectSelect }: AppSidebarProps) {
  const pathname = usePathname();

  const isActive = (href: string) => {
    if (!project) return false;
    const fullPath = `/projects/${project.id}${href}`;
    if (href === "") {
      return pathname === `/projects/${project.id}`;
    }
    return pathname.startsWith(fullPath);
  };

  return (
    <Sidebar>
      <SidebarHeader>
        <Link href="/" className="flex items-center gap-2 px-2 py-1.5">
          <BarChart3 className="size-6 text-primary" />
          <span className="text-lg font-semibold">Survey Automation</span>
        </Link>
      </SidebarHeader>

      <SidebarSeparator />

      <SidebarContent>
        {/* Project selector */}
        {project && projects && projects.length > 0 && (
          <SidebarGroup>
            <SidebarGroupLabel>Проект</SidebarGroupLabel>
            <SidebarGroupContent>
              <DropdownMenu>
                <DropdownMenuTrigger asChild>
                  <button className="flex w-full items-center justify-between rounded-md border border-border bg-background px-3 py-2 text-sm hover:bg-accent transition-colors">
                    <span className="truncate">{project.name}</span>
                    <ChevronDown className="ml-2 size-4 shrink-0 opacity-50" />
                  </button>
                </DropdownMenuTrigger>
                <DropdownMenuContent align="start" className="w-[--radix-dropdown-menu-trigger-width]">
                  {projects.map((p) => (
                    <DropdownMenuItem
                      key={p.id}
                      onClick={() => onProjectSelect?.(p.id)}
                    >
                      <ClipboardList className="mr-2 size-4" />
                      <span className="truncate">{p.name}</span>
                    </DropdownMenuItem>
                  ))}
                </DropdownMenuContent>
              </DropdownMenu>
            </SidebarGroupContent>
          </SidebarGroup>
        )}

        {/* Navigation */}
        <SidebarGroup>
          <SidebarGroupLabel>Навигация</SidebarGroupLabel>
          <SidebarGroupContent>
            <SidebarMenu>
              {!project ? (
                <SidebarMenuItem>
                  <SidebarMenuButton asChild isActive={pathname === "/"}>
                    <Link href="/">
                      <ClipboardList className="size-4" />
                      <span>Проекты</span>
                    </Link>
                  </SidebarMenuButton>
                </SidebarMenuItem>
              ) : (
                projectNavItems.map((item) => (
                  <SidebarMenuItem key={item.href}>
                    <SidebarMenuButton
                      asChild
                      isActive={isActive(item.href)}
                    >
                      <Link href={`/projects/${project.id}${item.href}`}>
                        <item.icon className="size-4" />
                        <span>{item.label}</span>
                      </Link>
                    </SidebarMenuButton>
                  </SidebarMenuItem>
                ))
              )}
            </SidebarMenu>
          </SidebarGroupContent>
        </SidebarGroup>
      </SidebarContent>
    </Sidebar>
  );
}
