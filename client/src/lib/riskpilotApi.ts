export type RiskPayload = {
  amount: number;
  customer_id: string;
  device_id: string;
  location: string;
  velocity: number;
  failed_attempts: number;
  account_age_days: number;
  merchant_id: string;
  merchant_risk_score: number;
  behavioral_deviation: number;
  transaction_id?: string;
};

const configuredBase = (import.meta.env.VITE_API_BASE_URL as string | undefined)?.trim();
const defaultBase = typeof window !== "undefined" && window.location.hostname !== "localhost" && window.location.hostname !== "127.0.0.1"
  ? "/api"
  : "http://localhost:8000";
export const API_BASE_URL = (configuredBase || defaultBase).replace(/\/$/, "");

async function request<T>(path: string, init?: RequestInit): Promise<T> {
  const response = await fetch(API_BASE_URL + path, {
    ...init,
    headers: { "Content-Type": "application/json", ...(init?.headers || {}) },
  });
  const raw = await response.text();
  let body: unknown = {};
  try { body = raw ? JSON.parse(raw) : {}; } catch { body = { detail: raw }; }
  if (!response.ok) {
    const message = typeof body === "object" && body !== null && "detail" in body
      ? String((body as { detail: unknown }).detail)
      : "RiskPilot API request failed (" + response.status + ")";
    throw new Error(message);
  }
  return body as T;
}

export function getHealth() { return request<Record<string, unknown>>("/v1/health"); }
export function getIntegrationStatus() { return request<Record<string, unknown>>("/v1/integrations/status"); }
export function analyzeRisk(payload: RiskPayload) {
  return request<Record<string, unknown>>("/v1/risk/analyze", { method: "POST", body: JSON.stringify(payload) });
}
export function explainInvestigation(payload: RiskPayload) {
  return request<Record<string, unknown>>("/v1/investigations/explain", { method: "POST", body: JSON.stringify({ context: payload }) });
}

export function createRazorpayOrder(payload: RiskPayload & { currency: string; notes?: Record<string, string> }) {
  return request<Record<string, unknown>>("/v1/razorpay/create-payment", { method: "POST", body: JSON.stringify(payload) });
}
export function getRecentAudit() { return request<Record<string, unknown>>("/v1/audit/recent?limit=10"); }
