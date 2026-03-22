const SUPPORTED_AUDIO = ['mp3', 'wav', 'ogg', 'flac', 'aac', 'm4a', 'wma', 'opus'];
const SUPPORTED_VIDEO = ['mp4', 'mkv', 'avi', 'mov', 'webm', 'wmv', 'flv', 'm4v'];
const SUPPORTED_EXTENSIONS = [...SUPPORTED_AUDIO, ...SUPPORTED_VIDEO];

export type FileType = 'audio' | 'video' | 'unknown';

export interface FileInfo {
  name: string;
  extension: string;
  type: FileType;
  sizeBytes: number;
  sizeFormatted: string;
  durationSeconds: number;
  objectUrl: string;
  file: File;
  /** Нативный путь на диске (Tauri drag-drop / dialog). Для больших файлов — обязателен. */
  nativePath?: string;
}

function getExtension(filename: string): string {
  return filename.split('.').pop()?.toLowerCase() ?? '';
}

function getFileType(ext: string): FileType {
  if (SUPPORTED_AUDIO.includes(ext)) return 'audio';
  if (SUPPORTED_VIDEO.includes(ext)) return 'video';
  return 'unknown';
}

function formatSize(bytes: number): string {
  if (bytes < 1024) return `${bytes} Б`;
  if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(1)} КБ`;
  if (bytes < 1024 * 1024 * 1024) return `${(bytes / (1024 * 1024)).toFixed(1)} МБ`;
  return `${(bytes / (1024 * 1024 * 1024)).toFixed(2)} ГБ`;
}

export function isSupported(filename: string): boolean {
  return SUPPORTED_EXTENSIONS.includes(getExtension(filename));
}

export function getAudioDuration(file: File): Promise<number> {
  const TIMEOUT_MS = 5000;

  return new Promise((resolve) => {
    const url = URL.createObjectURL(file);

    // Определяем тип по расширению (file.type может быть пустым в WebView2)
    const ext = getExtension(file.name);
    const isVideo = SUPPORTED_VIDEO.includes(ext) || file.type.startsWith('video/');
    const media = isVideo
      ? document.createElement('video')
      : document.createElement('audio');

    let settled = false;
    const finish = (duration: number) => {
      if (settled) return;
      settled = true;
      clearTimeout(timer);
      URL.revokeObjectURL(url);
      media.removeAttribute('src');
      media.load();
      resolve(duration);
    };

    // Таймаут — в WebView2 метаданные могут не загрузиться
    const timer = setTimeout(() => finish(0), TIMEOUT_MS);

    media.preload = 'metadata';
    media.onloadedmetadata = () => {
      const d = Number.isFinite(media.duration) ? Math.round(media.duration) : 0;
      finish(d);
    };
    media.onerror = () => finish(0); // Не ломаем flow — длительность определится через Whisper
    media.src = url;
  });
}

export async function processFile(file: File): Promise<FileInfo> {
  const ext = getExtension(file.name);

  if (!SUPPORTED_EXTENSIONS.includes(ext)) {
    throw new Error(`Формат .${ext} не поддерживается. Используйте: ${SUPPORTED_EXTENSIONS.join(', ')}`);
  }

  const duration = await getAudioDuration(file);
  const objectUrl = URL.createObjectURL(file);

  return {
    name: file.name,
    extension: ext,
    type: getFileType(ext),
    sizeBytes: file.size,
    sizeFormatted: formatSize(file.size),
    durationSeconds: duration,
    objectUrl,
    file,
  };
}

/**
 * Создаёт FileInfo из нативного пути (Tauri drag-drop / dialog).
 * Не загружает файл в память — только метаданные.
 */
export function fileInfoFromPath(path: string): FileInfo {
  const name = path.replace(/\\/g, '/').split('/').pop() ?? 'unknown';
  const ext = getExtension(name);
  return {
    name,
    extension: ext,
    type: getFileType(ext),
    sizeBytes: 0, // Размер неизвестен без чтения — не критично
    sizeFormatted: '—',
    durationSeconds: 0,
    objectUrl: '',
    file: new File([], name), // Пустой placeholder — не используется для path-based
    nativePath: path,
  };
}

export function formatDuration(seconds: number): string {
  const h = Math.floor(seconds / 3600);
  const m = Math.floor((seconds % 3600) / 60);
  const s = Math.floor(seconds % 60);

  if (h > 0) return `${h}:${m.toString().padStart(2, '0')}:${s.toString().padStart(2, '0')}`;
  return `${m}:${s.toString().padStart(2, '0')}`;
}

export function revokeFileUrl(url: string): void {
  if (url.startsWith('blob:')) {
    URL.revokeObjectURL(url);
  }
}
