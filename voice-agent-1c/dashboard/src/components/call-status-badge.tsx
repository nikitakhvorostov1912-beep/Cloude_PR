import { DEPARTMENT_LABELS, PRIORITY_LABELS } from "@/lib/constants";

export function DepartmentBadge({ department }: { department: string | null }) {
  if (!department) return <span className="text-muted-foreground/50">{"\u2014"}</span>;
  return (
    <span className="inline-flex items-center gap-1.5 rounded-lg bg-[oklch(0.72_0.19_200_/_0.1)] px-2.5 py-0.5 text-xs font-medium text-[oklch(0.72_0.19_200)]">
      <span className="h-1.5 w-1.5 rounded-full bg-[oklch(0.72_0.19_200)]" />
      {DEPARTMENT_LABELS[department] ?? department}
    </span>
  );
}

export function PriorityBadge({ priority }: { priority: string | null }) {
  if (!priority) return <span className="text-muted-foreground/50">{"\u2014"}</span>;

  const STYLES: Record<string, string> = {
    critical: "bg-[oklch(0.65_0.22_25_/_0.15)] text-[oklch(0.75_0.2_25)] border border-[oklch(0.65_0.22_25_/_0.2)]",
    high: "bg-[oklch(0.72_0.16_50_/_0.12)] text-[oklch(0.78_0.14_50)]",
    normal: "bg-[oklch(0.72_0.19_200_/_0.1)] text-[oklch(0.72_0.19_200)]",
    low: "bg-[oklch(0.3_0.02_270_/_0.3)] text-muted-foreground",
  };

  return (
    <span className={`inline-flex items-center rounded-lg px-2.5 py-0.5 text-xs font-medium ${STYLES[priority] ?? STYLES.normal}`}>
      {PRIORITY_LABELS[priority] ?? priority}
    </span>
  );
}
