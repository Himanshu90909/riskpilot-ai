"""
RiskPilot AI - LLM Risk Analyst Package.

Provides LLM-powered fraud investigation, fallback rule-based explanations,
and multi-step agentic investigation pipelines for RiskPilot AI.
"""

from llm.explanation_generator import ExplanationGenerator, extract_context_fields
from llm.investigation_agent import InvestigationAgent, assistantReply, assistant_reply
from llm.risk_analyst import RiskAnalyst, analyze_risk

__all__ = [
    "RiskAnalyst",
    "analyze_risk",
    "ExplanationGenerator",
    "extract_context_fields",
    "InvestigationAgent",
    "assistant_reply",
    "assistantReply",
]
