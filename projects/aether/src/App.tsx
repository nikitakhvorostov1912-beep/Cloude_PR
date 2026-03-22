import { BrowserRouter, Routes, Route, Navigate } from 'react-router-dom';
import { AnimatePresence } from 'motion/react';
import { useLocation } from 'react-router-dom';
import { lazy, Suspense, useEffect } from 'react';
import { AppLayout } from '@/components/layout/AppLayout';
import { OnboardingPage } from '@/pages/OnboardingPage';
import { DashboardPage } from '@/pages/DashboardPage';
import { useSettingsStore } from '@/stores/settings.store';
import { usePipelineStore } from '@/stores/pipeline.store';
import { useProjectsStore } from '@/stores/projects.store';
import { soundService } from '@/services/sound.service';
import { useShallow } from 'zustand/react/shallow';

// Lazy-loaded pages
const ProjectPage = lazy(() => import('@/pages/ProjectPage').then(m => ({ default: m.ProjectPage })));
const PipelinePage = lazy(() => import('@/pages/PipelinePage').then(m => ({ default: m.PipelinePage })));
const ViewerPage = lazy(() => import('@/pages/ViewerPage').then(m => ({ default: m.ViewerPage })));
const TemplatesPage = lazy(() => import('@/pages/TemplatesPage').then(m => ({ default: m.TemplatesPage })));
const SettingsPage = lazy(() => import('@/pages/SettingsPage').then(m => ({ default: m.SettingsPage })));
const GuidePage = lazy(() => import('@/pages/GuidePage').then(m => ({ default: m.GuidePage })));
const ProjectsListPage = lazy(() => import('@/pages/ProjectsListPage').then(m => ({ default: m.ProjectsListPage })));

function LazyFallback() {
  return (
    <div style={{
      display: 'flex',
      alignItems: 'center',
      justifyContent: 'center',
      height: '100%',
      background: 'transparent',
    }}>
      <div style={{
        width: 32,
        height: 32,
        border: '2px solid var(--accent)',
        borderTopColor: 'transparent',
        borderRadius: '50%',
        animation: 'spin 0.6s linear infinite',
      }} />
    </div>
  );
}

function AnimatedRoutes() {
  const location = useLocation();
  const onboardingCompleted = useSettingsStore((s) => s.onboardingCompleted);

  if (!onboardingCompleted) {
    return <OnboardingPage />;
  }

  return (
    <AnimatePresence mode="wait">
      <Routes location={location} key={location.pathname}>
        <Route element={<AppLayout />}>
          <Route path="/" element={<DashboardPage />} />
          <Route path="/projects" element={<Suspense fallback={<LazyFallback />}><ProjectsListPage /></Suspense>} />
          <Route path="/projects/:id" element={<Suspense fallback={<LazyFallback />}><ProjectPage /></Suspense>} />
          <Route path="/pipeline" element={<Suspense fallback={<LazyFallback />}><PipelinePage /></Suspense>} />
          <Route path="/viewer" element={<Suspense fallback={<LazyFallback />}><ViewerPage /></Suspense>} />
          <Route path="/templates" element={<Suspense fallback={<LazyFallback />}><TemplatesPage /></Suspense>} />
          <Route path="/guide" element={<Suspense fallback={<LazyFallback />}><GuidePage /></Suspense>} />
          <Route path="/settings" element={<Suspense fallback={<LazyFallback />}><SettingsPage /></Suspense>} />
          <Route path="*" element={<Navigate to="/" replace />} />
        </Route>
      </Routes>
    </AnimatePresence>
  );
}

export default function App() {
  const { loadKeys, soundEnabled, soundVolume } = useSettingsStore(
    useShallow((s) => ({ loadKeys: s.loadKeys, soundEnabled: s.soundEnabled, soundVolume: s.soundVolume })),
  );

  useEffect(() => {
    soundService.init();
    soundService.setEnabled(soundEnabled);
    soundService.setVolume(soundVolume);
    // Загружаем API-ключи из Stronghold при старте приложения
    loadKeys().catch((err) => {
      console.error('[App] Не удалось загрузить API-ключи:', err);
    });

    // P1-B: Очистка прерванного pipeline при рестарте
    const pipelineState = usePipelineStore.getState();
    if (pipelineState.meetingId && pipelineState.stages.complete !== 'completed') {
      const interruptedMeetingId = pipelineState.meetingId;
      usePipelineStore.getState().resetPipeline();
      useProjectsStore.getState().updateMeeting(interruptedMeetingId, {
        status: 'error',
        errorMessage: 'Обработка прервана (приложение было закрыто)',
      });
    }
  // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  return (
    <BrowserRouter>
      <AnimatedRoutes />
    </BrowserRouter>
  );
}
