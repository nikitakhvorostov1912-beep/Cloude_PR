import { motion } from 'motion/react';
import { useLocation, useNavigate } from 'react-router-dom';
import { useUIStore } from '@/stores/ui.store';

interface NavItem {
  path: string;
  label: string;
  icon: React.ReactNode;
  getPath?: () => string;
}

export function Sidebar() {
  const location = useLocation();
  const navigate = useNavigate();
  const collapsed = useUIStore((s) => s.sidebarCollapsed);
  const toggleSidebar = useUIStore((s) => s.toggleSidebar);

  const mainNavItems: NavItem[] = [
    {
      path: '/',
      label: 'Главная',
      icon: (
        <svg width="20" height="20" viewBox="0 0 20 20" fill="none">
          <path d="M3 10L10 3L17 10V17H12V13H8V17H3V10Z" stroke="currentColor" strokeWidth="1.5" strokeLinejoin="round" />
        </svg>
      ),
    },
    {
      path: '/projects',
      label: 'Проекты',
      icon: (
        <svg width="20" height="20" viewBox="0 0 20 20" fill="none">
          <rect x="3" y="3" width="6" height="6" rx="1.5" stroke="currentColor" strokeWidth="1.5" />
          <rect x="11" y="3" width="6" height="6" rx="1.5" stroke="currentColor" strokeWidth="1.5" />
          <rect x="3" y="11" width="6" height="6" rx="1.5" stroke="currentColor" strokeWidth="1.5" />
          <rect x="11" y="11" width="6" height="6" rx="1.5" stroke="currentColor" strokeWidth="1.5" />
        </svg>
      ),
    },
    {
      path: '/pipeline',
      label: 'Обработка',
      icon: (
        <svg width="20" height="20" viewBox="0 0 20 20" fill="none">
          <circle cx="5" cy="10" r="2" stroke="currentColor" strokeWidth="1.5" />
          <circle cx="15" cy="10" r="2" stroke="currentColor" strokeWidth="1.5" />
          <path d="M7 10H13" stroke="currentColor" strokeWidth="1.5" />
          <path d="M11 7L14 10L11 13" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round" />
        </svg>
      ),
    },
    {
      path: '/viewer',
      label: 'Артефакты',
      getPath: () => '/viewer',
      icon: (
        <svg width="20" height="20" viewBox="0 0 20 20" fill="none">
          <path d="M4 3H14L16 5V17H4V3Z" stroke="currentColor" strokeWidth="1.5" strokeLinejoin="round" />
          <path d="M7 8H13M7 11H13M7 14H10" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round" />
        </svg>
      ),
    },
  ];

  const settingsItem: NavItem = {
    path: '/settings',
    label: 'Настройки',
    icon: (
      <svg width="20" height="20" viewBox="0 0 20 20" fill="none">
        <circle cx="10" cy="10" r="3" stroke="currentColor" strokeWidth="1.5" />
        <path d="M10 2V4M10 16V18M18 10H16M4 10H2M15.66 4.34L14.24 5.76M5.76 14.24L4.34 15.66M15.66 15.66L14.24 14.24M5.76 5.76L4.34 4.34" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round" />
      </svg>
    ),
  };

  const renderNavButton = (item: NavItem) => {
    const isActive = location.pathname === item.path ||
      (item.path !== '/' && location.pathname.startsWith(item.path));
    const targetPath = item.getPath ? item.getPath() : item.path;

    return (
      <motion.button
        key={item.path}
        onClick={() => navigate(targetPath)}
        className="flex items-center gap-3 px-3 py-2.5 text-sm w-full text-left"
        style={{
          color: isActive ? '#3B2FC9' : 'rgba(26,21,80,0.55)',
          fontWeight: isActive ? 600 : 500,
          background: isActive ? 'rgba(255,255,255,0.40)' : 'transparent',
          border: isActive ? '1px solid rgba(255,255,255,0.70)' : '1px solid transparent',
          borderRadius: '10px',
          transition: 'all 150ms ease',
        }}
        onMouseEnter={(e) => {
          if (!isActive) {
            e.currentTarget.style.background = 'rgba(255,255,255,0.22)';
            e.currentTarget.style.color = 'var(--color-text)';
          }
        }}
        onMouseLeave={(e) => {
          if (!isActive) {
            e.currentTarget.style.background = 'transparent';
            e.currentTarget.style.color = 'rgba(26,21,80,0.55)';
          }
        }}
        whileTap={{ scale: 0.97 }}
      >
        <span className="flex-shrink-0">{item.icon}</span>
        <motion.span
          className="whitespace-nowrap overflow-hidden"
          animate={{ opacity: collapsed ? 0 : 1, width: collapsed ? 0 : 'auto' }}
        >
          {item.label}
        </motion.span>
        {isActive && (
          <motion.div
            className="absolute left-0 w-[3px] h-6 rounded-r-full"
            style={{ background: '#3B2FC9' }}
            layoutId="activeIndicator"
            transition={{ type: 'spring', damping: 20, stiffness: 300 }}
          />
        )}
      </motion.button>
    );
  };

  return (
    <motion.aside
      className="h-full flex flex-col py-4 z-10"
      style={{
        background: 'var(--bg-sidebar)',
        backdropFilter: 'var(--blur-sidebar)',
        WebkitBackdropFilter: 'var(--blur-sidebar)',
        borderRight: '1px solid var(--glass-border)',
      }}
      animate={{ width: collapsed ? 64 : 200 }}
      transition={{ type: 'spring', damping: 20, stiffness: 200 }}
    >
      {/* Logo */}
      <div className="px-4 mb-6 flex items-center gap-3">
        <div className="flex-shrink-0">
          <svg width="34" height="34" viewBox="0 0 34 34" fill="none">
            <defs>
              <linearGradient id="logoGrad" x1="0" y1="0" x2="34" y2="34" gradientUnits="userSpaceOnUse">
                <stop offset="0%" stopColor="#7B6FE8"/>
                <stop offset="100%" stopColor="#A855F7"/>
              </linearGradient>
            </defs>
            <rect width="34" height="34" rx="10" fill="url(#logoGrad)"/>
            <path
              d="M7 17 Q10 11 13 17 Q16 23 19 17 Q22 11 25 17 Q27 21 27 17"
              stroke="rgba(255,255,255,0.95)"
              strokeWidth="2"
              strokeLinecap="round"
              fill="none"
            />
            <circle cx="17" cy="17" r="2" fill="white" opacity="0.9"/>
          </svg>
        </div>
        <motion.span
          className="text-base font-semibold whitespace-nowrap overflow-hidden"
          style={{ color: 'var(--color-text)' }}
          animate={{ opacity: collapsed ? 0 : 1, width: collapsed ? 0 : 'auto' }}
        >
          Aether
        </motion.span>
      </div>

      {/* Main nav — 4 пункта */}
      <nav className="flex-1 flex flex-col gap-1 px-2">
        {mainNavItems.map(renderNavButton)}
      </nav>

      {/* Bottom section — Настройки + Справка + Collapse */}
      <div className="flex flex-col gap-1 px-2">
        {renderNavButton(settingsItem)}

        {/* Справка — только иконка ? */}
        <button
          onClick={() => navigate('/guide')}
          className="flex items-center justify-center w-full p-2 rounded-[10px]"
          style={{
            color: location.pathname === '/guide' ? '#3B2FC9' : 'rgba(26,21,80,0.45)',
            background: location.pathname === '/guide' ? 'rgba(255,255,255,0.40)' : 'transparent',
            border: location.pathname === '/guide' ? '1px solid rgba(255,255,255,0.70)' : '1px solid transparent',
            transition: 'all 150ms ease',
          }}
          onMouseEnter={(e) => {
            if (location.pathname !== '/guide') {
              e.currentTarget.style.background = 'rgba(255,255,255,0.22)';
              e.currentTarget.style.color = 'var(--color-text)';
            }
          }}
          onMouseLeave={(e) => {
            if (location.pathname !== '/guide') {
              e.currentTarget.style.background = 'transparent';
              e.currentTarget.style.color = 'rgba(26,21,80,0.45)';
            }
          }}
          title="Справка"
        >
          <svg width="18" height="18" viewBox="0 0 18 18" fill="none">
            <circle cx="9" cy="9" r="7" stroke="currentColor" strokeWidth="1.5" />
            <path d="M7 7C7 6.17 7.67 5.5 8.5 5.5H9.5C10.33 5.5 11 6.17 11 7C11 7.83 10.33 8.5 9.5 8.5H9V10" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round" />
            <circle cx="9" cy="12" r="0.7" fill="currentColor" />
          </svg>
        </button>

        {/* Collapse toggle */}
        <button
          onClick={toggleSidebar}
          className="flex items-center justify-center w-full p-2 rounded-[10px]"
          style={{ color: 'rgba(26,21,80,0.35)', transition: 'all 150ms ease' }}
          onMouseEnter={(e) => {
            e.currentTarget.style.background = 'rgba(255,255,255,0.22)';
            e.currentTarget.style.color = 'rgba(26,21,80,0.55)';
          }}
          onMouseLeave={(e) => {
            e.currentTarget.style.background = 'transparent';
            e.currentTarget.style.color = 'rgba(26,21,80,0.35)';
          }}
        >
          <motion.svg
            width="16"
            height="16"
            viewBox="0 0 16 16"
            fill="none"
            animate={{ rotate: collapsed ? 180 : 0 }}
          >
            <path d="M10 4L6 8L10 12" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round" />
          </motion.svg>
        </button>
      </div>
    </motion.aside>
  );
}
