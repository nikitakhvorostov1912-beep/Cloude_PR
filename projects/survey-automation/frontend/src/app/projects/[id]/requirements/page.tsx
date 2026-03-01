"use client";

import * as React from "react";
import { useParams } from "next/navigation";
import { useQuery } from "@tanstack/react-query";
import {
  ListChecks,
  Filter,
  FileSpreadsheet,
  FileText,
  Download,
} from "lucide-react";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
import {
  Table,
  TableBody,
  TableCell,
  TableFooter,
  TableHead,
  TableHeader,
  TableRow,
} from "@/components/ui/table";
import { Skeleton } from "@/components/ui/skeleton";
import { dataApi, exportApi } from "@/lib/api";
import type { Requirement } from "@/lib/types";

const typeLabels: Record<string, string> = {
  functional: "FR",
  non_functional: "NFR",
  integration: "IR",
  data: "DR",
  security: "SR",
};

const typeFullLabels: Record<string, string> = {
  functional: "Функциональное",
  non_functional: "Нефункциональное",
  integration: "Интеграционное",
  data: "Данные",
  security: "Безопасность",
};

const priorityLabels: Record<string, string> = {
  critical: "Must",
  high: "Should",
  medium: "Could",
  low: "Won't",
};

const priorityColors: Record<string, string> = {
  critical: "bg-red-500/10 text-red-500 border-red-500/30",
  high: "bg-orange-500/10 text-orange-500 border-orange-500/30",
  medium: "bg-yellow-500/10 text-yellow-500 border-yellow-500/30",
  low: "bg-zinc-500/10 text-zinc-400 border-zinc-500/30",
};

const statusLabels: Record<string, string> = {
  draft: "Черновик",
  reviewed: "Проверено",
  approved: "Утверждено",
  rejected: "Отклонено",
};

export default function RequirementsPage() {
  const params = useParams<{ id: string }>();
  const projectId = params.id;
  const [typeFilter, setTypeFilter] = React.useState<string>("all");
  const [priorityFilter, setPriorityFilter] = React.useState<string>("all");

  const { data, isLoading } = useQuery({
    queryKey: ["requirements", projectId],
    queryFn: () => dataApi.requirements(projectId),
    enabled: !!projectId,
  });

  const requirements = data?.requirements ?? [];

  const filtered = React.useMemo(() => {
    let result = requirements;
    if (typeFilter !== "all") {
      result = result.filter((r) => r.requirement_type === typeFilter);
    }
    if (priorityFilter !== "all") {
      result = result.filter((r) => r.priority === priorityFilter);
    }
    return result;
  }, [requirements, typeFilter, priorityFilter]);

  // Counts for summary
  const counts = React.useMemo(() => {
    const byType: Record<string, number> = {};
    const byPriority: Record<string, number> = {};
    requirements.forEach((r) => {
      byType[r.requirement_type] = (byType[r.requirement_type] ?? 0) + 1;
      byPriority[r.priority] = (byPriority[r.priority] ?? 0) + 1;
    });
    return { byType, byPriority, total: requirements.length };
  }, [requirements]);

  if (isLoading) {
    return (
      <div className="space-y-4">
        <Skeleton className="h-8 w-48" />
        <Skeleton className="h-10 w-full" />
        <Skeleton className="h-64" />
      </div>
    );
  }

  return (
    <div className="space-y-6">
      <div className="flex flex-col gap-4 sm:flex-row sm:items-center sm:justify-between">
        <div>
          <h2 className="text-2xl font-bold tracking-tight">Требования</h2>
          <p className="mt-1 text-muted-foreground">
            Всего требований: {counts.total}
          </p>
        </div>
        <div className="flex items-center gap-2">
          <Button variant="outline" size="sm" asChild>
            <a
              href={exportApi.requirementsExcel(projectId)}
              target="_blank"
              rel="noopener noreferrer"
            >
              <FileSpreadsheet className="mr-1 size-4" />
              Excel
            </a>
          </Button>
          <Button variant="outline" size="sm" asChild>
            <a
              href={exportApi.requirementsWord(projectId)}
              target="_blank"
              rel="noopener noreferrer"
            >
              <FileText className="mr-1 size-4" />
              Word
            </a>
          </Button>
        </div>
      </div>

      {/* Filters */}
      <div className="flex flex-wrap items-center gap-3">
        <div className="flex items-center gap-2">
          <Filter className="size-4 text-muted-foreground" />
          <span className="text-sm text-muted-foreground">Фильтры:</span>
        </div>
        <Select value={typeFilter} onValueChange={setTypeFilter}>
          <SelectTrigger className="w-[180px]">
            <SelectValue placeholder="Тип требования" />
          </SelectTrigger>
          <SelectContent>
            <SelectItem value="all">Все типы</SelectItem>
            <SelectItem value="functional">Функциональное (FR)</SelectItem>
            <SelectItem value="non_functional">Нефункциональное (NFR)</SelectItem>
            <SelectItem value="integration">Интеграционное (IR)</SelectItem>
            <SelectItem value="data">Данные (DR)</SelectItem>
            <SelectItem value="security">Безопасность (SR)</SelectItem>
          </SelectContent>
        </Select>
        <Select value={priorityFilter} onValueChange={setPriorityFilter}>
          <SelectTrigger className="w-[160px]">
            <SelectValue placeholder="Приоритет" />
          </SelectTrigger>
          <SelectContent>
            <SelectItem value="all">Все приоритеты</SelectItem>
            <SelectItem value="critical">Must</SelectItem>
            <SelectItem value="high">Should</SelectItem>
            <SelectItem value="medium">Could</SelectItem>
            <SelectItem value="low">Won't</SelectItem>
          </SelectContent>
        </Select>
        {(typeFilter !== "all" || priorityFilter !== "all") && (
          <Button
            variant="ghost"
            size="sm"
            onClick={() => {
              setTypeFilter("all");
              setPriorityFilter("all");
            }}
          >
            Сбросить
          </Button>
        )}
      </div>

      {/* Requirements table */}
      {requirements.length === 0 ? (
        <div className="flex flex-col items-center justify-center rounded-lg border border-dashed py-16">
          <ListChecks className="mb-4 size-12 text-muted-foreground" />
          <p className="text-lg font-medium">Нет требований</p>
          <p className="mt-1 text-sm text-muted-foreground">
            Требования будут сформированы на основе GAP-анализа
          </p>
        </div>
      ) : (
        <div className="rounded-md border">
          <Table>
            <TableHeader>
              <TableRow>
                <TableHead className="w-20">ID</TableHead>
                <TableHead className="w-16">Тип</TableHead>
                <TableHead>Описание</TableHead>
                <TableHead className="w-24">Приоритет</TableHead>
                <TableHead className="w-24">Статус</TableHead>
              </TableRow>
            </TableHeader>
            <TableBody>
              {filtered.map((req, index) => (
                <TableRow key={req.id}>
                  <TableCell className="font-mono text-xs">
                    {typeLabels[req.requirement_type] ?? "REQ"}-{String(index + 1).padStart(3, "0")}
                  </TableCell>
                  <TableCell>
                    <Badge variant="outline" className="text-xs">
                      {typeLabels[req.requirement_type] ?? req.requirement_type}
                    </Badge>
                  </TableCell>
                  <TableCell>
                    <div>
                      <p className="text-sm font-medium">{req.title}</p>
                      <p className="line-clamp-1 text-xs text-muted-foreground">
                        {req.description}
                      </p>
                    </div>
                  </TableCell>
                  <TableCell>
                    <Badge
                      className={`text-xs border ${priorityColors[req.priority] ?? ""}`}
                    >
                      {priorityLabels[req.priority] ?? req.priority}
                    </Badge>
                  </TableCell>
                  <TableCell>
                    <span className="text-xs text-muted-foreground">
                      {statusLabels[req.status] ?? req.status}
                    </span>
                  </TableCell>
                </TableRow>
              ))}
            </TableBody>
            <TableFooter>
              <TableRow>
                <TableCell colSpan={5}>
                  <div className="flex flex-wrap items-center gap-3 text-xs">
                    <span>
                      Показано: {filtered.length} из {requirements.length}
                    </span>
                    <span className="text-muted-foreground">|</span>
                    {Object.entries(counts.byPriority).map(([key, val]) => (
                      <Badge
                        key={key}
                        className={`text-xs border ${priorityColors[key] ?? ""}`}
                      >
                        {priorityLabels[key] ?? key}: {val}
                      </Badge>
                    ))}
                  </div>
                </TableCell>
              </TableRow>
            </TableFooter>
          </Table>
        </div>
      )}
    </div>
  );
}
