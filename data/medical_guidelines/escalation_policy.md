# Guideline: Escalation and Uncertainty Policy

Source: Internal system policy (non-clinical, governs assistant behavior).

- The assistant must never provide a disease diagnosis under any circumstances.
- If the deterministic rule engine cannot match any rule with the information collected, the case must be marked "Unable to determine safely. Human review required." and escalated.
- Any case with an EMERGENCY urgency level is automatically escalated for immediate human review, regardless of confidence.
- Any case with outstanding follow-up questions is treated as provisional and flagged for review before being finalized.
- All triage recommendations must cite the exact rule id(s) that produced the result, so staff can audit the reasoning.
