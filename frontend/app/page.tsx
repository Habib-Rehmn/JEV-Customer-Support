import Link from "next/link";

import { buttonVariants } from "@/components/ui/button";
import { cn } from "@/lib/utils";

const STEPS = [
  ["Jev decides", "Classifies each request as refund, replacement, technical support, billing or escalation."],
  ["Rules permit", "Deterministic business rules decide what is actually allowed."],
  ["OpenAI writes", "Drafts a reply that only states what was approved."],
  ["Agents approve", "A person reviews, edits and sends every reply."],
];

export default function Home() {
  return (
    <main className="mx-auto flex w-full max-w-3xl flex-1 flex-col justify-center gap-10 px-4 py-16">
      <div className="space-y-4">
        <h1 className="text-4xl font-semibold tracking-tight">Jev Support</h1>
        <p className="text-lg text-muted-foreground">
          Customer support where AI does the routing and drafting, and people stay in control.
        </p>
        <div className="flex flex-wrap gap-3">
          <Link href="/support" className={cn(buttonVariants({ size: "lg" }))}>
            Contact support
          </Link>
          <Link href="/login" className={cn(buttonVariants({ variant: "outline", size: "lg" }))}>
            Agent login
          </Link>
        </div>
      </div>
      <ol className="grid gap-4 sm:grid-cols-2">
        {STEPS.map(([title, text], i) => (
          <li key={title} className="rounded-xl border p-4">
            <p className="text-sm text-muted-foreground">Step {i + 1}</p>
            <p className="font-medium">{title}</p>
            <p className="text-sm text-muted-foreground">{text}</p>
          </li>
        ))}
      </ol>
    </main>
  );
}
