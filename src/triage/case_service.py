"""
Orchestrates a triage case end-to-end:
  patient message -> symptom extraction -> follow-up questions OR rule evaluation
  -> persistence in SQLite -> (later) report generation.

Conversation extraction state is kept in-memory per case_id (fine for a
single-process hackathon deployment) and is always re-derivable from the
persisted conversation transcript in SQLite, so a server restart can
optionally reconstruct it by replaying `conversations`.
"""

from __future__ import annotations

import json
import logging
import uuid
from datetime import datetime, timezone
from typing import Dict, List, Optional

from src.database.db import get_cursor
from src.rag.vector_store import get_rag
from src.triage.engine import TriageEngine
from src.triage.symptom_extractor import ExtractionState

logger = logging.getLogger("nexustiq24.case_service")

_engine = TriageEngine()
_state_cache: Dict[str, ExtractionState] = {}


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _new_id(prefix: str) -> str:
    return f"{prefix}-{uuid.uuid4().hex[:10]}"


def get_or_create_patient(
    patient_id: Optional[str],
    name: Optional[str] = None,
    age: Optional[int] = None,
    sex: Optional[str] = None,
    medical_history: Optional[str] = None,
    allergies: Optional[str] = None,
    vitals: Optional[dict] = None,
) -> str:
    vitals_json = json.dumps(vitals) if vitals else None
    with get_cursor() as cur:
        if patient_id:
            cur.execute("SELECT patient_id FROM patients WHERE patient_id = ?", (patient_id,))
            if cur.fetchone():
                cur.execute(
                    "UPDATE patients SET display_name = COALESCE(?, display_name), "
                    "age = COALESCE(?, age), sex = COALESCE(?, sex), "
                    "medical_history = COALESCE(?, medical_history), "
                    "allergies = COALESCE(?, allergies), vitals = COALESCE(?, vitals) "
                    "WHERE patient_id = ?",
                    (name, age, sex, medical_history, allergies, vitals_json, patient_id),
                )
                return patient_id
        pid = patient_id or _new_id("pat")
        cur.execute(
            "INSERT OR IGNORE INTO patients (patient_id, display_name, age, sex, medical_history, allergies, vitals, created_at) "
            "VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
            (pid, name, age, sex, medical_history, allergies, vitals_json, _now()),
        )
        return pid


def get_or_create_case(case_id: Optional[str], patient_id: str, chief_complaint: str) -> str:
    with get_cursor() as cur:
        if case_id:
            cur.execute("SELECT case_id FROM cases WHERE case_id = ?", (case_id,))
            if cur.fetchone():
                return case_id
        cid = case_id or _new_id("case")
        now = _now()
        cur.execute(
            "INSERT INTO cases (case_id, patient_id, chief_complaint, status, created_at, updated_at) "
            "VALUES (?, ?, ?, 'in_progress', ?, ?)",
            (cid, patient_id, chief_complaint, now, now),
        )
        _state_cache[cid] = ExtractionState()
        return cid


def _log_turn(case_id: str, role: str, message: str, metadata: Optional[dict] = None) -> None:
    with get_cursor() as cur:
        cur.execute(
            "INSERT INTO conversations (case_id, role, message, metadata, created_at) VALUES (?, ?, ?, ?, ?)",
            (case_id, role, message, json.dumps(metadata or {}), _now()),
        )


def log_assistant_turn(case_id: str, message: str, question: Optional[str] = None) -> None:
    _log_turn(case_id, "assistant", message, {"question": question} if question else {})
    state = get_state(case_id)
    if question and question not in state.asked_questions:
        state.asked_questions.append(question)


def get_state(case_id: str) -> ExtractionState:
    if case_id not in _state_cache:
        state = ExtractionState()
        with get_cursor() as cur:
            cur.execute(
                "SELECT role, message, metadata FROM conversations WHERE case_id = ? ORDER BY turn_id ASC",
                (case_id,),
            )
            rows = cur.fetchall()
            for r in rows:
                if r["role"] == "patient":
                    state.merge_text(r["message"])
                elif r["role"] == "assistant":
                    try:
                        meta = json.loads(r["metadata"] or "{}")
                        q = meta.get("question")
                        if q and q not in state.asked_questions:
                            state.asked_questions.append(q)
                    except Exception:
                        pass
        _state_cache[case_id] = state
    return _state_cache[case_id]


def process_patient_message(
    case_id: str,
    message: str,
    vitals: Optional[dict] = None,
    medical_history: Optional[str] = None,
    allergies: Optional[str] = None,
) -> ExtractionState:
    state = get_state(case_id)
    state.merge_text(message)
    if medical_history:
        state.merge_text(f"Medical history: {medical_history}")
    if allergies:
        state.merge_text(f"Known allergies: {allergies}")
    if vitals:
        temp = vitals.get("temperature")
        if temp is not None:
            try:
                temp_val = float(temp)
                state.facts["temperature_f"] = temp_val
                if temp_val > 103:
                    state.flags.add("fever_over_103")
                elif temp_val > 100.4:
                    state.flags.add("fever_mild")
                state.flags.add("fever_checked")
            except (ValueError, TypeError):
                pass
        spo2 = vitals.get("spo2")
        if spo2 is not None:
            try:
                spo2_val = float(spo2)
                state.facts["spo2"] = spo2_val
                if spo2_val < 90:
                    state.flags.add("low_oxygen")
            except (ValueError, TypeError):
                pass
        if vitals.get("heart_rate"):
            try:
                state.facts["heart_rate"] = float(vitals["heart_rate"])
            except (ValueError, TypeError):
                pass
        state._derive_composite_flags()

    _log_turn(case_id, "patient", message, {"flags": sorted(state.flags), "vitals": vitals})
    return state


def should_triage_now(state: ExtractionState) -> bool:
    """Evaluate whether enough seriousness questions have been asked.
    Ensures targeted questions (minimum 3 turns or until remaining questions are cleared)
    are asked before concluding triage."""
    remaining = state.required_questions()
    if not remaining:
        return True
    if len(state.asked_questions) >= 3 or state.turn_count >= 4:
        return True
    if _engine.has_emergency_match(state.flags) and len(state.raw_statements) >= 2:
        return True
    return False


def run_triage(
    case_id: str,
    override_urgency: Optional[str] = None,
    override_department: Optional[str] = None,
    override_reasoning: Optional[str] = None,
) -> dict:
    state = get_state(case_id)
    remaining = state.required_questions()
    result = _engine.evaluate(state.flags, remaining)

    if override_urgency and override_department:
        result["urgency_level"] = override_urgency
        result["recommended_department"] = override_department
        if override_reasoning:
            result["reasoning"] = override_reasoning
        result["confidence"] = 0.95
        result["escalation_required"] = override_urgency == "EMERGENCY"

    # RAG evidence lookup based on identified complaint categories
    rag = get_rag()
    evidence = []
    query = " ".join(state.categories) or " ".join(state.raw_statements[-1:])
    if query.strip():
        for chunk, score in rag.retrieve(query, top_k=3):
            evidence.append({"source": chunk.source, "text": chunk.text, "score": round(score, 3)})

    timestamp = _now()
    with get_cursor() as cur:
        cur.execute(
            """INSERT INTO triage_results
               (case_id, symptoms_identified, missing_information, urgency_level,
                recommended_department, triggered_rules, reasoning, evidence,
                escalation_required, confidence, created_at)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
            (
                case_id,
                json.dumps(sorted(state.flags)),
                json.dumps(remaining),
                result["urgency_level"],
                result["recommended_department"],
                json.dumps(result["triggered_rules"]),
                result["reasoning"],
                json.dumps(evidence),
                int(result["escalation_required"]),
                result["confidence"],
                timestamp,
            ),
        )
        cur.execute(
            """UPDATE cases SET urgency_level = ?, department = ?, escalation_required = ?,
               status = ?, updated_at = ? WHERE case_id = ?""",
            (
                result["urgency_level"],
                result["recommended_department"],
                int(result["escalation_required"]),
                "escalated" if result["escalation_required"] else "triaged",
                timestamp,
                case_id,
            ),
        )

    result["case_id"] = case_id
    result["timestamp"] = timestamp
    result["evidence"] = evidence
    result["missing_information"] = remaining
    result["symptoms_identified"] = sorted(state.flags)
    _log_turn(case_id, "assistant", result["reasoning"], {"triage": result["urgency_level"]})
    return result


def list_cases(limit: int = 200) -> List[dict]:
    with get_cursor() as cur:
        cur.execute(
            "SELECT * FROM cases ORDER BY created_at DESC LIMIT ?", (limit,)
        )
        return [dict(row) for row in cur.fetchall()]


def get_case_detail(case_id: str) -> Optional[dict]:
    with get_cursor() as cur:
        cur.execute("SELECT * FROM cases WHERE case_id = ?", (case_id,))
        case_row = cur.fetchone()
        if not case_row:
            return None
        cur.execute(
            "SELECT * FROM conversations WHERE case_id = ? ORDER BY turn_id ASC", (case_id,)
        )
        conv = [dict(r) for r in cur.fetchall()]
        cur.execute(
            "SELECT * FROM triage_results WHERE case_id = ? ORDER BY result_id DESC LIMIT 1",
            (case_id,),
        )
        triage_row = cur.fetchone()
        triage = dict(triage_row) if triage_row else None
        return {"case": dict(case_row), "conversation": conv, "triage": triage}


def get_analytics() -> dict:
    with get_cursor() as cur:
        cur.execute("SELECT COUNT(*) as c FROM cases")
        total = cur.fetchone()["c"]
        cur.execute("SELECT urgency_level, COUNT(*) as c FROM cases GROUP BY urgency_level")
        by_urgency = {row["urgency_level"] or "UNDETERMINED": row["c"] for row in cur.fetchall()}
        cur.execute("SELECT department, COUNT(*) as c FROM cases WHERE department IS NOT NULL GROUP BY department")
        by_dept = {row["department"]: row["c"] for row in cur.fetchall()}
        cur.execute("SELECT COUNT(*) as c FROM cases WHERE escalation_required = 1")
        escalated = cur.fetchone()["c"]
        cur.execute(
            "SELECT substr(created_at, 1, 10) as day, urgency_level, COUNT(*) as c "
            "FROM cases GROUP BY day, urgency_level ORDER BY day ASC"
        )
        over_time = [dict(r) for r in cur.fetchall()]

    return {
        "total_cases": total,
        "emergency_cases": by_urgency.get("EMERGENCY", 0),
        "urgent_cases": by_urgency.get("URGENT", 0),
        "standard_cases": by_urgency.get("STANDARD", 0),
        "escalated_cases": escalated,
        "department_distribution": by_dept,
        "urgency_over_time": over_time,
    }


def get_question_options(question: Optional[str]) -> List[dict]:
    """Map a follow-up question to interactive quick-choice options."""
    if not question:
        return []

    q = question.lower()

    if "primary symptom" in q or "best describes" in q:
        return [
            {"label": "Chest discomfort", "value": "I have chest pain or tightness"},
            {"label": "Breathing difficulty", "value": "I have shortness of breath"},
            {"label": "Severe headache / Migraine", "value": "I have a severe headache or migraine"},
            {"label": "Allergic reaction / Hives", "value": "I am having an allergic reaction with hives or swelling"},
            {"label": "Abdominal / Stomach pain", "value": "I have abdominal pain"},
            {"label": "Eye irritation or injury", "value": "I have an eye issue or injury"},
            {"label": "Skin rash or burn", "value": "I have a rash or skin burn"},
            {"label": "Ear or throat pain", "value": "I have ear or throat pain"},
            {"label": "Urinary burning / Flank pain", "value": "I have pain urinating or flank pain"},
            {"label": "Injury / Fall", "value": "I suffered an injury"},
            {"label": "Fever or chills", "value": "I have a fever"},
        ]

    if "temperature" in q:
        return [
            {"label": "Normal (< 100.4°F)", "value": "Temperature is normal, 98.6°F"},
            {"label": "Mild / Moderate (101°F - 103°F)", "value": "Temperature is 101.5°F"},
            {"label": "High fever (> 103°F)", "value": "High fever 104°F"},
            {"label": "Unmeasured / Unknown", "value": "Temperature unknown, not measured"},
        ]

    if "how long" in q or "experiencing" in q or "duration" in q or "days has the" in q or "when did" in q:
        return [
            {"label": "Started today / Just now", "value": "Started today, just a few hours ago"},
            {"label": "2 to 3 days", "value": "Experiencing this for 2 to 3 days"},
            {"label": "More than a week", "value": "Experiencing this for more than a week"},
        ]

    if "how severe" in q or "scale from mild to severe" in q or "mild, moderate, or severe" in q or "severity" in q:
        return [
            {"label": "Mild (1-3 / 10)", "value": "The symptoms are mild (1-3 / 10)"},
            {"label": "Moderate (4-6 / 10)", "value": "The symptoms are moderate (4-6 / 10)"},
            {"label": "Severe (7-10 / 10)", "value": "The symptoms are severe (7-10 / 10)"},
        ]

    if "breathing difficulty" in q:
        if "severe" in q:
            return [
                {"label": "Mild", "value": "Mild shortness of breath"},
                {"label": "Moderate", "value": "Moderate breathing difficulty"},
                {"label": "Severe (can't breathe)", "value": "Severe breathing, can't breathe at all"},
            ]
        return [
            {"label": "No breathing difficulty", "value": "No breathing difficulty"},
            {"label": "Mild shortness of breath", "value": "Shortness of breath, mild"},
            {"label": "Severe breathing difficulty", "value": "Severe breathing difficulty"},
        ]

    if "chest pain" in q:
        if "severe" in q:
            return [
                {"label": "Mild", "value": "The chest pain is mild"},
                {"label": "Moderate", "value": "The chest pain is moderate"},
                {"label": "Severe", "value": "The chest pain is severe"},
            ]
        if "how long" in q or "occurring" in q:
            return [
                {"label": "Just started today", "value": "Chest pain just started today"},
                {"label": "1 to 2 days", "value": "Chest pain for 2 days"},
                {"label": "More than 2 days", "value": "Chest pain for several days"},
            ]
        return [
            {"label": "No chest pain", "value": "No chest pain"},
            {"label": "Mild chest pain", "value": "Mild chest pain"},
            {"label": "Severe chest pain", "value": "Severe chest pain"},
        ]

    if "injury located" in q or "where is the injury" in q:
        return [
            {"label": "Ankle / Foot", "value": "Injured my ankle"},
            {"label": "Knee / Leg", "value": "Injured my knee"},
            {"label": "Wrist / Arm / Hand", "value": "Injured my wrist"},
            {"label": "Head / Neck", "value": "Injured my head"},
            {"label": "Back / Hip", "value": "Injured my back"},
            {"label": "Other body part", "value": "Injured on my body"},
        ]

    if "bleeding" in q:
        return [
            {"label": "No bleeding", "value": "No bleeding"},
            {"label": "Minor / controlled", "value": "Minor cut with controlled bleeding, no severe bleeding"},
            {"label": "Severe / heavy bleeding", "value": "Severe heavy bleeding, won't stop bleeding"},
        ]

    if "can the patient walk" in q or "walk" in q:
        return [
            {"label": "Yes, can walk normally", "value": "I can walk normally"},
            {"label": "No, cannot walk", "value": "I cannot walk"},
            {"label": "With difficulty / limp", "value": "I can walk with difficulty"},
        ]

    if "swelling" in q or "deformity" in q:
        return [
            {"label": "No swelling or deformity", "value": "No swelling or deformity"},
            {"label": "Noticeable swelling", "value": "There is noticeable swelling"},
            {"label": "Visible deformity", "value": "There is visible deformity"},
        ]

    if "dizzy" in q or "lightheaded" in q:
        return [
            {"label": "No dizziness", "value": "No dizziness"},
            {"label": "Yes, feeling dizzy", "value": "Yes, feeling dizzy and lightheaded"},
        ]

    if "abdominal pain" in q or "stomach" in q:
        if "located" in q or "where" in q:
            return [
                {"label": "Lower right side", "value": "Pain is in the lower right quadrant"},
                {"label": "Upper stomach", "value": "Pain is in the upper stomach"},
                {"label": "Lower abdomen", "value": "Pain is in the lower abdomen"},
                {"label": "All over / cramping", "value": "Pain is all over stomach"},
            ]
        if "severe" in q:
            return [
                {"label": "Mild", "value": "The abdominal pain is mild"},
                {"label": "Moderate", "value": "The abdominal pain is moderate"},
                {"label": "Severe", "value": "The abdominal pain is severe"},
            ]
        if "how long" in q or "lasted" in q:
            return [
                {"label": "Started today", "value": "Pain started today"},
                {"label": "2 to 3 days", "value": "Pain for 2 days"},
                {"label": "More than 5 days", "value": "Pain for 6 days"},
            ]
        if "fever" in q:
            return [
                {"label": "No fever", "value": "No fever, temperature normal"},
                {"label": "Yes, fever present", "value": "Yes, also have a fever"},
            ]

    if "vomiting" in q:
        return [
            {"label": "No vomiting", "value": "No vomiting"},
            {"label": "Yes, vomiting", "value": "Yes, vomiting"},
        ]

    if "asthma" in q:
        return [
            {"label": "No asthma history", "value": "No history of asthma"},
            {"label": "Yes, history of asthma", "value": "Yes, history of asthma"},
        ]

    if "oxygen" in q or "spo2" in q:
        return [
            {"label": "Normal (≥ 95%)", "value": "Oxygen saturation SpO2 is 98"},
            {"label": "Low (< 90%)", "value": "Oxygen saturation SpO2 is 88, low oxygen"},
            {"label": "Unknown / Unmeasured", "value": "Oxygen level unknown, haven't checked"},
        ]

    if "radiat" in q or "arm" in q or "jaw" in q:
        return [
            {"label": "No radiation (stays in chest)", "value": "No radiation, pain stays localized in chest"},
            {"label": "Yes, radiates to left arm", "value": "Pain radiates to my left arm"},
            {"label": "Yes, radiates to shoulder/jaw", "value": "Pain radiates to my shoulder and jaw"},
        ]

    if "warning signs" in q or "stiff neck" in q or "confusion" in q:
        return [
            {"label": "No warning signs (alert)", "value": "No warning signs, patient is alert and drinking fluids"},
            {"label": "Confusion / drowsiness", "value": "Patient is confused and drowsy"},
            {"label": "Stiff neck", "value": "Patient has a stiff neck"},
            {"label": "Inability to hold fluids", "value": "Persistent vomiting, unable to hold fluids"},
        ]

    if "heart disease" in q or "heart history" in q or "blood pressure" in q:
        return [
            {"label": "No prior heart history", "value": "No heart history or cardiac condition"},
            {"label": "Yes, heart disease / prior attack", "value": "Yes, history of heart condition or heart attack"},
            {"label": "High blood pressure", "value": "Yes, history of high blood pressure"},
        ]

    if "blood in vomit" in q or "blood in stool" in q:
        return [
            {"label": "No blood present", "value": "No blood in vomit or stool, abdomen is soft"},
            {"label": "Yes, blood in vomit", "value": "Yes, blood in vomit"},
            {"label": "Yes, bloody or black stool", "value": "Yes, bloody or black stool"},
            {"label": "Abdomen is rock-hard / rigid", "value": "Abdomen is rigid and rock-hard"},
        ]

    if "getting worse" in q or "start suddenly" in q or "suddenly" in q:
        return [
            {"label": "Started gradually, steady", "value": "Started gradually, stable"},
            {"label": "Sudden onset & worsening rapidly", "value": "Started suddenly and getting worse rapidly"},
            {"label": "Comes and goes in episodes", "value": "Comes and goes in episodes"},
        ]

    if "severe are your symptoms" in q or "severe are the symptoms" in q:
        return [
            {"label": "Mild (manageable at home)", "value": "Symptoms are mild, general fatigue"},
            {"label": "Moderate (slowed down)", "value": "Symptoms are moderate"},
            {"label": "Severe (bedridden / distress)", "value": "Symptoms are severe, unable to function"},
        ]

    if "swelling in your lips" in q or "lips, tongue" in q:
        return [
            {"label": "No swelling in lips or throat", "value": "No swelling in lips, tongue, or throat, airway is clear"},
            {"label": "Mild lip swelling, breathing normal", "value": "Mild swelling in lips, breathing normally"},
            {"label": "Throat tightness / Hard to breathe", "value": "Severe throat swelling and difficulty breathing"},
        ]

    if "widespread hives" in q or "itching, or swelling" in q or "hives" in q:
        return [
            {"label": "No hives or rash", "value": "No hives or rash present"},
            {"label": "Mild localized rash", "value": "Mild localized rash and slight itching"},
            {"label": "Widespread itchy hives all over", "value": "Widespread hives and intense itching across the body"},
        ]

    if "allergic symptoms develop" in q or "rapidly did these" in q:
        return [
            {"label": "Within minutes (< 30 min)", "value": "Symptoms started rapidly within minutes after exposure"},
            {"label": "Over a few hours", "value": "Symptoms developed over several hours"},
            {"label": "Gradual over days", "value": "Symptoms started gradually over a couple of days"},
        ]

    if "thunderclap" in q or "come on suddenly like" in q:
        return [
            {"label": "Sudden severe thunderclap", "value": "Sudden severe explosive thunderclap headache"},
            {"label": "Gradual onset over hours", "value": "Headache built up gradually over several hours"},
            {"label": "Comes and goes intermittently", "value": "Headache comes and goes in waves"},
        ]

    if "vision changes" in q or "sensitivity to light" in q or "weakness/numbness" in q:
        return [
            {"label": "No vision changes or weakness", "value": "No vision changes, no weakness or numbness"},
            {"label": "Sensitive to light / sound", "value": "Sensitive to bright light and sound, throbbing"},
            {"label": "Vision aura / blurry", "value": "Experiencing blurry vision and aura"},
            {"label": "Weakness / numbness on one side", "value": "Sudden weakness and numbness on one side of body"},
        ]

    if "blistering" in q or "skin peeling" in q or "open burns" in q:
        return [
            {"label": "No blisters or peeling (intact)", "value": "Skin is intact, no blistering or open wounds"},
            {"label": "Visible blisters / peeling", "value": "Visible blisters and skin peeling present"},
            {"label": "Severe open burns / spreading", "value": "Severe open burn with extensive blistering and rapid spread"},
        ]

    if "burning, pain, or itching" in q:
        return [
            {"label": "Mild discomfort / itching", "value": "Mild itching and slight discomfort"},
            {"label": "Moderate burning pain", "value": "Moderate burning pain"},
            {"label": "Severe, excruciating pain", "value": "Severe and excruciating burning pain"},
        ]

    if "chemical" in q or "foreign object" in q or "strike the eye" in q:
        return [
            {"label": "Chemical splash (cleaning/acid)", "value": "Chemical splash in the eye, chemical exposure"},
            {"label": "Direct impact / object in eye", "value": "Direct physical trauma or object hit the eye"},
            {"label": "No trauma / spontaneous redness", "value": "No chemical or trauma, spontaneous redness and irritation"},
        ]

    if "loss or blurring of vision" in q or "severe eye pain" in q:
        return [
            {"label": "Normal vision, mild irritation", "value": "Vision is normal, just mild eye irritation"},
            {"label": "Blurry vision with moderate pain", "value": "Blurry vision and moderate eye discomfort"},
            {"label": "Sudden loss of vision / severe pain", "value": "Sudden loss of vision with severe acute eye pain"},
        ]

    if "difficulty swallowing, breathing, or speaking" in q:
        return [
            {"label": "Can swallow and speak fine", "value": "I can swallow, speak, and breathe fine"},
            {"label": "Painful to swallow, but managing", "value": "Painful to swallow food, but can drink fluids and speak"},
            {"label": "Cannot swallow / choking feeling", "value": "Cannot swallow saliva, choking feeling and tight airway"},
        ]

    if "throat or ear pain" in q:
        return [
            {"label": "Mild scratchy discomfort", "value": "Mild scratchy sore throat or ear discomfort"},
            {"label": "Moderate pain", "value": "Moderate throat and ear pain, difficult to eat"},
            {"label": "Severe piercing pain", "value": "Severe piercing pain in ear or throat"},
        ]

    if "blood in the urine" in q or "lower back or flank" in q:
        return [
            {"label": "No blood, no back pain", "value": "No blood in urine and no lower back or flank pain"},
            {"label": "Visible blood in urine", "value": "Visible blood in urine, pink or reddish"},
            {"label": "Severe lower back / flank pain", "value": "Excruciating lower back and flank pain, suspect kidney stone"},
        ]

    if "burning sensation or pain when urinating" in q:
        return [
            {"label": "Mild burning / slight frequency", "value": "Mild burning sensation and increased frequency"},
            {"label": "Moderate burning pain", "value": "Moderate burning pain when urinating"},
            {"label": "Severe sharp pain urinating", "value": "Severe sharp pain and intense burning when passing urine"},
        ]

    if "distress or anxiety right now" in q:
        return [
            {"label": "Mild anxiety, manageable", "value": "Mild anxiety, feeling uneasy but coping"},
            {"label": "Moderate distress / overwhelmed", "value": "Moderate anxiety and feeling overwhelmed"},
            {"label": "Severe acute panic attack", "value": "Severe panic attack, feeling terrified and heart racing"},
        ]

    if "safe environment right now" in q:
        return [
            {"label": "Yes, safe with family/friends", "value": "Yes, I am in a safe environment with family"},
            {"label": "Alone, but physically safe", "value": "I am alone right now, but physically safe"},
            {"label": "Need immediate crisis support", "value": "I am in acute distress and need immediate support"},
        ]

    return [
        {"label": "Yes", "value": "Yes"},
        {"label": "No", "value": "No"},
        {"label": "Not sure", "value": "Not sure / unknown"},
    ]

