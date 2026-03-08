/**
 * Audio Engine — Pre-recorded Neural Voices + Sound Design
 *
 * Voice files generated via Yandex SpeechKit / Edge TTS (neural):
 * - marina/friendly (female, AI-assistant Аврора)
 * - DmitryNeural (male, client Сергей)
 * Files: /pitch/audio/{op-1,cl-1,op-2,cl-2,op-3,cl-3}.mp3
 *
 * Sound effects via Web Audio API:
 * - Realistic phone ring, ambient hum, whoosh, chime, ding
 */

let audioContext: AudioContext | null = null;
let ambientNode: { stop: () => void } | null = null;
let currentVoiceAudio: HTMLAudioElement | null = null;

/**
 * Unlock audio system. MUST be called directly from a user gesture (click).
 * Creates AudioContext and resumes it within the gesture scope.
 */
export async function unlockAudio(): Promise<void> {
  if (!audioContext || audioContext.state === "closed") {
    audioContext = new AudioContext();
  }
  if (audioContext.state === "suspended") {
    await audioContext.resume();
  }
}

function getCtx(): AudioContext {
  if (!audioContext || audioContext.state === "closed") {
    audioContext = new AudioContext();
  }
  // resume() is non-blocking here — unlockAudio() should have been called first
  if (audioContext.state === "suspended") {
    audioContext.resume();
  }
  return audioContext;
}

// ── Phone Ring ──────────────────────────────────────────────
export function playRingSound(): Promise<void> {
  return new Promise((resolve) => {
    try {
      const ctx = getCtx();
      const now = ctx.currentTime;
      const master = ctx.createGain();
      master.gain.value = 0;
      master.connect(ctx.destination);

      // Dual-tone ring (425 Hz + 480 Hz — realistic Russian phone)
      const freqs = [425, 480];
      const oscs = freqs.map((f) => {
        const osc = ctx.createOscillator();
        osc.type = "sine";
        osc.frequency.value = f;
        osc.connect(master);
        return osc;
      });

      // Ring pattern: ring 0.8s, silence 0.4s, ring 0.8s, silence
      const pattern = [
        [0, 0.12, 0.8],    // start, gain, duration
        [0.8, 0, 0.4],
        [1.2, 0.12, 0.8],
        [2.0, 0, 0.3],
      ] as const;

      for (const [time, gain, dur] of pattern) {
        master.gain.setValueAtTime(gain, now + time);
        if (gain > 0) {
          master.gain.setValueAtTime(gain, now + time + dur - 0.05);
          master.gain.linearRampToValueAtTime(0, now + time + dur);
        }
      }

      const total = 2.3;
      oscs.forEach((o) => { o.start(now); o.stop(now + total); });
      setTimeout(() => resolve(), total * 1000);
    } catch {
      resolve();
    }
  });
}

// ── Ambient Call-Center Hum ─────────────────────────────────
export function startAmbient(): void {
  try {
    const ctx = getCtx();
    const now = ctx.currentTime;

    // Very low noise-like hum (filtered brown noise)
    const bufferSize = ctx.sampleRate * 2;
    const buffer = ctx.createBuffer(1, bufferSize, ctx.sampleRate);
    const data = buffer.getChannelData(0);
    let last = 0;
    for (let i = 0; i < bufferSize; i++) {
      const white = Math.random() * 2 - 1;
      last = (last + 0.02 * white) / 1.02;
      data[i] = last * 3.5;
    }

    const source = ctx.createBufferSource();
    source.buffer = buffer;
    source.loop = true;

    const filter = ctx.createBiquadFilter();
    filter.type = "lowpass";
    filter.frequency.value = 200;

    const gain = ctx.createGain();
    gain.gain.setValueAtTime(0, now);
    gain.gain.linearRampToValueAtTime(0.03, now + 1);

    source.connect(filter);
    filter.connect(gain);
    gain.connect(ctx.destination);
    source.start();

    ambientNode = {
      stop: () => {
        gain.gain.linearRampToValueAtTime(0, ctx.currentTime + 0.5);
        setTimeout(() => { try { source.stop(); } catch {} }, 600);
      },
    };
  } catch {
    // Ignore
  }
}

export function stopAmbient(): void {
  if (ambientNode) {
    ambientNode.stop();
    ambientNode = null;
  }
}

// ── UI Whoosh (AI activation) ───────────────────────────────
export function playWhoosh(): void {
  try {
    const ctx = getCtx();
    const now = ctx.currentTime;

    const osc = ctx.createOscillator();
    osc.type = "sine";
    osc.frequency.setValueAtTime(200, now);
    osc.frequency.exponentialRampToValueAtTime(800, now + 0.15);
    osc.frequency.exponentialRampToValueAtTime(400, now + 0.3);

    const gain = ctx.createGain();
    gain.gain.setValueAtTime(0, now);
    gain.gain.linearRampToValueAtTime(0.08, now + 0.05);
    gain.gain.exponentialRampToValueAtTime(0.001, now + 0.35);

    osc.connect(gain);
    gain.connect(ctx.destination);
    osc.start(now);
    osc.stop(now + 0.4);
  } catch {}
}

// ── Scan Sound (analyzing) ──────────────────────────────────
export function playScanSound(): void {
  try {
    const ctx = getCtx();
    const now = ctx.currentTime;

    // Quick ascending bleeps
    for (let i = 0; i < 3; i++) {
      const osc = ctx.createOscillator();
      osc.type = "sine";
      osc.frequency.value = 600 + i * 200;

      const gain = ctx.createGain();
      const start = now + i * 0.12;
      gain.gain.setValueAtTime(0, start);
      gain.gain.linearRampToValueAtTime(0.06, start + 0.02);
      gain.gain.exponentialRampToValueAtTime(0.001, start + 0.1);

      osc.connect(gain);
      gain.connect(ctx.destination);
      osc.start(start);
      osc.stop(start + 0.12);
    }
  } catch {}
}

// ── Classification Complete Chime ───────────────────────────
export function playClassifyChime(): void {
  try {
    const ctx = getCtx();
    const now = ctx.currentTime;

    const notes = [523, 659, 784]; // C5, E5, G5 — major chord
    notes.forEach((freq, i) => {
      const osc = ctx.createOscillator();
      osc.type = "triangle";
      osc.frequency.value = freq;

      const gain = ctx.createGain();
      const start = now + i * 0.1;
      gain.gain.setValueAtTime(0.06, start);
      gain.gain.exponentialRampToValueAtTime(0.001, start + 0.5);

      osc.connect(gain);
      gain.connect(ctx.destination);
      osc.start(start);
      osc.stop(start + 0.55);
    });
  } catch {}
}

// ── Notification Ding (task created) ────────────────────────
export function playNotificationDing(): void {
  try {
    const ctx = getCtx();
    const now = ctx.currentTime;

    // Two-tone ding: G5 → C6
    const freqs = [784, 1047];
    freqs.forEach((freq, i) => {
      const osc = ctx.createOscillator();
      osc.type = "sine";
      osc.frequency.value = freq;

      const gain = ctx.createGain();
      const start = now + i * 0.15;
      gain.gain.setValueAtTime(0.1, start);
      gain.gain.exponentialRampToValueAtTime(0.001, start + 0.6);

      osc.connect(gain);
      gain.connect(ctx.destination);
      osc.start(start);
      osc.stop(start + 0.65);
    });
  } catch {}
}

// ── Success Fanfare (demo complete) ─────────────────────────
export function playSuccessSound(): void {
  try {
    const ctx = getCtx();
    const now = ctx.currentTime;

    const notes = [523, 659, 784, 1047]; // C5, E5, G5, C6
    notes.forEach((freq, i) => {
      const osc = ctx.createOscillator();
      osc.type = "triangle";
      osc.frequency.value = freq;

      const gain = ctx.createGain();
      const start = now + i * 0.12;
      gain.gain.setValueAtTime(0.08, start);
      gain.gain.exponentialRampToValueAtTime(0.001, start + 0.8);

      osc.connect(gain);
      gain.connect(ctx.destination);
      osc.start(start);
      osc.stop(start + 0.85);
    });
  } catch {}
}

// ── Keyboard Typing Sound ───────────────────────────────────
export function playTypeTick(): void {
  try {
    const ctx = getCtx();
    const now = ctx.currentTime;

    // Very subtle click
    const osc = ctx.createOscillator();
    osc.type = "square";
    osc.frequency.value = 4000 + Math.random() * 2000;

    const gain = ctx.createGain();
    gain.gain.setValueAtTime(0.015, now);
    gain.gain.exponentialRampToValueAtTime(0.001, now + 0.03);

    osc.connect(gain);
    gain.connect(ctx.destination);
    osc.start(now);
    osc.stop(now + 0.04);
  } catch {}
}

// ── Voice Playback (pre-recorded neural TTS) ────────────────

/** Audio file map: script ID → MP3 path */
const VOICE_FILES: Record<string, string> = {
  "op-1": "/pitch/audio/op-1.mp3",
  "cl-1": "/pitch/audio/cl-1.mp3",
  "op-2": "/pitch/audio/op-2.mp3",
  "cl-2": "/pitch/audio/cl-2.mp3",
  "op-3": "/pitch/audio/op-3.mp3",
  "cl-3": "/pitch/audio/cl-3.mp3",
};

/**
 * Play a pre-recorded voice file by script line ID.
 * Returns a promise that resolves when playback ends.
 * If muted=true, resolves immediately without playing.
 */
export function playVoice(lineId: string, muted: boolean): Promise<void> {
  return new Promise((resolve) => {
    if (muted) { resolve(); return; }

    const src = VOICE_FILES[lineId];
    if (!src) { resolve(); return; }

    try {
      stopVoice(); // stop any previous voice
      const audio = new Audio(src);
      audio.volume = 0.9;
      currentVoiceAudio = audio;

      audio.onended = () => { currentVoiceAudio = null; resolve(); };
      audio.onerror = () => { currentVoiceAudio = null; resolve(); };
      audio.play().catch((err) => {
        console.warn("[demo-audio] voice play() blocked:", err?.name, src);
        currentVoiceAudio = null;
        resolve();
      });
    } catch {
      resolve();
    }
  });
}

/** Stop current voice playback */
export function stopVoice(): void {
  if (currentVoiceAudio) {
    currentVoiceAudio.pause();
    currentVoiceAudio.currentTime = 0;
    currentVoiceAudio = null;
  }
}

// ── Cleanup ─────────────────────────────────────────────────
export function stopAllAudio(): void {
  stopVoice();
  stopAmbient();
  if (audioContext && audioContext.state !== "closed") {
    try { audioContext.close(); } catch {}
    audioContext = null;
  }
}
