import { Outlet } from 'react-router-dom';
import { Sidebar } from './Sidebar';
import { BackgroundBlobs } from './BackgroundBlobs';
import { GlassToastContainer } from '@/components/glass';

export function AppLayout() {
  return (
    <div className="h-screen flex relative">
      <BackgroundBlobs />
      <Sidebar />
      <main className="flex-1 overflow-y-auto relative z-[1] p-6">
        <Outlet />
      </main>
      <GlassToastContainer />
    </div>
  );
}
