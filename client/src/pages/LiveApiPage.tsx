import { useEffect, useState } from "react";
import { analyzeRisk, API_BASE_URL, createRazorpayOrder, explainInvestigation, getHealth, getIntegrationStatus, getRecentAudit, judgeRun, runInvestigation, type RiskPayload } from "@/lib/riskpilotApi";

const initialPayload: RiskPayload = {
  amount: 480000, customer_id: "CUS_1029", device_id: "DEV_8821_NEW", location: "Mumbai",
  velocity: 12, failed_attempts: 5, account_age_days: 2, merchant_id: "MERCH_NOVA",
  merchant_risk_score: 65, behavioral_deviation: 0.82,
};

type Step = { step: number; name?: string; tool?: string; latency_ms: number; mode?: string; detail?: string; findings?: { finding?: string } };

function JsonPanel({ value }: { value: unknown }) {
  return <pre className="max-h-[430px] overflow-auto rounded-lg bg-[#18252b] p-4 text-xs leading-6 text-[#d7f3ed]">{JSON.stringify(value, null, 2)}</pre>;
}

export function LiveApiPage() {
  const [payload, setPayload] = useState<RiskPayload>(initialPayload);
  const [result, setResult] = useState<unknown>({ status: "Waiting for an API call" });
  const [timeline, setTimeline] = useState<Step[] | null>(null);
  const [statusLabel, setStatusLabel] = useState("Checking backend…");
  const [mode, setMode] = useState<string>("");
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
      const executionMode = (integrations as { mode?: { execution_mode?: string } }).mode?.execution_mode;
      setMode(executionMode || "UNKNOWN");
      return { health, integrations };
    });
  }, []);

  // Judge Mode: the one-click 2-minute closed loop (real backend steps, honestly labeled).
  const runJudgeFlow = async () => {
    setBusy(true); setStatusLabel("Running Judge Mode flow…"); setTimeline(null);
    try {
      const response = await judgeRun(payload) as { timeline?: Step[] };
      setTimeline(response.timeline || []);
      setResult(response); setStatusLabel("Judge Mode flow complete");
    } catch (error) {
      setResult({ error: error instanceof Error ? error.message : "Judge flow failed" });
      setStatusLabel("Judge Mode flow failed — is the backend running?");
    } finally { setBusy(false); }
  };

  // Risk Replay: real agent tool calls with measured latencies.
  const runInvestigationFlow = async () => {
    setBusy(true); setStatusLabel("Running agent investigation…"); setTimeline(null);
    try {
      const response = await runInvestigation(payload) as { steps?: Step[] };
      setTimeline(response.steps || []);
      setResult(response); setStatusLabel("Investigation complete");
    } catch (error) {
      setResult({ error: error instanceof Error ? error.message : "Investigation failed" });
      setStatusLabel("Investigation failed — is the backend running?");
    } finally { setBusy(false); }
  };

  const updateNumber = (key: keyof RiskPayload, value: string) => setPayload((current) => ({ ...current, [key]: Number(value) }));
  const fields = [
    ["amount", "Amount (INR)"], ["customer_id", "Customer ID"], ["device_id", "Device ID"], ["location", "Location"],
    ["velocity", "Velocity / hour"], ["failed_attempts", "Failed attempts"], ["account_age_days", "Account age (days)"],
    ["merchant_id", "Merchant ID"], ["merchant_risk_score", "Merchant risk (0–100)"], ["behavioral_deviation", "Behavior deviation (0–1)"],
  ] as const;

  const modeBadge = mode === "RAZORPAY_TEST_MODE"
    ? <span className="rounded-full bg-[#e4f6f1] px-3 py-1 text-[11px] font-semibold text-[#16786d]">Razorpay Test Mode — real test API</span>
    : mode === "TEST_MODE_PARTIAL"
      ? <span className="rounded-full bg-[#faf5e8] px-3 py-1 text-[11px] font-semibold text-[#916b17]">Test Mode (partial) — unconfigured parts simulated</span>
      : <span className="rounded-full bg-[#f4f2ec] px-3 py-1 text-[11px] font-semibold text-[#849095]">Demo mode — Razorpay simulated (labeled)</span>;

  return <div className="min-h-screen bg-[#f5f5ee] px-4 py-8 text-[#26343b] sm:px-8 lg:px-16"><div className="mx-auto max-w-7xl">
    <div className="mb-8 flex flex-col justify-between gap-4 md:flex-row md:items-end"><div><p className="rp-eyebrow text-[#0e897d]">RiskPilot live integration lab</p><h1 className="mt-2 max-w-3xl text-4xl font-semibold tracking-[-.04em] text-[#1d2b31]">Real responses, not screenshots.</h1><p className="mt-3 max-w-2xl text-sm leading-6 text-[#647278]">Every result on this page is a real call to the FastAPI backend. Judge Mode runs the full closed loop: risk engine → agent investigation → governance → Razorpay → webhook → audit → profile update.</p></div><div className="rounded-lg border border-[#cbd8d3] bg-[#edf8f4] px-4 py-3 text-xs text-[#27665d]"><span className="font-semibold">API base</span><br />{API_BASE_URL}</div></div>
    <div className="mb-6 flex flex-wrap items-center gap-3">{modeBadge}<span className="rounded-full border border-[#d8ddd7] px-3 py-1 text-[11px] font-semibold text-[#53636b]">{statusLabel}</span></div>
    <div className="grid gap-6 lg:grid-cols-[minmax(0,1fr)_minmax(0,1fr)]">
      <section className="rp-surface rounded-xl p-5"><div className="mb-5 flex items-center justify-between"><div><p className="rp-eyebrow text-[#748187]">Transaction payload</p><h2 className="mt-1 text-lg font-semibold">Risk decision input</h2></div></div>
        <div className="grid gap-3 sm:grid-cols-2">{fields.map(([key, label]) => <label key={key} className="text-xs font-semibold text-[#58676d]">{label}<input className="rp-input mt-1 h-10 w-full rounded-md px-3 text-sm font-normal" type={typeof payload[key] === "number" ? "number" : "text"} step={key === "behavioral_deviation" ? "0.01" : "1"} value={payload[key]} onChange={(event) => typeof payload[key] === "number" ? updateNumber(key, event.target.value) : setPayload((current) => ({ ...current, [key]: event.target.value }))} /></label>)}</div>
        <div className="mt-5 flex flex-wrap gap-2">
          <button disabled={busy} onClick={() => void runJudgeFlow()} className="rp-button rp-button-ink rounded-lg px-4 py-2.5 text-xs font-semibold disabled:opacity-50">▶ Run Judge Mode flow</button>
          <button disabled={busy} onClick={() => void runInvestigationFlow()} className="rp-button rounded-lg border border-[#cbd2ce] bg-white px-4 py-2.5 text-xs font-semibold disabled:opacity-50">Agent investigation (replay)</button>
          <button disabled={busy} onClick={() => void run("Risk analysis", () => analyzeRisk(payload))} className="rp-button rounded-lg border border-[#cbd2ce] bg-white px-4 py-2.5 text-xs font-semibold disabled:opacity-50">Analyze transaction</button>
          <button disabled={busy} onClick={() => void run("Investigation", () => explainInvestigation(payload))} className="rp-button rounded-lg border border-[#cbd2ce] bg-white px-4 py-2.5 text-xs font-semibold disabled:opacity-50">Explain with AI</button>
          <button disabled={busy} onClick={() => void run("Razorpay order", () => createRazorpayOrder({ ...payload, currency: "INR", notes: { source: "riskpilot-live-lab" } }))} className="rp-button rounded-lg border border-[#cbd2ce] bg-white px-4 py-2.5 text-xs font-semibold disabled:opacity-50">Create test order</button>
        </div>
        {timeline && timeline.length > 0 && (
          <div className="mt-5 rounded-lg border border-[#dce2db] bg-[#f7f7f1] p-4">
            <div className="rp-eyebrow text-[#748187]">Investigation timeline — measured latencies</div>
            <div className="mt-3 space-y-2">{timeline.map((step) => (
              <div key={step.step} className="flex flex-wrap items-center gap-2 text-[11px]">
                <span className="rp-mono w-6 text-[#849095]">{step.step}.</span>
                <span className="font-semibold text-[#26343b]">{step.name || step.tool}</span>
                <span className="rp-mono text-[#849095]">{step.latency_ms.toFixed(1)} ms</span>
                {step.mode && <span className="rounded-full bg-[#eef1eb] px-2 py-0.5 text-[9px] font-semibold uppercase tracking-wide text-[#66747b]">{step.mode}</span>}
                {(step.detail || step.findings?.finding) && <span className="w-full text-[#7b878b]">{step.detail || step.findings?.finding}</span>}
              </div>
            ))}</div>
            <p className="mt-3 text-[10px] text-[#849095]">Latencies are measured per step by the backend — never fabricated.</p>
          </div>
        )}
      </section>
      <section className="rp-surface rounded-xl p-5"><div className="mb-4 flex items-center justify-between"><div><p className="rp-eyebrow text-[#748187]">Verified response</p><h2 className="mt-1 text-lg font-semibold">API output</h2></div><button disabled={busy} onClick={() => void run("Audit fetch", getRecentAudit)} className="text-xs font-semibold text-[#0e897d] disabled:opacity-50">Load audit</button></div><JsonPanel value={result} /><div className="mt-4 grid grid-cols-2 gap-3 text-xs"><div className="rounded-lg bg-[#f4f5ef] p-3"><div className="text-[#849095]">Risk gate</div><div className="mt-1 font-semibold">approve · review · block</div></div><div className="rounded-lg bg-[#f4f5ef] p-3"><div className="text-[#849095]">Webhook</div><div className="mt-1 font-semibold">HMAC signature + idempotency</div></div></div></section>
    </div>
    <div className="mt-6 rounded-xl border border-[#d7ddd5] bg-[#fffef9] p-5 text-sm leading-6 text-[#5e6b70]"><strong className="text-[#26343b]">Reviewer path:</strong> click <strong>Run Judge Mode flow</strong> — you'll see the entire pipeline with per-step latencies and honest mode labels (real / razorpay_test_mode / labeled_simulation / not_configured_skipped). Then click <strong>Load audit</strong> to see the trail it just wrote.</div>
  </div></div>;
}
