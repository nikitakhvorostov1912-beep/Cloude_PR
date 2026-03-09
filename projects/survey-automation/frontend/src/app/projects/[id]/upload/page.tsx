"use client";

import * as React from "react";
import { useParams } from "next/navigation";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { toast } from "sonner";
import {
  Upload,
  FileAudio,
  FileText,
  FolderInput,
  File,
  Loader2,
} from "lucide-react";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";

import { Badge } from "@/components/ui/badge";
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs";
import { Skeleton } from "@/components/ui/skeleton";
import { uploadApi, dataApi } from "@/lib/api";

const ACCEPTED_AUDIO = [".wav", ".mp3", ".ogg", ".m4a", ".flac"];
const ACCEPTED_TEXT = [".txt", ".json"];


export default function UploadPage() {
  const params = useParams<{ id: string }>();
  const projectId = params.id;
  const queryClient = useQueryClient();

  const [dragActive, setDragActive] = React.useState(false);

  const [folderPath, setFolderPath] = React.useState("");
  const fileInputRef = React.useRef<HTMLInputElement>(null);
  const textInputRef = React.useRef<HTMLInputElement>(null);

  const { data: transcriptsData, isLoading: transcriptsLoading } = useQuery({
    queryKey: ["transcripts", projectId],
    queryFn: () => dataApi.transcripts(projectId),
    enabled: !!projectId,
  });

  const [uploadingFiles, setUploadingFiles] = React.useState<Set<string>>(new Set());

  const uploadAudioMutation = useMutation({
    mutationFn: (file: File) => {
      setUploadingFiles((prev) => new Set(prev).add(file.name));

      return uploadApi.audio(projectId, file).finally(() => {
        setUploadingFiles((prev) => {
          const next = new Set(prev);
          next.delete(file.name);
          return next;
        });
      });
    },
    onSuccess: (_data, file) => {
      toast.success(`Файл "${file.name}" загружен`);
      queryClient.invalidateQueries({ queryKey: ["transcripts", projectId] });
    },
    onError: (err: Error, file) => {
      toast.error(`Ошибка загрузки "${file.name}": ${err.message}`);
    },
  });

  const uploadTranscriptMutation = useMutation({
    mutationFn: (file: File) => uploadApi.transcript(projectId, file),
    onSuccess: (_data, file) => {
      toast.success(`Транскрипт "${file.name}" загружен`);
      queryClient.invalidateQueries({ queryKey: ["transcripts", projectId] });
    },
    onError: (err: Error, file) => {
      toast.error(`Ошибка загрузки "${file.name}": ${err.message}`);
    },
  });

  const importFolderMutation = useMutation({
    mutationFn: (path: string) => uploadApi.importFolder(projectId, path),
    onSuccess: (data) => {
      toast.success(`Импортировано файлов: ${data.imported_count}`);
      setFolderPath("");
      queryClient.invalidateQueries({ queryKey: ["transcripts", projectId] });
    },
    onError: (err: Error) => {
      toast.error(err.message);
    },
  });

  const handleDrop = React.useCallback(
    (e: React.DragEvent) => {
      e.preventDefault();
      setDragActive(false);

      const files = Array.from(e.dataTransfer.files);
      files.forEach((file) => {
        const ext = "." + file.name.split(".").pop()?.toLowerCase();
        if (ACCEPTED_AUDIO.includes(ext)) {
          uploadAudioMutation.mutate(file);
        } else {
          toast.error(
            `Формат "${ext}" не поддерживается. Допустимые: ${ACCEPTED_AUDIO.join(", ")}`,
          );
        }
      });
    },
    [uploadAudioMutation],
  );

  const handleDragOver = (e: React.DragEvent) => {
    e.preventDefault();
    setDragActive(true);
  };

  const handleDragLeave = () => {
    setDragActive(false);
  };

  const handleFileSelect = (e: React.ChangeEvent<HTMLInputElement>, type: "audio" | "text") => {
    const files = Array.from(e.target.files ?? []);
    files.forEach((file) => {
      if (type === "audio") {
        uploadAudioMutation.mutate(file);
      } else {
        uploadTranscriptMutation.mutate(file);
      }
    });
    e.target.value = "";
  };

  const transcripts = transcriptsData?.transcripts ?? [];

  return (
    <div className="space-y-6">
      <div>
        <h2 className="text-2xl font-bold tracking-tight">Загрузка файлов</h2>
        <p className="mt-1 text-muted-foreground">
          Загрузите аудиозаписи интервью или готовые транскрипты
        </p>
      </div>

      <Tabs defaultValue="audio">
        <TabsList>
          <TabsTrigger value="audio">
            <FileAudio className="mr-1 size-4" />
            Аудио файлы
          </TabsTrigger>
          <TabsTrigger value="transcript">
            <FileText className="mr-1 size-4" />
            Загрузить транскрипт
          </TabsTrigger>
          <TabsTrigger value="folder">
            <FolderInput className="mr-1 size-4" />
            Указать папку
          </TabsTrigger>
        </TabsList>

        {/* Audio upload tab */}
        <TabsContent value="audio" className="mt-4">
          <div
            onDrop={handleDrop}
            onDragOver={handleDragOver}
            onDragLeave={handleDragLeave}
            onClick={() => fileInputRef.current?.click()}
            className={`flex min-h-[240px] cursor-pointer flex-col items-center justify-center rounded-lg border-2 border-dashed p-8 transition-colors ${
              dragActive
                ? "border-primary bg-primary/5"
                : "border-muted-foreground/25 hover:border-primary/50 hover:bg-muted/50"
            }`}
          >
            <Upload
              className={`mb-4 size-12 ${
                dragActive ? "text-primary" : "text-muted-foreground"
              }`}
            />
            <p className="mb-2 text-lg font-medium">
              Перетащите аудио файлы сюда
            </p>
            <p className="mb-4 text-sm text-muted-foreground">
              или нажмите для выбора
            </p>
            <p className="text-xs text-muted-foreground">
              Поддерживаемые форматы: WAV, MP3, OGG, M4A, FLAC
            </p>
            <input
              ref={fileInputRef}
              type="file"
              accept={ACCEPTED_AUDIO.join(",")}
              multiple
              className="hidden"
              onChange={(e) => handleFileSelect(e, "audio")}
            />
          </div>

          {/* Upload progress */}
          {uploadingFiles.size > 0 && (
            <div className="mt-4 space-y-2">
              {Array.from(uploadingFiles).map((name) => (
                <div key={name} className="flex items-center gap-3">
                  <Loader2 className="size-4 shrink-0 animate-spin text-primary" />
                  <span className="min-w-0 flex-1 truncate text-sm">{name}</span>
                  <span className="text-xs text-muted-foreground">Загрузка...</span>
                </div>
              ))}
            </div>
          )}
        </TabsContent>

        {/* Transcript upload tab */}
        <TabsContent value="transcript" className="mt-4">
          <Card>
            <CardHeader>
              <CardTitle className="text-base">Загрузка транскриптов</CardTitle>
            </CardHeader>
            <CardContent>
              <div className="space-y-4">
                <p className="text-sm text-muted-foreground">
                  Загрузите готовые транскрипты в формате TXT или JSON
                </p>
                <div
                  onClick={() => textInputRef.current?.click()}
                  className="flex min-h-[160px] cursor-pointer flex-col items-center justify-center rounded-lg border-2 border-dashed border-muted-foreground/25 p-6 transition-colors hover:border-primary/50 hover:bg-muted/50"
                >
                  <FileText className="mb-3 size-10 text-muted-foreground" />
                  <p className="mb-1 text-sm font-medium">
                    Нажмите для выбора файлов
                  </p>
                  <p className="text-xs text-muted-foreground">
                    Форматы: .txt, .json
                  </p>
                  <input
                    ref={textInputRef}
                    type="file"
                    accept={ACCEPTED_TEXT.join(",")}
                    multiple
                    className="hidden"
                    onChange={(e) => handleFileSelect(e, "text")}
                  />
                </div>
                {uploadTranscriptMutation.isPending && (
                  <div className="flex items-center gap-2 text-sm text-muted-foreground">
                    <Loader2 className="size-4 animate-spin" />
                    Загрузка...
                  </div>
                )}
              </div>
            </CardContent>
          </Card>
        </TabsContent>

        {/* Folder import tab */}
        <TabsContent value="folder" className="mt-4">
          <Card>
            <CardHeader>
              <CardTitle className="text-base">Импорт из папки</CardTitle>
            </CardHeader>
            <CardContent>
              <div className="space-y-4">
                <p className="text-sm text-muted-foreground">
                  Укажите путь к папке с аудио файлами на сервере
                </p>
                <div className="flex gap-2">
                  <div className="flex-1">
                    <Label htmlFor="folder-path" className="sr-only">
                      Путь к папке
                    </Label>
                    <Input
                      id="folder-path"
                      placeholder="C:\Interviews\Project1 или /data/interviews"
                      value={folderPath}
                      onChange={(e) => setFolderPath(e.target.value)}
                      onKeyDown={(e) => {
                        if (e.key === "Enter" && folderPath.trim()) {
                          importFolderMutation.mutate(folderPath.trim());
                        }
                      }}
                    />
                  </div>
                  <Button
                    onClick={() => {
                      if (folderPath.trim()) {
                        importFolderMutation.mutate(folderPath.trim());
                      }
                    }}
                    disabled={!folderPath.trim() || importFolderMutation.isPending}
                  >
                    {importFolderMutation.isPending ? (
                      <Loader2 className="mr-2 size-4 animate-spin" />
                    ) : (
                      <FolderInput className="mr-2 size-4" />
                    )}
                    Импортировать
                  </Button>
                </div>
              </div>
            </CardContent>
          </Card>
        </TabsContent>
      </Tabs>

      {/* Uploaded files list */}
      <div>
        <h3 className="mb-3 text-lg font-semibold">Загруженные файлы</h3>
        {transcriptsLoading ? (
          <div className="space-y-2">
            {Array.from({ length: 3 }).map((_, i) => (
              <Skeleton key={i} className="h-14" />
            ))}
          </div>
        ) : transcripts.length === 0 ? (
          <div className="flex flex-col items-center justify-center rounded-lg border border-dashed py-12">
            <File className="mb-3 size-10 text-muted-foreground" />
            <p className="text-sm text-muted-foreground">Нет загруженных файлов</p>
          </div>
        ) : (
          <div className="space-y-2">
            {transcripts.map((t) => (
              <Card key={t.id}>
                <CardContent className="flex items-center justify-between p-3">
                  <div className="flex items-center gap-3">
                    <FileAudio className="size-5 text-muted-foreground" />
                    <div>
                      <p className="text-sm font-medium">{t.filename}</p>
                      <p className="text-xs text-muted-foreground">
                        {t.source_type === "audio" ? "Аудио" : "Текст"}
                        {t.duration_seconds
                          ? ` / ${Math.round(t.duration_seconds / 60)} мин`
                          : ""}
                        {` / ${t.speaker_count} спикер(ов)`}
                      </p>
                    </div>
                  </div>
                  <div className="flex items-center gap-2">
                    <Badge variant="outline" className="text-xs">
                      {t.source_type}
                    </Badge>
                  </div>
                </CardContent>
              </Card>
            ))}
          </div>
        )}
      </div>
    </div>
  );
}
