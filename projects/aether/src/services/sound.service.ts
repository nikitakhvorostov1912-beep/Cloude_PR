type SoundName = 'click' | 'navigate' | 'upload' | 'start' | 'success' | 'error';

type SoundConfig = { frequency: number; duration: number; type: OscillatorType };

const SOUND_CONFIGS: Record<SoundName, SoundConfig> = {
  click:    { frequency: 800, duration: 0.08, type: 'sine' },
  navigate: { frequency: 600, duration: 0.15, type: 'sine' },
  upload:   { frequency: 500, duration: 0.25, type: 'sine' },
  start:    { frequency: 700, duration: 0.4,  type: 'sine' },
  success:  { frequency: 900, duration: 0.5,  type: 'sine' },
  error:    { frequency: 300, duration: 0.35, type: 'triangle' },
};

class SoundService {
  // Единый AudioContext на весь жизненный цикл приложения —
  // избегаем лимита одновременных контекстов в WebView2 (Chrome ~6 штук).
  private ctx: AudioContext | null = null;
  private enabled = true;
  private volume = 0.7;

  init() {
    // AudioContext создаётся лениво при первом play(), чтобы не нарушить
    // политику браузеров "autoplay blocked until user gesture".
  }

  private getContext(): AudioContext | null {
    try {
      if (!this.ctx || this.ctx.state === 'closed') {
        this.ctx = new AudioContext();
      }
      // Resume если был suspended (autoplay policy)
      if (this.ctx.state === 'suspended') {
        void this.ctx.resume();
      }
      return this.ctx;
    } catch {
      return null;
    }
  }

  play(name: SoundName) {
    if (!this.enabled) return;

    const config = SOUND_CONFIGS[name];
    if (!config) return;

    const ctx = this.getContext();
    if (!ctx) return;

    try {
      const osc = ctx.createOscillator();
      const gain = ctx.createGain();

      osc.type = config.type;
      osc.frequency.setValueAtTime(config.frequency, ctx.currentTime);

      if (name === 'success') {
        osc.frequency.setValueAtTime(700,  ctx.currentTime);
        osc.frequency.setValueAtTime(900,  ctx.currentTime + 0.15);
        osc.frequency.setValueAtTime(1100, ctx.currentTime + 0.3);
      }

      gain.gain.setValueAtTime(this.volume * 0.15, ctx.currentTime);
      gain.gain.exponentialRampToValueAtTime(0.001, ctx.currentTime + config.duration);

      osc.connect(gain);
      gain.connect(ctx.destination);

      osc.start(ctx.currentTime);
      osc.stop(ctx.currentTime + config.duration);
    } catch {
      // AudioContext недоступен или заблокирован
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
