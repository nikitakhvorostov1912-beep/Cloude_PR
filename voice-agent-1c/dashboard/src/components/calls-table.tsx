"use client";

import { motion } from "framer-motion";
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from "@/components/ui/table";
import { Skeleton } from "@/components/ui/skeleton";
import { DepartmentBadge, PriorityBadge } from "./call-status-badge";
import { formatDateTime, formatDuration, formatPhoneNumber } from "@/lib/format";
import type { CallEntry } from "@/lib/types";

interface CallsTableProps {
  calls: CallEntry[];
  loading?: boolean;
  onRowClick?: (callId: string) => void;
  compact?: boolean;
}

export function CallsTable({
  calls,
  loading,
  onRowClick,
  compact,
}: CallsTableProps) {
  if (loading) {
    return (
      <div className="space-y-2">
        {Array.from({ length: 5 }).map((_, i) => (
          <Skeleton key={i} className="h-12 w-full rounded-xl" />
        ))}
      </div>
    );
  }

  if (calls.length === 0) {
    return (
      <div className="py-12 text-center text-muted-foreground text-sm">
        {"\u0417\u0432\u043e\u043d\u043a\u043e\u0432 \u043f\u043e\u043a\u0430 \u043d\u0435\u0442"}
      </div>
    );
  }

  return (
    <Table>
      <TableHeader>
        <TableRow className="border-b border-[oklch(0.3_0.02_270_/_0.2)] hover:bg-transparent">
          <TableHead className="text-xs uppercase tracking-wider">{"\u0414\u0430\u0442\u0430"}</TableHead>
          <TableHead className="text-xs uppercase tracking-wider">{"\u0422\u0435\u043b\u0435\u0444\u043e\u043d"}</TableHead>
          {!compact && <TableHead className="text-xs uppercase tracking-wider">{"\u041a\u043b\u0438\u0435\u043d\u0442"}</TableHead>}
          <TableHead className="text-xs uppercase tracking-wider">{"\u041e\u0442\u0434\u0435\u043b"}</TableHead>
          {!compact && <TableHead className="text-xs uppercase tracking-wider">{"\u0421\u0440\u043e\u0447\u043d\u043e\u0441\u0442\u044c"}</TableHead>}
          <TableHead className="text-xs uppercase tracking-wider text-right">{"\u0414\u043b\u0438\u0442\u0435\u043b\u044c\u043d\u043e\u0441\u0442\u044c"}</TableHead>
        </TableRow>
      </TableHeader>
      <TableBody>
        {calls.map((call, i) => (
          <motion.tr
            key={call.call_id}
            initial={{ opacity: 0, x: -10 }}
            animate={{ opacity: 1, x: 0 }}
            transition={{ duration: 0.3, delay: i * 0.03 }}
            className={`border-b border-[oklch(0.3_0.02_270_/_0.1)] transition-colors duration-200 ${
              onRowClick
                ? "cursor-pointer hover:bg-[oklch(0.72_0.19_200_/_0.05)]"
                : ""
            }`}
            onClick={() => onRowClick?.(call.call_id)}
          >
            <TableCell className="text-xs text-muted-foreground">
              {formatDateTime(call.created_at)}
            </TableCell>
            <TableCell className="font-mono text-xs">
              {formatPhoneNumber(call.caller_number)}
            </TableCell>
            {!compact && (
              <TableCell>
                {call.client_name ?? (
                  <span className="text-muted-foreground/50">{"\u2014"}</span>
                )}
              </TableCell>
            )}
            <TableCell>
              <DepartmentBadge department={call.department} />
            </TableCell>
            {!compact && (
              <TableCell>
                <PriorityBadge priority={call.priority} />
              </TableCell>
            )}
            <TableCell className="text-right font-mono text-xs text-muted-foreground">
              {formatDuration(call.duration_seconds)}
            </TableCell>
          </motion.tr>
        ))}
      </TableBody>
    </Table>
  );
}
