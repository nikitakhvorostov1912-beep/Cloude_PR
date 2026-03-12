import { useRef, useEffect, useState, useCallback } from 'react';
import { motion } from 'motion/react';
import { formatDuration } from '@/services/file.service';

interface WaveformPlayerProps {
  audioUrl: string;
  className?: string;
  height?: number;
  onTimeUpdate?: (time: number) => void;
}

export function WaveformPlayer({ audioUrl, className = '', height = 80, onTimeUpdate }: WaveformPlayerProps) {
  const canvasRef = useRef<HTMLCanvasElement>(null);
  const audioRef = useRef<HTMLAudioElement | null>(null);
  const animationRef = useRef<number>(0);
  const waveformDataRef = useRef<number[]>([]);

  const [isPlaying, setIsPlaying] = useState(false);
  const [currentTime, setCurrentTime] = useState(0);
  const [duration, setDuration] = useState(0);
  const [isLoading, setIsLoading] = useState(true);

  // Decode audio and extract waveform data
  useEffect(() => {
    const audio = new Audio();
    audio.preload = 'metadata';
    audioRef.current = audio;

    audio.addEventListener('loadedmetadata', () => {
      setDuration(audio.duration);
      setIsLoading(false);
    });

    audio.addEventListener('ended', () => {
      setIsPlaying(false);
    });

    audio.src = audioUrl;

    // Extract waveform from AudioContext
    fetch(audioUrl)
      .then((r) => r.arrayBuffer())
      .then((buffer) => {
        const ctx = new AudioContext();
        return ctx.decodeAudioData(buffer);
      })
      .then((audioBuffer) => {
        const rawData = audioBuffer.getChannelData(0);
        const samples = 200;
        const blockSize = Math.floor(rawData.length / samples);
        const peaks: number[] = [];

        for (let i = 0; i < samples; i++) {
          let sum = 0;
          for (let j = 0; j < blockSize; j++) {
            sum += Math.abs(rawData[i * blockSize + j]);
          }
          peaks.push(sum / blockSize);
        }

        // Normalize
        const max = Math.max(...peaks);
        waveformDataRef.current = peaks.map((p) => p / max);
        drawWaveform(0);
      })
      .catch(() => {
        // Generate placeholder waveform
        waveformDataRef.current = Array.from({ length: 200 }, () =>
          0.2 + Math.random() * 0.6
        );
        drawWaveform(0);
      });

    return () => {
      audio.pause();
      audio.src = '';
      cancelAnimationFrame(animationRef.current);
    };
  }, [audioUrl]);

  const drawWaveform = useCallback((progress: number) => {
    const canvas = canvasRef.current;
    if (!canvas) return;

    const ctx = canvas.getContext('2d');
    if (!ctx) return;

    const dpr = window.devicePixelRatio || 1;
    const rect = canvas.getBoundingClientRect();
    canvas.width = rect.width * dpr;
    canvas.height = rect.height * dpr;
    ctx.scale(dpr, dpr);

    const w = rect.width;
    const h = rect.height;
    const data = waveformDataRef.current;
    const barWidth = w / data.length;
    const gap = 1;

    ctx.clearRect(0, 0, w, h);

    data.forEach((value, i) => {
      const x = i * barWidth;
      const barH = value * h * 0.85;
      const y = (h - barH) / 2;
      const progressFraction = i / data.length;

      if (progressFraction <= progress) {
        ctx.fillStyle = '#6C5CE7';
      } else {
        ctx.fillStyle = 'rgba(108, 92, 231, 0.2)';
      }

      ctx.beginPath();
      ctx.roundRect(x + gap / 2, y, barWidth - gap, barH, 1);
      ctx.fill();
    });
  }, []);

  // Animation loop for playback
  useEffect(() => {
    if (!isPlaying) return;

    const tick = () => {
      const audio = audioRef.current;
      if (!audio) return;

      setCurrentTime(audio.currentTime);
      onTimeUpdate?.(audio.currentTime);
      drawWaveform(audio.currentTime / audio.duration);
      animationRef.current = requestAnimationFrame(tick);
    };

    animationRef.current = requestAnimationFrame(tick);
    return () => cancelAnimationFrame(animationRef.current);
  }, [isPlaying, drawWaveform, onTimeUpdate]);

  const togglePlay = () => {
    const audio = audioRef.current;
    if (!audio) return;

    if (isPlaying) {
      audio.pause();
    } else {
      audio.play();
    }
    setIsPlaying(!isPlaying);
  };

  const handleCanvasClick = (e: React.MouseEvent<HTMLCanvasElement>) => {
    const canvas = canvasRef.current;
    const audio = audioRef.current;
    if (!canvas || !audio) return;

    const rect = canvas.getBoundingClientRect();
    const fraction = (e.clientX - rect.left) / rect.width;
    audio.currentTime = fraction * audio.duration;
    setCurrentTime(audio.currentTime);
    drawWaveform(fraction);
  };

  return (
    <div className={`glass-subtle rounded-xl p-4 ${className}`}>
      <div className="flex items-center gap-3">
        {/* Play/Pause button */}
        <motion.button
          className="w-10 h-10 rounded-xl bg-primary/10 flex items-center justify-center flex-shrink-0 hover:bg-primary/20 transition-colors"
          whileHover={{ scale: 1.05 }}
          whileTap={{ scale: 0.95 }}
          onClick={togglePlay}
          disabled={isLoading}
        >
          {isLoading ? (
            <motion.div
              className="w-4 h-4 border-2 border-primary/30 border-t-primary rounded-full"
              animate={{ rotate: 360 }}
              transition={{ duration: 0.8, repeat: Infinity, ease: 'linear' }}
            />
          ) : isPlaying ? (
            <svg width="16" height="16" viewBox="0 0 16 16" fill="none" className="text-primary">
              <rect x="3" y="2" width="4" height="12" rx="1" fill="currentColor" />
              <rect x="9" y="2" width="4" height="12" rx="1" fill="currentColor" />
            </svg>
          ) : (
            <svg width="16" height="16" viewBox="0 0 16 16" fill="none" className="text-primary">
              <path d="M4 2L14 8L4 14V2Z" fill="currentColor" />
            </svg>
          )}
        </motion.button>

        {/* Waveform */}
        <div className="flex-1">
          <canvas
            ref={canvasRef}
            className="w-full cursor-pointer"
            style={{ height: `${height}px` }}
            onClick={handleCanvasClick}
          />
        </div>
      </div>

      {/* Time */}
      <div className="flex justify-between mt-2">
        <span className="text-xs font-mono text-text-secondary">
          {formatDuration(Math.round(currentTime))}
        </span>
        <span className="text-xs font-mono text-text-muted">
          {formatDuration(Math.round(duration))}
        </span>
      </div>
    </div>
  );
}
