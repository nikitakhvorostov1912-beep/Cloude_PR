import { useState, useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import { GlassButton, GlassInput, GlassModal } from '@/components/glass';
import { FileCard } from '@/components/upload/FileCard';
import { useProjectsStore } from '@/stores/projects.store';
import { useShallow } from 'zustand/react/shallow';
import { useSound } from '@/hooks/useSound';
import type { FileInfo } from '@/services/file.service';

interface NewProjectModalProps {
  open: boolean;
  onClose: () => void;
  /** Один файл (обратная совместимость) */
  initialFile?: FileInfo | null;
  /** Несколько файлов (multi-file режим) */
  initialFiles?: FileInfo[];
}

export function NewProjectModal({ open, onClose, initialFile, initialFiles }: NewProjectModalProps) {
  const { addProject, addMeeting } = useProjectsStore(
    useShallow((s) => ({ addProject: s.addProject, addMeeting: s.addMeeting }))
  );
  const navigate = useNavigate();
  const { play } = useSound();

  const allInitialFiles = initialFiles?.length ? initialFiles : initialFile ? [initialFile] : [];

  const [projectName, setProjectName] = useState(
    allInitialFiles.length > 0 ? allInitialFiles[0].name.replace(/\.[^.]+$/, '') : ''
  );
  const [projectDesc, setProjectDesc] = useState('');
  const [uploadedFiles, setUploadedFiles] = useState<FileInfo[]>(allInitialFiles);

  const handleCreate = () => {
    if (!projectName.trim()) return;

    play('success');
    const id = crypto.randomUUID();
    const now = new Date().toISOString();
    addProject({
      id,
      name: projectName.trim(),
      description: projectDesc.trim(),
      folder: '',
      meetingIds: [],
      createdAt: now,
      updatedAt: now,
    });

    for (const file of uploadedFiles) {
      addMeeting({
        id: crypto.randomUUID(),
        projectId: id,
        title: file.name.replace(/\.[^.]+$/, ''),
        filePath: file.objectUrl,
        audioPath: file.objectUrl,
        durationSeconds: file.durationSeconds,
        fileSizeBytes: file.sizeBytes,
        qualityScore: 0,
        status: 'uploaded',
        errorMessage: null,
        createdAt: now,
        processedAt: null,
      });
    }

    handleClose();
    navigate(`/projects/${id}`);
  };

  const handleClose = () => {
    setProjectName('');
    setProjectDesc('');
    setUploadedFiles([]);
    onClose();
  };

  const removeFile = (index: number) => {
    setUploadedFiles((prev) => prev.filter((_, i) => i !== index));
  };

  // Синхронизируем файлы при открытии
  useEffect(() => {
    if (!open) return;
    const files = initialFiles?.length ? initialFiles : initialFile ? [initialFile] : [];
    if (files.length > 0) {
      setUploadedFiles((prev) => prev.length > 0 ? prev : files);
      setProjectName((prev) => prev || files[0].name.replace(/\.[^.]+$/, ''));
    }
  }, [open, initialFile, initialFiles]);

  return (
    <GlassModal
      open={open}
      onClose={handleClose}
      title="Новый проект"
      footer={
        <>
          <GlassButton variant="ghost" onClick={handleClose}>
            Отмена
          </GlassButton>
          <GlassButton
            disabled={!projectName.trim()}
            onClick={handleCreate}
          >
            Создать
          </GlassButton>
        </>
      }
    >
      <div className="flex flex-col gap-4">
        <GlassInput
          label="Название проекта"
          placeholder="Например: Обследование бухгалтерии"
          value={projectName}
          onChange={(e) => setProjectName(e.target.value)}
        />
        <GlassInput
          label="Описание (необязательно)"
          placeholder="Краткое описание проекта"
          value={projectDesc}
          onChange={(e) => setProjectDesc(e.target.value)}
        />
        {uploadedFiles.length > 0 && (
          <div>
            <p className="text-xs font-medium text-text-secondary mb-2">
              {uploadedFiles.length === 1 ? 'Загруженный файл' : `Загружено файлов: ${uploadedFiles.length}`}
            </p>
            <div className="flex flex-col gap-1.5">
              {uploadedFiles.map((file, i) => (
                <FileCard key={file.name + i} file={file} onRemove={() => removeFile(i)} />
              ))}
            </div>
          </div>
        )}
      </div>
    </GlassModal>
  );
}
