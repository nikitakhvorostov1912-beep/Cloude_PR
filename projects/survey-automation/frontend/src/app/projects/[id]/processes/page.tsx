"use client";

import * as React from "react";
import { useParams } from "next/navigation";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { toast } from "sonner";
import {
  Workflow,
  Pencil,
  Save,
  X,
  AlertTriangle,
  Users,
  Building,
  Zap,
  Eye,
  Play,
  Target,
  Clock,
  BarChart3,
  Link2,
  FileText,
} from "lucide-react";
import { Button } from "@/components/ui/button";
import { Card, CardContent } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { Input } from "@/components/ui/input";
import { Textarea } from "@/components/ui/textarea";
import {
  Accordion,
  AccordionContent,
  AccordionItem,
  AccordionTrigger,
} from "@/components/ui/accordion";
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from "@/components/ui/table";
import { Skeleton } from "@/components/ui/skeleton";
import { Separator } from "@/components/ui/separator";
import { dataApi } from "@/lib/api";
import { SvgPreviewDialog } from "@/components/svg-preview-dialog";
import type { Process, ProcessStep, PainPoint } from "@/lib/types";

const severityColors: Record<string, string> = {
  low: "bg-yellow-500/10 text-yellow-500 border-yellow-500/20",
  medium: "bg-orange-500/10 text-orange-500 border-orange-500/20",
  high: "bg-red-500/10 text-red-500 border-red-500/20",
  critical: "bg-red-600/10 text-red-600 border-red-600/20",
};

const severityLabels: Record<string, string> = {
  low: "Низкая",
  medium: "Средняя",
  high: "Высокая",
  critical: "Критичная",
};

export default function ProcessesPage() {
  const params = useParams<{ id: string }>();
  const projectId = params.id;
  const queryClient = useQueryClient();
  const [editingId, setEditingId] = React.useState<string | null>(null);
  const [editData, setEditData] = React.useState<Partial<Process>>({});
  const [previewProcess, setPreviewProcess] = React.useState<{
    processId: string;
    processName: string;
  } | null>(null);

  const { data, isLoading } = useQuery({
    queryKey: ["processes", projectId],
    queryFn: () => dataApi.processes(projectId),
    enabled: !!projectId,
  });

  const updateMutation = useMutation({
    mutationFn: ({ id, data }: { id: string; data: Partial<Process> }) =>
      dataApi.updateProcess(projectId, id, data),
    onSuccess: () => {
      toast.success("Процесс обновлён");
      setEditingId(null);
      setEditData({});
      queryClient.invalidateQueries({ queryKey: ["processes", projectId] });
    },
    onError: (err: Error) => {
      toast.error(err.message);
    },
  });

  const processes = (data?.processes ?? []).filter(
    (p) => !p.id.endsWith("_bpmn") && p.name,
  );

  const startEdit = (process: Process) => {
    setEditingId(process.id);
    setEditData({
      name: process.name,
      description: process.description,
      department: process.department,
    });
  };

  const cancelEdit = () => {
    setEditingId(null);
    setEditData({});
  };

  const saveEdit = (id: string) => {
    updateMutation.mutate({ id, data: editData });
  };

  if (isLoading) {
    return (
      <div className="space-y-4">
        <Skeleton className="h-8 w-48" />
        {Array.from({ length: 3 }).map((_, i) => (
          <Skeleton key={i} className="h-24" />
        ))}
      </div>
    );
  }

  if (processes.length === 0) {
    return (
      <div className="space-y-6">
        <h2 className="text-2xl font-bold tracking-tight">Процессы</h2>
        <div className="flex flex-col items-center justify-center rounded-lg border border-dashed py-16">
          <Workflow className="mb-4 size-12 text-muted-foreground" />
          <p className="text-lg font-medium">Нет процессов</p>
          <p className="mt-1 text-sm text-muted-foreground">
            Загрузите транскрипции и запустите извлечение процессов
          </p>
        </div>
      </div>
    );
  }

  return (
    <div className="space-y-6">
      <div>
        <h2 className="text-2xl font-bold tracking-tight">Процессы</h2>
        <p className="mt-1 text-muted-foreground">
          Найдено процессов: {processes.length}
        </p>
      </div>

      <Accordion type="multiple" className="space-y-2">
        {processes.map((process) => {
          const isEditing = editingId === process.id;

          return (
            <AccordionItem
              key={process.id}
              value={process.id}
              className="rounded-lg border bg-card"
            >
              <AccordionTrigger className="px-4 hover:no-underline">
                <div className="flex flex-1 items-center gap-3 text-left">
                  <Workflow className="size-5 shrink-0 text-primary" />
                  <div className="min-w-0 flex-1">
                    <div className="flex items-center gap-2">
                      <span className="font-semibold">{process.name}</span>
                      <Badge variant="outline" className="text-xs">
                        {process.status === "draft"
                          ? "Черновик"
                          : process.status === "reviewed"
                            ? "На проверке"
                            : "Утверждён"}
                      </Badge>
                    </div>
                    <div className="mt-1 flex gap-3 text-xs text-muted-foreground">
                      <span className="flex items-center gap-1">
                        <Building className="size-3" />
                        {process.department || "Не указан"}
                      </span>
                      <span className="flex items-center gap-1">
                        <Users className="size-3" />
                        {process.participants.length} участник(ов)
                      </span>
                      {process.pain_points.length > 0 && (
                        <span className="flex items-center gap-1 text-destructive">
                          <AlertTriangle className="size-3" />
                          {process.pain_points.length} проблем(ы)
                        </span>
                      )}
                    </div>
                  </div>
                </div>
              </AccordionTrigger>

              <AccordionContent className="px-4 pb-4">
                <div className="space-y-4">
                  {/* Edit controls */}
                  <div className="flex justify-end gap-2">
                    {isEditing ? (
                      <>
                        <Button
                          size="sm"
                          variant="outline"
                          onClick={cancelEdit}
                        >
                          <X className="mr-1 size-3" />
                          Отмена
                        </Button>
                        <Button
                          size="sm"
                          onClick={() => saveEdit(process.id)}
                          disabled={updateMutation.isPending}
                        >
                          <Save className="mr-1 size-3" />
                          Сохранить
                        </Button>
                      </>
                    ) : (
                      <>
                        <Button
                          size="sm"
                          variant="outline"
                          onClick={() =>
                            setPreviewProcess({
                              processId: process.id,
                              processName: process.name,
                            })
                          }
                        >
                          <Eye className="mr-1 size-3" />
                          Диаграмма
                        </Button>
                        <Button
                          size="sm"
                          variant="outline"
                          onClick={() => startEdit(process)}
                        >
                          <Pencil className="mr-1 size-3" />
                          Редактировать
                        </Button>
                      </>
                    )}
                  </div>

                  {/* Process info */}
                  <div className="grid gap-4 sm:grid-cols-2">
                    <div>
                      <label className="text-xs font-medium text-muted-foreground">
                        Название
                      </label>
                      {isEditing ? (
                        <Input
                          value={editData.name ?? ""}
                          onChange={(e) =>
                            setEditData((prev) => ({
                              ...prev,
                              name: e.target.value,
                            }))
                          }
                          className="mt-1"
                        />
                      ) : (
                        <p className="mt-1 text-sm">{process.name}</p>
                      )}
                    </div>
                    <div>
                      <label className="text-xs font-medium text-muted-foreground">
                        Отдел
                      </label>
                      {isEditing ? (
                        <Input
                          value={editData.department ?? ""}
                          onChange={(e) =>
                            setEditData((prev) => ({
                              ...prev,
                              department: e.target.value,
                            }))
                          }
                          className="mt-1"
                        />
                      ) : (
                        <p className="mt-1 text-sm">
                          {process.department || "—"}
                        </p>
                      )}
                    </div>
                  </div>

                  <div>
                    <label className="text-xs font-medium text-muted-foreground">
                      Описание
                    </label>
                    {isEditing ? (
                      <Textarea
                        value={editData.description ?? ""}
                        onChange={(e) =>
                          setEditData((prev) => ({
                            ...prev,
                            description: e.target.value,
                          }))
                        }
                        className="mt-1"
                        rows={3}
                      />
                    ) : (
                      <p className="mt-1 text-sm">
                        {process.description || "—"}
                      </p>
                    )}
                  </div>

                  {/* Trigger & Result */}
                  {(process.trigger || process.result) && (
                    <div className="grid gap-4 sm:grid-cols-2">
                      {process.trigger && (
                        <div className="flex items-start gap-2 rounded-md border border-green-500/20 bg-green-500/5 p-3">
                          <Play className="mt-0.5 size-4 shrink-0 text-green-500" />
                          <div>
                            <p className="text-xs font-medium text-muted-foreground">Триггер</p>
                            <p className="mt-0.5 text-sm">{process.trigger}</p>
                          </div>
                        </div>
                      )}
                      {process.result && (
                        <div className="flex items-start gap-2 rounded-md border border-blue-500/20 bg-blue-500/5 p-3">
                          <Target className="mt-0.5 size-4 shrink-0 text-blue-500" />
                          <div>
                            <p className="text-xs font-medium text-muted-foreground">Результат</p>
                            <p className="mt-0.5 text-sm">{process.result}</p>
                          </div>
                        </div>
                      )}
                    </div>
                  )}

                  {/* Metrics */}
                  {process.metrics && Object.keys(process.metrics).length > 0 && (
                    <div>
                      <label className="text-xs font-medium text-muted-foreground flex items-center gap-1">
                        <BarChart3 className="size-3" /> Метрики процесса
                      </label>
                      <div className="mt-1 grid gap-2 sm:grid-cols-3">
                        {process.metrics.frequency && (
                          <div className="rounded-md border p-2 text-center">
                            <p className="text-xs text-muted-foreground">Частота</p>
                            <p className="text-sm font-semibold">{process.metrics.frequency}</p>
                          </div>
                        )}
                        {process.metrics.duration && (
                          <div className="rounded-md border p-2 text-center">
                            <p className="text-xs text-muted-foreground">Длительность</p>
                            <p className="text-sm font-semibold">{process.metrics.duration}</p>
                          </div>
                        )}
                        {process.metrics.participants_count && (
                          <div className="rounded-md border p-2 text-center">
                            <p className="text-xs text-muted-foreground">Участников</p>
                            <p className="text-sm font-semibold">{process.metrics.participants_count}</p>
                          </div>
                        )}
                      </div>
                    </div>
                  )}

                  {/* Integrations */}
                  {process.integrations && process.integrations.length > 0 && (
                    <div>
                      <label className="text-xs font-medium text-muted-foreground flex items-center gap-1">
                        <Link2 className="size-3" /> Используемые системы
                      </label>
                      <div className="mt-1 flex flex-wrap gap-1">
                        {process.integrations.map((sys, i) => (
                          <Badge key={i} variant="outline" className="text-xs border-primary/30 text-primary">
                            {sys}
                          </Badge>
                        ))}
                      </div>
                    </div>
                  )}

                  {/* Analysis summary */}
                  {(process.steps.length > 0 || process.pain_points.length > 0) && (
                    <div className="rounded-md border border-primary/20 bg-primary/5 p-3">
                      <div className="flex items-center gap-2 mb-2">
                        <FileText className="size-4 text-primary" />
                        <h4 className="text-sm font-semibold">Аналитическая сводка</h4>
                      </div>
                      <div className="text-sm text-muted-foreground space-y-1">
                        <p>
                          Процесс включает <strong className="text-foreground">{process.steps.length} шагов</strong> с участием{" "}
                          <strong className="text-foreground">{process.participants.length} ролей</strong>.
                          {process.decisions.length > 0 && (
                            <> Содержит <strong className="text-foreground">{process.decisions.length} точк{process.decisions.length === 1 ? "у" : process.decisions.length < 5 ? "и" : ""} принятия решений</strong>, что увеличивает сложность маршрутизации.</>
                          )}
                        </p>
                        {process.pain_points.length > 0 && (() => {
                          const critical = process.pain_points.filter(pp => {
                            const obj = typeof pp === "string" ? null : pp;
                            return obj && (obj.severity === "critical" || obj.severity === "high");
                          }).length;
                          return (
                            <p>
                              Выявлено <strong className="text-foreground">{process.pain_points.length} проблемных зон</strong>
                              {critical > 0 && (
                                <>, из них <strong className="text-destructive">{critical} критических/высокого приоритета</strong></>
                              )}. Рекомендуется приоритизировать автоматизацию узких мест.
                            </p>
                          );
                        })()}
                        {process.integrations && process.integrations.length > 1 && (
                          <p>
                            Процесс затрагивает <strong className="text-foreground">{process.integrations.length} информационных систем</strong>,
                            что требует проработки интеграционных сценариев при внедрении.
                          </p>
                        )}
                      </div>
                    </div>
                  )}

                  {/* Participants */}
                  {process.participants.length > 0 && (
                    <div>
                      <label className="text-xs font-medium text-muted-foreground">
                        Участники
                      </label>
                      <div className="mt-1 flex flex-wrap gap-1">
                        {process.participants.map((p, i) => {
                          const label = typeof p === "string" ? p : (p as { role?: string; department?: string }).role ?? JSON.stringify(p);
                          const dept = typeof p === "object" ? (p as { department?: string }).department : undefined;
                          return (
                            <Badge key={i} variant="secondary" className="text-xs">
                              {label}{dept ? ` (${dept})` : ""}
                            </Badge>
                          );
                        })}
                      </div>
                    </div>
                  )}

                  <Separator />

                  {/* Steps table */}
                  {process.steps.length > 0 && (
                    <div>
                      <h4 className="mb-2 text-sm font-semibold">
                        Шаги процесса
                      </h4>
                      <div className="rounded-md border">
                        <Table>
                          <TableHeader>
                            <TableRow>
                              <TableHead className="w-12">#</TableHead>
                              <TableHead>Название</TableHead>
                              <TableHead>Описание</TableHead>
                              <TableHead>Исполнитель</TableHead>
                              <TableHead>Системы</TableHead>
                              <TableHead>Длительность</TableHead>
                            </TableRow>
                          </TableHeader>
                          <TableBody>
                            {[...process.steps]
                              .sort((a, b) => a.order - b.order)
                              .map((step, i) => (
                                <TableRow key={`${process.id}-step-${step.order}-${step.name}`}>
                                  <TableCell className="font-mono text-xs">
                                    {step.order}
                                  </TableCell>
                                  <TableCell className="font-medium">
                                    {step.name}
                                  </TableCell>
                                  <TableCell className="max-w-[200px] truncate text-muted-foreground">
                                    {step.description}
                                  </TableCell>
                                  <TableCell>{step.actor || "—"}</TableCell>
                                  <TableCell>{step.system || "—"}</TableCell>
                                  <TableCell>
                                    {step.duration_estimate || "—"}
                                  </TableCell>
                                </TableRow>
                              ))}
                          </TableBody>
                        </Table>
                      </div>
                    </div>
                  )}

                  {/* Decisions */}
                  {process.decisions.length > 0 && (
                    <div>
                      <h4 className="mb-2 text-sm font-semibold">
                        Точки принятия решений
                      </h4>
                      <div className="space-y-2">
                        {process.decisions.map((d, i) => (
                          <Card key={d.id ?? i}>
                            <CardContent className="p-3">
                              <div className="flex items-start gap-2">
                                <Zap className="mt-0.5 size-4 shrink-0 text-yellow-500" />
                                <div>
                                  <p className="text-sm font-medium">
                                    {d.condition ?? d.question ?? "Решение"}
                                  </p>
                                  <div className="mt-1 flex flex-wrap gap-1">
                                    {d.yes_branch && (
                                      <Badge variant="outline" className="text-xs text-green-400 border-green-400/30">
                                        Да: {d.yes_branch}
                                      </Badge>
                                    )}
                                    {d.no_branch && (
                                      <Badge variant="outline" className="text-xs text-red-400 border-red-400/30">
                                        Нет: {d.no_branch}
                                      </Badge>
                                    )}
                                    {d.options?.map((opt: { label?: string }, j: number) => (
                                      <Badge
                                        key={j}
                                        variant="outline"
                                        className="text-xs"
                                      >
                                        {opt.label ?? String(opt)}
                                      </Badge>
                                    ))}
                                  </div>
                                </div>
                              </div>
                            </CardContent>
                          </Card>
                        ))}
                      </div>
                    </div>
                  )}

                  {/* Pain points */}
                  {process.pain_points.length > 0 && (
                    <div>
                      <h4 className="mb-2 text-sm font-semibold">
                        Проблемные зоны
                      </h4>
                      <div className="space-y-2">
                        {process.pain_points.map((pp, i) => {
                          const ppObj = typeof pp === "string" ? { description: pp } as unknown as PainPoint : pp;
                          return (
                            <div
                              key={ppObj.id ?? `pp-${i}`}
                              className={`flex items-start gap-2 rounded-md border p-3 ${severityColors[ppObj.severity] ?? ""}`}
                            >
                              <AlertTriangle className="mt-0.5 size-4 shrink-0" />
                              <div className="min-w-0 flex-1">
                                <p className="text-sm">{ppObj.description}</p>
                                <div className="mt-1 flex gap-2">
                                  {ppObj.severity && (
                                    <Badge
                                      variant="outline"
                                      className="text-xs"
                                    >
                                      {severityLabels[ppObj.severity] ?? ppObj.severity}
                                    </Badge>
                                  )}
                                  {ppObj.category && (
                                    <Badge
                                      variant="outline"
                                      className="text-xs"
                                    >
                                      {ppObj.category}
                                    </Badge>
                                  )}
                                </div>
                              </div>
                            </div>
                          );
                        })}
                      </div>
                    </div>
                  )}
                </div>
              </AccordionContent>
            </AccordionItem>
          );
        })}
      </Accordion>

      {/* SVG Preview Dialog */}
      {previewProcess && (
        <SvgPreviewDialog
          open={!!previewProcess}
          onOpenChange={(open) => {
            if (!open) setPreviewProcess(null);
          }}
          projectId={projectId}
          processId={previewProcess.processId}
          processName={previewProcess.processName}
        />
      )}
    </div>
  );
}
