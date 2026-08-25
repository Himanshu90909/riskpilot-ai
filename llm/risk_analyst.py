"""
RiskPilot AI - LLM Risk Analyst Module.

Provides LLM-powered fraud investigation summaries, key risk factor synthesis,
actionable recommendations, and follow-up analyst questions using Google Gemini API
(gemini-2.0-flash via google-genai library). Fallbacks to rule-based explanation generator
when the Gemini API is unreachable or key is unconfigured.
"""

import json
import logging
import os
from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field

from llm.explanation_generator import ExplanationGenerator

logger = logging.getLogger("RiskPilot.RiskAnalyst")


class RiskAnalysisSchema(BaseModel):
    """Structured Pydantic response schema for RiskAnalyst LLM output."""

    summary: str = Field(
        description="A concise 2-3 sentence natural language investigation summary explaining WHY the transaction is suspicious or safe."
    )
    risk_factors: List[str] = Field(
        description="List of key risk factors identified from the transaction context."
    )
    recommended_action: str = Field(
        description="Recommended action (e.g. BLOCK, FLAG_FOR_REVIEW, ALLOW) with primary rationale."
    )
    reasoning: str = Field(
        description="Detailed technical reasoning supporting the recommended action."
    )
    follow_up_questions: List[str] = Field(
        description="2-4 actionable follow-up questions for human risk analysts to consider during review."
    )


class RiskAnalyst:
    """
    LLM-powered Risk Analyst service using Google Gemini 2.0 Flash.
    Positions itself as 'RiskPilot AI Risk Analyst' - a defense-only fraud investigation assistant.
    """

    SYSTEM_PROMPT = """You are RiskPilot AI Risk Analyst, an elite defense-only fraud investigation assistant built for financial risk and fraud detection platforms.

YOUR PURPOSE:
Analyze financial transaction data, behavioral metrics, device telemetry, velocity signals, and automated risk engine scores to generate crisp, authoritative, and actionable risk investigation reports for human fraud analysts and decision systems.

DEFENSE-ONLY GUARDRAILS (STRICT COMPLIANCE REQUIRED):
1. You operate strictly as a defense-only tool focused on identifying, mitigating, and preventing financial fraud.
2. Under NO circumstances will you provide instructions, techniques, code, advice, or suggestions on how to commit fraud, bypass security controls, spoof locations/devices, evade velocity limits, or manipulate transaction parameters.
3. If an inquiry or context appears to ask for exploit or fraud techniques, refuse the request and redirect exclusively to defensive fraud analysis and risk mitigation.

ANALYSIS GUIDELINES:
- Direct & Professional: Deliver concise, high-signal risk assessments without conversational filler.
- Score-Aware Reasoning: Incorporate the transaction's calculated risk score, risk level, and AI decision directly into your summary and recommendations.
- Specific Risk Signals: Detail concrete telemetry factors (e.g., VPN usage, geo-distance shift, velocity bursts, failed authentication) driving the risk assessment.
- Actionable Recommendations: Frame recommendations clearly (BLOCK / FLAG_FOR_REVIEW / ALLOW) backed by solid business logic.
"""

    def __init__(
        self,
        api_key: Optional[str] = None,
        model_name: str = "gemini-2.0-flash",
        fallback_generator: Optional[ExplanationGenerator] = None,
    ):
        """
        Initialize the RiskAnalyst service.

        Args:
            api_key: Gemini API key (defaults to GEMINI_API_KEY environment variable).
            model_name: Model identifier (defaults to 'gemini-2.0-flash').
            fallback_generator: Custom ExplanationGenerator instance if provided.
        """
        self.api_key = api_key or os.getenv("GEMINI_API_KEY")
        self.model_name = model_name
        self.fallback_generator = fallback_generator or ExplanationGenerator()
        self._client = None

        if self.api_key:
            try:
                from google import genai
                self._client = genai.Client(api_key=self.api_key)
                logger.info("Initialized Google Gemini client with model: %s", self.model_name)
            except Exception as e:
                logger.warning(
                    "Failed to initialize Google Gemini client: %s. Falling back to rule-based engine.", e
                )
                self._client = None
        else:
            logger.info("GEMINI_API_KEY environment variable not found. Operating in fallback rule-based mode.")

    def analyze_transaction(self, context: Dict[str, Any]) -> Dict[str, Any]:
        """
        Analyze a transaction context dictionary and return a structured risk assessment.

        Args:
            context: Dictionary containing transaction details (amount, customer history,
                     device info, location, velocity, failed_attempts, merchant info,
                     risk_score, risk_level, ai_decision).

        Returns:
            Dict containing summary, risk_factors, recommended_action, reasoning,
            follow_up_questions, is_fallback, and engine_used.
        """
        if not self._client:
            logger.info("Executing rule-based fallback generator for transaction risk analysis.")
            return self.fallback_generator.generate_explanation(context)

        try:
            from google.genai import types

            prompt = self._build_prompt(context)

            response = self._client.models.generate_content(
                model=self.model_name,
                contents=prompt,
                config=types.GenerateContentConfig(
                    system_instruction=self.SYSTEM_PROMPT,
                    response_mime_type="application/json",
                    response_schema=RiskAnalysisSchema,
                    temperature=0.2,
                ),
            )

            if response and response.text:
                data = json.loads(response.text)
                return {
                    "summary": data.get("summary", ""),
                    "risk_factors": data.get("risk_factors", []),
                    "recommended_action": data.get("recommended_action", ""),
                    "reasoning": data.get("reasoning", ""),
                    "follow_up_questions": data.get("follow_up_questions", []),
                    "is_fallback": False,
                    "engine_used": self.model_name,
                }
            else:
                raise ValueError("Empty response text returned by Gemini API.")

        except Exception as e:
            logger.error(
                "Gemini API execution failed (%s). Executing rule-based fallback generator.", e
            )
            fallback_result = self.fallback_generator.generate_explanation(context)
            fallback_result["fallback_reason"] = f"Gemini API error: {str(e)}"
            return fallback_result

    def _build_prompt(self, context: Dict[str, Any]) -> str:
        """Construct structured user prompt with transaction telemetry and risk scores."""
        risk_score = context.get("risk_score", "N/A")
        risk_level = context.get("risk_level", "N/A")
        ai_decision = context.get("ai_decision", "N/A")

        return f"""Analyze the following RiskPilot AI transaction context and generate a risk investigation report:

TRANSACTION RISK METRICS:
- Risk Score: {risk_score} / 100
- Risk Level: {risk_level}
- AI Decision: {ai_decision}

FULL TRANSACTION CONTEXT:
{json.dumps(context, indent=2, default=str)}

OUTPUT INSTRUCTIONS:
1. Provide a concise 2-3 sentence investigation summary explaining WHY this transaction is suspicious or safe.
2. List all key risk factors identified from the context signals.
3. State a clear recommended action (BLOCK, FLAG_FOR_REVIEW, ALLOW) with justification.
4. Detail the technical reasoning behind the decision.
5. Provide 2-4 critical follow-up questions for a human risk analyst to investigate further.
"""


def analyze_risk(context: Dict[str, Any], api_key: Optional[str] = None) -> Dict[str, Any]:
    """Convenience function to perform risk analysis on transaction context."""
    analyst = RiskAnalyst(api_key=api_key)
    return analyst.analyze_transaction(context)
