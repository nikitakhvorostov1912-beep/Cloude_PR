"use client";

import { cn } from "@/lib/utils";

interface AuroraLogoProps {
  size?: "sm" | "md" | "lg";
  showText?: boolean;
  className?: string;
}

/**
 * Aurora Logo — Glow version for dark theme.
 * Brighter stroke colors, neon glow filter, white text with text-shadow.
 */
export function AuroraLogo({
  size = "md",
  showText = true,
  className,
}: AuroraLogoProps) {
  const sizes = {
    sm: { mark: 28, text: "text-sm", gap: "gap-1.5" },
    md: { mark: 36, text: "text-xl", gap: "gap-2" },
    lg: { mark: 48, text: "text-3xl", gap: "gap-3" },
  };

  const s = sizes[size];

  return (
    <div className={cn("flex items-center", s.gap, className)}>
      <svg
        width={s.mark}
        height={s.mark}
        viewBox="0 0 48 48"
        fill="none"
        xmlns="http://www.w3.org/2000/svg"
        aria-label="Аврора"
      >
        <defs>
          <filter id="aurora-glow" x="-50%" y="-50%" width="200%" height="200%">
            <feGaussianBlur in="SourceGraphic" stdDeviation="2" result="blur" />
            <feMerge>
              <feMergeNode in="blur" />
              <feMergeNode in="SourceGraphic" />
            </feMerge>
          </filter>
        </defs>

        <path
          d="M6 36 C6 36 12 8 24 8 C36 8 42 36 42 36"
          stroke="#6366F1"
          strokeWidth="4"
          strokeLinecap="round"
          fill="none"
          filter="url(#aurora-glow)"
        />
        <path
          d="M10 32 C10 32 16 14 24 14 C32 14 38 32 38 32"
          stroke="#FF4547"
          strokeWidth="3"
          strokeLinecap="round"
          fill="none"
          filter="url(#aurora-glow)"
        />
        <path
          d="M14 28 C14 28 18 18 24 18 C30 18 34 28 34 28"
          stroke="#7DBEF4"
          strokeWidth="2.5"
          strokeLinecap="round"
          fill="none"
          filter="url(#aurora-glow)"
        />
        <circle cx="24" cy="10" r="3" fill="#7DBEF4" opacity="0.8" filter="url(#aurora-glow)" />
        <circle cx="24" cy="10" r="1.5" fill="#FFFFFF" opacity="0.9" />
      </svg>

      {showText && (
        <span
          className={cn(
            "font-bold tracking-tight text-text-primary text-glow",
            s.text
          )}
        >
          Аврора
        </span>
      )}
    </div>
  );
}
