// Mirrors the FastAPI schemas in backend/app/schemas.

export type TicketStatus =
  | "NEW"
  | "ANALYZING"
  | "JEV_FAILED"
  | "WAITING_FOR_AGENT"
  | "WAITING_FOR_CUSTOMER"
  | "ESCALATED"
  | "RESOLVED"
  | "CLOSED";

export type TicketPriority = "LOW" | "NORMAL" | "HIGH" | "URGENT";

export type SupportAction = "refund" | "replacement" | "technical_support" | "billing" | "human_escalation";

export const SUPPORT_ACTIONS: SupportAction[] = [
  "refund",
  "replacement",
  "technical_support",
  "billing",
  "human_escalation",
];

export interface User {
  id: number;
  name: string;
  email: string;
  role: "ADMIN" | "AGENT";
  created_at: string;
}

export interface TokenResponse {
  access_token: string;
  token_type: string;
  user: User;
}

export interface TicketCreate {
  customer_name: string;
  email: string;
  order_number: string | null;
  subject: string;
  message: string;
}

export interface Ticket {
  id: number;
  customer_id: number;
  order_id: number | null;
  subject: string;
  message: string;
  status: TicketStatus;
  priority: TicketPriority;
  final_action: SupportAction | null;
  created_at: string;
  updated_at: string;
  resolved_at: string | null;
}

export interface TicketList {
  items: Ticket[];
  total: number;
}

export interface Customer {
  id: number;
  name: string;
  email: string;
  created_at: string;
}

export interface Order {
  id: number;
  customer_id: number;
  order_number: string;
  total_amount: string;
  status: string;
  created_at: string;
  delivered_at: string | null;
}

export interface RuleHit {
  rule: string;
  reason: string;
}

export interface JevDecision {
  id: number;
  selected_action: SupportAction;
  confidence: number;
  refund_probability: number;
  replacement_probability: number;
  technical_support_probability: number;
  billing_probability: number;
  human_escalation_probability: number;
  billing_dispute_probability: number | null;
  item_damaged_probability: number | null;
  permitted_action: SupportAction | null;
  requires_approval: boolean | null;
  rule_hits: RuleHit[] | null;
  created_at: string;
}

export interface AIResponse {
  id: number;
  generated_text: string | null;
  final_text: string | null;
  model: string | null;
  approved: boolean;
  approved_by: number | null;
  created_at: string;
  sent_at: string | null;
}

export interface TicketDetail extends Ticket {
  customer: Customer;
  order: Order | null;
  latest_jev_decision: JevDecision | null;
  latest_ai_response: AIResponse | null;
}

export interface AnalyticsOverview {
  since_days: number | null;
  tickets: {
    total: number;
    open: number;
    escalated: number;
    resolved: number;
    jev_failed: number;
    analyzed: number;
    auto_routed: number;
  };
  escalation_rate: number | null;
  average_jev_confidence: number | null;
  by_category: Record<SupportAction, number>;
  closed_out_with_decision: number;
  human_override_rate: number | null;
  jev_human_agreement_rate: number | null;
  reply_edit_rate: number | null;
}
