# RiskPilot Repository Audit

The repository is a public GitHub project on `main` with a React/Vite client and a Python FastAPI backend. It includes dedicated `server/`, `ml/`, `llm/`, `razorpay/`, `evaluation/`, and `demo/` modules. The latest commit adds Groq-compatible LLM auto-detection.

The existing backend already has real risk analysis, ML-backed scoring, audit storage, human override flow, LLM analysis with Gemini/Groq and rule-based fallback, and Razorpay test-mode integration. The existing frontend has landing/demo/dashboard routes, reusable mock/evaluation data, a guided investigation demo, and a polished RiskPilot visual system.

The RiskPilot v2 workspace adds a separate full-stack command center with typed persistence, deterministic versioned scoring, rationale-required governance, NVD synchronization, structured summary validation, safe abstention, evaluation/telemetry persistence, and protected tRPC procedures. The next integration step is to port the governed backend contracts and analyst command-center screens into the GitHub repository without removing the existing ML, LLM, and Razorpay demo flows.
