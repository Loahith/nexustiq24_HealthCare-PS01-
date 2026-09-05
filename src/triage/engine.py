"""
Deterministic triage rule engine.

Loads rules from data/triage_rules/rules.json and evaluates a set of
boolean flags (produced by symptom_extractor.py) against them. This is
the ONLY component that decides urgency level / department. It never
calls an LLM and never guesses -- if flags are insufficient to trigger
any rule, the case is marked for escalation with STANDARD-review status
rather than assigning a false urgency.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Dict, List, Set

RULES_PATH = Path(__file__).resolve().parents[2] / "data" / "triage_rules" / "rules.json"

URGENCY_RANK = {"EMERGENCY": 3, "URGENT": 2, "STANDARD": 1}

MIN_QUESTIONS_ANSWERED_FOR_STANDARD = 2  # minimum signal before we allow a STANDARD, non-escalated result


def load_rules() -> List[dict]:
    with open(RULES_PATH, "r", encoding="utf-8") as f:
        return json.load(f)


class TriageEngine:
    def __init__(self) -> None:
        self.rules = load_rules()

    def has_emergency_match(self, flags: Set[str]) -> bool:
        for rule in self.rules:
            conditions = rule["conditions"].get("all", [])
            if rule["urgency"] == "EMERGENCY" and conditions and all(c in flags for c in conditions):
                return True
        return False

    def evaluate(self, flags: Set[str], remaining_questions: List[str]) -> Dict:
        triggered = []
        for rule in self.rules:
            conditions = rule["conditions"].get("all", [])
            if conditions and all(c in flags for c in conditions):
                triggered.append(rule)

        if not triggered:
            # Not enough / no matching signal -> never guess, escalate for human review.
            return {
                "urgency_level": "UNDETERMINED",
                "recommended_department": "General Medicine",
                "triggered_rules": [],
                "reasoning": (
                    "Unable to determine safely with the information collected so far. "
                    "No deterministic triage rule was matched. Human review required."
                ),
                "escalation_required": True,
                "confidence": 0.0,
            }

        # Highest-severity rule wins; ties broken by first match.
        best = max(triggered, key=lambda r: URGENCY_RANK[r["urgency"]])
        urgency = best["urgency"]
        department = best["department"]

        escalation_required = urgency == "EMERGENCY" or bool(remaining_questions)

        reasoning_parts = [
            f"Rule {r['rule_id']} ({r['description']}) matched -> {r['urgency']}."
            for r in triggered
        ]
        reasoning = " ".join(reasoning_parts)
        if remaining_questions:
            reasoning += (
                " Note: some follow-up information is still missing; the recommendation "
                "may change once it is provided."
            )

        confidence = min(0.95, 0.6 + 0.15 * len(triggered)) if not remaining_questions else 0.55

        return {
            "urgency_level": urgency,
            "recommended_department": department,
            "triggered_rules": [
                {"rule_id": r["rule_id"], "description": r["description"], "outcome": r["urgency"]}
                for r in triggered
            ],
            "reasoning": reasoning,
            "escalation_required": escalation_required,
            "confidence": confidence,
        }
