import { useEffect, useState } from "react";
import { analyzeRisk, API_BASE_URL, createRazorpayOrder, getHealth, getIntegrationStatus, getRecentAudit, type RiskPayload } from "@/lib/riskpilotApi";

const initialPayload: RiskPayload = {
  amount: 84999, customer_id: "CUS_1029", device_id: "DEV_8821", location: "Mumbai",
  velocity: 8, failed_attempts: 3, account_age_days: 2, merchant_id: "MERCH_NOVA",
  merchant_risk_score: 65, behavioral_deviation: 0.82,
};

function JsonPanel({ value }: { value: unknown }) {
  return <pre className="max-h-[430px] overflow-auto rounded-lg bg-[#18252b] p-4 text-xs leading-6 text-[#d7f3ed]">{JSON.stringify(value, null, 2)}</pre>;
}

export function LiveApiPage() {
  const [payload, setPayload] = useState<RiskPayload>(initialPayload);
  const [result, setResult] = useState<unknown>({ status: "Waiting for an API call" });
  const [statusLabel, setStatusLabel] = useState("Checking backend…");
  const [busy, setBusy] = useState(false);

  const run = async (label: string, action: () => Promise<unknown>) => {
    setBusy(true); setStatusLabel(label + "…");
    try { setResult(await action()); setStatusLabel(label + " succeeded"); }
    catch (error) { setResult({ error: error instanceof Error ? error.message : "Unknown API error" }); setStatusLabel(label + " failed"); }
    finally { setBusy(false); }
  };

  useEffect(() => {
    void run("Health check", async () => {
      const [health, integrations] = await Promise.all([getHealth(), getIntegrationStatus()]);
      return { health, integrations };
    });
  }, []);

  const updateNumber = (key: keyof RiskPayload, value: string) => setPayload((current) => ({ ...current, [key]: Number(value) }));
  const fields = [
    ["amount", "Amount (INR)"], ["customer_id", "Customer ID"], ["device_id", "Device ID"], ["location", "Location"],
    ["velocity", "Velocity / hour"], ["failed_attempts", "Failed attempts"], ["account_age_days", "Account age (days)"],
    ["merchant_id", "Merchant ID"], ["merchant_risk_score", "Merchant risk (0–100)"], ["behavioral_deviation", "Behavior deviation (0–1)"],
  ] as const;

  return <div className="min-h-screen bg-[#f5f5ee] px-4 py-8 text-[#26343b] sm:px-8 lg:px-16"><div className="mx-auto max-w-7xl">
    <div className="mb-8 flex flex-col justify-between gap-4 md:flex-row md:items-end"><div><p className="rp-eyebrow text-[#0e897d]">RiskPilot live integration lab</p><h1 className="mt-2 max-w-3xl text-4xl font-semibold tracking-[-.04em] text-[#1d2b31]">Real responses, not screenshots.</h1><p className="mt-3 max-w-2xl text-sm leading-6 text-[#647278]">Exercise the FastAPI risk engine, Razorpay test-mode order gate, audit trail, and integration health from one reviewer-friendly screen.</p></div><div className="rounded-lg border border-[#cbd8d3] bg-[#edf8f4] px-4 py-3 text-xs text-[#27665d]"><span className="font-semibold">API base</span><br />{API_BASE_URL}</div></div>
    <div className="grid gap-6 lg:grid-cols-[minmax(0,1fr)_minmax(0,1fr)]">
      <section className="rp-surface rounded-xl p-5"><div className="mb-5 flex items-center justify-between"><div><p className="rp-eyebrow text-[#748187]">Transaction payload</p><h2 className="mt-1 text-lg font-semibold">Risk decision input</h2></div><span className="rounded-full bg-[#edf8f4] px-3 py-1 text-[11px] font-semibold text-[#0e897d]">{statusLabel}</span></div>
        <div className="grid gap-3 sm:grid-cols-2">{fields.map(([key, label]) => <label key={key} className="text-xs font-semibold text-[#58676d]">{label}<input className="rp-input mt-1 h-10 w-full rounded-md px-3 text-sm font-normal" type={typeof payload[key] === "number" ? "number" : "text"} step={key === "behavioral_deviation" ? "0.01" : "1"} value={payload[key]} onChange={(event) => typeof payload[key] === "number" ? updateNumber(key, event.target.value) : setPayload((current) => ({ ...current, [key]: event.target.value }))} /></label>)}</div>
        <div className="mt-5 flex flex-wrap gap-2"><button disabled={busy} onClick={() => void run("Risk analysis", () => analyzeRisk(payload))} className="rp-button rp-button-ink rounded-lg px-4 py-2.5 text-xs font-semibold disabled:opacity-50">Analyze transaction</button><button disabled={busy} onClick={() => void run("Razorpay order", () => createRazorpayOrder({ ...payload, currency: "INR", notes: { source: "riskpilot-live-lab" } }))} className="rp-button rounded-lg border border-[#cbd2ce] bg-white px-4 py-2.5 text-xs font-semibold disabled:opacity-50">Create test order</button></div>
      </section>
      <section className="rp-surface rounded-xl p-5"><div className="mb-4 flex items-center justify-between"><div><p className="rp-eyebrow text-[#748187]">Verified response</p><h2 className="mt-1 text-lg font-semibold">API output</h2></div><button disabled={busy} onClick={() => void run("Audit fetch", getRecentAudit)} className="text-xs font-semibold text-[#0e897d] disabled:opacity-50">Load audit</button></div><JsonPanel value={result} /><div className="mt-4 grid grid-cols-2 gap-3 text-xs"><div className="rounded-lg bg-[#f4f5ef] p-3"><div className="text-[#849095]">Risk gate</div><div className="mt-1 font-semibold">approve · review · block</div></div><div className="rounded-lg bg-[#f4f5ef] p-3"><div className="text-[#849095]">Webhook</div><div className="mt-1 font-semibold">HMAC signature checked</div></div></div></section>
    </div>
    <div className="mt-6 rounded-xl border border-[#d7ddd5] bg-[#fffef9] p-5 text-sm leading-6 text-[#5e6b70]"><strong className="text-[#26343b]">Reviewer path:</strong> run “Analyze transaction,” then “Create test order,” then “Load audit.” With Razorpay test keys configured, the order is created remotely; without them, the response explicitly identifies the deterministic simulation instead of hiding it.</div>
  </div></div>;
}
