"use client";

import * as React from "react";
import { useRouter } from "next/navigation";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { toast } from "sonner";
import {
  Plus,
  ClipboardList,
  Calendar,
  FolderOpen,
} from "lucide-react";
import { Button } from "@/components/ui/button";
import {
  Card,
  CardContent,
  CardDescription,
  CardHeader,
  CardTitle,
} from "@/components/ui/card";
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
  DialogTrigger,
} from "@/components/ui/dialog";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Textarea } from "@/components/ui/textarea";
import { Skeleton } from "@/components/ui/skeleton";
import { Progress } from "@/components/ui/progress";
import { Badge } from "@/components/ui/badge";
import { projectsApi } from "@/lib/api";
import type { Project, ProjectCreate } from "@/lib/types";

const statusLabels: Record<string, string> = {
  new: "Новый",
  in_progress: "В работе",
  completed: "Завершён",
  error: "Ошибка",
};

const statusVariants: Record<string, "default" | "secondary" | "destructive" | "outline"> = {
  new: "outline",
  in_progress: "default",
  completed: "secondary",
  error: "destructive",
};

function formatDate(dateStr: string): string {
  return new Date(dateStr).toLocaleDateString("ru-RU", {
    day: "numeric",
    month: "long",
    year: "numeric",
  });
}

export default function ProjectsPage() {
  const router = useRouter();
  const queryClient = useQueryClient();
  const [dialogOpen, setDialogOpen] = React.useState(false);
  const [name, setName] = React.useState("");
  const [description, setDescription] = React.useState("");

  const { data, isLoading, error } = useQuery({
    queryKey: ["projects"],
    queryFn: () => projectsApi.list(),
  });

  const createMutation = useMutation({
    mutationFn: (data: ProjectCreate) => projectsApi.create(data),
    onSuccess: (res) => {
      queryClient.invalidateQueries({ queryKey: ["projects"] });
      toast.success("Проект создан");
      setDialogOpen(false);
      setName("");
      setDescription("");
      router.push(`/projects/${res.id}`);
    },
    onError: (err: Error) => {
      toast.error(err.message);
    },
  });

  const handleCreate = () => {
    if (!name.trim()) {
      toast.error("Введите название проекта");
      return;
    }
    createMutation.mutate({ name: name.trim(), description: description.trim() });
  };

  const projects = data?.projects ?? [];

  const pipelineProgress = (project: Project): number => {
    const stages = project.pipeline_state?.completed_stages ?? [];
    return Math.round((stages.length / 7) * 100);
  };

  if (error) {
    return (
      <div className="flex min-h-screen items-center justify-center">
        <Card className="w-full max-w-md">
          <CardHeader>
            <CardTitle className="text-destructive">Ошибка загрузки</CardTitle>
            <CardDescription>{(error as Error).message}</CardDescription>
          </CardHeader>
        </Card>
      </div>
    );
  }

  return (
    <div className="min-h-screen bg-background">
      <div className="mx-auto max-w-6xl p-6">
        {/* Header */}
        <div className="mb-8 flex items-center justify-between">
          <div>
            <h1 className="text-3xl font-bold tracking-tight">Проекты</h1>
            <p className="mt-1 text-muted-foreground">
              Управление проектами обследования
            </p>
          </div>
          <Dialog open={dialogOpen} onOpenChange={setDialogOpen}>
            <DialogTrigger asChild>
              <Button>
                <Plus className="mr-2 size-4" />
                Создать проект
              </Button>
            </DialogTrigger>
            <DialogContent>
              <DialogHeader>
                <DialogTitle>Новый проект</DialogTitle>
                <DialogDescription>
                  Создайте новый проект обследования бизнес-процессов
                </DialogDescription>
              </DialogHeader>
              <div className="grid gap-4 py-4">
                <div className="grid gap-2">
                  <Label htmlFor="name">Название</Label>
                  <Input
                    id="name"
                    placeholder="Название проекта"
                    value={name}
                    onChange={(e) => setName(e.target.value)}
                    onKeyDown={(e) => {
                      if (e.key === "Enter") handleCreate();
                    }}
                  />
                </div>
                <div className="grid gap-2">
                  <Label htmlFor="description">Описание</Label>
                  <Textarea
                    id="description"
                    placeholder="Краткое описание проекта"
                    value={description}
                    onChange={(e) => setDescription(e.target.value)}
                    rows={3}
                  />
                </div>
              </div>
              <DialogFooter>
                <Button
                  variant="outline"
                  onClick={() => setDialogOpen(false)}
                >
                  Отмена
                </Button>
                <Button
                  onClick={handleCreate}
                  disabled={createMutation.isPending}
                >
                  {createMutation.isPending ? "Создание..." : "Создать"}
                </Button>
              </DialogFooter>
            </DialogContent>
          </Dialog>
        </div>

        {/* Loading state */}
        {isLoading && (
          <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-3">
            {Array.from({ length: 6 }).map((_, i) => (
              <Card key={i}>
                <CardHeader>
                  <Skeleton className="h-5 w-3/4" />
                  <Skeleton className="h-4 w-1/2" />
                </CardHeader>
                <CardContent>
                  <Skeleton className="h-2 w-full" />
                </CardContent>
              </Card>
            ))}
          </div>
        )}

        {/* Empty state */}
        {!isLoading && projects.length === 0 && (
          <div className="flex flex-col items-center justify-center rounded-lg border border-dashed py-16">
            <FolderOpen className="mb-4 size-16 text-muted-foreground" />
            <h2 className="mb-2 text-xl font-semibold">Нет проектов</h2>
            <p className="mb-6 text-muted-foreground">
              Создайте первый проект для начала работы
            </p>
            <Button onClick={() => setDialogOpen(true)}>
              <Plus className="mr-2 size-4" />
              Создать проект
            </Button>
          </div>
        )}

        {/* Project cards */}
        {!isLoading && projects.length > 0 && (
          <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-3">
            {projects.map((project) => (
              <Card
                key={project.id}
                className="cursor-pointer transition-colors hover:bg-accent/50"
                onClick={() => router.push(`/projects/${project.id}`)}
              >
                <CardHeader className="pb-3">
                  <div className="flex items-start justify-between">
                    <div className="flex items-center gap-2">
                      <ClipboardList className="size-5 text-primary" />
                      <CardTitle className="text-base">{project.name}</CardTitle>
                    </div>
                    <Badge variant={statusVariants[project.status] ?? "outline"}>
                      {statusLabels[project.status] ?? project.status}
                    </Badge>
                  </div>
                  {project.description && (
                    <CardDescription className="line-clamp-2">
                      {project.description}
                    </CardDescription>
                  )}
                </CardHeader>
                <CardContent>
                  <div className="space-y-2">
                    <div className="flex items-center justify-between text-xs text-muted-foreground">
                      <span className="flex items-center gap-1">
                        <Calendar className="size-3" />
                        {formatDate(project.created_at)}
                      </span>
                      <span>{pipelineProgress(project)}%</span>
                    </div>
                    <Progress value={pipelineProgress(project)} />
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
