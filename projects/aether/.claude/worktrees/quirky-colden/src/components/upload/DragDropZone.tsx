import { useState, useCallback, useRef } from 'react';
import { motion, AnimatePresence } from 'motion/react';
import { isSupported, processFile } from '@/services/file.service';
import type { FileInfo } from '@/services/file.service';
import { useSound } from '@/hooks/useSound';

interface DragDropZoneProps {
  onFileProcessed: (file: FileInfo) => void;
  onError?: (message: string) => void;
  compact?: boolean;
}

export function DragDropZone({ onFileProcessed, onError, compact = false }: DragDropZoneProps) {
  const [isDragOver, setIsDragOver] = useState(false);
  const [isProcessing, setIsProcessing] = useState(false);
  const inputRef = useRef<HTMLInputElement>(null);
  const { play } = useSound();

  const handleFiles = useCallback(async (files: FileList | File[]) => {
    const fileArray = Array.from(files);
    const validFile = fileArray.find((f) => isSupported(f.name));

    if (!validFile) {
      play('error');
      onError?.('Неподдерживаемый формат. Используйте аудио или видео файлы.');
      return;
    }

    setIsProcessing(true);
    play('upload');

    try {
      const info = await processFile(validFile);
      onFileProcessed(info);
      play('success');
    } catch (err) {
      play('error');
      onError?.(err instanceof Error ? err.message : 'Ошибка обработки файла');
    } finally {
      setIsProcessing(false);
    }
  }, [onFileProcessed, onError, play]);

  const handleDragOver = useCallback((e: React.DragEvent) => {
    e.preventDefault();
    e.stopPropagation();
    setIsDragOver(true);
  }, []);

  const handleDragLeave = useCallback((e: React.DragEvent) => {
    e.preventDefault();
    e.stopPropagation();
    setIsDragOver(false);
  }, []);

  const handleDrop = useCallback((e: React.DragEvent) => {
    e.preventDefault();
    e.stopPropagation();
    setIsDragOver(false);
    handleFiles(e.dataTransfer.files);
  }, [handleFiles]);

  const handleClick = () => {
    play('click');
    inputRef.current?.click();
  };

  const handleInputChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    if (e.target.files?.length) {
      handleFiles(e.target.files);
    }
  };

  return (
    <>
      <input
        ref={inputRef}
        type="file"
        accept="audio/*,video/*,.mp3,.wav,.ogg,.flac,.aac,.m4a,.mp4,.mkv,.avi,.mov,.webm"
        className="hidden"
        onChange={handleInputChange}
      />

      <motion.div
        className={`
          rounded-2xl border-2 border-dashed flex flex-col items-center justify-center text-center
          transition-colors duration-300 cursor-pointer
          ${compact ? 'p-6' : 'p-12'}
          ${isDragOver
            ? 'border-primary bg-primary/5 shadow-[0_0_40px_rgba(108,92,231,0.15)]'
            : 'border-primary/20 hover:border-primary/40 hover:bg-white/20'
          }
        `}
        onDragOver={handleDragOver}
        onDragLeave={handleDragLeave}
        onDrop={handleDrop}
        onClick={handleClick}
        animate={isDragOver ? { scale: 1.01 } : { scale: 1 }}
      >
        <AnimatePresence mode="wait">
          {isProcessing ? (
            <motion.div
              key="processing"
              initial={{ opacity: 0, scale: 0.9 }}
              animate={{ opacity: 1, scale: 1 }}
              exit={{ opacity: 0, scale: 0.9 }}
              className="flex flex-col items-center gap-3"
            >
              <motion.div
                className="w-12 h-12 border-3 border-primary/20 border-t-primary rounded-full"
                animate={{ rotate: 360 }}
                transition={{ duration: 1, repeat: Infinity, ease: 'linear' }}
              />
              <p className="text-sm font-medium text-primary">Обработка файла...</p>
            </motion.div>
          ) : (
            <motion.div
              key="idle"
              initial={{ opacity: 0 }}
              animate={{ opacity: 1 }}
              exit={{ opacity: 0 }}
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
                  {isDragOver ? 'Отпустите файл' : 'Перетащите аудио или видео файл'}
                </p>
                {!compact && (
                  <p className="text-xs text-text-muted">
                    MP3, WAV, MP4, MKV и другие форматы ffmpeg
                  </p>
                )}
              </div>
            </motion.div>
          )}
        </AnimatePresence>
      </motion.div>
    </>
  );
}
