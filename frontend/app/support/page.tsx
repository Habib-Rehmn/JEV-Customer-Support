"use client";

import Link from "next/link";
import { useState } from "react";

import { Logo } from "@/components/app/logo";
import { ThemeToggle } from "@/components/app/theme-toggle";
import { Alert, AlertDescription, AlertTitle } from "@/components/ui/alert";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Textarea } from "@/components/ui/textarea";
import { api } from "@/lib/api";

export default function SupportPage() {
  const [submitting, setSubmitting] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [ticketId, setTicketId] = useState<number | null>(null);

  async function onSubmit(event: React.FormEvent<HTMLFormElement>) {
    event.preventDefault();
    const form = new FormData(event.currentTarget);
    const text = (name: string) => String(form.get(name) ?? "").trim();

    setSubmitting(true);
    setError(null);
    try {
      const ticket = await api.createTicket({
        customer_name: text("customer_name"),
        email: text("email"),
        order_number: text("order_number") || null,
        subject: text("subject"),
        message: text("message"),
      });
      setTicketId(ticket.id);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Something went wrong");
    } finally {
      setSubmitting(false);
    }
  }

  return (
    <main className="mx-auto w-full max-w-xl flex-1 px-4 py-12">
      <ThemeToggle className="fixed top-3 right-3" />
      <Link href="/" className="self-start hover:opacity-80">
        <Logo />
      </Link>
      <Card className="mt-4">
        <CardHeader>
          <CardTitle>Contact support</CardTitle>
          <CardDescription>Tell us what happened and we&apos;ll get back to you by email.</CardDescription>
        </CardHeader>
        <CardContent>
          {ticketId ? (
            <Alert>
              <AlertTitle>Request received: ticket #{ticketId}</AlertTitle>
              <AlertDescription className="space-y-3">
                <p>Our team is on it. We&apos;ll email you a reply, usually within one business day.</p>
                <Button variant="outline" size="sm" onClick={() => setTicketId(null)}>
                  Submit another request
                </Button>
              </AlertDescription>
            </Alert>
          ) : (
            <form onSubmit={onSubmit} className="space-y-4">
              <div className="grid gap-4 sm:grid-cols-2">
                <Field label="Your name" name="customer_name" required autoComplete="name" />
                <Field label="Email" name="email" type="email" required autoComplete="email" />
              </div>
              <Field label="Order number (optional)" name="order_number" placeholder="ORD-10342" />
              <Field label="Subject" name="subject" required maxLength={300} />
              <div className="space-y-2">
                <Label htmlFor="message">Message</Label>
                <Textarea id="message" name="message" required rows={6} maxLength={10000} />
              </div>
              {error && (
                <Alert variant="destructive">
                  <AlertDescription>{error}</AlertDescription>
                </Alert>
              )}
              <Button type="submit" size="lg" disabled={submitting} className="w-full">
                {submitting ? "Sending…" : "Send request"}
              </Button>
            </form>
          )}
        </CardContent>
      </Card>
    </main>
  );
}

function Field({ label, name, ...props }: { label: string; name: string } & React.ComponentProps<"input">) {
  return (
    <div className="space-y-2">
      <Label htmlFor={name}>{label}</Label>
      <Input id={name} name={name} {...props} />
    </div>
  );
}
