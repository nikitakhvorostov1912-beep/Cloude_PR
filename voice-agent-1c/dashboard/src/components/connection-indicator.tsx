"use client";

import { useHealthCheck } from "@/hooks/use-dashboard";

export function ConnectionIndicator() {
  const { data, isError, isLoading } = useHealthCheck();

  const isOnline = !isError && !isLoading && data?.status === "ok";

  return (
    <div className="flex items-center gap-2">
      <span
        className={`h-2 w-2 rounded-full pulse-dot ${
          isOnline
            ? "bg-[oklch(0.75_0.18_160)] text-[oklch(0.75_0.18_160)]"
            : "bg-[oklch(0.65_0.22_25)] text-[oklch(0.65_0.22_25)]"
        }`}
      />
      <span className="text-xs text-muted-foreground">
        {isOnline ? "\u041f\u043e\u0434\u043a\u043b\u044e\u0447\u0435\u043d\u043e" : "\u041d\u0435\u0442 \u0441\u0432\u044f\u0437\u0438"}
      </span>
    </div>
  );
}
