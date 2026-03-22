import { describe, it, expect, vi, beforeEach } from 'vitest';
import {
  isSupported,
  formatDuration,
  revokeFileUrl,
  processFile,
} from '@/services/file.service';

describe('isSupported', () => {
  it('supports mp3', () => expect(isSupported('meeting.mp3')).toBe(true));
  it('supports wav', () => expect(isSupported('audio.wav')).toBe(true));
  it('supports ogg', () => expect(isSupported('sound.ogg')).toBe(true));
  it('supports flac', () => expect(isSupported('track.flac')).toBe(true));
  it('supports aac', () => expect(isSupported('audio.aac')).toBe(true));
  it('supports m4a', () => expect(isSupported('podcast.m4a')).toBe(true));
  it('supports opus', () => expect(isSupported('voice.opus')).toBe(true));
  it('supports mp4 video', () => expect(isSupported('meeting.mp4')).toBe(true));
  it('supports mkv', () => expect(isSupported('video.mkv')).toBe(true));
  it('supports mov', () => expect(isSupported('screen.mov')).toBe(true));
  it('supports webm', () => expect(isSupported('recording.webm')).toBe(true));
  it('rejects txt', () => expect(isSupported('document.txt')).toBe(false));
  it('rejects pdf', () => expect(isSupported('report.pdf')).toBe(false));
  it('rejects exe', () => expect(isSupported('app.exe')).toBe(false));
  it('rejects files with no extension', () => expect(isSupported('noextension')).toBe(false));
  it('is case-insensitive', () => expect(isSupported('MEETING.MP3')).toBe(true));
});

describe('formatDuration', () => {
  it('formats seconds only (< 1 minute)', () => {
    expect(formatDuration(45)).toBe('0:45');
  });

  it('formats exactly 1 minute', () => {
    expect(formatDuration(60)).toBe('1:00');
  });

  it('formats minutes and seconds', () => {
    expect(formatDuration(125)).toBe('2:05');
  });

  it('formats exactly 1 hour', () => {
    expect(formatDuration(3600)).toBe('1:00:00');
  });

  it('formats hours, minutes, seconds', () => {
    expect(formatDuration(3661)).toBe('1:01:01');
  });

  it('formats 90 minutes', () => {
    expect(formatDuration(5400)).toBe('1:30:00');
  });

  it('formats 0 seconds', () => {
    expect(formatDuration(0)).toBe('0:00');
  });

  it('pads single digit seconds', () => {
    expect(formatDuration(5)).toBe('0:05');
  });
});

describe('revokeFileUrl', () => {
  it('revokes blob URLs', () => {
    revokeFileUrl('blob:http://localhost/abc-123');
    expect(URL.revokeObjectURL).toHaveBeenCalledWith('blob:http://localhost/abc-123');
  });

  it('does not revoke non-blob URLs', () => {
    revokeFileUrl('https://example.com/file.mp3');
    expect(URL.revokeObjectURL).not.toHaveBeenCalled();
  });

  it('does not throw for empty string', () => {
    expect(() => revokeFileUrl('')).not.toThrow();
  });
});

describe('processFile', () => {
  let mockFile: File;

  beforeEach(() => {
    // Mock getAudioDuration via HTMLMediaElement
    mockFile = new File(['audio-content'], 'meeting.mp3', { type: 'audio/mpeg' });

    // Mock audio element for duration extraction
    const mockAudio = {
      preload: '',
      src: '',
      duration: 3600,
      onloadedmetadata: null as (() => void) | null,
      onerror: null as (() => void) | null,
    };

    vi.spyOn(document, 'createElement').mockImplementation((tag: string) => {
      if (tag === 'audio' || tag === 'video') {
        return mockAudio as unknown as HTMLElement;
      }
      return document.createElement.call(document, tag);
    });

    // Trigger onloadedmetadata when src is set
    Object.defineProperty(mockAudio, 'src', {
      set(_: string) {
        setTimeout(() => mockAudio.onloadedmetadata?.(), 0);
      },
      get() { return ''; },
    });
  });

  it('throws for unsupported file formats', async () => {
    const badFile = new File([''], 'document.pdf', { type: 'application/pdf' });
    await expect(processFile(badFile)).rejects.toThrow('не поддерживается');
  });

  it('throws for txt files', async () => {
    const txtFile = new File([''], 'notes.txt', { type: 'text/plain' });
    await expect(processFile(txtFile)).rejects.toThrow();
  });
});
