import {
  BotIcon,
  CheckCircle2Icon,
  CircleAlertIcon,
  InboxIcon,
  PencilIcon,
  ScaleIcon,
  SendIcon,
  ShieldAlertIcon,
  SparklesIcon,
  WrenchIcon,
} from "lucide-react";

import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { ACTION_LABELS, URGENCY_LABELS, dateTime, percent, ruleLabel, timeAgo } from "@/lib/format";
import { cn } from "@/lib/utils";
import type { SupportAction, TicketEvent } from "@/types/api";

type Tone = "default" | "warning" | "danger" | "success";

interface Described {
  icon: React.ComponentType<{ className?: string }>;
  title: string;
  detail?: string;
  tone?: Tone;
  context?: unknown;
}

// Internal "started" markers add noise; the completed/failed event tells the story.
const HIDDEN = new Set(["openai_generation_started"]);

const action = (value: unknown) => ACTION_LABELS[value as SupportAction] ?? String(value);

function describe(event: TicketEvent): Described {
  const d = event.data;
  const who = event.actor;
  switch (event.event_type) {
    case "ticket_created":
      return {
        icon: InboxIcon,
        title: "Ticket submitted by the customer",
        detail: d.submitted_order_number
          ? `Order ${d.submitted_order_number} ${d.order_found ? "matched" : "not found for this customer"}`
          : "No order number given",
      };
    case "jev_request_started":
      return { icon: BotIcon, title: "Sent to Jev for classification", context: d.context };
    case "jev_request_completed":
      return {
        icon: BotIcon,
        title: `Jev recommended ${action(d.action)}`,
        detail: `Confidence ${percent(d.confidence as number)}${
          typeof d.urgency === "number"
            ? ` · urgency ${URGENCY_LABELS[Math.round(d.urgency)]} (${d.urgency.toFixed(1)}/3)`
            : ""
        }`,
      };
    case "jev_request_failed":
      return { icon: CircleAlertIcon, title: "Jev could not classify the ticket", detail: String(d.detail ?? d.error), tone: "danger" };
    case "rule_triggered":
      return { icon: ScaleIcon, title: `Rule: ${ruleLabel(String(d.rule))}`, detail: String(d.reason), tone: "warning" };
    case "ticket_escalated":
      return {
        icon: ShieldAlertIcon,
        title: d.by === "rules" ? "Escalated by the rules" : who ? `Escalated by ${who}` : "Escalated by an agent",
        detail: d.reason ? String(d.reason) : undefined,
        tone: "warning",
      };
    case "openai_generation_completed":
      return {
        icon: SparklesIcon,
        title: who ? `${who} regenerated the reply` : "Reply drafted",
        detail: String(d.model),
      };
    case "openai_generation_failed":
      return { icon: CircleAlertIcon, title: "Reply drafting failed", detail: String(d.detail ?? d.error), tone: "danger" };
    case "response_edited":
      return {
        icon: PencilIcon,
        title: d.manual
          ? who ? `${who} wrote a reply` : "Reply written by hand"
          : who ? `${who} edited the reply` : "Reply edited",
      };
    case "ticket_approved": {
      const notes = [d.overridden && "overrode the rules", d.edited && "edited the draft"].filter(Boolean);
      return {
        icon: SendIcon,
        title: who ? `${who} approved and sent the reply` : "Reply approved and sent",
        detail: `Final action ${action(d.final_action)}${notes.length ? ` · ${notes.join(", ")}` : ""}`,
        tone: "success",
      };
    }
    case "ticket_resolved":
      return {
        icon: CheckCircle2Icon,
        title: who ? `Resolved by ${who}` : "Resolved",
        detail: [`Final action ${action(d.final_action)}`, d.note].filter(Boolean).join(" · "),
        tone: "success",
      };
    case "ticket_updated":
      return {
        icon: WrenchIcon,
        title: who ? `${who} changed ticket fields` : "Ticket fields changed",
        detail: Object.entries((d.changes as Record<string, string>) ?? {})
          .map(([k, v]) => `${k} → ${v}`)
          .join(", "),
      };
    default:
      return { icon: WrenchIcon, title: event.event_type.replaceAll("_", " ") };
  }
}

const TONE_STYLES: Record<Tone, string> = {
  default: "bg-muted text-muted-foreground",
  warning: "bg-amber-100 text-amber-900 dark:bg-amber-950 dark:text-amber-300",
  danger: "bg-red-100 text-red-800 dark:bg-red-950 dark:text-red-300",
  success: "bg-emerald-100 text-emerald-800 dark:bg-emerald-950 dark:text-emerald-300",
};

export function ActivityTimeline({ events }: { events: TicketEvent[] }) {
  const visible = events.filter((e) => !HIDDEN.has(e.event_type));
  return (
    <Card>
      <CardHeader>
        <CardTitle>Activity</CardTitle>
        <CardDescription>Everything that happened to this ticket, oldest first</CardDescription>
      </CardHeader>
      <CardContent>
        <ol className="relative space-y-4">
          {visible.map((event, i) => {
            const { icon: Icon, title, detail, tone = "default", context } = describe(event);
            return (
              <li key={event.id} className="relative flex gap-3">
                {i < visible.length - 1 && (
                  <span className="absolute top-8 bottom-[-1rem] left-[0.9375rem] w-px bg-border" aria-hidden />
                )}
                <span className={cn("z-10 flex size-8 shrink-0 items-center justify-center rounded-full", TONE_STYLES[tone])}>
                  <Icon className="size-4" />
                </span>
                <div className="min-w-0 flex-1 pt-1 text-sm">
                  <div className="flex flex-wrap items-baseline justify-between gap-x-3">
                    <p className="font-medium">{title}</p>
                    <time className="text-xs text-muted-foreground" dateTime={event.created_at} title={dateTime(event.created_at)}>
                      {timeAgo(event.created_at)}
                    </time>
                  </div>
                  {detail && (
                    <p className="line-clamp-3 text-muted-foreground [overflow-wrap:anywhere]" title={detail}>
                      {detail}
                    </p>
                  )}
                  {context !== undefined && (
                    <details className="mt-1">
                      <summary className="cursor-pointer text-xs text-muted-foreground hover:text-foreground">
                        What Jev was given
                      </summary>
                      <pre className="mt-2 rounded-md bg-muted p-3 text-xs whitespace-pre-wrap [overflow-wrap:anywhere]">
                        {JSON.stringify(context, null, 2)}
                      </pre>
                    </details>
                  )}
                </div>
              </li>
            );
          })}
        </ol>
      </CardContent>
    </Card>
  );
}
