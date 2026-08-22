/* Editorial Trust Layer: deterministic evidence-first synthetic data for the RiskPilot demo. */

export type RiskLevel = "low" | "medium" | "high" | "critical";
export type Decision = "approve" | "review" | "block";

export type RiskSignal = {
  label: string;
  value: number;
  tone: "critical" | "warning" | "positive" | "neutral";
};

export type Transaction = {
  id: string;
  customer: string;
  customerId: string;
  amount: number;
  merchant: string;
  merchantId: string;
  location: string;
  device: string;
  riskScore: number;
  level: RiskLevel;
  decision: Decision;
  status: "flagged" | "cleared" | "review";
  time: string;
  scenario: string;
  paymentMethod: string;
  currency: "INR";
  signals: RiskSignal[];
};

export type Customer = {
  id: string;
  name: string;
  initials: string;
  riskScore: number;
  status: "trusted" | "watch" | "high-risk";
  averageTransaction: number;
  knownDevices: number;
  locations: string[];
  accountAge: string;
  failedPayments: number;
  riskEvents: number;
  lastSeen: string;
};

export type Merchant = {
  id: string;
  name: string;
  category: string;
  transactions: string;
  riskRate: number;
  fraudRate: number;
  blockedAmount: number;
  trend: number[];
  status: "healthy" | "watch" | "elevated";
};

export type AuditRecord = {
  id: string;
  score: number;
  signals: string;
  aiDecision: string;
  humanDecision: string;
  action: string;
  timestamp: string;
  model: string;
};

export type Rule = {
  id: string;
  title: string;
  description: string;
  impact: string;
  category: string;
  enabled: boolean;
};

const customerNames = [
  "Rahul Mehta", "Aarav Shah", "Diya Nair", "Ishaan Kapoor", "Ananya Rao",
  "Kabir Bansal", "Meera Iyer", "Vihaan Joshi", "Sana Khan", "Arjun Verma",
  "Riya Patel", "Aditya Malhotra", "Nisha Das", "Dev Menon", "Tara Sethi",
  "Kunal Arora", "Simran Gill", "Yash Thakur", "Aditi Singhania", "Rohan Roy",
  "Neha Kulkarni", "Aman Desai", "Pooja Bhat", "Manav Chawla", "Ira Mukherjee",
  "Vikram Sood", "Maya Fernandes", "Reyansh Jain", "Tanvi Oberoi", "Siddharth Bose",
];

const merchantNames = [
  ["Nova Electronics", "Consumer electronics"], ["Aster Travel Co.", "Travel"],
  ["MangoCart", "Marketplace"], ["PulseFit", "Health & wellness"],
  ["UrbanNest", "Home & living"], ["Cobalt Cloud", "SaaS"],
  ["The Daily Basket", "Grocery"], ["Luma Studios", "Digital goods"],
  ["Orbit Mobility", "Mobility"], ["BlueKite Learning", "Education"],
  ["Saffron Kitchen", "Food & beverage"], ["Hush & Hue", "Fashion"],
  ["Greenline Pharmacy", "Healthcare"], ["Craftlane", "Marketplace"],
  ["Northstar Tickets", "Entertainment"],
];

const locations = ["Mumbai", "Pune", "Bengaluru", "Delhi", "Hyderabad", "Chennai", "Kolkata", "Jaipur"];
const devices = ["Known device", "Known device", "Known device", "New device", "New device", "Trusted device"];
const scenarios = ["Baseline purchase", "Baseline purchase", "Account takeover", "Velocity attack", "Payment fraud", "Geographic anomaly", "Friendly fraud"];
const paymentMethods = ["Card •••• 4208", "UPI ••• 1920", "Card •••• 8821", "Netbanking", "Wallet •••• 0812"];

function levelFor(score: number): RiskLevel {
  if (score <= 30) return "low";
  if (score <= 60) return "medium";
  if (score <= 80) return "high";
  return "critical";
}

function decisionFor(level: RiskLevel): Decision {
  if (level === "low") return "approve";
  if (level === "critical") return "block";
  return "review";
}

function signalsFor(score: number, index: number, device: string, location: string): RiskSignal[] {
  const base = [
    { label: "Transaction anomaly", value: Math.max(3, Math.min(22, Math.round(score * 0.24))), tone: score > 70 ? "critical" : "warning" } as RiskSignal,
    { label: device === "New device" ? "New device" : "Device reputation", value: device === "New device" ? 18 : 4, tone: device === "New device" ? "critical" : "positive" } as RiskSignal,
    { label: index % 5 === 0 ? "Location anomaly" : `Location: ${location}`, value: index % 5 === 0 ? 16 : 3, tone: index % 5 === 0 ? "warning" : "positive" } as RiskSignal,
    { label: index % 7 === 0 ? "Velocity attack" : "Normal velocity", value: index % 7 === 0 ? 14 : 2, tone: index % 7 === 0 ? "critical" : "positive" } as RiskSignal,
  ];
  return base;
}

export const transactions: Transaction[] = Array.from({ length: 100 }, (_, index) => {
  const isHero = index === 0;
  const riskScore = isHero ? 91 : Math.min(98, 14 + ((index * 17 + 9) % 77));
  const level = levelFor(riskScore);
  const customerIndex = (index * 7 + 3) % customerNames.length;
  const merchantIndex = (index * 5 + 1) % merchantNames.length;
  const location = isHero ? "Mumbai" : locations[(index * 3 + 2) % locations.length];
  const device = isHero ? "New device" : devices[index % devices.length];
  const timeMinutes = (8 * 60 + 12 + index * 4) % (24 * 60);
  const hour = String(Math.floor(timeMinutes / 60)).padStart(2, "0");
  const minute = String(timeMinutes % 60).padStart(2, "0");
  const amount = isHero ? 84999 : 680 + ((index * 2331 + 1570) % 132000);
  const id = isHero ? "TXN-84921" : `TXN-${String(84921 + index * 37).padStart(5, "0")}`;
  const scenario = isHero ? "Account takeover" : scenarios[index % scenarios.length];
  return {
    id,
    customer: isHero ? "Rahul Mehta" : customerNames[customerIndex],
    customerId: `CUS_${String(1029 + customerIndex).padStart(4, "0")}`,
    amount,
    merchant: isHero ? "Nova Electronics" : merchantNames[merchantIndex][0],
    merchantId: `MER_${String(201 + merchantIndex).padStart(3, "0")}`,
    location,
    device,
    riskScore,
    level,
    decision: decisionFor(level),
    status: level === "low" ? "cleared" : level === "critical" ? "flagged" : "review",
    time: isHero ? "14:32" : `${hour}:${minute}`,
    scenario,
    paymentMethod: isHero ? "Card •••• 8821" : paymentMethods[index % paymentMethods.length],
    currency: "INR",
    signals: signalsFor(riskScore, index, device, location),
  };
});

export const customers: Customer[] = customerNames.map((name, index) => {
  const score = index === 0 ? 18 : Math.min(86, 10 + ((index * 19 + 7) % 72));
  const status = score <= 30 ? "trusted" : score <= 60 ? "watch" : "high-risk";
  return {
    id: `CUS_${String(1029 + index).padStart(4, "0")}`,
    name,
    initials: name.split(" ").map((part) => part[0]).join(""),
    riskScore: score,
    status,
    averageTransaction: index === 0 ? 4200 : 1200 + ((index * 779) % 16800),
    knownDevices: 1 + (index % 4),
    locations: [locations[index % locations.length], locations[(index + 3) % locations.length]],
    accountAge: index === 0 ? "2.4 years" : `${1 + (index % 4)}.${index % 10} years`,
    failedPayments: index % 6,
    riskEvents: (index * 3) % 8,
    lastSeen: index % 3 === 0 ? "2 min ago" : `${index + 4} min ago`,
  };
});

export const merchants: Merchant[] = merchantNames.map(([name, category], index) => {
  const riskRate = 1.2 + ((index * 2.7) % 12);
  const fraudRate = 0.2 + ((index * 0.9) % 4.8);
  return {
    id: `MER_${String(201 + index).padStart(3, "0")}`,
    name,
    category,
    transactions: `${(3.4 + ((index * 1.7) % 13)).toFixed(1)}K`,
    riskRate: Number(riskRate.toFixed(1)),
    fraudRate: Number(fraudRate.toFixed(1)),
    blockedAmount: 84000 + ((index * 43320) % 910000),
    trend: Array.from({ length: 7 }, (_, day) => Math.round(18 + ((index * 11 + day * 9) % 56) + (day === 6 ? index : 0))),
    status: riskRate < 5 ? "healthy" : riskRate < 9 ? "watch" : "elevated",
  };
});

export const auditRecords: AuditRecord[] = transactions.slice(0, 18).map((transaction, index) => ({
  id: transaction.id,
  score: transaction.riskScore,
  signals: transaction.signals.filter((signal) => signal.value > 8).map((signal) => signal.label).join(", "),
  aiDecision: transaction.decision.toUpperCase(),
  humanDecision: index % 5 === 0 ? "OVERRIDDEN" : "—",
  action: index % 5 === 0 ? "Step-up verification" : transaction.decision === "block" ? "Blocked at edge" : "Decision logged",
  timestamp: `Aug 22, 2026 · ${transaction.time}:0${index % 9}`,
  model: index % 2 === 0 ? "RP-Guard 2.4" : "RP-Guard 2.3",
}));

export const defaultRules: Rule[] = [
  { id: "rule-01", title: "Transaction amount threshold", description: "Transaction > ₹50,000", impact: "+15 risk", category: "Amount", enabled: true },
  { id: "rule-02", title: "New device + large transaction", description: "New device with amount above ₹25,000", impact: "+20 risk", category: "Device", enabled: true },
  { id: "rule-03", title: "Velocity attack", description: "10+ transactions in 5 minutes", impact: "+25 risk", category: "Velocity", enabled: true },
  { id: "rule-04", title: "New country + new device", description: "First-seen country paired with a new device", impact: "+20 risk", category: "Geo", enabled: true },
  { id: "rule-05", title: "Multiple failed payments", description: "3+ failed payment attempts in 10 minutes", impact: "+15 risk", category: "Payment", enabled: false },
];

export const riskTrend = [
  { label: "Aug 16", prevented: 38, flagged: 22 }, { label: "Aug 17", prevented: 46, flagged: 28 },
  { label: "Aug 18", prevented: 41, flagged: 24 }, { label: "Aug 19", prevented: 58, flagged: 33 },
  { label: "Aug 20", prevented: 64, flagged: 37 }, { label: "Aug 21", prevented: 72, flagged: 42 },
  { label: "Aug 22", prevented: 81, flagged: 49 },
];

export const riskDistribution = [
  { name: "Low", value: 61, color: "#19C6B1" },
  { name: "Medium", value: 21, color: "#D5A94C" },
  { name: "High", value: 11, color: "#E4795F" },
  { name: "Critical", value: 7, color: "#CA4B57" },
];

export const riskCategories = [
  ["Payment fraud", 34, "#CA4B57"], ["Account takeover", 24, "#E4795F"], ["Velocity attack", 19, "#D5A94C"],
  ["Device anomaly", 12, "#A67C52"], ["Geographic anomaly", 8, "#8E9BAA"], ["Behavioral anomaly", 7, "#6B7787"],
] as const;

export function calculateRiskScore(input: { amount: number; newDevice: boolean; newLocation: boolean; velocity: number; failedAttempts: number; accountAge: number; merchantRisk: number; behaviorDeviation: number }) {
  const factors = [
    { label: "Transaction amount", value: input.amount >= 50000 ? 22 : input.amount >= 25000 ? 12 : 4 },
    { label: "New device", value: input.newDevice ? 18 : 2 },
    { label: "Location anomaly", value: input.newLocation ? 16 : 2 },
    { label: "Transaction velocity", value: input.velocity >= 10 ? 25 : input.velocity >= 5 ? 12 : 3 },
    { label: "Failed payment attempts", value: input.failedAttempts >= 3 ? 15 : input.failedAttempts * 3 },
    { label: "Account age", value: input.accountAge < 0.5 ? 9 : input.accountAge < 1 ? 4 : 1 },
    { label: "Merchant risk", value: Math.round(input.merchantRisk * 1.4) },
    { label: "Behavioral deviation", value: Math.round(input.behaviorDeviation * 0.18) },
  ];
  const score = Math.min(100, factors.reduce((sum, factor) => sum + factor.value, 0));
  const level = levelFor(score);
  return { score, level, decision: decisionFor(level), factors };
}

export function assistantReply(question: string): string {
  const normalized = question.toLowerCase();
  if (normalized.includes("block") || normalized.includes("84921") || normalized.includes("why")) {
    return "TXN-84921 was blocked at 14:32 because the ₹84,999 amount deviated sharply from Rahul Mehta's baseline, arrived from a first-seen device and location, and followed elevated velocity. The agent combined seven signals into a 91/100 critical score.";
  }
  if (normalized.includes("merchant")) {
    return "Nova Electronics is currently the highest-volume merchant under watch, with a 12.4% risk rate. Aster Travel Co. has the steepest week-over-week increase in flagged activity; the simulation suggests reviewing its card-testing thresholds.";
  }
  if (normalized.includes("account takeover") || normalized.includes("takeover")) {
    return "The strongest account takeover cluster combines new device, new location, password reset, and an unusually large purchase. RiskPilot has surfaced 37 related events in the demo window, concentrated across Mumbai and Bengaluru.";
  }
  if (normalized.includes("fraud") || normalized.includes("prevented")) {
    return "NovaPay's demo environment shows ₹3.82 Cr in potential fraud prevented, with 12,481 transactions blocked and a 1.8% false-positive rate. These are synthetic figures for the hackathon walkthrough.";
  }
  if (normalized.includes("today") || normalized.includes("riskiest")) {
    return "Today's riskiest transactions are TXN-84921 at 91, TXN-85288 at 96, and TXN-85473 at 93. All three share a new-device signal; two also show elevated velocity.";
  }
  return "I can explain a decision, surface the riskiest transactions, compare merchant patterns, or summarize today's fraud impact. Try asking about TXN-84921 or the account takeover cluster.";
}

export const apiRequest = `{
  "amount": 84999,
  "currency": "INR",
  "customer_id": "CUS_1029",
  "device_id": "DEV_8821",
  "location": "Mumbai",
  "payment_method": "card"
}`;

export const apiResponse = `{
  "risk_score": 91,
  "risk_level": "critical",
  "decision": "block",
  "reasons": [
    "new_device",
    "location_anomaly",
    "high_velocity"
  ]
}`;
