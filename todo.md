# RiskPilot AI — Track 02 Submission Checklist

- [x] Define one loss class: account takeover on digital payment transactions.
- [x] Create a reproducible synthetic dataset generator with labeled risk outcomes and documented feature schema.
- [x] Implement a defense-only rule-based detector with score, decision, reasons, and no offensive capability.
- [x] Split records into train/tuning and a sealed held-out test set without leakage.
- [x] Compute precision, recall, F1, confusion matrix, and false-positive cost from the held-out set.
- [x] Add an evaluation report with assumptions, threshold, class balance, and limitations.
- [x] Connect calculated evaluation results to the guided demo and README.
- [x] Verify reproducibility, build, responsive UI, and final interview walkthrough.
- [x] Save the completed Track 02 checkpoint.

## Chatbot reliability

- [ ] Support modern Google AI Studio AQ-format keys in the Gemini chatbot backend
- [ ] Default the chatbot to a current Gemini model and preserve schema-validated output
- [ ] Live-test the chatbot with the configured Gemini key and confirm non-fallback output
- [ ] Push the chatbot compatibility fix to GitHub
- [ ] Configure GEMINI_API_KEY in the deployed Vercel environment without committing the secret
- [ ] Verify the deployed chatbot and rotate the exposed GitHub token
