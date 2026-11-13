import type { AnswerValue, Condition, EgressEntry, Form, MatchResult, MemberSummary, Mode, SessionState } from "./types";

export const API_URL = process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000";

export class ApiError extends Error {
  constructor(
    readonly status: number,
    message: string,
  ) {
    super(message);
  }
}

const RETRIES = 2;

/**
 * Every write carries an idempotency key, so a request that failed in transit (or whose reply was lost)
 * is safe to send again: the server returns the stored result instead of acting twice.
 */
async function request<T>(path: string, init?: RequestInit): Promise<T> {
  let lastError: unknown;
  for (let attempt = 0; attempt <= RETRIES; attempt++) {
    try {
      const response = await fetch(`${API_URL}${path}`, {
        ...init,
        headers: { "Content-Type": "application/json", ...init?.headers },
      });
      if (response.ok) return (await response.json()) as T;
      const body = (await response.json().catch(() => ({}))) as { detail?: unknown };
      const message = typeof body.detail === "string" ? body.detail : `Request failed (${response.status})`;
      if (response.status < 500 && response.status !== 409) throw new ApiError(response.status, message);
      lastError = new ApiError(response.status, message);
    } catch (error) {
      if (error instanceof ApiError && error.status < 500 && error.status !== 409) throw error;
      lastError = error;
    }
    await new Promise((resolve) => setTimeout(resolve, 300 * 2 ** attempt));
  }
  throw lastError instanceof Error ? lastError : new Error("Network error");
}

export function newKey(): string {
  return crypto.randomUUID();
}

export const api = {
  members: () => request<MemberSummary[]>("/members"),
  form: (mode: Mode) => request<Form>(`/form?mode=${mode}`),
  conditions: () => request<{ conditions: Condition[] }>("/catalog/conditions").then((c) => c.conditions),
  createSession: (memberId: string, mode: Mode, clientKey: string) =>
    request<SessionState>("/sessions", {
      method: "POST",
      body: JSON.stringify({ member_id: memberId, mode, client_key: clientKey }),
    }),
  session: (id: string) => request<SessionState>(`/sessions/${id}`),
  egress: (id: string) => request<EgressEntry[]>(`/sessions/${id}/egress`),
  matchCondition: (id: string, text: string, key: string) =>
    request<MatchResult>(`/sessions/${id}/conditions/match`, {
      method: "POST",
      body: JSON.stringify({ text, request_key: key }),
    }),
  matchOption: (id: string, screenId: string, text: string, key: string) =>
    request<MatchResult>(`/sessions/${id}/screens/${screenId}/match`, {
      method: "POST",
      body: JSON.stringify({ text, request_key: key }),
    }),
  answer: (id: string, screenId: string, value: AnswerValue, key: string, taps: number) =>
    request<SessionState>(`/sessions/${id}/answers`, {
      method: "POST",
      body: JSON.stringify({ screen_id: screenId, value, idempotency_key: key, taps }),
    }),
};
