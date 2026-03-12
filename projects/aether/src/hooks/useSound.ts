import { useCallback } from 'react';
import { soundService } from '@/services/sound.service';
import { useSettingsStore } from '@/stores/settings.store';

type SoundName = 'click' | 'navigate' | 'upload' | 'start' | 'success' | 'error';

export function useSound() {
  const soundEnabled = useSettingsStore((s) => s.soundEnabled);
  const soundVolume = useSettingsStore((s) => s.soundVolume);

  const play = useCallback(
    (name: SoundName) => {
      soundService.setEnabled(soundEnabled);
      soundService.setVolume(soundVolume);
      soundService.play(name);
    },
    [soundEnabled, soundVolume]
  );

  return { play };
}
