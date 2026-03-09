"use client";

import * as React from "react";
import { useParams } from "next/navigation";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { toast } from "sonner";
import {
  Play,
  CheckCircle2,
  XCircle,
  Clock,
  Loader2,
  Upload,
  FileSearch,
  Workflow,
  GitCompareArrows,
  RefreshCw,
  FileText,
  AlertTriangle,
} from "lucide-react";
import { Button } from "@/components/ui/button";
import {
  Card,
  CardContent,
  CardDescription,
  CardHeader,
  CardTitle,
} from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { Progress } from "@/components/ui/progress";
import { Skeleton } from "@/components/ui/skeleton";
import { projectsApi, pipelineApi } from "@/lib/api";
import type { PipelineStage, StageStatus, StageInfo } from "@/lib/types";

const stageConfig: {
  name: PipelineStage;
  label: string;
  icon: React.ElementType;
}[] = [
  { name: "transcribe", label: "Транскрипция", icon: FileText },
  { name: "extract", label: "Извлечение процессов", icon: FileSearch },
  { name: "generate-bpmn", label: "BPMN / Visio", icon: Workflow },
  { name: "gap-analysis", label: "GAP-анализ", icon: GitCompareArrows },
  { name: "generate-tobe", label: "TO-BE", icon: RefreshCw },
  { name: "generate-docs", label: "Документы", icon: FileText },
];

const statusLabels: Record<StageStatus, string> = {
  pending: "Ожидание",
  running: "Выполняется",
  completed: "Завершено",
  error: "Ошибка",
  skipped: "Пропущено",
};

const statusIcons: Record<StageStatus, React.ElementType> = {
  pending: Clock,
  running: Loader2,
  completed: CheckCircle2,
  error: XCircle,
  skipped: Clock,
};

function getStageRunner(stage: PipelineStage) {
  const runners: Record<PipelineStage, (id: string) => Promise<void>> = {
    upload: async () => {},
    transcribe: (id) => pipelineApi.transcribe(id),
    extract: (id) => pipelineApi.extract(id),
    "generate-bpmn": (id) => pipelineApi.generateBpmn(id),
    "gap-analysis": (id) => pipelineApi.gapAnalysis(id),
    "generate-tobe": (id) => pipelineApi.generateTobe(id),
    "generate-docs": (id) => pipelineApi.generateDocs(id),
  };
  return runners[stage];
}

export default function ProjectOverviewPage() {
  const params = useParams<{ id: string }>();
  const projectId = params.id;
  const queryClient = useQueryClient();

  const { data: projectData, isLoading } = useQuery({
    queryKey: ["project", projectId],
    queryFn: () => projectsApi.get(projectId),
    enabled: !!projectId,
  });

  const { data: statusData } = useQuery({
    queryKey: ["pipeline-status", projectId],
    queryFn: () => pipelineApi.status(projectId),
    enabled: !!projectId,
    refetchInterval: (query) => {
      const stages = query.state.data?.stages ?? [];
      const hasRunning = stages.some((s) => s.status === "running");
      return hasRunning ? 3000 : false;
    },
  });

  const runStageMutation = useMutation({
    mutationFn: ({ stage }: { stage: PipelineStage }) => {
      const runner = getStageRunner(stage);
      return runner(projectId);
    },
    onSuccess: () => {
      toast.success("Этап запущен");
      queryClient.invalidateQueries({ queryKey: ["pipeline-status", projectId] });
      queryClient.invalidateQueries({ queryKey: ["project", projectId] });
    },
    onError: (err: Error) => {
      toast.error(err.message);
    },
  });

  const project = projectData;
  const stages = statusData?.stages ?? [];
  const overallProgress = statusData?.overall_progress ?? 0;

  const getStageInfo = (stageName: PipelineStage): StageInfo | undefined => {
    return stages.find((s) => s.name === stageName);
  };

  const canRunStage = (stageName: PipelineStage): boolean => {
    const info = getStageInfo(stageName);
    if (!info) return false;
    if (info.status === "running") return false;
    const hasRunning = stages.some((s) => s.status === "running");
    if (hasRunning) return false;
    return true;
  };

  if (isLoading) {
    return (
      <div className="space-y-6">
        <Skeleton className="h-8 w-64" />
        <Skeleton className="h-4 w-96" />
        <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-3">
          {Array.from({ length: 6 }).map((_, i) => (
            <Skeleton key={i} className="h-32" />
          ))}
        </div>
      </div>
    );
  }

  return (
    <div className="space-y-6">
      {/* Project info */}
      <div>
        <h2 className="text-2xl font-bold tracking-tight">
          {project?.name ?? "Проект"}
        </h2>
        {project?.description && (
          <p className="mt-1 text-muted-foreground">{project.description}</p>
        )}
      </div>

      {/* Overall progress */}
      <Card>
        <CardHeader className="pb-3">
          <CardTitle className="text-base">Общий прогресс</CardTitle>
          <CardDescription>Конвейер обработки данных</CardDescription>
        </CardHeader>
        <CardContent>
          <div className="space-y-2">
            <div className="flex items-center justify-between text-sm">
              <span className="text-muted-foreground">Прогресс</span>
              <span className="font-medium">{overallProgress}%</span>
            </div>
            <Progress value={overallProgress} />
          </div>
        </CardContent>
      </Card>

      {/* Pipeline stages */}
      <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-3">
        {stageConfig.map((stage, index) => {
          const info = getStageInfo(stage.name);
          const status: StageStatus = info?.status ?? "pending";
          const StatusIcon = statusIcons[status];
          const StageIcon = stage.icon;
          const isRunning = status === "running";
          const isError = status === "error";

          return (
            <Card
              key={stage.name}
              className={
                isRunning
                  ? "border-primary/50 shadow-primary/10 shadow-md"
                  : isError
                    ? "border-destructive/50"
                    : ""
              }
            >
              <CardHeader className="pb-3">
                <div className="flex items-center justify-between">
                  <div className="flex items-center gap-2">
                    <div className="flex size-8 items-center justify-center rounded-md bg-muted">
                      <StageIcon className="size-4" />
                    </div>
                    <div>
                      <CardTitle className="text-sm">
                        {index + 1}. {stage.label}
                      </CardTitle>
                    </div>
                  </div>
                  <Badge
                    variant={
                      status === "completed"
                        ? "default"
                        : status === "running"
                          ? "secondary"
                          : status === "error"
                            ? "destructive"
                            : "outline"
                    }
                    className="text-xs"
                  >
                    <StatusIcon
                      className={`mr-1 size-3 ${isRunning ? "animate-spin" : ""}`}
                    />
                    {statusLabels[status]}
                  </Badge>
                </div>
              </CardHeader>
              <CardContent>
                <div className="space-y-3">
                  {isRunning && info && (
                    <Progress value={info.progress} className="h-1.5" />
                  )}

                  {isError && info?.error && (
                    <div className="flex items-start gap-2 rounded-md bg-destructive/10 p-2 text-xs text-destructive">
                      <AlertTriangle className="mt-0.5 size-3 shrink-0" />
                      <span>{info.error}</span>
                    </div>
                  )}

                  {canRunStage(stage.name) && (
                    <Button
                      size="sm"
                      className="w-full"
                      onClick={() =>
                        runStageMutation.mutate({ stage: stage.name })
                      }
                      disabled={runStageMutation.isPending}
                    >
                      {runStageMutation.isPending ? (
                        <Loader2 className="mr-2 size-3 animate-spin" />
                      ) : (
                        <Play className="mr-2 size-3" />
                      )}
                      Запустить
                    </Button>
                  )}
                </div>
              </CardContent>
            </Card>
          );
        })}
      </div>
    </div>
  );
}
