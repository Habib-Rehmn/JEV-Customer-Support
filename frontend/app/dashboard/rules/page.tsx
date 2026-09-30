"use client";

import Link from "next/link";
import { useState } from "react";

import { ActionBadge } from "@/components/app/badges";
import { BarList } from "@/components/app/bar-list";
import { StatTile } from "@/components/app/stat-tile";
import { Alert, AlertDescription } from "@/components/ui/alert";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Skeleton } from "@/components/ui/skeleton";
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from "@/components/ui/table";
import { api } from "@/lib/api";
import { useAuth } from "@/lib/auth";
import { percent, ruleLabel } from "@/lib/format";
import { useApi } from "@/lib/use-api";
import { cn } from "@/lib/utils";
import type { RuleOutcomeKind, RulesPolicy, SimulatedOutcome, SimulationResult } from "@/types/api";

const FIELDS: { key: keyof RulesPolicy; label: string; hint: string; step: number; min: number; max?: number }[] = [
  { key: "min_confidence", label: "Minimum Jev confidence", hint: "Below this, escalate", step: 0.01, min: 0, max: 1 },
  { key: "signal_threshold", label: "Signal threshold", hint: "Billing dispute / item damaged", step: 0.05, min: 0, max: 1 },
  { key: "refund_approval_limit", label: "Large refund above ($)", hint: "Flagged for approval", step: 10, min: 0 },
  { key: "auto_replacement_limit", label: "Pre-approve replacements under ($)", hint: "When the item arrived damaged", step: 10, min: 0 },
  { key: "replacement_window_days", label: "Replacement window (days)", hint: "After delivery", step: 1, min: 0 },
  { key: "max_refunds_30_days", label: "Refunds in 30 days before escalating", hint: "Abuse check", step: 1, min: 1 },
];

const OUTCOME_LABELS: Record<RuleOutcomeKind, string> = {
  escalated: "Escalated",
  needs_approval: "Needs approval",
  pre_approved: "Pre-approved",
};

export default function RulesPage() {
  const { user } = useAuth();
  const current = useApi(() => api.rulesPolicy(), "rules-policy");
  const calibration = useApi(() => api.calibration(), "calibration");

  if (user?.role !== "ADMIN") {
    return (
      <Alert>
        <AlertDescription>Only admins can use the rules lab.</AlertDescription>
      </Alert>
    );
  }

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-2xl font-semibold">Rules lab</h1>
        <p className="text-sm text-muted-foreground">
          Try different thresholds against real past tickets before changing anything, and check whether Jev&apos;s
          confidence can be trusted.
        </p>
      </div>

      {current.data ? <Simulator current={current.data} /> : <Skeleton className="h-72" />}

      <Card>
        <CardHeader>
          <CardTitle>Is Jev&apos;s confidence meaningful?</CardTitle>
          <CardDescription>
            Latest decision per ticket. If humans agree just as often at 0.75 as at 0.99, the confidence threshold
            isn&apos;t separating good decisions from bad ones.
          </CardDescription>
        </CardHeader>
        <CardContent>
          {calibration.data ? (
            <div className="grid gap-8 lg:grid-cols-2">
              <div className="space-y-3">
                <p className="text-sm font-medium">How confident Jev is</p>
                <BarList
                  label="Jev decisions by confidence"
                  items={calibration.data.buckets.map((b) => ({
                    label: b.label,
                    value: b.decisions,
                    display: String(b.decisions),
                    detail: b.max <= calibration.data!.min_confidence ? "below the escalation threshold" : undefined,
                  }))}
                />
              </div>
              <div className="space-y-3">
                <p className="text-sm font-medium">How often humans agreed</p>
                <BarList
                  label="Human agreement with Jev by confidence"
                  max={1}
                  items={calibration.data.buckets.map((b) => ({
                    label: b.label,
                    value: b.agreement_rate ?? 0,
                    display: b.agreement_rate === null ? "–" : percent(b.agreement_rate),
                    detail: `${b.closed_out} closed ticket${b.closed_out === 1 ? "" : "s"}`,
                  }))}
                />
                <p className="text-xs text-muted-foreground">
                  Agreement = the final action matched Jev&apos;s recommendation. “–” means no closed tickets yet.
                </p>
              </div>
            </div>
          ) : (
            <Skeleton className="h-48" />
          )}
        </CardContent>
      </Card>
    </div>
  );
}

function Simulator({ current }: { current: RulesPolicy }) {
  const [draft, setDraft] = useState<RulesPolicy>(current);
  const [result, setResult] = useState<SimulationResult | null>(null);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const changedFields = FIELDS.filter((f) => draft[f.key] !== current[f.key]);

  async function run(event: React.FormEvent) {
    event.preventDefault();
    setBusy(true);
    setError(null);
    try {
      setResult(await api.simulateRules(draft));
    } catch (err) {
      setError(err instanceof Error ? err.message : "Simulation failed");
    } finally {
      setBusy(false);
    }
  }

  return (
    <div className="grid gap-6 lg:grid-cols-3">
      <Card>
        <CardHeader>
          <CardTitle>Thresholds</CardTitle>
          <CardDescription>Change values, then simulate. This does not change the live rules.</CardDescription>
        </CardHeader>
        <CardContent>
          <form onSubmit={run} className="space-y-3">
            {FIELDS.map((f) => (
              <div key={f.key} className="space-y-1">
                <Label htmlFor={f.key} className="flex justify-between gap-2">
                  <span>{f.label}</span>
                  {draft[f.key] !== current[f.key] && (
                    <span className="text-xs font-normal text-muted-foreground">now {current[f.key]}</span>
                  )}
                </Label>
                <Input
                  id={f.key}
                  type="number"
                  step={f.step}
                  min={f.min}
                  max={f.max}
                  required
                  value={draft[f.key]}
                  onChange={(e) => setDraft({ ...draft, [f.key]: e.target.valueAsNumber })}
                  className={cn(draft[f.key] !== current[f.key] && "border-viz-accent")}
                />
                <p className="text-xs text-muted-foreground">{f.hint}</p>
              </div>
            ))}
            {error && (
              <Alert variant="destructive">
                <AlertDescription>{error}</AlertDescription>
              </Alert>
            )}
            <div className="flex gap-2 pt-1">
              <Button type="submit" disabled={busy}>
                {busy ? "Simulating…" : "Simulate"}
              </Button>
              <Button
                type="button"
                variant="ghost"
                disabled={changedFields.length === 0}
                onClick={() => {
                  setDraft(current);
                  setResult(null);
                }}
              >
                Reset
              </Button>
            </div>
          </form>
        </CardContent>
      </Card>

      <div className="space-y-6 lg:col-span-2">
        {!result ? (
          <Card>
            <CardContent className="py-10 text-center text-sm text-muted-foreground">
              Every analyzed ticket is replayed with the answer Jev gave and the exact context it saw. No API calls are
              made.
            </CardContent>
          </Card>
        ) : (
          <SimulationResults result={result} />
        )}
      </div>
    </div>
  );
}

function SimulationResults({ result }: { result: SimulationResult }) {
  const delta = (kind: RuleOutcomeKind) => {
    const d = result.proposed[kind] - result.current[kind];
    return d === 0 ? "no change" : `${d > 0 ? "+" : ""}${d} vs now (${result.current[kind]})`;
  };

  return (
    <>
      <div className="grid grid-cols-3 gap-3">
        {(Object.keys(OUTCOME_LABELS) as RuleOutcomeKind[]).map((kind) => (
          <StatTile key={kind} label={OUTCOME_LABELS[kind]} value={result.proposed[kind]} hint={delta(kind)} />
        ))}
      </div>

      <Card>
        <CardHeader>
          <CardTitle>
            {result.changed.length} of {result.replayed} ticket{result.replayed === 1 ? "" : "s"} would change
          </CardTitle>
          <CardDescription>
            {result.skipped > 0 && `${result.skipped} analyzed ticket(s) had no stored context and were skipped. `}
            To apply new values, set the matching <code>RULE_*</code> variables in <code>.env</code> and restart the
            backend.
          </CardDescription>
        </CardHeader>
        <CardContent>
          {result.changed.length === 0 ? (
            <p className="py-6 text-center text-sm text-muted-foreground">No outcomes change with these thresholds.</p>
          ) : (
            <Table>
              <TableHeader>
                <TableRow>
                  <TableHead>Ticket</TableHead>
                  <TableHead>Jev</TableHead>
                  <TableHead>Now</TableHead>
                  <TableHead>With these thresholds</TableHead>
                </TableRow>
              </TableHeader>
              <TableBody>
                {result.changed.map((c) => (
                  <TableRow key={c.ticket_id}>
                    <TableCell className="max-w-56">
                      <Link href={`/dashboard/tickets/${c.ticket_id}`} className="block truncate hover:underline">
                        <span className="text-muted-foreground">#{c.ticket_id}</span> {c.subject}
                      </Link>
                    </TableCell>
                    <TableCell>
                      <ActionBadge action={c.recommended_action} />
                    </TableCell>
                    <TableCell>
                      <Outcome outcome={c.current} />
                    </TableCell>
                    <TableCell>
                      <Outcome outcome={c.proposed} />
                    </TableCell>
                  </TableRow>
                ))}
              </TableBody>
            </Table>
          )}
        </CardContent>
      </Card>
    </>
  );
}

const OUTCOME_STYLES: Record<RuleOutcomeKind, string> = {
  escalated: "bg-orange-100 text-orange-900 dark:bg-orange-950 dark:text-orange-300",
  needs_approval: "bg-amber-100 text-amber-900 dark:bg-amber-950 dark:text-amber-300",
  pre_approved: "bg-emerald-100 text-emerald-800 dark:bg-emerald-950 dark:text-emerald-300",
};

function Outcome({ outcome }: { outcome: SimulatedOutcome }) {
  return (
    <div className="space-y-1">
      <div className="flex flex-wrap items-center gap-1.5">
        <Badge variant="secondary" className={cn("border-0", OUTCOME_STYLES[outcome.outcome])}>
          {OUTCOME_LABELS[outcome.outcome]}
        </Badge>
        {outcome.outcome !== "escalated" && <ActionBadge action={outcome.permitted_action} />}
      </div>
      {outcome.rules.length > 0 && (
        <p className="text-xs text-muted-foreground">{outcome.rules.map(ruleLabel).join(", ")}</p>
      )}
    </div>
  );
}
