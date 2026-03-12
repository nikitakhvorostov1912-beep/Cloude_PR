import { motion } from 'motion/react';
import { AnimatedPage } from '@/components/shared/AnimatedPage';
import { GlassCard, GlassButton } from '@/components/glass';
import { useArtifactsStore } from '@/stores/artifacts.store';
import { useShallow } from 'zustand/react/shallow';
import { ARTIFACT_LABELS } from '@/types/artifact.types';
import { useSound } from '@/hooks/useSound';

export function TemplatesPage() {
  const { templates, selectedTemplate, setSelectedTemplate } = useArtifactsStore(
    useShallow((s) => ({ templates: s.templates, selectedTemplate: s.selectedTemplate, setSelectedTemplate: s.setSelectedTemplate }))
  );
  const { play } = useSound();

  return (
    <AnimatedPage>
      <div className="max-w-4xl mx-auto">
        <div className="flex items-center justify-between mb-6">
          <div>
            <h1 className="text-2xl font-bold text-text">Шаблоны</h1>
            <p className="text-sm text-text-secondary mt-1">
              Предустановленные и пользовательские профили артефактов
            </p>
          </div>
          <GlassButton variant="secondary" onClick={() => play('click')}>
            Создать шаблон
          </GlassButton>
        </div>

        <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
          {templates.map((template, i) => (
            <motion.div
              key={template.id}
              initial={{ opacity: 0, y: 20 }}
              animate={{ opacity: 1, y: 0 }}
              transition={{ delay: i * 0.05 }}
            >
              <GlassCard
                hoverable
                padding="md"
                className={selectedTemplate === template.id ? 'ring-2 ring-primary/40' : ''}
                onClick={() => {
                  play('click');
                  setSelectedTemplate(template.id);
                }}
              >
                <div className="flex items-start justify-between mb-3">
                  <div>
                    <h3 className="font-semibold text-text">{template.name}</h3>
                    <p className="text-xs text-text-secondary mt-0.5">{template.description}</p>
                  </div>
                  {template.isPreset && (
                    <span className="text-[10px] px-2 py-0.5 rounded-md bg-primary/10 text-primary font-medium">
                      Встроенный
                    </span>
                  )}
                </div>
                <div className="flex flex-wrap gap-1.5">
                  {template.artifactTypes.map((type) => (
                    <span
                      key={type}
                      className="text-[11px] px-2 py-0.5 rounded-md bg-white/50 text-text-secondary"
                    >
                      {ARTIFACT_LABELS[type]}
                    </span>
                  ))}
                </div>
                {selectedTemplate === template.id && (
                  <motion.div
                    className="mt-3 pt-3 border-t border-white/20 text-xs text-primary font-medium"
                    initial={{ opacity: 0 }}
                    animate={{ opacity: 1 }}
                  >
                    Выбран для обработки
                  </motion.div>
                )}
              </GlassCard>
            </motion.div>
          ))}
        </div>
      </div>
    </AnimatedPage>
  );
}
