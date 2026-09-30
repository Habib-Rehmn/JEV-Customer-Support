"use client";

import { useState } from "react";

import { NativeSelect } from "@/components/app/native-select";
import { Alert, AlertDescription } from "@/components/ui/alert";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardDescription, CardFooter, CardHeader, CardTitle } from "@/components/ui/card";
import { Label } from "@/components/ui/label";
import { Textarea } from "@/components/ui/textarea";
import { api } from "@/lib/api";
import { ACTION_LABELS, CLOSED_STATUSES, dateTime } from "@/lib/format";
import { SUPPORT_ACTIONS, type SupportAction, type TicketDetail } from "@/types/api";

type Mode = "reply" | "escalate" | "resolve";

export function ReplyPanel({ ticket, onChanged }: { ticket: TicketDetail; onChanged: () => void }) {
  const reply = ticket.latest_ai_response;
  const permitted = ticket.latest_jev_decision?.permitted_action ?? null;

  const [text, setText] = useState(reply && !reply.approved ? (reply.final_text ?? "") : "");
  const [savedText, setSavedText] = useState(text);
  const [action, setAction] = useState<SupportAction | "">(permitted ?? "");
  const [nextStatus, setNextStatus] = useState<"RESOLVED" | "WAITING_FOR_CUSTOMER">(
    permitted === "technical_support" || permitted === "human_escalation" ? "WAITING_FOR_CUSTOMER" : "RESOLVED",
  );
  const [mode, setMode] = useState<Mode>("reply");
  const [note, setNote] = useState("");
  const [busy, setBusy] = useState<string | null>(null);
  const [writingFollowUp, setWritingFollowUp] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const dirty = text !== savedText;
  const canEscalate = ticket.status !== "ESCALATED";

  async function run(label: string, fn: () => Promise<unknown>) {
    setBusy(label);
    setError(null);
    try {
      await fn();
      onChanged();
    } catch (err) {
      setError(err instanceof Error ? err.message : "Something went wrong");
    } finally {
      setBusy(null);
    }
  }

  const saveDraft = () =>
    run("save", async () => {
      await api.editResponse(ticket.id, text);
      setSavedText(text);
    });

  const regenerate = () => {
    if (dirty && !window.confirm("Replace your edits with a new AI draft?")) return;
    return run("regenerate", async () => {
      const fresh = await api.generateResponse(ticket.id);
      setText(fresh.final_text ?? "");
      setSavedText(fresh.final_text ?? "");
    });
  };

  const approve = () =>
    run("approve", () =>
      api.approve(ticket.id, {
        final_text: dirty ? text : undefined,
        action: action && action !== permitted ? action : undefined,
        next_status: nextStatus,
      }),
    );

  // Already answered: show what was sent. While the ticket is open, the agent can follow up or close it.
  if (reply?.approved && !writingFollowUp) {
    const open = !CLOSED_STATUSES.includes(ticket.status);
    const finalAction = ticket.final_action ?? permitted;
    return (
      <Card>
        <CardHeader>
          <CardTitle>Reply sent</CardTitle>
          <CardDescription>{reply.sent_at && dateTime(reply.sent_at)}</CardDescription>
        </CardHeader>
        <CardContent className="space-y-3">
          <p className="rounded-lg bg-muted p-4 text-sm whitespace-pre-wrap">{reply.final_text}</p>
          {error && (
            <Alert variant="destructive">
              <AlertDescription>{error}</AlertDescription>
            </Alert>
          )}
        </CardContent>
        {open && (
          <CardFooter className="flex flex-wrap gap-2 border-t pt-4">
            <Button variant="outline" onClick={() => setWritingFollowUp(true)} disabled={!!busy}>
              Write follow-up
            </Button>
            {finalAction && (
              <Button onClick={() => run("resolve", () => api.resolve(ticket.id, finalAction))} disabled={!!busy}>
                {busy === "resolve" ? "Resolving…" : "Mark resolved"}
              </Button>
            )}
          </CardFooter>
        )}
      </Card>
    );
  }

  return (
    <Card>
      <CardHeader>
        <CardTitle>{writingFollowUp ? "Follow-up" : "Reply"}</CardTitle>
        <CardDescription>
          {writingFollowUp
            ? "Write a follow-up to the customer."
            : reply?.generated_text
            ? `Drafted by ${reply.model}. Edit freely: only what you approve is sent.`
            : "No AI draft yet. Generate one or write the reply yourself."}
        </CardDescription>
      </CardHeader>
      <CardContent className="space-y-4">
        <Textarea
          value={text}
          onChange={(e) => setText(e.target.value)}
          rows={10}
          placeholder="Write the reply to the customer…"
          aria-label="Reply to the customer"
        />
        <div className="flex flex-wrap gap-2">
          <Button variant="outline" size="sm" onClick={saveDraft} disabled={!dirty || !text.trim() || !!busy}>
            {busy === "save" ? "Saving…" : dirty ? "Save draft" : "Draft saved"}
          </Button>
          <Button variant="outline" size="sm" onClick={regenerate} disabled={!permitted || !!busy}>
            {busy === "regenerate" ? "Generating…" : reply?.generated_text ? "Regenerate" : "Generate draft"}
          </Button>
        </div>

        {error && (
          <Alert variant="destructive">
            <AlertDescription>{error}</AlertDescription>
          </Alert>
        )}

        {mode === "reply" && (
          <div className="grid gap-3 rounded-lg border p-3 sm:grid-cols-2">
            <div className="space-y-1.5">
              <Label htmlFor="final-action">Final action</Label>
              <NativeSelect
                id="final-action"
                className="w-full"
                value={action}
                onChange={(e) => setAction(e.target.value as SupportAction)}
              >
                {!permitted && <option value="">Choose an action…</option>}
                {SUPPORT_ACTIONS.map((a) => (
                  <option key={a} value={a}>
                    {ACTION_LABELS[a]}
                    {a === permitted ? " (permitted)" : ""}
                  </option>
                ))}
              </NativeSelect>
            </div>
            <div className="space-y-1.5">
              <Label htmlFor="next-status">After sending</Label>
              <NativeSelect
                id="next-status"
                className="w-full"
                value={nextStatus}
                onChange={(e) => setNextStatus(e.target.value as typeof nextStatus)}
              >
                <option value="RESOLVED">Resolve ticket</option>
                <option value="WAITING_FOR_CUSTOMER">Wait for customer</option>
              </NativeSelect>
            </div>
            {permitted && action && action !== permitted && (
              <p className="text-xs text-muted-foreground sm:col-span-2">
                You&apos;re overriding the rules ({ACTION_LABELS[permitted]}). This is recorded.
              </p>
            )}
          </div>
        )}

        {mode !== "reply" && (
          <div className="space-y-3 rounded-lg border p-3">
            {mode === "resolve" && (
              <div className="space-y-1.5">
                <Label htmlFor="resolve-action">How was it handled?</Label>
                <NativeSelect
                  id="resolve-action"
                  className="w-full"
                  value={action}
                  onChange={(e) => setAction(e.target.value as SupportAction)}
                >
                  <option value="">Choose an action…</option>
                  {SUPPORT_ACTIONS.map((a) => (
                    <option key={a} value={a}>
                      {ACTION_LABELS[a]}
                    </option>
                  ))}
                </NativeSelect>
              </div>
            )}
            <div className="space-y-1.5">
              <Label htmlFor="note">{mode === "escalate" ? "Why escalate? (optional)" : "Note (optional)"}</Label>
              <Textarea id="note" rows={2} value={note} onChange={(e) => setNote(e.target.value)} />
            </div>
            <div className="flex gap-2">
              {mode === "escalate" ? (
                <Button
                  variant="destructive"
                  size="sm"
                  disabled={!!busy}
                  onClick={() => run("escalate", () => api.escalate(ticket.id, note || undefined))}
                >
                  {busy === "escalate" ? "Escalating…" : "Confirm escalation"}
                </Button>
              ) : (
                <Button
                  size="sm"
                  disabled={!action || !!busy}
                  onClick={() => run("resolve", () => api.resolve(ticket.id, action as SupportAction, note || undefined))}
                >
                  {busy === "resolve" ? "Resolving…" : "Resolve without sending"}
                </Button>
              )}
              <Button variant="ghost" size="sm" onClick={() => setMode("reply")}>
                Cancel
              </Button>
            </div>
          </div>
        )}
      </CardContent>

      {mode === "reply" && (
        <CardFooter className="flex flex-wrap gap-2 border-t pt-4">
          <Button onClick={approve} disabled={!text.trim() || !action || !!busy}>
            {busy === "approve" ? "Sending…" : "Approve & send"}
          </Button>
          {canEscalate && (
            <Button variant="outline" onClick={() => setMode("escalate")} disabled={!!busy}>
              Escalate
            </Button>
          )}
          <Button variant="ghost" onClick={() => setMode("resolve")} disabled={!!busy}>
            Resolve without reply
          </Button>
        </CardFooter>
      )}
    </Card>
  );
}
