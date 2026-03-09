import { type ReactNode } from "react";

/**
 * Pitch layout — fullscreen presentation mode.
 * TopNav is hidden by LayoutShell detecting /pitch pathname.
 * Aurora + Noise backgrounds come from root layout.
 */
export default function PitchLayout({ children }: { children: ReactNode }) {
  return <div className="relative z-10">{children}</div>;
}
