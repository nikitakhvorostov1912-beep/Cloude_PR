/**
 * Страница шаблонов артефактов.
 * Предустановленные и пользовательские профили с CRUD.
 */

import { useState, useCallback } from 'react';
import { motion, AnimatePresence } from 'motion/react';
import { AnimatedPage } from '@/components/shared/AnimatedPage';
import { GlassCard, GlassButton, GlassInput, GlassModal } from '@/components/glass';
import { useArtifactsStore } from '@/stores/artifacts.store';
import { useShallow } from 'zustand/react/shallow';
import type { ArtifactType, Template } from '@/types/artifact.types';
import { ARTIFACT_LABELS, ARTIFACT_ICONS } from '@/types/artifact.types';
import { useSound } from '@/hooks/useSound';

const ALL_TYPES: ArtifactType[] = [
  'protocol', 'requirements', 'risks', 'glossary', 'questions', 'transcript',
];

/** Модальное окно создания/редактирования шаблона */
function TemplateModal({
  open,
  onClose,
  editTemplate,
}: {
  open: boolean;
  onClose: () => void;
  editTemplate?: Template | null;
}) {
  const { addTemplate, updateTemplate } = useArtifactsStore(
    useShallow((s) => ({ addTemplate: s.addTemplate, updateTemplate: s.updateTemplate })),
  );
  const { play } = useSound();
  const isEdit = !!editTemplate;

  const [name, setName] = useState(editTemplate?.name || '');
  const [description, setDescription] = useState(editTemplate?.description || '');
  const [types, setTypes] = useState<ArtifactType[]>(editTemplate?.artifactTypes || ['protocol']);
  const [customPrompt, setCustomPrompt] = useState(editTemplate?.customPrompt || '');
  const [error, setError] = useState('');

  const toggleType = useCallback((t: ArtifactType) => {
    setTypes((prev) =>
      prev.includes(t) ? prev.filter((x) => x !== t) : [...prev, t],
    );
  }, []);

  const handleSave = () => {
    if (!name.trim()) {
      setError('Введите название шаблона');
      return;
    }
    if (types.length === 0) {
      setError('Выберите хотя бы один тип артефакта');
      return;
    }

    if (isEdit && editTemplate) {
      updateTemplate(editTemplate.id, {
        name: name.trim(),
        description: description.trim(),
        artifactTypes: types,
        customPrompt: customPrompt.trim() || null,
      });
    } else {
      addTemplate({
        id: `custom-${Date.now()}`,
        name: name.trim(),
        description: description.trim(),
        artifactTypes: types,
        customPrompt: customPrompt.trim() || null,
        isPreset: false,
        createdAt: new Date().toISOString(),
      });
    }
    play('success');
    onClose();
  };

  return (
    <GlassModal
      open={open}
      onClose={onClose}
      title={isEdit ? 'Редактировать шаблон' : 'Новый шаблон'}
      footer={
        <>
          <GlassButton variant="secondary" size="sm" onClick={onClose}>
            Отмена
          </GlassButton>
          <GlassButton size="sm" onClick={handleSave}>
            {isEdit ? 'Сохранить' : 'Создать'}
          </GlassButton>
        </>
      }
    >
      <div className="space-y-4">
        <GlassInput
          label="Название"
          placeholder="Например: Мой шаблон"
          value={name}
          onChange={(e) => { setName(e.target.value); setError(''); }}
          error={error && !name.trim() ? error : undefined}
        />

        <GlassInput
          label="Описание"
          placeholder="Краткое описание назначения"
          value={description}
          onChange={(e) => setDescription(e.target.value)}
        />

        {/* Выбор типов артефактов */}
        <div>
          <label className="text-sm font-medium text-text-secondary block mb-2">
            Типы артефактов
          </label>
          {error && types.length === 0 && (
            <p className="text-xs text-error mb-2">{error}</p>
          )}
          <div className="grid grid-cols-2 gap-2">
            {ALL_TYPES.map((t) => {
              const selected = types.includes(t);
              return (
                <button
                  key={t}
                  onClick={() => toggleType(t)}
                  className={`
                    flex items-center gap-2 px-3 py-2 rounded-xl text-sm transition-all duration-200
                    ${selected
                      ? 'bg-primary/15 text-primary border border-primary/30'
                      : 'bg-white/30 text-text-secondary border border-white/20 hover:bg-white/50'
                    }
                  `}
                >
                  <span>{ARTIFACT_ICONS[t]}</span>
                  <span>{ARTIFACT_LABELS[t]}</span>
                  {selected && (
                    <svg className="w-3.5 h-3.5 ml-auto text-primary" viewBox="0 0 14 14" fill="none">
                      <path d="M2 7L5.5 10.5L12 3.5" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" />
                    </svg>
                  )}
                </button>
              );
            })}
          </div>
        </div>

        {/* Кастомный промпт */}
        <div>
          <label className="text-sm font-medium text-text-secondary block mb-1.5">
            Кастомный промпт
            <span className="text-text-muted font-normal ml-1">(опционально)</span>
          </label>
          <textarea
            value={customPrompt}
            onChange={(e) => setCustomPrompt(e.target.value)}
            placeholder="Дополнительные инструкции для AI..."
            rows={3}
            className="
              w-full px-4 py-2.5 rounded-xl text-sm
              bg-white/50 backdrop-blur-sm
              border border-white/30
              text-text placeholder:text-text-muted
              focus:outline-none focus:ring-2 focus:ring-primary/30 focus:border-primary/50
              transition-all duration-200 resize-none
            "
          />
        </div>
      </div>
    </GlassModal>
  );
}

/** Подтверждение удаления */
function DeleteConfirmModal({
  open,
  onClose,
  onConfirm,
  templateName,
}: {
  open: boolean;
  onClose: () => void;
  onConfirm: () => void;
  templateName: string;
}) {
  return (
    <GlassModal
      open={open}
      onClose={onClose}
      title="Удалить шаблон?"
      footer={
        <>
          <GlassButton variant="secondary" size="sm" onClick={onClose}>
            Отмена
          </GlassButton>
          <GlassButton
            size="sm"
            onClick={onConfirm}
            className="!bg-error/20 !text-error hover:!bg-error/30"
          >
            Удалить
          </GlassButton>
        </>
      }
    >
      <p className="text-sm text-text-secondary">
        Шаблон <strong className="text-text">«{templateName}»</strong> будет удалён.
        Это действие нельзя отменить.
      </p>
    </GlassModal>
  );
}

export function TemplatesPage() {
  const { templates, selectedTemplate, setSelectedTemplate, removeTemplate } = useArtifactsStore(
    useShallow((s) => ({
      templates: s.templates,
      selectedTemplate: s.selectedTemplate,
      setSelectedTemplate: s.setSelectedTemplate,
      removeTemplate: s.removeTemplate,
    })),
  );
  const { play } = useSound();

  const [createOpen, setCreateOpen] = useState(false);
  const [editTemplate, setEditTemplate] = useState<Template | null>(null);
  const [deleteTemplate, setDeleteTemplate] = useState<Template | null>(null);

  const presetTemplates = templates.filter((t) => t.isPreset);
  const customTemplates = templates.filter((t) => !t.isPreset);

  const handleSelect = (id: string) => {
    play('click');
    setSelectedTemplate(id);
  };

  const handleDelete = () => {
    if (!deleteTemplate) return;
    removeTemplate(deleteTemplate.id);
    play('click');
    setDeleteTemplate(null);
  };

  const renderCard = (template: Template, i: number) => (
    <motion.div
      key={template.id}
      initial={{ opacity: 0, y: 20 }}
      animate={{ opacity: 1, y: 0 }}
      exit={{ opacity: 0, scale: 0.95 }}
      transition={{ delay: i * 0.05 }}
      layout
    >
      <GlassCard
        hoverable
        padding="md"
        className={selectedTemplate === template.id ? 'ring-2 ring-primary/40' : ''}
        onClick={() => handleSelect(template.id)}
      >
        <div className="flex items-start justify-between mb-3">
          <div className="flex-1 min-w-0">
            <h3 className="font-semibold text-text">{template.name}</h3>
            <p className="text-xs text-text-secondary mt-0.5">{template.description}</p>
          </div>
          <div className="flex items-center gap-1.5 flex-shrink-0 ml-2">
            {template.isPreset && (
              <span className="text-[10px] px-2 py-0.5 rounded-md bg-primary/10 text-primary font-medium">
                Встроенный
              </span>
            )}
            {!template.isPreset && (
              <>
                <button
                  onClick={(e) => { e.stopPropagation(); setEditTemplate(template); }}
                  className="w-7 h-7 flex items-center justify-center rounded-lg hover:bg-white/40 text-text-muted hover:text-primary transition-colors"
                  title="Редактировать"
                >
                  <svg width="14" height="14" viewBox="0 0 14 14" fill="none">
                    <path d="M10 2L12 4L5 11H3V9L10 2Z" stroke="currentColor" strokeWidth="1.5" strokeLinejoin="round" />
                  </svg>
                </button>
                <button
                  onClick={(e) => { e.stopPropagation(); setDeleteTemplate(template); }}
                  className="w-7 h-7 flex items-center justify-center rounded-lg hover:bg-error/10 text-text-muted hover:text-error transition-colors"
                  title="Удалить"
                >
                  <svg width="14" height="14" viewBox="0 0 14 14" fill="none">
                    <path d="M2 4H12M5 4V2H9V4M5 6V11M9 6V11M3 4L4 12H10L11 4" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round" />
                  </svg>
                </button>
              </>
            )}
          </div>
        </div>

        {/* Типы артефактов */}
        <div className="flex flex-wrap gap-1.5">
          {template.artifactTypes.map((type) => (
            <span
              key={type}
              className="text-[11px] px-2 py-0.5 rounded-md bg-white/50 text-text-secondary"
            >
              {ARTIFACT_ICONS[type]} {ARTIFACT_LABELS[type]}
            </span>
          ))}
        </div>

        {/* Кастомный промпт */}
        {template.customPrompt && (
          <div className="mt-2 pt-2 border-t border-white/15">
            <p className="text-[10px] text-text-muted truncate">
              💬 {template.customPrompt}
            </p>
          </div>
        )}

        {/* Индикатор выбора */}
        {selectedTemplate === template.id && (
          <motion.div
            className="mt-3 pt-3 border-t border-white/20 flex items-center gap-2 text-xs text-primary font-medium"
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
          >
            <svg width="14" height="14" viewBox="0 0 14 14" fill="none">
              <circle cx="7" cy="7" r="6" stroke="currentColor" strokeWidth="1.5" />
              <path d="M4 7L6 9L10 5" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round" />
            </svg>
            Выбран для обработки
          </motion.div>
        )}
      </GlassCard>
    </motion.div>
  );

  return (
    <AnimatedPage>
      <div className="max-w-4xl mx-auto">
        {/* Шапка */}
        <div className="flex items-center justify-between mb-6">
          <div>
            <h1 className="text-2xl font-bold text-text">Шаблоны</h1>
            <p className="text-sm text-text-secondary mt-1">
              Предустановленные и пользовательские профили артефактов
            </p>
          </div>
          <GlassButton
            onClick={() => {
              play('click');
              setCreateOpen(true);
            }}
          >
            <svg width="16" height="16" viewBox="0 0 16 16" fill="none" className="mr-1.5">
              <path d="M8 3V13M3 8H13" stroke="currentColor" strokeWidth="2" strokeLinecap="round" />
            </svg>
            Создать шаблон
          </GlassButton>
        </div>

        {/* Встроенные шаблоны */}
        <div className="mb-8">
          <h2 className="text-sm font-semibold text-text-muted uppercase tracking-wider mb-3">
            Встроенные шаблоны
          </h2>
          <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
            <AnimatePresence mode="popLayout">
              {presetTemplates.map((t, i) => renderCard(t, i))}
            </AnimatePresence>
          </div>
        </div>

        {/* Пользовательские шаблоны */}
        <div>
          <h2 className="text-sm font-semibold text-text-muted uppercase tracking-wider mb-3">
            Пользовательские шаблоны
          </h2>
          {customTemplates.length === 0 ? (
            <div className="glass rounded-2xl p-8 text-center">
              <p className="text-text-muted text-sm">
                Нет пользовательских шаблонов. Нажмите «Создать шаблон» чтобы добавить.
              </p>
            </div>
          ) : (
            <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
              <AnimatePresence mode="popLayout">
                {customTemplates.map((t, i) => renderCard(t, i))}
              </AnimatePresence>
            </div>
          )}
        </div>
      </div>

      {/* Модалка создания */}
      {createOpen && (
        <TemplateModal
          open={createOpen}
          onClose={() => setCreateOpen(false)}
        />
      )}

      {/* Модалка редактирования */}
      {editTemplate && (
        <TemplateModal
          open={!!editTemplate}
          onClose={() => setEditTemplate(null)}
          editTemplate={editTemplate}
        />
      )}

      {/* Подтверждение удаления */}
      {deleteTemplate && (
        <DeleteConfirmModal
          open={!!deleteTemplate}
          onClose={() => setDeleteTemplate(null)}
          onConfirm={handleDelete}
          templateName={deleteTemplate.name}
        />
      )}
    </AnimatedPage>
  );
}
