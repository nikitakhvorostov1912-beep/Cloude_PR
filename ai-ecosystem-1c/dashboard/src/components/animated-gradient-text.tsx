"use client";

import { cn } from "@/lib/utils";
import { type ReactNode } from "react";

interface AnimatedGradientTextProps {
  children: ReactNode;
  className?: string;
}

/**
 * AnimatedGradientText — text with animated gradient background.
 * Uses the gradient-text CSS class from globals.css.
 * Colors cycle: blue → red → purple → blue.
 */
export function AnimatedGradientText({
  children,
  className,
}: AnimatedGradientTextProps) {
  return (
    <span className={cn("gradient-text", className)}>
      {children}
    </span>
  );
}
