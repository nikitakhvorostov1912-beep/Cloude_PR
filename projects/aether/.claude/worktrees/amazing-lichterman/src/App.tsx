import { BrowserRouter, Routes, Route, Navigate } from 'react-router-dom';
import { AnimatePresence } from 'motion/react';
import { useLocation } from 'react-router-dom';
import { AppLayout } from '@/components/layout/AppLayout';
import { OnboardingPage } from '@/pages/OnboardingPage';
import { DashboardPage } from '@/pages/DashboardPage';
import { ProjectPage } from '@/pages/ProjectPage';
import { PipelinePage } from '@/pages/PipelinePage';
import { ViewerPage } from '@/pages/ViewerPage';
import { TemplatesPage } from '@/pages/TemplatesPage';
import { SettingsPage } from '@/pages/SettingsPage';
import { useSettingsStore } from '@/stores/settings.store';
import { useEffect } from 'react';
import { soundService } from '@/services/sound.service';

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
          <Route path="/projects" element={<DashboardPage />} />
          <Route path="/projects/:id" element={<ProjectPage />} />
          <Route path="/pipeline" element={<PipelinePage />} />
          <Route path="/viewer" element={<ViewerPage />} />
          <Route path="/templates" element={<TemplatesPage />} />
          <Route path="/settings" element={<SettingsPage />} />
          <Route path="*" element={<Navigate to="/" replace />} />
        </Route>
      </Routes>
    </AnimatePresence>
  );
}

export default function App() {
  useEffect(() => {
    soundService.init();
  }, []);

  return (
    <BrowserRouter>
      <AnimatedRoutes />
    </BrowserRouter>
  );
}
