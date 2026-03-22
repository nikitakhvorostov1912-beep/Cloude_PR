import { useState, useCallback, useEffect, useRef } from 'react';
import { motion, AnimatePresence } from 'motion/react';
import { isSupported, fileInfoFromPath } from '@/services/file.service';
import type { FileInfo } from '@/services/file.service';
import { useSound } from '@/hooks/useSound';

interface DragDropZoneProps {
  /** Обработчик одного файла (обратная совместимость) */
  onFileProcessed?: (file: FileInfo) => void;
  /** Обработчик нескольких файлов (multi-file режим) */
  onFilesProcessed?: (files: FileInfo[]) => void;
  onError?: (message: string) => void;
  compact?: boolean;
}

function formatFileSize(bytes: number): string {
  if (bytes === 0) return '—';
  if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(0)} КБ`;
  return `${(bytes / (1024 * 1024)).toFixed(1)} МБ`;
}

export function DragDropZone({ onFileProcessed, onFilesProcessed, onError, compact = false }: DragDropZoneProps) {
  const [isDragOver, setIsDragOver] = useState(false);
  /** Очередь файлов для multi-file режима */
  const [fileQueue, setFileQueue] = useState<FileInfo[]>([]);
  const { play } = useSound();

  const isMultiFile = !!onFilesProcessed;
  const fileInputRef = useRef<HTMLInputElement>(null);

  /**
   * Обработка нативных путей файлов (Tauri drag-drop или dialog).
   * НЕ загружает файлы в память — передаёт путь напрямую в Rust/ffmpeg.
   */
  const handleNativePaths = useCallback((paths: string[]) => {
    const validPaths = paths.filter((p) => {
      const name = p.replace(/\\/g, '/').split('/').pop() ?? '';
      return isSupported(name);
    });

    if (validPaths.length === 0) {
      play('error');
      onError?.('Неподдерживаемый формат. Используйте аудио или видео файлы.');
      return;
    }

    play('upload');

    const fileInfos = validPaths.map((p) => fileInfoFromPath(p));

    if (isMultiFile) {
      setFileQueue((prev) => {
        const next = [...prev, ...fileInfos];
        onFilesProcessed?.(next);
        return next;
      });
    } else {
      onFileProcessed?.(fileInfos[0]);
    }

    play('success');
  }, [onFileProcessed, onFilesProcessed, isMultiFile, onError, play]);

  /**
   * Обработка File объектов из HTML5 drag-drop или input.
   * Для dev-режима без Tauri.
   */
  const handleWebFiles = useCallback((files: FileList) => {
    const validFiles = Array.from(files).filter((f) => isSupported(f.name));
    if (validFiles.length === 0) {
      play('error');
      onError?.('Неподдерживаемый формат. Используйте аудио или видео файлы.');
      return;
    }
    play('upload');
    const fileInfos: FileInfo[] = validFiles.map((f) => {
      const ext = f.name.split('.').pop()?.toLowerCase() ?? '';
      return {
        file: f,
        name: f.name,
        extension: ext,
        sizeBytes: f.size,
        sizeFormatted: formatFileSize(f.size),
        type: f.type.startsWith('video/') ? 'video' as const : 'audio' as const,
        durationSeconds: 0,
        objectUrl: URL.createObjectURL(f),
      };
    });
    if (isMultiFile) {
      setFileQueue((prev) => {
        const next = [...prev, ...fileInfos];
        onFilesProcessed?.(next);
        return next;
      });
    } else {
      onFileProcessed?.(fileInfos[0]);
    }
    play('success');
  }, [onFileProcessed, onFilesProcessed, isMultiFile, onError, play]);

  /**
   * Подписка на нативные события drag-drop от Tauri.
   * Даёт нам реальные пути файлов на диске (без загрузки в память).
   * В dev-режиме (без Tauri) — HTML5 drag-drop обработается через onDrop.
   */
  const [isTauriEnv, setIsTauriEnv] = useState(false);

  useEffect(() => {
    let unlisten: (() => void) | undefined;

    (async () => {
      try {
        const { getCurrentWebview } = await import('@tauri-apps/api/webview');
        const webview = getCurrentWebview();
        setIsTauriEnv(true);
        unlisten = await webview.onDragDropEvent((event) => {
          if (event.payload.type === 'over') {
            setIsDragOver(true);
          } else if (event.payload.type === 'leave') {
            setIsDragOver(false);
          } else if (event.payload.type === 'drop') {
            setIsDragOver(false);
            handleNativePaths(event.payload.paths);
          }
        });
      } catch {
        // Не Tauri окружение — drag-drop через HTML5
        setIsTauriEnv(false);
      }
    })();

    return () => { unlisten?.(); };
  }, [handleNativePaths]);

  /**
   * Открытие файлового диалога: Tauri plugin-dialog или HTML5 <input>.
   */
  const handleClick = useCallback(async () => {
    play('click');

    if (isTauriEnv) {
      try {
        const { open } = await import('@tauri-apps/plugin-dialog');
        const result = await open({
          multiple: isMultiFile,
          filters: [{
            name: 'Аудио и видео',
            extensions: ['mp3', 'wav', 'ogg', 'flac', 'aac', 'm4a', 'mp4', 'mkv', 'avi', 'mov', 'webm', 'wmv', 'flv', 'm4v'],
          }],
        });
        if (!result) return;
        const paths = Array.isArray(result) ? result : [result];
        handleNativePaths(paths);
      } catch (err) {
        console.warn('[DragDrop] File dialog error:', err);
        onError?.(`Файловый диалог: ${err instanceof Error ? err.message : 'недоступен'}`);
      }
    } else {
      fileInputRef.current?.click();
    }
  }, [isTauriEnv, isMultiFile, handleNativePaths, play, onError]);

  const removeFile = useCallback((index: number) => {
    setFileQueue((prev) => {
      const next = prev.filter((_, i) => i !== index);
      onFilesProcessed?.(next);
      return next;
    });
  }, [onFilesProcessed]);

  const moveFile = useCallback((index: number, direction: -1 | 1) => {
    setFileQueue((prev) => {
      const newIndex = index + direction;
      if (newIndex < 0 || newIndex >= prev.length) return prev;
      const next = [...prev];
      [next[index], next[newIndex]] = [next[newIndex], next[index]];
      onFilesProcessed?.(next);
      return next;
    });
  }, [onFilesProcessed]);

  /** HTML5 drag-drop обработчики (только для не-Tauri окружения) */
  const handleDragOver = useCallback((e: React.DragEvent) => {
    if (isTauriEnv) return;
    e.preventDefault();
    e.stopPropagation();
    setIsDragOver(true);
  }, [isTauriEnv]);

  const handleDragLeave = useCallback((e: React.DragEvent) => {
    if (isTauriEnv) return;
    e.preventDefault();
    e.stopPropagation();
    setIsDragOver(false);
  }, [isTauriEnv]);

  const handleDrop = useCallback((e: React.DragEvent) => {
    if (isTauriEnv) return;
    e.preventDefault();
    e.stopPropagation();
    setIsDragOver(false);
    if (e.dataTransfer.files.length > 0) {
      handleWebFiles(e.dataTransfer.files);
    }
  }, [isTauriEnv, handleWebFiles]);

  const handleInputChange = useCallback((e: React.ChangeEvent<HTMLInputElement>) => {
    if (e.target.files && e.target.files.length > 0) {
      handleWebFiles(e.target.files);
    }
    e.target.value = '';
  }, [handleWebFiles]);

  return (
    <div className="space-y-3">
      {/* Скрытый input для web-режима */}
      <input
        ref={fileInputRef}
        type="file"
        accept="audio/*,video/*"
        multiple={isMultiFile}
        onChange={handleInputChange}
        className="hidden"
      />

      <motion.div
        className={`
          rounded-2xl border-2 border-dashed flex flex-col items-center justify-center text-center
          cursor-pointer
          ${compact ? 'p-6' : 'p-12'}
        `}
        style={{
          background: isDragOver ? 'var(--accent-dim)' : 'var(--bg-card)',
          backdropFilter: 'var(--blur-section)',
          WebkitBackdropFilter: 'var(--blur-section)',
          borderColor: isDragOver ? 'var(--accent)' : 'rgba(91,79,212,0.35)',
          boxShadow: isDragOver ? 'var(--shadow-md)' : 'var(--shadow-section)',
          transition: 'all 200ms ease',
        }}
        onClick={handleClick}
        onDragOver={handleDragOver}
        onDragLeave={handleDragLeave}
        onDrop={handleDrop}
        animate={isDragOver ? { scale: 1.01 } : { scale: 1 }}
      >
        <motion.div
          key="idle"
          initial={{ opacity: 0 }}
          animate={{ opacity: 1 }}
          className="flex flex-col items-center gap-3"
        >
          <motion.div
            className={`rounded-2xl bg-primary/10 flex items-center justify-center ${compact ? 'w-10 h-10' : 'w-14 h-14'}`}
            animate={isDragOver ? { scale: 1.1, y: -4 } : { scale: 1, y: 0 }}
          >
            <svg width="28" height="28" viewBox="0 0 28 28" fill="none" className="text-primary">
              <path d="M14 4V18M8 10L14 4L20 10" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" />
              <path d="M4 20V22C4 23.1 4.9 24 6 24H22C23.1 24 24 23.1 24 22V20" stroke="currentColor" strokeWidth="2" strokeLinecap="round" />
            </svg>
          </motion.div>
          <div>
            <p className={`font-medium text-text ${compact ? 'text-sm' : 'text-sm mb-1'}`}>
              {isDragOver
                ? 'Отпустите файлы'
                : isMultiFile
                  ? fileQueue.length > 0
                    ? 'Добавить ещё файлы'
                    : 'Перетащите аудио или видео файлы'
                  : 'Перетащите аудио или видео файл'
              }
            </p>
            {!compact && (
              <p className="text-xs text-text-muted">
                MP3, WAV, MP4, MKV и другие форматы ffmpeg
                {isMultiFile && ' · Несколько файлов'}
              </p>
            )}
          </div>
        </motion.div>
      </motion.div>

      {/* Список загруженных файлов (multi-file) */}
      {isMultiFile && fileQueue.length > 0 && (
        <div className="glass-subtle rounded-xl p-3 space-y-2">
          <div className="flex items-center justify-between text-xs text-text-muted px-1">
            <span>{fileQueue.length} {fileQueue.length === 1 ? 'файл' : fileQueue.length < 5 ? 'файла' : 'файлов'}</span>
            {fileQueue.length > 1 && <span className="text-[10px]">Порядок = хронология встреч</span>}
          </div>
          <AnimatePresence>
            {fileQueue.map((file, index) => (
              <motion.div
                key={(file.nativePath ?? file.name) + index}
                initial={{ opacity: 0, y: -8 }}
                animate={{ opacity: 1, y: 0 }}
                exit={{ opacity: 0, height: 0 }}
                className="flex items-center gap-2 glass-subtle rounded-lg px-3 py-2"
              >
                <span className="text-xs font-mono font-bold text-text-muted w-5 text-center flex-shrink-0">
                  {index + 1}
                </span>
                <span className="text-xs text-primary/60 flex-shrink-0">
                  {file.type === 'video' ? '🎥' : '🎵'}
                </span>
                <span className="text-sm text-text truncate min-w-0 flex-1">{file.name}</span>
                <span className="text-[10px] text-text-muted flex-shrink-0">
                  {formatFileSize(file.sizeBytes)}
                </span>
                {/* Кнопки порядка */}
                {fileQueue.length > 1 && (
                  <div className="flex gap-0.5 flex-shrink-0">
                    <button
                      onClick={(e) => { e.stopPropagation(); moveFile(index, -1); }}
                      disabled={index === 0}
                      className="w-5 h-5 rounded text-[10px] text-text-muted hover:bg-primary/10 hover:text-primary disabled:opacity-20 disabled:cursor-default"
                    >
                      ▲
                    </button>
                    <button
                      onClick={(e) => { e.stopPropagation(); moveFile(index, 1); }}
                      disabled={index === fileQueue.length - 1}
                      className="w-5 h-5 rounded text-[10px] text-text-muted hover:bg-primary/10 hover:text-primary disabled:opacity-20 disabled:cursor-default"
                    >
                      ▼
                    </button>
                  </div>
                )}
                {/* Удалить */}
                <button
                  onClick={(e) => { e.stopPropagation(); removeFile(index); }}
                  className="w-5 h-5 rounded text-text-muted hover:bg-error/10 hover:text-error text-xs flex-shrink-0"
                >
                  ×
                </button>
              </motion.div>
            ))}
          </AnimatePresence>
        </div>
      )}
    </div>
  );
}
