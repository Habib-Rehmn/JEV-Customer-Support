import type {
  AIResponse,
  AnalyticsOverview,
  SupportAction,
  Ticket,
  TicketCreate,
  TicketDetail,
  TicketList,
  TicketStatus,
  TokenResponse,
  User,
} from "@/types/api";

const API_URL = process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000/api/v1";
const TOKEN_KEY = "jev_token";

export class ApiError extends Error {
  constructor(
    public status: number,
    message: string,
  ) {
    super(message);
  }
}

export function getToken(): string | null {
  try {
    return localStorage.getItem(TOKEN_KEY);
  } catch {
    return null;
  }
}

export function setToken(token: string | null) {
  try {
    if (token) localStorage.setItem(TOKEN_KEY, token);
    else localStorage.removeItem(TOKEN_KEY);
  } catch {
    // Storage unavailable (e.g. private mode): the session just won't persist.
  }
}

// Called when the API rejects the token, so the app can send the agent back to /login.
let onUnauthorized: (() => void) | null = null;
export function setUnauthorizedHandler(handler: (() => void) | null) {
  onUnauthorized = handler;
}

async function request<T>(path: string, init: RequestInit = {}): Promise<T> {
  const token = getToken();
  const headers = new Headers(init.headers);
  if (init.body) headers.set("Content-Type", "application/json");
  if (token) headers.set("Authorization", `Bearer ${token}`);

  let res: Response;
  try {
    res = await fetch(`${API_URL}${path}`, { ...init, headers });
  } catch {
    throw new ApiError(0, "Cannot reach the server. Is the backend running?");
  }

  if (res.status === 401 && token) onUnauthorized?.();
  if (!res.ok) throw new ApiError(res.status, await errorMessage(res));
  return (await res.json()) as T;
}

async function errorMessage(res: Response): Promise<string> {
  try {
    const body = await res.json();
    if (typeof body.detail === "string") return body.detail;
    if (Array.isArray(body.detail)) {
      // FastAPI validation errors: [{loc: [..., "field"], msg}]
      return body.detail.map((e: { loc: string[]; msg: string }) => `${e.loc.at(-1)}: ${e.msg}`).join("; ");
    }
  } catch {
    // fall through
  }
  return `Request failed (HTTP ${res.status})`;
}

const post = <T>(path: string, body: unknown = {}) => request<T>(path, { method: "POST", body: JSON.stringify(body) });

export const api = {
  login: (email: string, password: string) => post<TokenResponse>("/auth/login", { email, password }),
  me: () => request<User>("/auth/me"),
  listUsers: () => request<User[]>("/users"),
  createUser: (data: { name: string; email: string; password: string; role: User["role"] }) =>
    post<User>("/users", data),
  updateUser: (id: number, data: { name?: string; role?: User["role"]; password?: string }) =>
    request<User>(`/users/${id}`, { method: "PATCH", body: JSON.stringify(data) }),

  createTicket: (data: TicketCreate) => post<Ticket>("/tickets", data),
  listTickets: (params: { status?: TicketStatus; q?: string; limit?: number; offset?: number } = {}) => {
    const query = new URLSearchParams();
    for (const [key, value] of Object.entries(params)) if (value !== undefined && value !== "") query.set(key, String(value));
    return request<TicketList>(`/tickets?${query}`);
  },
  getTicket: (id: number) => request<TicketDetail>(`/tickets/${id}`),
  analyze: (id: number) => post<Ticket>(`/tickets/${id}/analyze`),
  generateResponse: (id: number) => post<AIResponse>(`/tickets/${id}/generate-response`),
  editResponse: (id: number, final_text: string) =>
    request<AIResponse>(`/tickets/${id}/response`, { method: "PUT", body: JSON.stringify({ final_text }) }),
  approve: (
    id: number,
    body: { final_text?: string; action?: SupportAction; next_status?: "RESOLVED" | "WAITING_FOR_CUSTOMER" },
  ) => post<Ticket>(`/tickets/${id}/approve`, body),
  escalate: (id: number, reason?: string) => post<Ticket>(`/tickets/${id}/escalate`, { reason }),
  resolve: (id: number, final_action: SupportAction, note?: string) =>
    post<Ticket>(`/tickets/${id}/resolve`, { final_action, note }),

  analytics: (since_days?: number) =>
    request<AnalyticsOverview>(`/analytics/overview${since_days ? `?since_days=${since_days}` : ""}`),
};
