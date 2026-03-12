import { AnimatedPage } from '@/components/shared/AnimatedPage';
import { EmptyState } from '@/components/shared/EmptyState';

export function ViewerPage() {
  return (
    <AnimatedPage>
      <div className="max-w-4xl mx-auto">
        <h1 className="text-2xl font-bold text-text mb-6">Артефакты</h1>
        <EmptyState
          title="Нет артефактов"
          description="Обработайте запись встречи, чтобы увидеть результаты"
          icon={
            <svg width="32" height="32" viewBox="0 0 32 32" fill="none">
              <path d="M6 4H20L26 10V28H6V4Z" stroke="currentColor" strokeWidth="2" strokeLinejoin="round" />
              <path d="M10 14H22M10 19H22M10 24H16" stroke="currentColor" strokeWidth="2" strokeLinecap="round" />
            </svg>
          }
        />
      </div>
    </AnimatedPage>
  );
}
