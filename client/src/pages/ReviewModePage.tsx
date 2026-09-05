import { useState } from "react";
import { Link } from "wouter";
import { ArrowRight, CheckCircle2, CircleAlert, Clock3, ExternalLink, GitBranch, ShieldCheck } from "lucide-react";

const steps = [
  { id: "problem", label: "01 / Problem", title: "Stop merchant loss before it compounds", text: "Account takeover and fraud decisions create a trade-off: block too aggressively and good customers suffer; wait too long and the merchant pays the loss." },
  { id: "evidence", label: "02 / Evidence", title: "Measured on held-out data", text: "RP-Guard 2.4 is evaluated on a deterministic 100,000-record synthetic dataset with a reserved 20,000-record held-out set. The dashboard shows what it catches, misses, and costs." },
  { id: "response", label: "03 / Response", title: "Risk score becomes bounded action", text: "The Counterfactual Response Lab compares block, step-up verification, and analyst hold against the same incident, including blast radius and false-positive cost." },
  { id: "failure", label: "04 / Failure", title: "Safe when a provider fails", text: "A simulated provider timeout downgrades the action to analyst review. No money moves, retry is idempotent, and the append-only audit event remains visible." },
];

const metrics = [
  ["93.35%", "precision"],
  ["88.97%", "recall"],
  ["91.11%", "F1 score"],
  ["3.53%", "false-positive rate"],
];

export default function ReviewModePage() {
  const [active, setActive] = useState(0);
  const step = steps[active];
  return (
    <div className="min-h-screen bg-[#101d23] text-[#e8f0ed]">
      <header className="border-b border-white/10 bg-[#101d23]/95 px-5 py-4 backdrop-blur md:px-10">
        <div className="mx-auto flex max-w-6xl items-center justify-between">
          <Link href="/" className="flex items-center gap-3"><div className="flex h-8 w-8 items-center justify-center rounded bg-[#19c6b1] text-sm font-black text-[#102127]">R</div><div><div className="rp-display text-sm font-semibold">RiskPilot AI</div><div className="rp-eyebrow text-[#78918e]">Judge review mode</div></div></Link>
          <Link href="/demo" className="rp-button rounded-lg border border-white/15 px-3 py-2 text-xs font-semibold text-[#c8d5d1]">Open full demo <ExternalLink className="ml-1 inline" size={13} /></Link>
        </div>
      </header>
      <main className="mx-auto max-w-6xl px-5 py-10 md:px-10 md:py-16">
        <div className="max-w-3xl"><div className="rp-eyebrow text-[#6de0d1]">Razorpay AI Buildathon · Track 02</div><h1 className="rp-display mt-4 text-4xl font-semibold leading-tight tracking-[-.05em] md:text-6xl">A risk decision you can <span className="text-[#6de0d1]">measure, explain, and recover.</span></h1><p className="mt-5 max-w-2xl text-base leading-7 text-[#a9bbb7]">RiskPilot is a defense-only AI Risk Manager for merchant loss. This 90-second review mode shows the evidence a reviewer needs before opening the product.</p></div>
        <section className="mt-10 grid gap-3 sm:grid-cols-4">{metrics.map(([value, label]) => <div key={label} className="border border-white/10 bg-[#172b32] p-5"><div className="rp-display text-3xl font-semibold text-[#6de0d1]">{value}</div><div className="rp-eyebrow mt-2 text-[#78918e]">{label}</div></div>)}</section>
        <section className="mt-10 grid gap-6 lg:grid-cols-[.85fr_1.15fr]">
          <div className="border border-white/10 bg-[#14272e] p-5"><div className="rp-eyebrow text-[#78918e]">Review path</div><div className="mt-5 space-y-2">{steps.map((item, index) => <button key={item.id} onClick={() => setActive(index)} className={`flex w-full items-center gap-3 border p-3 text-left transition ${active === index ? "border-[#19c6b1] bg-[#193b3d]" : "border-white/10 hover:border-white/25"}`}><div className={`flex h-7 w-7 items-center justify-center rounded-full text-xs font-bold ${active === index ? "bg-[#19c6b1] text-[#102127]" : "bg-[#24363b] text-[#8fa4a1]"}`}>{index + 1}</div><div><div className="text-xs font-semibold">{item.label}</div><div className="mt-1 text-[10px] text-[#8fa4a1]">{item.title}</div></div></button>)}</div><div className="mt-6 border-t border-white/10 pt-5 text-[11px] leading-5 text-[#8fa4a1]"><ShieldCheck className="mr-2 inline text-[#6de0d1]" size={15} />Built for defense only. No exploit, refund, account-lock, or live-funds action is available.</div></div>
          <div className="border border-white/10 bg-[#f4f6f0] p-6 text-[#17252c] md:p-8"><div className="flex items-center justify-between"><div className="rp-eyebrow text-[#51716d]">{step.label}</div><div className="rp-mono text-xs text-[#51716d]">{active + 1} / {steps.length}</div></div><h2 className="rp-display mt-5 text-3xl font-semibold tracking-[-.04em]">{step.title}</h2><p className="mt-4 max-w-xl text-sm leading-6 text-[#53636b]">{step.text}</p><div className="mt-8 grid gap-3 sm:grid-cols-2"><div className="border-l-2 border-[#19a998] bg-[#e8f4ee] p-4"><CheckCircle2 className="text-[#168f80]" size={17} /><div className="mt-3 text-xs font-bold">Evidence visible</div><div className="mt-1 text-[11px] leading-5 text-[#61746f]">Reviewer can reproduce this path from the public demo.</div></div><div className="border-l-2 border-[#d5a94c] bg-[#fff5dc] p-4"><CircleAlert className="text-[#a87b19]" size={17} /><div className="mt-3 text-xs font-bold">Honest boundary</div><div className="mt-1 text-[11px] leading-5 text-[#7c6b40]">Synthetic/test-mode data is labelled; no production claim is made.</div></div></div><div className="mt-8 flex flex-wrap gap-3"><button onClick={() => setActive((active + 1) % steps.length)} className="rp-button rp-button-primary rounded-lg px-4 py-3 text-xs font-bold">Next proof point <ArrowRight className="ml-1 inline" size={14} /></button><Link href={active === 2 ? "/response-lab" : "/demo"} className="rp-button rounded-lg border border-[#cbd8d2] px-4 py-3 text-xs font-bold text-[#53636b]">{active === 2 ? "Open Response Lab" : "Open guided demo"}</Link></div></div>
        </section>
        <section className="mt-8 flex flex-wrap items-center gap-5 border-t border-white/10 pt-5 text-[10px] text-[#78918e]"><span><GitBranch className="mr-1 inline" size={13} /> Public GitHub repository</span><span><Clock3 className="mr-1 inline" size={13} /> Designed for a 5-minute pitch</span><span><ShieldCheck className="mr-1 inline" size={13} /> Safe fallback + audit trail</span></section>
      </main>
    </div>
  );
}

export { ReviewModePage };
