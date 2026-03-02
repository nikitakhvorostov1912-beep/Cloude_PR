"use client";

import * as React from "react";
import { useQuery } from "@tanstack/react-query";
import {
  ZoomIn,
  ZoomOut,
  Maximize2,
  Download,
  ExternalLink,
  Loader2,
  AlertCircle,
} from "lucide-react";
import {
  Dialog,
  DialogContent,
  DialogHeader,
  DialogTitle,
} from "@/components/ui/dialog";
import { Button } from "@/components/ui/button";
import { Skeleton } from "@/components/ui/skeleton";
import { fetchSvgContent, exportApi } from "@/lib/api";

interface SvgPreviewDialogProps {
  open: boolean;
  onOpenChange: (open: boolean) => void;
  projectId: string;
  processId: string;
  processName: string;
}

const ZOOM_STEP = 0.25;
const ZOOM_MIN = 0.25;
const ZOOM_MAX = 3;

export function SvgPreviewDialog({
  open,
  onOpenChange,
  projectId,
  processId,
  processName,
}: SvgPreviewDialogProps) {
  const [zoom, setZoom] = React.useState(1);
  const containerRef = React.useRef<HTMLDivElement>(null);

  const {
    data: svgContent,
    isLoading,
    isError,
    error,
    refetch,
  } = useQuery({
    queryKey: ["svg-preview", projectId, processId],
    queryFn: () => fetchSvgContent(projectId, processId),
    enabled: open,
    staleTime: 5 * 60 * 1000,
  });

  // Reset zoom when dialog opens
  React.useEffect(() => {
    if (open) setZoom(1);
  }, [open]);

  const handleZoomIn = () =>
    setZoom((z) => Math.min(z + ZOOM_STEP, ZOOM_MAX));
  const handleZoomOut = () =>
    setZoom((z) => Math.max(z - ZOOM_STEP, ZOOM_MIN));
  const handleFitWidth = () => setZoom(1);

  const handleOpenNewTab = () => {
    const url = exportApi.svgPreview(projectId, processId);
    window.open(url, "_blank", "noopener,noreferrer");
  };

  const handleDownload = (type: "svg" | "bpmn" | "visio") => {
    let url: string;
    switch (type) {
      case "svg":
        url = exportApi.svgPreview(projectId, processId);
        break;
      case "bpmn":
        url = exportApi.bpmn(projectId, processId);
        break;
      case "visio":
        url = exportApi.visio(projectId, processId);
        break;
    }
    const link = document.createElement("a");
    link.href = url;
    link.download = "";
    document.body.appendChild(link);
    link.click();
    document.body.removeChild(link);
  };

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent aria-describedby={undefined} className="sm:max-w-[92vw] h-[90vh] flex flex-col gap-0 p-0">
        <DialogHeader className="flex-none border-b px-4 py-3">
          <div className="flex items-center justify-between">
            <DialogTitle className="text-base font-semibold truncate mr-4">
              {processName || processId}
            </DialogTitle>
            <div className="flex items-center gap-1 shrink-0">
              {/* Zoom controls */}
              <Button
                variant="ghost"
                size="icon"
                className="size-8"
                onClick={handleZoomOut}
                disabled={zoom <= ZOOM_MIN}
                title="Уменьшить"
              >
                <ZoomOut className="size-4" />
              </Button>
              <span className="min-w-[3rem] text-center text-xs text-muted-foreground">
                {Math.round(zoom * 100)}%
              </span>
              <Button
                variant="ghost"
                size="icon"
                className="size-8"
                onClick={handleZoomIn}
                disabled={zoom >= ZOOM_MAX}
                title="Увеличить"
              >
                <ZoomIn className="size-4" />
              </Button>
              <Button
                variant="ghost"
                size="icon"
                className="size-8"
                onClick={handleFitWidth}
                title="По ширине"
              >
                <Maximize2 className="size-4" />
              </Button>

              <div className="mx-1 h-5 w-px bg-border" />

              {/* Downloads */}
              <Button
                variant="ghost"
                size="sm"
                className="h-8 text-xs"
                onClick={() => handleDownload("svg")}
                title="Скачать SVG"
              >
                <Download className="mr-1 size-3" />
                SVG
              </Button>
              <Button
                variant="ghost"
                size="sm"
                className="h-8 text-xs"
                onClick={() => handleDownload("bpmn")}
                title="Скачать BPMN XML"
              >
                <Download className="mr-1 size-3" />
                BPMN
              </Button>
              <Button
                variant="ghost"
                size="sm"
                className="h-8 text-xs"
                onClick={() => handleDownload("visio")}
                title="Скачать Visio"
              >
                <Download className="mr-1 size-3" />
                Visio
              </Button>

              <div className="mx-1 h-5 w-px bg-border" />

              {/* Open in new tab */}
              <Button
                variant="ghost"
                size="icon"
                className="size-8"
                onClick={handleOpenNewTab}
                title="Открыть в новой вкладке"
              >
                <ExternalLink className="size-4" />
              </Button>
            </div>
          </div>
        </DialogHeader>

        {/* SVG Content */}
        <div
          ref={containerRef}
          className="flex-1 overflow-auto bg-muted/30"
        >
          {isLoading && (
            <div className="flex h-full items-center justify-center">
              <div className="flex flex-col items-center gap-3">
                <Loader2 className="size-8 animate-spin text-primary" />
                <p className="text-sm text-muted-foreground">
                  Загрузка диаграммы...
                </p>
              </div>
            </div>
          )}

          {isError && (
            <div className="flex h-full items-center justify-center">
              <div className="flex flex-col items-center gap-3 text-center">
                <AlertCircle className="size-8 text-destructive" />
                <p className="text-sm font-medium">
                  Не удалось загрузить диаграмму
                </p>
                <p className="text-xs text-muted-foreground max-w-sm">
                  {(error as Error)?.message ?? "Неизвестная ошибка"}
                </p>
                <Button size="sm" variant="outline" onClick={() => refetch()}>
                  Повторить
                </Button>
              </div>
            </div>
          )}

          {svgContent && (
            <div className="flex min-h-full items-start justify-center p-6">
              <div
                className="rounded-lg bg-white p-4 shadow-sm transition-transform"
                style={{
                  transform: `scale(${zoom})`,
                  transformOrigin: "top center",
                }}
                dangerouslySetInnerHTML={{ __html: svgContent }}
              />
            </div>
          )}
        </div>
      </DialogContent>
    </Dialog>
  );
}
