import { describe, it, expect, beforeEach } from 'vitest';
import { useProjectsStore } from '@/stores/projects.store';
import type { Project, Meeting } from '@/types/project.types';

const makeProject = (override: Partial<Project> = {}): Project => ({
  id: 'project-1',
  name: 'Тестовый проект',
  description: 'Описание',
  folder: '/projects/test',
  createdAt: '2026-01-01T00:00:00.000Z',
  updatedAt: '2026-01-01T00:00:00.000Z',
  ...override,
});

const makeMeeting = (override: Partial<Meeting> = {}): Meeting => ({
  id: 'meeting-1',
  projectId: 'project-1',
  title: 'Встреча 1',
  filePath: '/files/meeting.mp3',
  audioPath: '/audio/meeting.mp3',
  durationSeconds: 3600,
  fileSizeBytes: 50_000_000,
  qualityScore: 0.9,
  status: 'uploaded',
  errorMessage: null,
  createdAt: '2026-01-01T00:00:00.000Z',
  processedAt: null,
  ...override,
});

describe('useProjectsStore', () => {
  beforeEach(() => {
    useProjectsStore.setState({
      projects: [],
      meetings: [],
      activeProjectId: null,
      activeMeetingId: null,
    });
  });

  describe('initial state', () => {
    it('starts empty', () => {
      const s = useProjectsStore.getState();
      expect(s.projects).toEqual([]);
      expect(s.meetings).toEqual([]);
      expect(s.activeProjectId).toBeNull();
      expect(s.activeMeetingId).toBeNull();
    });
  });

  describe('addProject', () => {
    it('adds a project', () => {
      useProjectsStore.getState().addProject(makeProject());
      expect(useProjectsStore.getState().projects).toHaveLength(1);
    });

    it('adds multiple projects', () => {
      useProjectsStore.getState().addProject(makeProject({ id: 'p1' }));
      useProjectsStore.getState().addProject(makeProject({ id: 'p2' }));
      expect(useProjectsStore.getState().projects).toHaveLength(2);
    });
  });

  describe('updateProject', () => {
    it('updates project name', () => {
      useProjectsStore.getState().addProject(makeProject({ id: 'p1' }));
      useProjectsStore.getState().updateProject('p1', { name: 'Новое имя' });
      const p = useProjectsStore.getState().projects.find((p) => p.id === 'p1');
      expect(p?.name).toBe('Новое имя');
    });

    it('updates updatedAt timestamp', () => {
      const before = new Date().toISOString();
      useProjectsStore.getState().addProject(makeProject({ id: 'p1', updatedAt: '2020-01-01' }));
      useProjectsStore.getState().updateProject('p1', { name: 'Updated' });
      const p = useProjectsStore.getState().projects.find((p) => p.id === 'p1');
      expect(p?.updatedAt >= before).toBe(true);
    });

    it('does not update other projects', () => {
      useProjectsStore.getState().addProject(makeProject({ id: 'p1', name: 'A' }));
      useProjectsStore.getState().addProject(makeProject({ id: 'p2', name: 'B' }));
      useProjectsStore.getState().updateProject('p1', { name: 'A Updated' });
      const p2 = useProjectsStore.getState().projects.find((p) => p.id === 'p2');
      expect(p2?.name).toBe('B');
    });
  });

  describe('removeProject', () => {
    it('removes project and its meetings', () => {
      useProjectsStore.getState().addProject(makeProject({ id: 'p1' }));
      useProjectsStore.getState().addMeeting(makeMeeting({ id: 'm1', projectId: 'p1' }));
      useProjectsStore.getState().addMeeting(makeMeeting({ id: 'm2', projectId: 'p1' }));
      useProjectsStore.getState().removeProject('p1');
      expect(useProjectsStore.getState().projects).toHaveLength(0);
      expect(useProjectsStore.getState().meetings).toHaveLength(0);
    });

    it('clears activeProjectId if removing active project', () => {
      useProjectsStore.getState().addProject(makeProject({ id: 'p1' }));
      useProjectsStore.getState().setActiveProject('p1');
      useProjectsStore.getState().removeProject('p1');
      expect(useProjectsStore.getState().activeProjectId).toBeNull();
    });

    it('does not clear activeProjectId for different project', () => {
      useProjectsStore.getState().addProject(makeProject({ id: 'p1' }));
      useProjectsStore.getState().addProject(makeProject({ id: 'p2' }));
      useProjectsStore.getState().setActiveProject('p1');
      useProjectsStore.getState().removeProject('p2');
      expect(useProjectsStore.getState().activeProjectId).toBe('p1');
    });
  });

  describe('setActiveProject', () => {
    it('sets active project', () => {
      useProjectsStore.getState().setActiveProject('p1');
      expect(useProjectsStore.getState().activeProjectId).toBe('p1');
    });

    it('clears active project with null', () => {
      useProjectsStore.getState().setActiveProject('p1');
      useProjectsStore.getState().setActiveProject(null);
      expect(useProjectsStore.getState().activeProjectId).toBeNull();
    });
  });

  describe('meetings', () => {
    it('adds a meeting', () => {
      useProjectsStore.getState().addMeeting(makeMeeting());
      expect(useProjectsStore.getState().meetings).toHaveLength(1);
    });

    it('updates meeting status', () => {
      useProjectsStore.getState().addMeeting(makeMeeting({ id: 'm1', status: 'uploaded' }));
      useProjectsStore.getState().updateMeeting('m1', { status: 'completed' });
      const m = useProjectsStore.getState().meetings.find((m) => m.id === 'm1');
      expect(m?.status).toBe('completed');
    });

    it('removes a meeting', () => {
      useProjectsStore.getState().addMeeting(makeMeeting({ id: 'm1' }));
      useProjectsStore.getState().removeMeeting('m1');
      expect(useProjectsStore.getState().meetings).toHaveLength(0);
    });

    it('clears activeMeetingId when removing active meeting', () => {
      useProjectsStore.getState().addMeeting(makeMeeting({ id: 'm1' }));
      useProjectsStore.getState().setActiveMeeting('m1');
      useProjectsStore.getState().removeMeeting('m1');
      expect(useProjectsStore.getState().activeMeetingId).toBeNull();
    });
  });

  describe('getProjectMeetings', () => {
    it('returns meetings for specific project', () => {
      useProjectsStore.getState().addMeeting(makeMeeting({ id: 'm1', projectId: 'p1' }));
      useProjectsStore.getState().addMeeting(makeMeeting({ id: 'm2', projectId: 'p1' }));
      useProjectsStore.getState().addMeeting(makeMeeting({ id: 'm3', projectId: 'p2' }));
      const meetings = useProjectsStore.getState().getProjectMeetings('p1');
      expect(meetings).toHaveLength(2);
      expect(meetings.every((m) => m.projectId === 'p1')).toBe(true);
    });

    it('returns empty array for project with no meetings', () => {
      const meetings = useProjectsStore.getState().getProjectMeetings('p-empty');
      expect(meetings).toEqual([]);
    });
  });
});
