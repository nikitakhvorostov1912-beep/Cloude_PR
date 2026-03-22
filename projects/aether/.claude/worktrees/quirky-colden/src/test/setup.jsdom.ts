/**
 * Additional setup shared across all environments.
 * jest-dom matchers work in both jsdom and node (just adds expect matchers).
 * Motion mock: needed for component tests in jsdom.
 */
import '@testing-library/jest-dom';
import { vi } from 'vitest';

// ─── Mock motion/react (needed for component rendering) ───────────────────────

vi.mock('motion/react', () => {
  // eslint-disable-next-line @typescript-eslint/no-require-imports
  const React = require('react');

  const MotionDiv = React.forwardRef(
    (props: Record<string, unknown>, ref: React.Ref<HTMLDivElement>) => {
      // Strip motion-specific props that would cause React warnings
      const {
        animate: _a, initial: _i, exit: _e, transition: _t,
        whileHover: _wh, whileTap: _wt, layout: _l,
        ...rest
      } = props;
      return React.createElement('div', { ...rest, ref });
    },
  );
  MotionDiv.displayName = 'motion.div';

  const MotionButton = React.forwardRef(
    (props: Record<string, unknown>, ref: React.Ref<HTMLButtonElement>) => {
      const {
        animate: _a, initial: _i, exit: _e, transition: _t,
        whileHover: _wh, whileTap: _wt, layout: _l,
        ...rest
      } = props;
      return React.createElement('button', { ...rest, ref });
    },
  );
  MotionButton.displayName = 'motion.button';

  return {
    motion: {
      div: MotionDiv,
      span: MotionDiv,
      button: MotionButton,
    },
    AnimatePresence: ({ children }: { children: React.ReactNode }) => children,
  };
});

// ─── Mock react-router-dom navigation hooks ───────────────────────────────────

vi.mock('react-router-dom', async () => {
  const actual = await vi.importActual('react-router-dom');
  return {
    ...actual,
    useNavigate: vi.fn().mockReturnValue(vi.fn()),
    useParams: vi.fn().mockReturnValue({}),
    useLocation: vi.fn().mockReturnValue({ pathname: '/', search: '', hash: '' }),
  };
});

// ─── Mock Web Audio API (for jsdom, which doesn't have AudioContext) ──────────

if (typeof globalThis.AudioContext === 'undefined') {
  const mockAudioContext = {
    createOscillator: vi.fn().mockReturnValue({
      connect: vi.fn(), start: vi.fn(), stop: vi.fn(),
      frequency: { setValueAtTime: vi.fn() }, type: 'sine',
    }),
    createGain: vi.fn().mockReturnValue({
      connect: vi.fn(),
      gain: { setValueAtTime: vi.fn(), exponentialRampToValueAtTime: vi.fn() },
    }),
    destination: {}, currentTime: 0, state: 'running',
    close: vi.fn().mockResolvedValue(undefined),
  };
  Object.defineProperty(globalThis, 'AudioContext', {
    value: vi.fn().mockImplementation(() => mockAudioContext),
    writable: true, configurable: true,
  });
}
