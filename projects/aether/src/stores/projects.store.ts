import { create } from 'zustand';
import { persist } from 'zustand/middleware';
import type { Project, Meeting } from '@/types/project.types';

interface ProjectsState {
  projects: Project[];
  meetings: Meeting[];
  activeProjectId: string | null;
  activeMeetingId: string | null;
  addProject: (project: Project) => void;
  updateProject: (id: string, data: Partial<Project>) => void;
  removeProject: (id: string) => void;
  setActiveProject: (id: string | null) => void;
  addMeeting: (meeting: Meeting) => void;
  /** Создаёт meeting, привязывает к проекту, возвращает meetingId */
  createMeeting: (projectId: string, file: File) => string;
  updateMeeting: (id: string, data: Partial<Meeting>) => void;
  removeMeeting: (id: string) => void;
  setActiveMeeting: (id: string | null) => void;
  getProjectMeetings: (projectId: string) => Meeting[];
}

export const useProjectsStore = create<ProjectsState>()(
  persist(
    (set, get) => ({
      projects: [],
      meetings: [],
      activeProjectId: null,
      activeMeetingId: null,
      addProject: (project) =>
        set((s) => ({
          projects: [...s.projects, { ...project, meetingIds: project.meetingIds ?? [] }],
        })),
      updateProject: (id, data) =>
        set((s) => ({
          projects: s.projects.map((p) =>
            p.id === id ? { ...p, ...data, updatedAt: new Date().toISOString() } : p
          ),
        })),
      removeProject: (id) =>
        set((s) => ({
          projects: s.projects.filter((p) => p.id !== id),
          meetings: s.meetings.filter((m) => m.projectId !== id),
          activeProjectId: s.activeProjectId === id ? null : s.activeProjectId,
        })),
      setActiveProject: (id) => set({ activeProjectId: id }),
      addMeeting: (meeting) =>
        set((s) => ({
          meetings: [...s.meetings, meeting],
          // Обновляем meetingIds проекта
          projects: s.projects.map((p) =>
            p.id === meeting.projectId
              ? { ...p, meetingIds: [...(p.meetingIds ?? []), meeting.id] }
              : p
          ),
        })),
      createMeeting: (projectId, file) => {
        const meetingId = crypto.randomUUID();
        const now = new Date().toISOString();
        const objectUrl = URL.createObjectURL(file);
        const meeting: Meeting = {
          id: meetingId,
          projectId,
          title: file.name.replace(/\.[^/.]+$/, ''),
          filePath: objectUrl,
          audioPath: objectUrl,
          durationSeconds: 0,
          fileSizeBytes: file.size,
          qualityScore: 0,
          status: 'uploaded',
          errorMessage: null,
          createdAt: now,
          processedAt: null,
        };
        set((s) => ({
          meetings: [...s.meetings, meeting],
          projects: s.projects.map((p) =>
            p.id === projectId
              ? { ...p, meetingIds: [...(p.meetingIds ?? []), meetingId] }
              : p
          ),
        }));
        return meetingId;
      },
      updateMeeting: (id, data) =>
        set((s) => ({
          meetings: s.meetings.map((m) =>
            m.id === id ? { ...m, ...data } : m
          ),
        })),
      removeMeeting: (id) =>
        set((s) => {
          const meeting = s.meetings.find((m) => m.id === id);
          return {
            meetings: s.meetings.filter((m) => m.id !== id),
            projects: meeting
              ? s.projects.map((p) =>
                  p.id === meeting.projectId
                    ? { ...p, meetingIds: (p.meetingIds ?? []).filter((mid) => mid !== id) }
                    : p
                )
              : s.projects,
            activeMeetingId: s.activeMeetingId === id ? null : s.activeMeetingId,
          };
        }),
      setActiveMeeting: (id) => set({ activeMeetingId: id }),
      getProjectMeetings: (projectId) =>
        get().meetings.filter((m) => m.projectId === projectId),
    }),
    {
      name: 'aether-projects',
      version: 2,
      migrate: (persisted: unknown, version: number) => {
        const state = persisted as Record<string, unknown>;
        if (version < 2) {
          // v2: добавляем meetingIds в проекты
          const projects = (state.projects as Project[]) ?? [];
          const meetings = (state.meetings as Meeting[]) ?? [];
          state.projects = projects.map((p) => ({
            ...p,
            meetingIds: p.meetingIds ?? meetings.filter((m) => m.projectId === p.id).map((m) => m.id),
          }));
        }
        return state as unknown as ProjectsState;
      },
    }
  )
);
