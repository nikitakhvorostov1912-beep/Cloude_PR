"use client";

import * as React from "react";
import { useParams } from "next/navigation";
import { useQuery } from "@tanstack/react-query";
import {
  FileText,
  Clock,
  Users,
  MessageSquare,
  AlignLeft,
} from "lucide-react";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs";
import { ScrollArea } from "@/components/ui/scroll-area";
import { Skeleton } from "@/components/ui/skeleton";
import { Separator } from "@/components/ui/separator";
import { dataApi } from "@/lib/api";
import type { Transcript, TranscriptSegment } from "@/lib/types";

const speakerColors = [
  "text-blue-400",
  "text-green-400",
  "text-yellow-400",
  "text-purple-400",
  "text-pink-400",
  "text-orange-400",
  "text-teal-400",
  "text-red-400",
];

function formatTime(seconds: number): string {
  const m = Math.floor(seconds / 60);
  const s = Math.floor(seconds % 60);
  return `${m.toString().padStart(2, "0")}:${s.toString().padStart(2, "0")}`;
}

function formatDuration(seconds: number): string {
  const h = Math.floor(seconds / 3600);
  const m = Math.floor((seconds % 3600) / 60);
  if (h > 0) return `${h} ч ${m} мин`;
  return `${m} мин`;
}

function getSpeakerColorClass(speaker: string, speakers: string[]): string {
  const idx = speakers.indexOf(speaker);
  return speakerColors[idx % speakerColors.length];
}

export default function TranscriptsPage() {
  const params = useParams<{ id: string }>();
  const projectId = params.id;
  const [selectedId, setSelectedId] = React.useState<string | null>(null);

  const { data, isLoading } = useQuery({
    queryKey: ["transcripts", projectId],
    queryFn: () => dataApi.transcripts(projectId),
    enabled: !!projectId,
  });

  const { data: selectedTranscript, isLoading: transcriptLoading } = useQuery({
    queryKey: ["transcript", projectId, selectedId],
    queryFn: () => dataApi.transcript(projectId, selectedId!),
    enabled: !!projectId && !!selectedId,
  });

  const transcripts = data ?? [];

  // Auto-select first transcript
  React.useEffect(() => {
    if (transcripts.length > 0 && !selectedId) {
      setSelectedId(transcripts[0].id);
    }
  }, [transcripts, selectedId]);

  const speakers = React.useMemo(() => {
    if (!selectedTranscript?.segments) return [];
    const uniqueSpeakers = new Set(selectedTranscript.segments.map((s) => s.speaker));
    return Array.from(uniqueSpeakers);
  }, [selectedTranscript]);

  const speakerStats = React.useMemo(() => {
    if (!selectedTranscript?.segments) return [];
    const stats: Record<string, { count: number; totalDuration: number }> = {};
    selectedTranscript.segments.forEach((seg) => {
      if (!stats[seg.speaker]) {
        stats[seg.speaker] = { count: 0, totalDuration: 0 };
      }
      stats[seg.speaker].count += 1;
      stats[seg.speaker].totalDuration += (seg.end_time ?? 0) - (seg.start_time ?? 0);
    });
    return Object.entries(stats).map(([speaker, data]) => ({
      speaker,
      ...data,
    }));
  }, [selectedTranscript]);

  if (isLoading) {
    return (
      <div className="space-y-4">
        <Skeleton className="h-8 w-48" />
        <div className="grid gap-4 lg:grid-cols-[300px_1fr]">
          <div className="space-y-2">
            {Array.from({ length: 4 }).map((_, i) => (
              <Skeleton key={i} className="h-20" />
            ))}
          </div>
          <Skeleton className="h-96" />
        </div>
      </div>
    );
  }

  if (transcripts.length === 0) {
    return (
      <div className="space-y-6">
        <h2 className="text-2xl font-bold tracking-tight">Транскрипции</h2>
        <div className="flex flex-col items-center justify-center rounded-lg border border-dashed py-16">
          <FileText className="mb-4 size-12 text-muted-foreground" />
          <p className="text-lg font-medium">Нет транскрипций</p>
          <p className="mt-1 text-sm text-muted-foreground">
            Загрузите аудио файлы и запустите транскрипцию
          </p>
        </div>
      </div>
    );
  }

  return (
    <div className="space-y-6">
      <h2 className="text-2xl font-bold tracking-tight">Транскрипции</h2>

      <div className="grid gap-4 lg:grid-cols-[300px_1fr]">
        {/* Left: transcript list */}
        <ScrollArea className="h-[calc(100vh-200px)]">
          <div className="space-y-2 pr-2">
            {transcripts.map((t) => (
              <Card
                key={t.id}
                className={`cursor-pointer transition-colors hover:bg-accent/50 ${
                  selectedId === t.id ? "border-primary bg-accent/50" : ""
                }`}
                onClick={() => setSelectedId(t.id)}
              >
                <CardContent className="p-3">
                  <div className="flex items-start gap-2">
                    <FileText className="mt-0.5 size-4 shrink-0 text-muted-foreground" />
                    <div className="min-w-0 flex-1">
                      <p className="truncate text-sm font-medium">
                        {t.filename}
                      </p>
                      <div className="mt-1 flex flex-wrap gap-2 text-xs text-muted-foreground">
                        {t.duration_seconds && (
                          <span className="flex items-center gap-1">
                            <Clock className="size-3" />
                            {formatDuration(t.duration_seconds)}
                          </span>
                        )}
                        <span className="flex items-center gap-1">
                          <Users className="size-3" />
                          {t.speaker_count} спикер(ов)
                        </span>
                      </div>
                    </div>
                  </div>
                </CardContent>
              </Card>
            ))}
          </div>
        </ScrollArea>

        {/* Right: transcript content */}
        <Card className="flex flex-col">
          {transcriptLoading ? (
            <CardContent className="p-6">
              <div className="space-y-3">
                {Array.from({ length: 8 }).map((_, i) => (
                  <Skeleton key={i} className="h-6" />
                ))}
              </div>
            </CardContent>
          ) : selectedTranscript ? (
            <>
              <CardHeader className="pb-3">
                <CardTitle className="text-base">
                  {selectedTranscript.filename}
                </CardTitle>
              </CardHeader>
              <CardContent className="flex-1">
                <Tabs defaultValue="dialogue">
                  <TabsList>
                    <TabsTrigger value="dialogue">
                      <MessageSquare className="mr-1 size-4" />
                      Диалог
                    </TabsTrigger>
                    <TabsTrigger value="fulltext">
                      <AlignLeft className="mr-1 size-4" />
                      Полный текст
                    </TabsTrigger>
                  </TabsList>

                  {/* Dialogue view */}
                  <TabsContent value="dialogue" className="mt-4">
                    <ScrollArea className="h-[calc(100vh-420px)]">
                      <div className="space-y-3 pr-4">
                        {(selectedTranscript.segments ?? []).map((seg) => (
                          <div key={seg.id} className="group">
                            <div className="flex items-baseline gap-2 text-xs">
                              <span
                                className={`font-semibold ${getSpeakerColorClass(seg.speaker, speakers)}`}
                              >
                                {seg.speaker}
                              </span>
                              <span className="text-muted-foreground">
                                {formatTime(seg.start_time ?? 0)} — {formatTime(seg.end_time ?? 0)}
                              </span>
                            </div>
                            <p className="mt-0.5 text-sm leading-relaxed">
                              {seg.text}
                            </p>
                          </div>
                        ))}
                      </div>
                    </ScrollArea>
                  </TabsContent>

                  {/* Full text view */}
                  <TabsContent value="fulltext" className="mt-4">
                    <ScrollArea className="h-[calc(100vh-420px)]">
                      <p className="whitespace-pre-wrap pr-4 text-sm leading-relaxed">
                        {selectedTranscript.text}
                      </p>
                    </ScrollArea>
                  </TabsContent>
                </Tabs>

                {/* Speaker statistics */}
                {speakerStats.length > 0 && (
                  <>
                    <Separator className="my-4" />
                    <div>
                      <h4 className="mb-2 text-sm font-medium">
                        Статистика по спикерам
                      </h4>
                      <div className="grid gap-2 sm:grid-cols-2">
                        {speakerStats.map((stat) => (
                          <div
                            key={stat.speaker}
                            className="flex items-center justify-between rounded-md border p-2"
                          >
                            <span
                              className={`text-sm font-medium ${getSpeakerColorClass(stat.speaker, speakers)}`}
                            >
                              {stat.speaker}
                            </span>
                            <div className="flex gap-2 text-xs text-muted-foreground">
                              <Badge variant="outline" className="text-xs">
                                {stat.count} реплик
                              </Badge>
                              <Badge variant="outline" className="text-xs">
                                {formatDuration(stat.totalDuration)}
                              </Badge>
                            </div>
                          </div>
                        ))}
                      </div>
                    </div>
                  </>
                )}
              </CardContent>
            </>
          ) : (
            <CardContent className="flex items-center justify-center p-12">
              <p className="text-sm text-muted-foreground">
                Выберите транскрипцию из списка
              </p>
            </CardContent>
          )}
        </Card>
      </div>
    </div>
  );
}
