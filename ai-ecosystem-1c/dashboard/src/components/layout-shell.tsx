"use client";

import { type ReactNode, useCallback } from "react";
import { usePathname } from "next/navigation";
import { TopNav } from "@/components/top-nav";
import { CommandPalette } from "@/components/command-palette";

/**
 * LayoutShell — client component that wraps main content.
 * Provides TopNav with command palette trigger + CommandPalette overlay.
 * Hides navigation on /pitch routes (fullscreen presentation mode).
 */
export function LayoutShell({ children }: { children: ReactNode }) {
  const pathname = usePathname();
  const isPitch = pathname.startsWith("/pitch");

  const handleCommandOpen = useCallback(() => {
    window.dispatchEvent(new Event("command-palette:open"));
  }, []);

  if (isPitch) {
    return <main className="min-h-screen">{children}</main>;
  }

  return (
    <>
      {/* Top navigation bar */}
      <TopNav onCommandOpen={handleCommandOpen} />

      {/* Main content with top padding for nav */}
      <main className="min-h-screen pt-14">{children}</main>

      {/* Command palette (Ctrl+K) */}
      <CommandPalette />
    </>
  );
}
