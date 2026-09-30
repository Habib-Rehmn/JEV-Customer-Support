import { BarList } from "@/components/app/bar-list";
import { ActionBadge } from "@/components/app/badges";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Separator } from "@/components/ui/separator";
import { ACTION_LABELS, percent, ruleLabel } from "@/lib/format";
import { SUPPORT_ACTIONS, type JevDecision } from "@/types/api";

export function JevDecisionCard({ decision }: { decision: JevDecision }) {
  const probabilities = SUPPORT_ACTIONS.map((action) => ({
    action,
    value: decision[`${action}_probability`],
  })).sort((a, b) => b.value - a.value);

  const escalated = decision.permitted_action === "human_escalation";
  const overruled = decision.permitted_action !== null && decision.permitted_action !== decision.selected_action;

  return (
    <Card>
      <CardHeader>
        <CardTitle>Jev decision</CardTitle>
        <CardDescription>Probability of each action · confidence {percent(decision.confidence)}</CardDescription>
      </CardHeader>
      <CardContent className="space-y-5">
        <BarList
          label="Jev probability per action"
          emphasisMode
          max={1}
          items={probabilities.map(({ action, value }) => ({
            label: ACTION_LABELS[action],
            value,
            display: percent(value),
            emphasis: action === decision.selected_action,
          }))}
        />

        <Separator />

        <dl className="grid gap-3 text-sm sm:grid-cols-2">
          <div className="space-y-1">
            <dt className="text-muted-foreground">Jev recommends</dt>
            <dd>
              <ActionBadge action={decision.selected_action} />
            </dd>
          </div>
          <div className="space-y-1">
            <dt className="text-muted-foreground">Rules permit</dt>
            <dd className="flex flex-wrap items-center gap-2">
              <ActionBadge action={decision.permitted_action} />
              {overruled && <span className="text-xs text-muted-foreground">overruled by rules</span>}
            </dd>
          </div>
          <Signal label="Billing dispute signal" value={decision.billing_dispute_probability} />
          <Signal label="Item damaged signal" value={decision.item_damaged_probability} />
        </dl>

        {decision.rule_hits && decision.rule_hits.length > 0 && (
          <ul className="space-y-1.5 text-sm">
            {decision.rule_hits.map((hit) => (
              <li key={hit.rule} className="rounded-md bg-muted px-3 py-2">
                <span className="font-medium">{ruleLabel(hit.rule)}</span>
                <span className="text-muted-foreground"> · {hit.reason}</span>
              </li>
            ))}
          </ul>
        )}

        <p className="text-sm text-muted-foreground">
          {escalated
            ? "Escalated: handle this one personally. The draft below only tells the customer a specialist will reply."
            : decision.requires_approval
              ? "The rules require your explicit approval before this action goes out."
              : "Pre-approved by policy. Review the reply and send."}
        </p>
      </CardContent>
    </Card>
  );
}

function Signal({ label, value }: { label: string; value: number | null }) {
  return (
    <div className="space-y-1">
      <dt className="text-muted-foreground">{label}</dt>
      <dd className="tabular-nums">{percent(value)}</dd>
    </div>
  );
}
