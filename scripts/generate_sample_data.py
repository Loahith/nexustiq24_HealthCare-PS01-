"""
Generates 100 synthetic patient intake cases, runs them through the real
symptom extractor + deterministic rule engine (same code path the live API
uses), and:
  1. Writes data/sample_cases/sample_cases.json for reference/demo purposes.
  2. Inserts the cases into the SQLite database so the dashboard has data
     to show immediately after a fresh install.

Run with:  python scripts/generate_sample_data.py
"""

from __future__ import annotations

import json
import random
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from src.database.db import init_db  # noqa: E402
from src.triage import case_service  # noqa: E402

random.seed(42)

FIRST_NAMES = ["Aarav", "Priya", "Rahul", "Sneha", "Vikram", "Anjali", "Karthik", "Divya",
               "Arjun", "Meera", "Rohan", "Kavya", "Suresh", "Lakshmi", "Sanjay", "Pooja"]
LAST_NAMES = ["Sharma", "Patel", "Kumar", "Reddy", "Nair", "Iyer", "Menon", "Rao",
              "Gupta", "Verma", "Pillai", "Chatterjee"]

# Each template: (message_sequence, category) -- message_sequence is the full
# set of statements a patient would give across turns, written so the
# deterministic extractor picks up all needed flags.
TEMPLATES = [
    # EMERGENCY: chest pain + breathing difficulty
    ["I have chest pain and difficulty breathing.",
     "The pain is severe and started 1 day ago.",
     "Yes I also feel dizzy.", "No history of asthma.", "Oxygen level unknown."],
    # EMERGENCY: chest pain + dizziness
    ["I have chest pain and I feel very dizzy.",
     "It's moderate pain, started today.", "No breathing difficulty.", "No asthma history."],
    # EMERGENCY: severe bleeding after injury
    ["I injured my leg while playing football and there is severe bleeding.",
     "It's on my lower leg.", "I cannot walk.", "There is visible deformity."],
    # URGENT: high fever
    ["I have a fever of 104F.",
     "It started 2 days ago.", "No breathing difficulty.", "No chest pain."],
    # URGENT: prolonged fever
    ["I have had a fever for 6 days now.",
     "My temperature is around 101F.", "No breathing difficulty.", "No chest pain."],
    # URGENT: cannot walk after injury
    ["I injured my ankle while playing football.",
     "It's on my ankle.", "No bleeding.", "I cannot walk on it.", "There is some swelling."],
    # URGENT: severe abdominal pain
    ["I have severe abdominal pain.",
     "It's in the lower right side.", "No vomiting.", "I have had it for 1 day."],
    # URGENT: abdominal pain with vomiting
    ["I have stomach pain and I've been vomiting.",
     "It's around my belly button.", "I have had it for 2 days."],
    # URGENT: breathing difficulty + asthma
    ["I have breathing difficulty and I have asthma.",
     "It's moderate severity.", "No chest pain."],
    # STANDARD: mild fever
    ["I have had a fever for 2 days.",
     "It's around 100F.", "No breathing difficulty.", "No chest pain."],
    # STANDARD: minor injury
    ["I injured my wrist while playing football.",
     "It's on my wrist.", "No bleeding.", "Yes I can walk fine.", "No swelling."],
    # STANDARD: mild abdominal pain
    ["I have mild abdominal pain.",
     "It's in my upper stomach.", "No vomiting.", "It's been 1 day.", "No fever."],
]

DEPARTMENTS_HINT = {
    0: "Emergency Medicine", 1: "Emergency Medicine", 2: "Emergency Medicine",
    3: "General Medicine", 4: "General Medicine", 5: "Orthopedics",
    6: "Gastroenterology", 7: "Gastroenterology", 8: "Pulmonology",
    9: "General Medicine", 10: "Orthopedics", 11: "Gastroenterology",
}


def run() -> None:
    init_db()
    all_cases = []

    for i in range(100):
        template_idx = i % len(TEMPLATES)
        messages = TEMPLATES[template_idx]
        name = f"{random.choice(FIRST_NAMES)} {random.choice(LAST_NAMES)}"
        age = random.randint(5, 85)
        sex = random.choice(["Male", "Female"])

        patient_id = case_service.get_or_create_patient(None, name, age, sex)
        case_id = case_service.get_or_create_case(None, patient_id, chief_complaint=messages[0])

        state = None
        for msg in messages:
            state = case_service.process_patient_message(case_id, msg)
            if case_service.should_triage_now(state):
                break

        result = case_service.run_triage(case_id)

        all_cases.append(
            {
                "case_id": case_id,
                "patient_id": patient_id,
                "patient_name": name,
                "age": age,
                "sex": sex,
                "messages": messages,
                "urgency_level": result["urgency_level"],
                "recommended_department": result["recommended_department"],
                "triggered_rules": result["triggered_rules"],
                "escalation_required": result["escalation_required"],
            }
        )

    out_path = Path(__file__).resolve().parents[1] / "data" / "sample_cases" / "sample_cases.json"
    out_path.parent.mkdir(parents=True, exist_ok=True)
    with open(out_path, "w", encoding="utf-8") as f:
        json.dump(all_cases, f, indent=2)

    print(f"Generated {len(all_cases)} sample cases -> {out_path}")
    urgency_counts = {}
    for c in all_cases:
        urgency_counts[c["urgency_level"]] = urgency_counts.get(c["urgency_level"], 0) + 1
    print("Urgency distribution:", urgency_counts)


if __name__ == "__main__":
    run()
