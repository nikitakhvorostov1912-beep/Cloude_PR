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
  return new Promise((resolve, reject) => {
    const url = URL.createObjectURL(file);
    const media = file.type.startsWith('video/')
      ? document.createElement('video')
      : document.createElement('audio');

    media.preload = 'metadata';
    media.onloadedmetadata = () => {
      URL.revokeObjectURL(url);
      resolve(Math.round(media.duration));
    };
    media.onerror = () => {
      URL.revokeObjectURL(url);
      reject(new Error('Не удалось прочитать метаданные файла'));
    };
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

export function formatDuration(seconds: number): string {
  const h = Math.floor(seconds / 3600);
  const m = Math.floor((seconds % 3600) / 60);
  const s = seconds % 60;

  if (h > 0) return `${h}:${m.toString().padStart(2, '0')}:${s.toString().padStart(2, '0')}`;
  return `${m}:${s.toString().padStart(2, '0')}`;
}

export function revokeFileUrl(url: string): void {
  if (url.startsWith('blob:')) {
    URL.revokeObjectURL(url);
  }
}
