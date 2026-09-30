"use client";

import Link from "next/link";
import { useParams } from "next/navigation";
import { useCallback, useEffect, useRef, useState } from "react";

import { ActivityTimeline } from "@/components/app/activity-timeline";
import { ActionBadge, PriorityBadge, StatusBadge } from "@/components/app/badges";
import { JevDecisionCard } from "@/components/app/jev-decision-card";
import { ReplyPanel } from "@/components/app/reply-panel";
import { Alert, AlertDescription, AlertTitle } from "@/components/ui/alert";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Skeleton } from "@/components/ui/skeleton";
import { api } from "@/lib/api";
import { CLOSED_STATUSES, dateTime, money } from "@/lib/format";
import { useApi } from "@/lib/use-api";

// After analysis finishes, OpenAI drafts the reply a moment later: keep polling briefly for it.
const POLL_MS = 2000;
const EXTRA_POLLS_FOR_REPLY = 8;

export default function TicketPage() {
  const { id } = useParams<{ id: string }>();
  const ticketId = Number(id);
  const { data: ticket, error, reload: reloadTicket } = useApi(() => api.getTicket(ticketId), `ticket:${ticketId}`);
  const { data: events, reload: reloadEvents } = useApi(() => api.getTicketEvents(ticketId), `events:${ticketId}`);
  const reload = useCallback(() => {
    reloadTicket();
    reloadEvents();
  }, [reloadTicket, reloadEvents]);
  const [retrying, setRetrying] = useState(false);
  const extraPolls = useRef(0);

  useEffect(() => {
    if (!ticket) return;
    const waitingForReply =
      ticket.latest_jev_decision && !ticket.latest_ai_response && extraPolls.current < EXTRA_POLLS_FOR_REPLY;
    if (ticket.status === "ANALYZING") extraPolls.current = 0;
    else if (waitingForReply) extraPolls.current += 1;
    else return;
    const timer = setTimeout(reload, POLL_MS);
    return () => clearTimeout(timer);
  }, [ticket, reload]);

  if (error) {
    return (
      <Alert variant="destructive">
        <AlertDescription>{error}</AlertDescription>
      </Alert>
    );
  }
  if (!ticket) return <Skeleton className="h-96" />;

  const closed = CLOSED_STATUSES.includes(ticket.status);
  const analyzing = ticket.status === "ANALYZING";

  async function retryAnalysis() {
    setRetrying(true);
    try {
      await api.analyze(ticketId);
      reload();
    } finally {
      setRetrying(false);
    }
  }

  return (
    <div className="space-y-6">
      <div className="space-y-2">
        <Link href="/dashboard/tickets" className="text-sm text-muted-foreground hover:underline">
          ← Tickets
        </Link>
        <div className="flex flex-wrap items-center gap-2">
          <h1 className="text-2xl font-semibold">
            <span className="text-muted-foreground">#{ticket.id}</span> {ticket.subject}
          </h1>
          <StatusBadge status={ticket.status} />
          <PriorityBadge priority={ticket.priority} />
        </div>
        <p className="text-sm text-muted-foreground">Received {dateTime(ticket.created_at)}</p>
      </div>

      <div className="grid gap-6 lg:grid-cols-3">
        <div className="space-y-6 lg:col-span-2">
          <Card>
            <CardHeader>
              <CardTitle>Customer message</CardTitle>
            </CardHeader>
            <CardContent>
              <p className="text-sm whitespace-pre-wrap">{ticket.message}</p>
            </CardContent>
          </Card>

          {analyzing && (
            <Alert>
              <AlertTitle>Jev is analyzing this ticket…</AlertTitle>
              <AlertDescription>This page updates automatically.</AlertDescription>
            </Alert>
          )}

          {ticket.status === "JEV_FAILED" && (
            <Alert variant="destructive">
              <AlertTitle>Jev couldn&apos;t classify this ticket</AlertTitle>
              <AlertDescription className="space-y-3">
                <p>Nothing was guessed. Retry the analysis, or choose an action and write the reply yourself.</p>
                <Button size="sm" variant="outline" onClick={retryAnalysis} disabled={retrying}>
                  {retrying ? "Retrying…" : "Retry analysis"}
                </Button>
              </AlertDescription>
            </Alert>
          )}

          {!analyzing && !closed && <ReplyPanel key={replyKey(ticket)} ticket={ticket} onChanged={reload} />}

          {closed && (
            <>
              {ticket.latest_ai_response?.approved && <ReplyPanel ticket={ticket} onChanged={reload} />}
              <Alert>
                <AlertTitle>
                  Resolved {ticket.resolved_at && dateTime(ticket.resolved_at)}
                </AlertTitle>
                <AlertDescription className="flex items-center gap-2">
                  Final action <ActionBadge action={ticket.final_action} />
                </AlertDescription>
              </Alert>
            </>
          )}

          {events && <ActivityTimeline events={events} />}
        </div>

        <div className="space-y-6">
          {ticket.latest_jev_decision && <JevDecisionCard decision={ticket.latest_jev_decision} />}

          <Card>
            <CardHeader>
              <CardTitle>Customer</CardTitle>
            </CardHeader>
            <CardContent className="space-y-1 text-sm">
              <p className="font-medium">{ticket.customer.name}</p>
              <p className="text-muted-foreground">{ticket.customer.email}</p>
              <p className="text-muted-foreground">Customer since {dateTime(ticket.customer.created_at)}</p>
            </CardContent>
          </Card>

          <Card>
            <CardHeader>
              <CardTitle>Order</CardTitle>
            </CardHeader>
            <CardContent className="text-sm">
              {ticket.order ? (
                <dl className="grid grid-cols-2 gap-y-1">
                  <dt className="text-muted-foreground">Number</dt>
                  <dd>{ticket.order.order_number}</dd>
                  <dt className="text-muted-foreground">Total</dt>
                  <dd>{money(ticket.order.total_amount)}</dd>
                  <dt className="text-muted-foreground">Status</dt>
                  <dd className="capitalize">{ticket.order.status}</dd>
                  <dt className="text-muted-foreground">Delivered</dt>
                  <dd>{ticket.order.delivered_at ? dateTime(ticket.order.delivered_at) : "–"}</dd>
                </dl>
              ) : (
                <p className="text-muted-foreground">No matching order for this customer.</p>
              )}
            </CardContent>
          </Card>
        </div>
      </div>
    </div>
  );
}

/** Remount the reply editor when a new draft or decision arrives, so its local state resets. */
function replyKey(ticket: { latest_ai_response: { id: number } | null; latest_jev_decision: { id: number } | null }) {
  return `${ticket.latest_jev_decision?.id ?? "none"}-${ticket.latest_ai_response?.id ?? "none"}`;
}
