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
  /** When a reply is due by the priority's response-time target; null once replied/closed. */
  response_due_at: string | null;
  overdue: boolean;
}

export interface TicketListItem extends Ticket {
  current_action: SupportAction | null;
}

export interface TicketList {
  items: TicketListItem[];
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
  /** 0 (low) .. 3 (urgent) */
  urgency_score: number | null;
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

export interface TicketEvent {
  id: number;
  event_type: string;
  data: Record<string, unknown>;
  actor: string | null;
  created_at: string;
}

export interface AnalyticsOverview {
  since_days: number | null;
  tickets: {
    total: number;
    open: number;
    escalated: number;
    resolved: number;
    jev_failed: number;
    overdue: number;
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

export interface RulesPolicy {
  min_confidence: number;
  refund_approval_limit: number;
  max_refunds_30_days: number;
  replacement_window_days: number;
  auto_replacement_limit: number;
  signal_threshold: number;
}

export type RuleOutcomeKind = "escalated" | "needs_approval" | "pre_approved";

export interface SimulatedOutcome {
  outcome: RuleOutcomeKind;
  permitted_action: SupportAction;
  rules: string[];
}

export interface SimulationResult {
  current_policy: RulesPolicy;
  proposed_policy: RulesPolicy;
  replayed: number;
  skipped: number;
  current: Record<RuleOutcomeKind, number>;
  proposed: Record<RuleOutcomeKind, number>;
  changed: {
    ticket_id: number;
    subject: string;
    recommended_action: SupportAction;
    current: SimulatedOutcome;
    proposed: SimulatedOutcome;
  }[];
}

export interface Calibration {
  min_confidence: number;
  buckets: {
    label: string;
    min: number;
    max: number;
    decisions: number;
    closed_out: number;
    agreement_rate: number | null;
  }[];
}
