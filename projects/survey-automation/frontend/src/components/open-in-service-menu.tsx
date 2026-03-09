"use client";

import * as React from "react";
import { ExternalLink } from "lucide-react";
import { toast } from "sonner";
import { Button } from "@/components/ui/button";
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuLabel,
  DropdownMenuSeparator,
  DropdownMenuTrigger,
} from "@/components/ui/dropdown-menu";

type FileType = "bpmn" | "visio" | "docx" | "xlsx";

interface ServiceInfo {
  name: string;
  url: string;
  instruction: string;
}

const SERVICES: Record<FileType, ServiceInfo[]> = {
  bpmn: [
    {
      name: "diagrams.net",
      url: "https://app.diagrams.net/",
      instruction:
        "Перетащите скачанный .bpmn файл в редактор или используйте Файл > Импорт",
    },
    {
      name: "bpmn.io",
      url: "https://demo.bpmn.io/new",
      instruction:
        "Нажмите иконку импорта (стрелка вверх) и выберите скачанный .bpmn файл",
    },
  ],
  visio: [
    {
      name: "diagrams.net",
      url: "https://app.diagrams.net/",
      instruction:
        "Перетащите скачанный .vsdx файл в редактор или используйте Файл > Импорт",
    },
  ],
  docx: [
    {
      name: "Google Docs",
      url: "https://docs.google.com/document/",
      instruction:
        "Нажмите «Пустой документ» → Файл → Открыть → Загрузить скачанный .docx файл",
    },
    {
      name: "Office Online",
      url: "https://www.office.com/launch/word",
      instruction:
        "Войдите в аккаунт и загрузите скачанный .docx файл через «Отправить и открыть»",
    },
  ],
  xlsx: [
    {
      name: "Google Sheets",
      url: "https://sheets.google.com/",
      instruction:
        "Нажмите «Пустая таблица» → Файл → Открыть → Загрузить скачанный .xlsx файл",
    },
    {
      name: "Office Online",
      url: "https://www.office.com/launch/excel",
      instruction:
        "Войдите в аккаунт и загрузите скачанный .xlsx файл через «Отправить и открыть»",
    },
  ],
};

interface OpenInServiceMenuProps {
  downloadUrl: string;
  fileType: FileType;
}

export function OpenInServiceMenu({
  downloadUrl,
  fileType,
}: OpenInServiceMenuProps) {
  const services = SERVICES[fileType] ?? [];

  if (services.length === 0) return null;

  const handleOpenInService = (service: ServiceInfo) => {
    // 1. Trigger file download
    const link = document.createElement("a");
    link.href = downloadUrl;
    link.download = "";
    document.body.appendChild(link);
    link.click();
    document.body.removeChild(link);

    // 2. Open the service in a new tab
    window.open(service.url, "_blank", "noopener,noreferrer");

    // 3. Show instruction toast
    toast.info(service.instruction, {
      duration: 8000,
      description: `Файл скачан. Откройте его в ${service.name}:`,
    });
  };

  return (
    <DropdownMenu>
      <DropdownMenuTrigger asChild>
        <Button
          variant="ghost"
          size="icon"
          className="size-8 shrink-0"
          title="Открыть в онлайн-сервисе"
        >
          <ExternalLink className="size-4" />
        </Button>
      </DropdownMenuTrigger>
      <DropdownMenuContent align="end">
        <DropdownMenuLabel className="text-xs">
          Открыть в...
        </DropdownMenuLabel>
        <DropdownMenuSeparator />
        {services.map((service) => (
          <DropdownMenuItem
            key={service.name}
            onClick={() => handleOpenInService(service)}
            className="cursor-pointer"
          >
            <ExternalLink className="mr-2 size-3" />
            {service.name}
          </DropdownMenuItem>
        ))}
      </DropdownMenuContent>
    </DropdownMenu>
  );
}
