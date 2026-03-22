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
        set((s) => ({ projects: [...s.projects, project] })),
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
        set((s) => ({ meetings: [...s.meetings, meeting] })),
      updateMeeting: (id, data) =>
        set((s) => ({
          meetings: s.meetings.map((m) =>
            m.id === id ? { ...m, ...data } : m
          ),
        })),
      removeMeeting: (id) =>
        set((s) => ({
          meetings: s.meetings.filter((m) => m.id !== id),
          activeMeetingId: s.activeMeetingId === id ? null : s.activeMeetingId,
        })),
      setActiveMeeting: (id) => set({ activeMeetingId: id }),
      getProjectMeetings: (projectId) =>
        get().meetings.filter((m) => m.projectId === projectId),
    }),
    {
      name: 'aether-projects',
    }
  )
);
