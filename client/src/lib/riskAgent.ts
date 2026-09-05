import { assistantReply } from "./mockData";

const agentBase = (import.meta.env.VITE_API_BASE_URL || "").replace(/\/$/, "");

export async function askRiskAgent(question: string): Promise<{ text: string; engine: string }> {
  try {
    const response = await fetch(`${agentBase}/v1/assistant/chat`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ question }),
    });
    if (!response.ok) throw new Error(`agent_${response.status}`);
    const data = await response.json();
    return { text: data.answer, engine: data.engine || "RiskPilot local agent" };
  } catch {
    return { text: assistantReply(question), engine: "RiskPilot offline fallback" };
  }
}

export const riskAgentCapabilities = ["decision explanations", "risk patterns", "fraud impact", "safe defensive guidance"];
