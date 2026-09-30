import type { SupportAction, TicketStatus } from "@/types/api";

export const ACTION_LABELS: Record<SupportAction, string> = {
  refund: "Refund",
  replacement: "Replacement",
  technical_support: "Tech support",
  billing: "Billing",
  human_escalation: "Human escalation",
};

export const STATUS_LABELS: Record<TicketStatus, string> = {
  NEW: "New",
  ANALYZING: "Analyzing",
  JEV_FAILED: "Jev failed",
  WAITING_FOR_AGENT: "Waiting for agent",
  WAITING_FOR_CUSTOMER: "Waiting for customer",
  ESCALATED: "Escalated",
  RESOLVED: "Resolved",
  CLOSED: "Closed",
};

export const CLOSED_STATUSES: TicketStatus[] = ["RESOLVED", "CLOSED"];

export function percent(value: number | null | undefined, digits = 0): string {
  return value === null || value === undefined ? "–" : `${(value * 100).toFixed(digits)}%`;
}

export function money(value: string | number): string {
  return Number(value).toLocaleString(undefined, { style: "currency", currency: "USD" });
}

export function dateTime(value: string): string {
  return new Date(value).toLocaleString(undefined, { dateStyle: "medium", timeStyle: "short" });
}

export function timeAgo(value: string): string {
  const seconds = Math.round((Date.now() - new Date(value).getTime()) / 1000);
  if (seconds < 60) return "just now";
  const units: [number, string][] = [
    [60 * 60 * 24, "d"],
    [60 * 60, "h"],
    [60, "m"],
  ];
  for (const [size, unit] of units) if (seconds >= size) return `${Math.floor(seconds / size)}${unit} ago`;
  return "just now";
}

/** Rule ids from the backend (e.g. "billing_dispute") as readable text. */
export function ruleLabel(rule: string): string {
  return rule.replaceAll("_", " ").replace(/^./, (c) => c.toUpperCase());
}
