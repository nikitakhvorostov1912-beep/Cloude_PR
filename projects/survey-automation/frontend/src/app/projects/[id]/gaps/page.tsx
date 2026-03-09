"use client";

import * as React from "react";
import { useParams } from "next/navigation";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { toast } from "sonner";
import {
  GitCompareArrows,
  Play,
  Loader2,
  AlertTriangle,
  BarChart3,
} from "lucide-react";
import { Button } from "@/components/ui/button";
import {
  Card,
  CardContent,
  CardHeader,
  CardTitle,
} from "@/components/ui/card";
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
  TableHead,
  TableHeader,
  TableRow,
} from "@/components/ui/table";
import { Skeleton } from "@/components/ui/skeleton";
import { pipelineApi, dataApi } from "@/lib/api";

const erpOptions = [
  { value: "1c_erp", label: "1С:ERP" },
  { value: "1c_ka", label: "1С:КА" },
  { value: "1c_ut", label: "1С:УТ" },
  { value: "1c_zup", label: "1С:ЗУП" },
];

const severityLabels: Record<string, string> = {
  low: "Низкая",
  medium: "Средняя",
  high: "Высокая",
  critical: "Критичная",
};

const severityVariants: Record<string, "default" | "secondary" | "destructive" | "outline"> = {
  low: "outline",
  medium: "secondary",
  high: "default",
  critical: "destructive",
};

const gapTypeLabels: Record<string, string> = {
  missing_feature: "Отсутствует функция",
  customization: "Необходима доработка",
  integration: "Интеграция",
  workflow: "Бизнес-процесс",
  data_migration: "Миграция данных",
};


export default function GapsPage() {
  const params = useParams<{ id: string }>();
  const projectId = params.id;
  const queryClient = useQueryClient();
  const [erpConfig, setErpConfig] = React.useState("1c_erp");

  const { data, isLoading } = useQuery({
    queryKey: ["gaps", projectId],
    queryFn: () => dataApi.gaps(projectId),
    enabled: !!projectId,
  });

  const runGapMutation = useMutation({
    mutationFn: () => pipelineApi.gapAnalysis(projectId, erpConfig),
    onSuccess: () => {
      toast.success("GAP-анализ запущен");
      queryClient.invalidateQueries({ queryKey: ["gaps", projectId] });
      queryClient.invalidateQueries({ queryKey: ["pipeline-status", projectId] });
    },
    onError: (err: Error) => {
      toast.error(err.message);
    },
  });

  const gaps = data?.gaps ?? [];
  const summary = data?.summary;

  // Calculate derived stats
  const totalGaps = summary?.total_gaps ?? gaps.length;
  const criticalGaps = summary?.by_severity?.critical ?? 0;
  const highGaps = summary?.by_severity?.high ?? 0;

  if (isLoading) {
    return (
      <div className="space-y-4">
        <Skeleton className="h-8 w-48" />
        <div className="grid gap-4 sm:grid-cols-3">
          <Skeleton className="h-24" />
          <Skeleton className="h-24" />
          <Skeleton className="h-24" />
        </div>
        <Skeleton className="h-64" />
      </div>
    );
  }

  return (
    <div className="space-y-6">
      <div className="flex flex-col gap-4 sm:flex-row sm:items-center sm:justify-between">
        <div>
          <h2 className="text-2xl font-bold tracking-tight">GAP-анализ</h2>
          <p className="mt-1 text-muted-foreground">
            Анализ разрывов между текущими процессами и возможностями ERP
          </p>
        </div>
        <div className="flex items-center gap-2">
          <Select value={erpConfig} onValueChange={setErpConfig}>
            <SelectTrigger className="w-[160px]">
              <SelectValue />
            </SelectTrigger>
            <SelectContent>
              {erpOptions.map((opt) => (
                <SelectItem key={opt.value} value={opt.value}>
                  {opt.label}
                </SelectItem>
              ))}
            </SelectContent>
          </Select>
          <Button
            onClick={() => runGapMutation.mutate()}
            disabled={runGapMutation.isPending}
          >
            {runGapMutation.isPending ? (
              <Loader2 className="mr-2 size-4 animate-spin" />
            ) : (
              <Play className="mr-2 size-4" />
            )}
            Запустить GAP-анализ
          </Button>
        </div>
      </div>

      {/* Summary cards */}
      <div className="grid gap-4 sm:grid-cols-3">
        <Card>
          <CardHeader className="flex flex-row items-center justify-between pb-2">
            <CardTitle className="text-sm font-medium">Всего GAP</CardTitle>
            <GitCompareArrows className="size-4 text-muted-foreground" />
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold">{totalGaps}</div>
          </CardContent>
        </Card>
        <Card>
          <CardHeader className="flex flex-row items-center justify-between pb-2">
            <CardTitle className="text-sm font-medium">
              Критичные GAP
            </CardTitle>
            <AlertTriangle className="size-4 text-destructive" />
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold text-destructive">
              {criticalGaps + highGaps}
            </div>
          </CardContent>
        </Card>
        <Card>
          <CardHeader className="flex flex-row items-center justify-between pb-2">
            <CardTitle className="text-sm font-medium">По типам</CardTitle>
            <BarChart3 className="size-4 text-muted-foreground" />
          </CardHeader>
          <CardContent>
            <div className="flex flex-wrap gap-1">
              {summary?.by_type &&
                Object.entries(summary.by_type).map(([type, count]) => (
                  <Badge key={type} variant="outline" className="text-xs">
                    {gapTypeLabels[type] ?? type}: {count as number}
                  </Badge>
                ))}
              {(!summary?.by_type ||
                Object.keys(summary.by_type).length === 0) && (
                <span className="text-sm text-muted-foreground">—</span>
              )}
            </div>
          </CardContent>
        </Card>
      </div>

      {/* Gaps table */}
      {gaps.length === 0 ? (
        <div className="flex flex-col items-center justify-center rounded-lg border border-dashed py-16">
          <GitCompareArrows className="mb-4 size-12 text-muted-foreground" />
          <p className="text-lg font-medium">Нет данных GAP-анализа</p>
          <p className="mt-1 text-sm text-muted-foreground">
            Выберите конфигурацию ERP и запустите анализ
          </p>
        </div>
      ) : (
        <div className="rounded-md border">
          <Table>
            <TableHeader>
              <TableRow>
                <TableHead>Процесс</TableHead>
                <TableHead>Описание GAP</TableHead>
                <TableHead>Тип</TableHead>
                <TableHead>Модуль ERP</TableHead>
                <TableHead>Критичность</TableHead>
                <TableHead>Рекомендация</TableHead>
                <TableHead>Трудоёмкость</TableHead>
              </TableRow>
            </TableHeader>
            <TableBody>
              {gaps.map((gap) => (
                <TableRow key={gap.id}>
                  <TableCell className="font-medium">
                    {gap.process_name}
                  </TableCell>
                  <TableCell className="max-w-[200px]">
                    <span className="line-clamp-2 text-sm">
                      {gap.description}
                    </span>
                  </TableCell>
                  <TableCell>
                    <Badge variant="outline" className="text-xs whitespace-nowrap">
                      {gapTypeLabels[gap.gap_type] ?? gap.gap_type}
                    </Badge>
                  </TableCell>
                  <TableCell>{gap.erp_module || "—"}</TableCell>
                  <TableCell>
                    <Badge
                      variant={severityVariants[gap.severity] ?? "outline"}
                      className="text-xs"
                    >
                      {severityLabels[gap.severity] ?? gap.severity}
                    </Badge>
                  </TableCell>
                  <TableCell className="max-w-[200px]">
                    <span className="line-clamp-2 text-sm">
                      {gap.recommendation}
                    </span>
                  </TableCell>
                  <TableCell>{gap.effort_estimate || "—"}</TableCell>
                </TableRow>
              ))}
            </TableBody>
          </Table>
        </div>
      )}
    </div>
  );
}
