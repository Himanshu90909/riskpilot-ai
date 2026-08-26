"""
RiskPilot AI - LLM Risk Analyst Module.

Provides LLM-powered fraud investigation summaries, key risk factor synthesis,
actionable recommendations, and follow-up analyst questions. Supports multiple
LLM backends: Groq (OpenAI-compatible), Google Gemini, and rule-based fallback.
"""

import json
import logging
import os
import urllib.request
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
    LLM-powered Risk Analyst service.
    Supports Groq (OpenAI-compatible API) and Google Gemini as backends.
    Falls back to rule-based explanation generator when no LLM is available.
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

OUTPUT FORMAT:
Return a JSON object with these fields:
- summary: 2-3 sentence investigation summary
- risk_factors: array of key risk factor strings
- recommended_action: BLOCK / FLAG_FOR_REVIEW / ALLOW with rationale
- reasoning: detailed technical reasoning
- follow_up_questions: array of 2-4 questions for human analysts
"""

    def __init__(
        self,
        api_key: Optional[str] = None,
        model_name: Optional[str] = None,
        fallback_generator: Optional[ExplanationGenerator] = None,
    ):
        """
        Initialize the RiskAnalyst service.

        Auto-detects available LLM backend:
        1. Groq (XAI_API_KEY or GROQ_API_KEY env var) — OpenAI-compatible, ultra-fast
        2. Google Gemini (GEMINI_API_KEY env var) — google-genai SDK
        3. Rule-based fallback (no API key needed)

        Args:
            api_key: Override API key (auto-detected if not provided).
            model_name: Override model name (auto-selected if not provided).
            fallback_generator: Custom ExplanationGenerator instance.
        """
        self.fallback_generator = fallback_generator or ExplanationGenerator()
        self._backend = "none"
        self._client = None
        self.api_key = None
        self.model_name = None

        # 1. Try Groq (OpenAI-compatible)
        groq_key = api_key or os.getenv("XAI_API_KEY") or os.getenv("GROQ_API_KEY")
        if groq_key and groq_key.startswith("gsk_"):
            self._backend = "groq"
            self.api_key = groq_key
            self.model_name = model_name or "openai/gpt-oss-120b"
            logger.info("Initialized Groq LLM backend with model: %s", self.model_name)

        # 2. Try Google Gemini / AI Studio. Modern AI Studio keys may use AQ. as well as AIza.
        gemini_key = api_key or os.getenv("GEMINI_API_KEY")
        if gemini_key and self._backend == "none":

            self._backend = "gemini"
            self.api_key = gemini_key
            self.model_name = model_name or os.getenv("GEMINI_MODEL", "gemini-2.5-flash")
            try:
                from google import genai
                self._client = genai.Client(api_key=self.api_key)
                logger.info("Initialized Google Gemini client with model: %s", self.model_name)
            except Exception as e:
                logger.warning("Gemini init failed: %s. Using fallback.", e)
                self._backend = "none"

        # 3. Fallback
        else:
            logger.info("No valid LLM API key found. Operating in fallback rule-based mode.")

    @property
    def is_llm_active(self) -> bool:
        """Check if an LLM backend is active (not fallback mode)."""
        return self._backend in ("groq", "gemini")

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
        if not self.is_llm_active:
            logger.info("Executing rule-based fallback generator for transaction risk analysis.")
            result = self.fallback_generator.generate_explanation(context)
            result["engine_used"] = "rule_based_fallback"
            return result

        try:
            if self._backend == "groq":
                return self._call_groq(context)
            elif self._backend == "gemini":
                return self._call_gemini(context)
            else:
                raise ValueError(f"Unknown backend: {self._backend}")
        except Exception as e:
            logger.error("LLM API failed (%s). Using fallback.", e)
            fallback_result = self.fallback_generator.generate_explanation(context)
            fallback_result["fallback_reason"] = f"LLM API error: {str(e)}"
            fallback_result["engine_used"] = "rule_based_fallback"
            return fallback_result

    def _call_groq(self, context: Dict[str, Any]) -> Dict[str, Any]:
        """Call Groq API (OpenAI-compatible) for risk analysis."""
        prompt = self._build_prompt(context)

        url = "https://api.groq.com/openai/v1/chat/completions"
        payload = json.dumps({
            "model": self.model_name,
            "messages": [
                {"role": "system", "content": self.SYSTEM_PROMPT},
                {"role": "user", "content": prompt},
            ],
            "max_tokens": 600,
            "temperature": 0.2,
            "response_format": {"type": "json_object"},
        }).encode()

        req = urllib.request.Request(url, data=payload, method="POST")
        req.add_header("Content-Type", "application/json")
        req.add_header("Authorization", f"Bearer {self.api_key}")
        req.add_header("User-Agent", "RiskPilot-AI/1.0")

        with urllib.request.urlopen(req, timeout=30) as resp:
            data = json.loads(resp.read())
            content = data["choices"][0]["message"]["content"]
            parsed = json.loads(content)

        return {
            "summary": parsed.get("summary", ""),
            "risk_factors": parsed.get("risk_factors", []),
            "recommended_action": parsed.get("recommended_action", ""),
            "reasoning": parsed.get("reasoning", ""),
            "follow_up_questions": parsed.get("follow_up_questions", []),
            "is_fallback": False,
            "engine_used": f"groq:{self.model_name}",
        }

    def _call_gemini(self, context: Dict[str, Any]) -> Dict[str, Any]:
        """Call Google Gemini API for risk analysis."""
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
                "engine_used": f"gemini:{self.model_name}",
            }
        else:
            raise ValueError("Empty response from Gemini API.")

    def _build_prompt(self, context: Dict[str, Any]) -> str:
        """Construct structured user prompt with transaction telemetry and risk scores."""
        risk_score = context.get("risk_score", "N/A")
        risk_level = context.get("risk_level", "N/A")
        ai_decision = context.get("ai_decision", "N/A")

        return f"""Analyze the following RiskPilot AI transaction context and generate a risk investigation report.

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

Return a JSON object with fields: summary, risk_factors, recommended_action, reasoning, follow_up_questions"""


def analyze_risk(context: Dict[str, Any], api_key: Optional[str] = None) -> Dict[str, Any]:
    """Convenience function to perform risk analysis on transaction context."""
    analyst = RiskAnalyst(api_key=api_key)
    return analyst.analyze_transaction(context)
