import { useMemo, useState } from "react";
import { Link } from "wouter";
import {
  Activity,
  ArrowLeft,
  Check,
  CheckCircle2,
  ChevronRight,
  CircleAlert,
  Clock3,
  GitBranch,
  LockKeyhole,
  RotateCcw,
  ShieldAlert,
  SlidersHorizontal,
  Sparkles,
  Terminal,
  X,
} from "lucide-react";

type ActionKey = "block" | "step_up" | "hold";
type Action = { key: ActionKey; label: string; description: string; cost: number; capture: number; color: string };

const actions: Action[] = [
  { key: "block", label: "Block + refund", description: "Stop the payment and queue a customer-safe refund review.", cost: 180, capture: 94, color: "#ca4b57" },
  { key: "step_up", label: "Step-up verification", description: "Ask for a second factor before releasing the payment.", cost: 62, capture: 81, color: "#d5a94c" },
  { key: "hold", label: "Hold for analyst", description: "Pause settlement for 15 minutes while evidence is verified.", cost: 38, capture: 72, color: "#19c6b1" },
];

const signals = [
  ["New device", 0.92, "DEV_8821 has no trusted history for this customer"],
  ["Velocity burst", 0.86, "7 attempts across 3 merchants in 11 minutes"],
  ["Location drift", 0.68, "Mumbai → Bengaluru impossible-travel delta"],
  ["Account age", 0.31, "Customer account is 418 days old"],
] as const;

export function ResponseLabPage() {
  const [selected, setSelected] = useState<ActionKey>("step_up");
  const [threshold, setThreshold] = useState(72);
  const [ran, setRan] = useState(false);
  const [failed, setFailed] = useState(false);
  const action = actions.find((item) => item.key === selected) || actions[1];
  const confidence = Math.min(99, Math.round(78 + (threshold - 72) * 0.25));
  const expectedLoss = Math.round((100 - action.capture) * 12.4);
  const falsePositiveCost = action.cost * (selected === "block" ? 4 : selected === "step_up" ? 2 : 1);
  const recommended = useMemo(() => threshold >= 84 ? "block" : threshold >= 68 ? "step_up" : "hold", [threshold]);

  const runResponse = () => {
    setRan(true);
    setFailed(false);
    window.setTimeout(() => {
      if (selected === "block") setFailed(true);
    }, 700);
  };

  return (
    <div className="min-h-screen bg-[#f4f2ec] text-[#101820]">
      <header className="border-b border-[#dfe1d9] bg-[#fffef9]">
        <div className="mx-auto flex max-w-[1240px] items-center justify-between px-6 py-5 lg:px-10">
          <div className="flex items-center gap-3"><div className="flex h-9 w-9 items-center justify-center rounded-[10px] bg-[#101820] text-sm font-bold text-[#19c6b1]">RP</div><div><div className="rp-display text-[16px] font-bold">RiskPilot <span className="text-[#19c6b1]">AI</span></div><div className="rp-eyebrow text-[#748187]">Operator response lab</div></div></div>
          <Link href="/app" className="rp-button flex items-center gap-2 rounded-lg border border-[#d4d8d1] bg-white px-3 py-2 text-xs font-semibold text-[#53636b]"><ArrowLeft size={14} /> Back to command center</Link>
        </div>
      </header>
      <main className="mx-auto max-w-[1240px] px-6 py-8 lg:px-10 lg:py-12">
        <div className="mb-8 flex flex-col justify-between gap-5 lg:flex-row lg:items-end"><div><div className="rp-eyebrow text-[#537b78]">New · Track 02 differentiator</div><h1 className="rp-display mt-2 max-w-3xl text-4xl font-semibold tracking-[-.06em] sm:text-5xl">Don&apos;t just score risk.<br /><span className="text-[#159684]">Choose the safest response.</span></h1><p className="mt-4 max-w-2xl text-sm leading-6 text-[#66747b]">A counterfactual sandbox for payment teams: compare bounded interventions before they touch money, quantify the trade-off, and preserve a reviewable action trail.</p></div><div className="flex items-center gap-2 rounded-full border border-[#bfe5dc] bg-[#e8f8f3] px-3 py-2 text-[10px] font-semibold uppercase tracking-[.1em] text-[#16786d]"><span className="h-2 w-2 rounded-full bg-[#19c6b1] rp-pulse" /> Synthetic incident · safe mode</div></div>

        <section className="rp-surface overflow-hidden rounded-xl">
          <div className="grid gap-0 lg:grid-cols-[1.1fr_.9fr]">
            <div className="border-b border-[#e5e6df] p-6 lg:border-b-0 lg:border-r lg:p-8"><div className="flex items-start justify-between"><div><div className="rp-eyebrow text-[#748187]">Incident  ·  RP-2026-0914</div><h2 className="rp-display mt-2 text-2xl font-semibold tracking-[-.04em]">Account takeover cluster</h2><p className="mt-2 max-w-lg text-xs leading-5 text-[#66747b]">37 transactions share a device fingerprint and a burst pattern. The model recommends intervention, but the operator controls the blast radius.</p></div><div className="flex h-12 w-12 items-center justify-center rounded-xl bg-[#f8dfe1] text-[#a03c4a]"><ShieldAlert size={22} /></div></div><div className="mt-7 grid gap-3 sm:grid-cols-3"><div className="rounded-lg bg-[#f7f7f1] p-4"><div className="rp-eyebrow text-[#849095]">Exposure</div><div className="rp-display mt-2 text-2xl font-semibold">₹4.8L</div><div className="mt-1 text-[10px] text-[#849095]">at-risk volume</div></div><div className="rounded-lg bg-[#f7f7f1] p-4"><div className="rp-eyebrow text-[#849095]">Cases</div><div className="rp-display mt-2 text-2xl font-semibold">37</div><div className="mt-1 text-[10px] text-[#849095]">linked transactions</div></div><div className="rounded-lg bg-[#f7f7f1] p-4"><div className="rp-eyebrow text-[#849095]">Confidence</div><div className="rp-display mt-2 text-2xl font-semibold text-[#a03c4a]">{confidence}%</div><div className="mt-1 text-[10px] text-[#849095]">policy-adjusted</div></div></div><div className="mt-7"><div className="mb-3 flex items-center justify-between"><div className="rp-eyebrow text-[#748187]">Evidence graph</div><span className="rp-mono text-[10px] text-[#a03c4a]">4 signals · 1 cluster</span></div><div className="space-y-3">{signals.map(([label, strength, note]) => <div key={label} className="flex items-center gap-3"><div className="w-28 shrink-0 text-xs font-semibold text-[#53636b]">{label}</div><div className="h-2 flex-1 overflow-hidden rounded-full bg-[#ecece5]"><div className="h-full rounded-full" style={{ width: `${strength * 100}%`, background: strength > .8 ? "#ca4b57" : strength > .5 ? "#d5a94c" : "#19c6b1" }} /></div><div className="w-9 text-right rp-mono text-[10px] text-[#849095]">{Math.round(strength * 100)}</div></div>)}<div className="mt-2 border-l-2 border-[#19c6b1] pl-3 text-[11px] leading-5 text-[#66747b]">The graph links customer, device, location, and velocity evidence without exposing any offensive capability.</div></div></div></div>
            <div className="bg-[#101820] p-6 text-[#f8f5ec] lg:p-8"><div className="flex items-center gap-2"><SlidersHorizontal size={16} className="text-[#19c6b1]" /><div className="rp-eyebrow text-[#8ba6a1]">Counterfactual response</div></div><h2 className="rp-display mt-3 text-xl font-semibold">What if we intervene this way?</h2><p className="mt-2 text-xs leading-5 text-[#9fb1ad]">Move the confidence gate, compare expected cost, then run one bounded action.</p><div className="mt-6"><div className="flex items-center justify-between text-xs"><span className="text-[#b8c9c6]">Human-review threshold</span><span className="rp-mono text-[#6de0d1]">{threshold}/100</span></div><input aria-label="Human-review threshold" type="range" min="40" max="95" value={threshold} onChange={(event) => setThreshold(Number(event.target.value))} className="mt-3 w-full accent-[#19c6b1]" /><div className="mt-2 flex justify-between text-[10px] text-[#6f8280]"><span>More recall</span><span>Fewer false positives</span></div></div><div className="mt-6 space-y-2">{actions.map((item) => <button key={item.key} onClick={() => { setSelected(item.key); setRan(false); setFailed(false); }} className={`flex w-full items-start gap-3 rounded-lg border p-3 text-left transition ${selected === item.key ? "border-[#19c6b1] bg-[#193039]" : "border-white/10 bg-[#16242b] hover:border-white/25"}`}><div className="mt-0.5 h-3 w-3 rounded-full border-2" style={{ borderColor: item.color, background: selected === item.key ? item.color : "transparent" }} /><div className="min-w-0 flex-1"><div className="flex items-center justify-between gap-3 text-xs font-semibold"><span>{item.label}</span><span className="rp-mono text-[10px]" style={{ color: item.color }}>₹{item.cost} / FP</span></div><div className="mt-1 text-[10px] leading-4 text-[#8fa4a1]">{item.description}</div></div></button>)}</div><div className="mt-6 grid grid-cols-2 gap-3 border-t border-white/10 pt-5"><div><div className="rp-eyebrow text-[#78918e]">Expected loss</div><div className="rp-display mt-2 text-2xl font-semibold text-[#ff9c8e]">₹{expectedLoss}K</div></div><div><div className="rp-eyebrow text-[#78918e]">False-positive cost</div><div className="rp-display mt-2 text-2xl font-semibold text-[#f3d37a]">₹{falsePositiveCost}</div></div></div><button onClick={runResponse} className="rp-button rp-button-primary mt-6 flex w-full items-center justify-center gap-2 rounded-lg px-4 py-3 text-xs font-bold">{ran ? "Action recorded" : "Run bounded response"} <ChevronRight size={15} /></button></div>
          </div>
        </section>

        <section className="mt-5 grid gap-5 lg:grid-cols-[1.05fr_.95fr]"><div className="rp-surface rounded-xl p-6"><div className="flex items-center justify-between"><div><div className="rp-eyebrow text-[#748187]">Policy recommendation</div><h2 className="rp-display mt-1 text-lg font-semibold">{recommended === selected ? "Selected action is policy-aligned" : `Policy would prefer ${actions.find((item) => item.key === recommended)?.label}`}</h2></div><Sparkles className="text-[#159684]" size={19} /></div><div className="mt-5 grid gap-3 sm:grid-cols-3">{[["Capture rate", `${action.capture}%`, "of linked loss"], ["Blast radius", selected === "block" ? "37/37" : selected === "step_up" ? "37/37" : "12/37", "transactions gated"], ["Stop rule", "15 min", "auto-release window"]].map(([label, value, note]) => <div key={label} className="border-l-2 border-[#19c6b1] pl-3"><div className="rp-eyebrow text-[#849095]">{label}</div><div className="rp-display mt-2 text-xl font-semibold">{value}</div><div className="mt-1 text-[10px] text-[#849095]">{note}</div></div>)}</div><div className="mt-6 rounded-lg bg-[#edf8f4] p-4 text-xs leading-5 text-[#27665d]"><LockKeyhole className="mr-2 inline" size={14} />Every money action is gated by policy <span className="rp-mono">RP-2.4</span>. No automatic refund or account lock is permitted from this sandbox.</div></div><div className="rp-surface rounded-xl p-6"><div className="flex items-center justify-between"><div><div className="rp-eyebrow text-[#748187]">Append-only action log</div><h2 className="rp-display mt-1 text-lg font-semibold">Evidence of control</h2></div><Terminal size={17} className="text-[#849095]" /></div><div className="mt-5 space-y-3 text-xs">{ran ? <><div className="flex gap-3"><CheckCircle2 size={16} className="mt-0.5 shrink-0 text-[#19a998]" /><div><div className="font-semibold">{action.label} dispatched</div><div className="mt-1 text-[10px] text-[#849095]">actor: analyst.demo · policy: RP-2.4 · just now</div></div></div>{failed && <div className="flex gap-3"><CircleAlert size={16} className="mt-0.5 shrink-0 text-[#d5a94c]" /><div><div className="font-semibold">Provider timeout handled safely</div><div className="mt-1 text-[10px] leading-4 text-[#849095]">No money moved. Case downgraded to analyst review; retry is idempotent.</div></div></div>}</> : <div className="flex gap-3 text-[#849095]"><Clock3 size={16} className="mt-0.5 shrink-0" /><div><div className="font-semibold text-[#53636b]">Awaiting operator action</div><div className="mt-1 text-[10px]">Nothing has been executed in this simulation.</div></div></div>}<div className="flex gap-3"><Activity size={16} className="mt-0.5 shrink-0 text-[#19a998]" /><div><div className="font-semibold">{ran ? "Audit event sealed" : "Policy evaluated"}</div><div className="mt-1 text-[10px] text-[#849095]">hash: 9f2a…c81d · immutable event chain</div></div></div></div><button onClick={() => { setRan(false); setFailed(false); }} className="rp-button mt-6 flex items-center gap-2 text-xs font-semibold text-[#53636b] hover:text-[#101820]"><RotateCcw size={13} /> Reset simulation</button></div></section>
        <div className="mt-6 flex flex-wrap items-center gap-4 border-t border-[#dfe1d9] pt-5 text-[10px] text-[#849095]"><span className="flex items-center gap-1.5"><GitBranch size={13} /> Counterfactual, not predictive</span><span className="flex items-center gap-1.5"><LockKeyhole size={13} /> Defense-only workflow</span><span className="flex items-center gap-1.5"><X size={13} /> No live funds touched</span></div>
      </main>
    </div>
  );
}

export default ResponseLabPage;
