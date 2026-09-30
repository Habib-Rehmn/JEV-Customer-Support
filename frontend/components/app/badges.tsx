import { Badge } from "@/components/ui/badge";
import { ACTION_LABELS, STATUS_LABELS } from "@/lib/format";
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
  if (priority === "NORMAL" || priority === "LOW") return null;
  return <Badge variant="destructive">{priority === "URGENT" ? "Urgent" : "High priority"}</Badge>;
}
