"use client";

import * as React from "react";
import { useParams } from "next/navigation";
import { useQuery } from "@tanstack/react-query";
import {
  Download,
  FileSpreadsheet,
  FileText,
  Image,
  FolderOpen,
  Archive,
  Workflow,
  Eye,
} from "lucide-react";
import { Button } from "@/components/ui/button";
import { Card, CardContent } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { Skeleton } from "@/components/ui/skeleton";
import { Separator } from "@/components/ui/separator";
import { SvgPreviewDialog } from "@/components/svg-preview-dialog";
import { OpenInServiceMenu } from "@/components/open-in-service-menu";
import { dataApi, exportApi } from "@/lib/api";

type ServiceFileType = "bpmn" | "visio" | "docx" | "xlsx";

interface FileCard {
  name: string;
  type: string;
  ext: string;
  url: string;
  icon: React.ElementType;
  processId?: string;
  processName?: string;
  previewable?: boolean;
  serviceType?: ServiceFileType;
}

export default function FilesPage() {
  const params = useParams<{ id: string }>();
  const projectId = params.id;

  // State for SVG preview dialog
  const [previewProcess, setPreviewProcess] = React.useState<{
    processId: string;
    processName: string;
  } | null>(null);

  const { data: processesData, isLoading: processesLoading } = useQuery({
    queryKey: ["processes", projectId],
    queryFn: () => dataApi.processes(projectId),
    enabled: !!projectId,
  });

  const processes = processesData?.processes ?? [];
  const isLoading = processesLoading;

  // Build file groups from available data
  const fileGroups = React.useMemo(() => {
    const groups: {
      title: string;
      icon: React.ElementType;
      files: FileCard[];
    }[] = [];

    // Filter out _bpmn duplicates — only real processes with names
    const realProcesses = processes.filter(
      (p) => !p.id.endsWith("_bpmn") && p.name,
    );

    // Visio files — for all real processes
    const visioFiles: FileCard[] = realProcesses.map((p) => ({
      name: `${p.name}.vsdx`,
      type: "Visio",
      ext: ".vsdx",
      url: exportApi.visio(projectId, p.id),
      icon: Workflow,
      processId: p.id,
      processName: p.name,
      previewable: true,
      serviceType: "visio" as ServiceFileType,
    }));
    if (visioFiles.length > 0) {
      groups.push({
        title: "Visio файлы",
        icon: Workflow,
        files: visioFiles,
      });
    }

    // BPMN files — for all real processes
    const bpmnFiles: FileCard[] = realProcesses.map((p) => ({
      name: `${p.name}.bpmn`,
      type: "BPMN",
      ext: ".bpmn",
      url: exportApi.bpmn(projectId, p.id),
      icon: Image,
      processId: p.id,
      processName: p.name,
      previewable: true,
      serviceType: "bpmn" as ServiceFileType,
    }));
    if (bpmnFiles.length > 0) {
      groups.push({
        title: "BPMN-диаграммы",
        icon: Image,
        files: bpmnFiles,
      });
    }

    // Documents
    const docFiles: FileCard[] = [
      {
        name: "Описание процессов.docx",
        type: "Документ",
        ext: ".docx",
        url: exportApi.processDoc(projectId),
        icon: FileText,
        serviceType: "docx" as ServiceFileType,
      },
      {
        name: "Требования.docx",
        type: "Документ",
        ext: ".docx",
        url: exportApi.requirementsWord(projectId),
        icon: FileText,
        serviceType: "docx" as ServiceFileType,
      },
    ];
    groups.push({
      title: "Документы",
      icon: FileText,
      files: docFiles,
    });

    // Spreadsheets
    const xlsFiles: FileCard[] = [
      {
        name: "Требования.xlsx",
        type: "Таблица",
        ext: ".xlsx",
        url: exportApi.requirementsExcel(projectId),
        icon: FileSpreadsheet,
        serviceType: "xlsx" as ServiceFileType,
      },
      {
        name: "GAP-отчёт.xlsx",
        type: "Таблица",
        ext: ".xlsx",
        url: exportApi.gapReport(projectId),
        icon: FileSpreadsheet,
        serviceType: "xlsx" as ServiceFileType,
      },
    ];
    groups.push({
      title: "Таблицы",
      icon: FileSpreadsheet,
      files: xlsFiles,
    });

    return groups;
  }, [processes, projectId]);

  const extColor: Record<string, string> = {
    ".vsdx": "bg-blue-500/10 text-blue-400",
    ".bpmn": "bg-purple-500/10 text-purple-400",
    ".svg": "bg-pink-500/10 text-pink-400",
    ".docx": "bg-sky-500/10 text-sky-400",
    ".xlsx": "bg-green-500/10 text-green-400",
  };

  if (isLoading) {
    return (
      <div className="space-y-4">
        <Skeleton className="h-8 w-48" />
        <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-3">
          {Array.from({ length: 6 }).map((_, i) => (
            <Skeleton key={i} className="h-24" />
          ))}
        </div>
      </div>
    );
  }

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <div>
          <h2 className="text-2xl font-bold tracking-tight">Файлы</h2>
          <p className="mt-1 text-muted-foreground">
            Экспорт результатов проекта
          </p>
        </div>
        <Button asChild>
          <a
            href={exportApi.all(projectId)}
            target="_blank"
            rel="noopener noreferrer"
          >
            <Archive className="mr-2 size-4" />
            Скачать всё (ZIP)
          </a>
        </Button>
      </div>

      {fileGroups.map((group) => (
        <div key={group.title}>
          <div className="mb-3 flex items-center gap-2">
            <group.icon className="size-5 text-muted-foreground" />
            <h3 className="text-lg font-semibold">{group.title}</h3>
            <Badge variant="outline" className="text-xs">
              {group.files.length}
            </Badge>
          </div>
          <div className="grid gap-3 sm:grid-cols-2 lg:grid-cols-3">
            {group.files.map((file, idx) => (
              <Card
                key={idx}
                className="transition-colors hover:bg-accent/50"
              >
                <CardContent className="flex items-center justify-between p-4">
                  <div className="flex items-center gap-3 min-w-0">
                    <div
                      className={`flex size-10 shrink-0 items-center justify-center rounded-md ${
                        extColor[file.ext] ??
                        "bg-muted text-muted-foreground"
                      }`}
                    >
                      <file.icon className="size-5" />
                    </div>
                    <div className="min-w-0">
                      <p className="truncate text-sm font-medium">
                        {file.name}
                      </p>
                      <div className="flex items-center gap-1.5 mt-0.5">
                        <Badge variant="outline" className="text-xs">
                          {file.ext}
                        </Badge>
                        <span className="text-xs text-muted-foreground">
                          {file.type}
                        </span>
                      </div>
                    </div>
                  </div>

                  {/* Action buttons */}
                  <div className="flex items-center gap-0.5 shrink-0 ml-2">
                    {/* Preview button — only for BPMN/Visio */}
                    {file.previewable && file.processId && (
                      <Button
                        variant="ghost"
                        size="icon"
                        className="size-8"
                        title="Просмотр диаграммы"
                        onClick={() =>
                          setPreviewProcess({
                            processId: file.processId!,
                            processName: file.processName ?? file.name,
                          })
                        }
                      >
                        <Eye className="size-4" />
                      </Button>
                    )}

                    {/* Open in service menu */}
                    {file.serviceType && (
                      <OpenInServiceMenu
                        downloadUrl={file.url}
                        fileType={file.serviceType}
                      />
                    )}

                    {/* Download button */}
                    <Button
                      variant="ghost"
                      size="icon"
                      asChild
                      className="size-8"
                      title="Скачать"
                    >
                      <a
                        href={file.url}
                        target="_blank"
                        rel="noopener noreferrer"
                      >
                        <Download className="size-4" />
                      </a>
                    </Button>
                  </div>
                </CardContent>
              </Card>
            ))}
          </div>
          <Separator className="mt-6" />
        </div>
      ))}

      {fileGroups.length === 0 && (
        <div className="flex flex-col items-center justify-center rounded-lg border border-dashed py-16">
          <FolderOpen className="mb-4 size-12 text-muted-foreground" />
          <p className="text-lg font-medium">Нет файлов</p>
          <p className="mt-1 text-sm text-muted-foreground">
            Файлы появятся после обработки данных проекта
          </p>
        </div>
      )}

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
