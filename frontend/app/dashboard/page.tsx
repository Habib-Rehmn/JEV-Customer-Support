"use client";

import Link from "next/link";
import { useState } from "react";

import { BarList } from "@/components/app/bar-list";
import { NativeSelect } from "@/components/app/native-select";
import { StatTile } from "@/components/app/stat-tile";
import { TicketsTable } from "@/components/app/tickets-table";
import { Alert, AlertDescription } from "@/components/ui/alert";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Skeleton } from "@/components/ui/skeleton";
import { api } from "@/lib/api";
import { ACTION_LABELS, percent } from "@/lib/format";
import { useApi } from "@/lib/use-api";
import { SUPPORT_ACTIONS } from "@/types/api";

const RANGES = [
  { label: "All time", value: "" },
  { label: "Last 7 days", value: "7" },
  { label: "Last 30 days", value: "30" },
  { label: "Last 90 days", value: "90" },
];

export default function DashboardPage() {
  const [range, setRange] = useState("");
  const analytics = useApi(() => api.analytics(range ? Number(range) : undefined), `analytics:${range}`);
  const recent = useApi(() => api.listTickets({ limit: 8 }), "recent");
  const stats = analytics.data;

  return (
    <div className="space-y-8">
      <div className="flex flex-wrap items-end justify-between gap-3">
        <div>
          <h1 className="text-2xl font-semibold">Support dashboard</h1>
          <p className="text-sm text-muted-foreground">How tickets are flowing and how well Jev is deciding.</p>
        </div>
        <NativeSelect value={range} onChange={(e) => setRange(e.target.value)} aria-label="Time range">
          {RANGES.map((r) => (
            <option key={r.value} value={r.value}>
              {r.label}
            </option>
          ))}
        </NativeSelect>
      </div>

      {analytics.error && (
        <Alert variant="destructive">
          <AlertDescription>{analytics.error}</AlertDescription>
        </Alert>
      )}

      {!stats ? (
        <div className="grid grid-cols-2 gap-3 lg:grid-cols-4">
          {Array.from({ length: 4 }, (_, i) => (
            <Skeleton key={i} className="h-24" />
          ))}
        </div>
      ) : (
        <>
          <section className="grid grid-cols-2 gap-3 lg:grid-cols-4" aria-label="Ticket counts">
            <StatTile
              label="Open"
              value={stats.tickets.open}
              hint={`${stats.tickets.total} total${stats.tickets.overdue ? ` · ${stats.tickets.overdue} overdue` : ""}`}
            />
            <StatTile
              label="Escalated"
              value={stats.tickets.escalated}
              hint={`${percent(stats.escalation_rate)} escalated at some point`}
            />
            <StatTile label="Resolved" value={stats.tickets.resolved} />
            <StatTile
              label="Auto-routed"
              value={stats.tickets.auto_routed}
              hint={`of ${stats.tickets.analyzed} analyzed${
                stats.tickets.jev_failed ? ` · ${stats.tickets.jev_failed} Jev failed` : ""
              }`}
            />
          </section>

          <div className="grid gap-4 lg:grid-cols-5">
            <Card className="lg:col-span-3">
              <CardHeader>
                <CardTitle>Tickets by category</CardTitle>
                <CardDescription>Jev&apos;s recommended action, latest decision per ticket</CardDescription>
              </CardHeader>
              <CardContent>
                <BarList
                  label="Tickets by Jev category"
                  items={SUPPORT_ACTIONS.map((action) => {
                    const count = stats.by_category[action];
                    return {
                      label: ACTION_LABELS[action],
                      value: count,
                      display: String(count),
                      detail: `${percent(stats.tickets.analyzed ? count / stats.tickets.analyzed : null)} of analyzed`,
                    };
                  })}
                />
              </CardContent>
            </Card>

            <Card className="lg:col-span-2">
              <CardHeader>
                <CardTitle>Decision quality</CardTitle>
                <CardDescription>
                  Based on {stats.closed_out_with_decision} ticket{stats.closed_out_with_decision === 1 ? "" : "s"}{" "}
                  with a Jev decision and a final human action
                </CardDescription>
              </CardHeader>
              <CardContent>
                <dl className="grid grid-cols-2 gap-x-4 gap-y-4 text-sm">
                  <Metric label="Jev / human agreement" value={percent(stats.jev_human_agreement_rate, 1)} />
                  <Metric label="Human override rate" value={percent(stats.human_override_rate, 1)} />
                  <Metric label="Avg Jev confidence" value={percent(stats.average_jev_confidence)} />
                  <Metric label="Replies edited" value={percent(stats.reply_edit_rate)} />
                </dl>
              </CardContent>
            </Card>
          </div>
        </>
      )}

      <Card>
        <CardHeader>
          <CardTitle>Recent tickets</CardTitle>
          <CardDescription>
            <Link href="/dashboard/tickets" className="hover:underline">
              View all tickets →
            </Link>
          </CardDescription>
        </CardHeader>
        <CardContent>
          {recent.data ? <TicketsTable tickets={recent.data.items} /> : <Skeleton className="h-40" />}
        </CardContent>
      </Card>
    </div>
  );
}

function Metric({ label, value }: { label: string; value: string }) {
  return (
    <div>
      <dt className="text-muted-foreground">{label}</dt>
      <dd className="text-xl font-semibold tabular-nums">{value}</dd>
    </div>
  );
}
