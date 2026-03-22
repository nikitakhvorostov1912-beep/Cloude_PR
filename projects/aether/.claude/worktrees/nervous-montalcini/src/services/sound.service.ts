import { Howl } from 'howler';

type SoundName = 'click' | 'navigate' | 'upload' | 'start' | 'success' | 'error';

class SoundService {
  private sounds: Map<SoundName, Howl> = new Map();
  private enabled = true;
  private volume = 0.7;

  init() {
    // Создаём синтетические звуки через Web Audio API — отдельные MP3 не нужны
    // Используем data URI с простыми тонами
    const soundConfigs: Record<SoundName, { frequency: number; duration: number; type: OscillatorType }> = {
      click: { frequency: 800, duration: 0.08, type: 'sine' },
      navigate: { frequency: 600, duration: 0.15, type: 'sine' },
      upload: { frequency: 500, duration: 0.25, type: 'sine' },
      start: { frequency: 700, duration: 0.4, type: 'sine' },
      success: { frequency: 900, duration: 0.5, type: 'sine' },
      error: { frequency: 300, duration: 0.35, type: 'triangle' },
    };

    for (const [name, config] of Object.entries(soundConfigs)) {
      this.createSyntheticSound(name as SoundName, config);
    }
  }

  private createSyntheticSound(
    name: SoundName,
    config: { frequency: number; duration: number; type: OscillatorType }
  ) {
    // Howler.js для управления, но звуки генерируем программно
    // Создаём silent howl как placeholder — реальный звук через AudioContext
    const howl = new Howl({
      src: ['data:audio/wav;base64,UklGRiQAAABXQVZFZm10IBAAAAABAAEARKwAAIhYAQACABAAZGF0YQAAAAA='],
      volume: this.volume,
    });
    this.sounds.set(name, howl);

    // Сохраняем конфиг для play
    (howl as unknown as Record<string, unknown>)._synthConfig = config;
  }

  play(name: SoundName) {
    if (!this.enabled) return;

    const howl = this.sounds.get(name);
    if (!howl) return;

    const config = (howl as unknown as Record<string, unknown>)._synthConfig as {
      frequency: number;
      duration: number;
      type: OscillatorType;
    } | undefined;

    if (!config) return;

    try {
      const ctx = new AudioContext();
      const osc = ctx.createOscillator();
      const gain = ctx.createGain();

      osc.type = config.type;
      osc.frequency.setValueAtTime(config.frequency, ctx.currentTime);

      if (name === 'success') {
        osc.frequency.setValueAtTime(700, ctx.currentTime);
        osc.frequency.setValueAtTime(900, ctx.currentTime + 0.15);
        osc.frequency.setValueAtTime(1100, ctx.currentTime + 0.3);
      }

      gain.gain.setValueAtTime(this.volume * 0.15, ctx.currentTime);
      gain.gain.exponentialRampToValueAtTime(0.001, ctx.currentTime + config.duration);

      osc.connect(gain);
      gain.connect(ctx.destination);

      osc.start(ctx.currentTime);
      osc.stop(ctx.currentTime + config.duration);

      osc.onended = () => ctx.close();
    } catch {
      // AudioContext not available
    }
  }

  setEnabled(enabled: boolean) {
    this.enabled = enabled;
  }

  setVolume(volume: number) {
    this.volume = Math.max(0, Math.min(1, volume));
  }
}

export const soundService = new SoundService();
