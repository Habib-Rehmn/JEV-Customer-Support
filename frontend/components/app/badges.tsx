"use client";

import { Badge } from "@/components/ui/badge";
import { ACTION_LABELS, STATUS_LABELS, duration } from "@/lib/format";
import { useNow } from "@/lib/use-now";
import { cn } from "@/lib/utils";
import type { SupportAction, TicketPriority, TicketStatus } from "@/types/api";

const STATUS_STYLES: Record<TicketStatus, string> = {
  NEW: "bg-muted text-muted-foreground",
  ANALYZING: "bg-sky-100 text-sky-800 dark:bg-sky-950 dark:text-sky-300",
  JEV_FAILED: "bg-red-100 text-red-800 dark:bg-red-950 dark:text-red-300",
  WAITING_FOR_AGENT: "bg-amber-100 text-amber-900 dark:bg-amber-950 dark:text-amber-300",
  WAITING_FOR_CUSTOMER: "bg-violet-100 text-violet-800 dark:bg-violet-950 dark:text-violet-300",
  ESCALATED: "bg-orange-100 text-orange-900 dark:bg-orange-950 dark:text-orange-300",
  RESOLVED: "bg-emerald-100 text-emerald-800 dark:bg-emerald-950 dark:text-emerald-300",
  CLOSED: "bg-muted text-muted-foreground",
};

export function StatusBadge({ status }: { status: TicketStatus }) {
  return (
    <Badge variant="secondary" className={cn("border-0", STATUS_STYLES[status])}>
      {STATUS_LABELS[status]}
    </Badge>
  );
}

export function ActionBadge({ action }: { action: SupportAction | null }) {
  if (!action) return <span className="text-muted-foreground">–</span>;
  return <Badge variant="outline">{ACTION_LABELS[action]}</Badge>;
}

export function PriorityBadge({ priority }: { priority: TicketPriority }) {
  if (priority === "NORMAL") return null;
  if (priority === "LOW") return <Badge variant="outline" className="text-muted-foreground">Low</Badge>;
  return <Badge variant="destructive">{priority === "URGENT" ? "Urgent" : "High priority"}</Badge>;
}

/** Time left until a reply is due, or how long it is overdue. */
export function DueBadge({ dueAt, overdue }: { dueAt: string | null; overdue: boolean }) {
  const now = useNow();
  if (!dueAt) return <span className="text-muted-foreground">–</span>;
  const left = new Date(dueAt).getTime() - now;
  if (overdue || left <= 0) {
    return (
      <Badge variant="destructive" title={`Reply was due ${new Date(dueAt).toLocaleString()}`}>
        Overdue {duration(left)}
      </Badge>
    );
  }
  return (
    <span className="text-muted-foreground tabular-nums" title={`Reply due ${new Date(dueAt).toLocaleString()}`}>
      in {duration(left)}
    </span>
  );
}
