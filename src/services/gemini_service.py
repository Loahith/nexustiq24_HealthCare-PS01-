"""
Gemini AI integration for dynamic, multi-specialty clinical intake triage.

Capabilities:
1. Live network AI triage via Google Gemini:
   - Evaluates any patient complaint across any medical specialty.
   - Analyzes multi-factor inputs: Demographics, Medical History, Allergies, and Vitals.
   - Assesses clinical seriousness, acuity, progression, and red flags.
   - Communicates with a warm, empathetic bedside manner.
   - Drives 1-by-1 follow-up questioning with tailored multiple-choice options.
   - Strictly obeys clinical safety guidelines (never diagnoses, routes appropriately).
2. Universal offline clinical fallback:
   - Covers 15+ hospital specialties deterministically if offline or if no API key is set.
   - Formats acknowledgements naturally and conversationally without exposing raw internal variables.
"""

from __future__ import annotations

import json
import logging
import os
import re
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

logger = logging.getLogger("nexustiq24.gemini")

TRIAGE_SYSTEM_INSTRUCTION = """You are an expert, compassionate clinical triage nurse assistant at a modern hospital intake center.
Your role is to warmly communicate with patients, assess the seriousness and acuity of their condition, ask 1 targeted follow-up question at a time, and route them to the appropriate medical department.

CRITICAL CLINICAL & COMMUNICATION GUIDELINES:
1. BED-SIDE MANNER: Speak with genuine warmth, empathy, and reassurance. Never sound robotic or cold.
2. ABSOLUTE DIAGNOSTIC PROHIBITION: NEVER provide a definitive medical diagnosis. Never prescribe medications. You screen acuity and route patients; only physicians diagnose.
3. SCREEN SERIOUSNESS: Systematically evaluate symptom severity (1-10), onset/duration, progression (sudden vs gradual), red flags (airway, breathing, chest, neuro, bleeding), and relevant vitals/medical history.
4. PACING: Ask only ONE clear follow-up question at a time.
5. MULTIPLE CHOICE: Always provide 3 to 4 concise, patient-friendly multiple choice options for your question.
6. UNIVERSAL COVERAGE: You handle ANY disease or complaint:
   - Cardiology (chest pain, palpitations) -> Emergency Medicine / Cardiology
   - Pulmonology (breathing distress, asthma flare) -> Emergency Medicine / Pulmonology
   - Neurology (migraines, acute headaches, stroke signs, seizures) -> Emergency Medicine / Neurology
   - Allergy & Immunology (anaphylaxis, hives, angioedema) -> Emergency Medicine / Allergy & Immunology
   - Dermatology (burns, rashes, infections) -> Dermatology / Emergency Medicine
   - Ophthalmology (eye trauma, chemical splash, vision loss) -> Emergency Medicine / Ophthalmology
   - Gastroenterology (severe abdominal pain, vomiting, GI bleed) -> Emergency Medicine / Gastroenterology
   - Orthopedics (fractures, joint trauma, inability to bear weight) -> Orthopedics / Emergency Medicine
   - ENT (ear infections, severe throat swelling, epistaxis) -> ENT / Emergency Medicine
   - Urology / Nephrology (flank pain, hematuria, severe dysuria) -> Urology / Emergency Medicine
   - Psychiatry (panic attack, crisis) -> Psychiatry / Emergency Medicine
   - General Medicine / Pediatrics (fevers, malaise, viral illness) -> General Medicine / Pediatrics
7. DECISION TO TRIAGE:
   - If an immediate life-threatening emergency is detected (e.g. severe chest pain radiating to arm, anaphylaxis with throat swelling, sudden thunderclap headache, chemical in eye, massive bleeding, SpO2 < 90%), mark `ready_for_triage: true` immediately.
   - Otherwise, ask 2 to 4 targeted questions to thoroughly understand the acuity, then mark `ready_for_triage: true`.
8. OUTPUT FORMAT: Always respond in valid JSON matching the exact schema specified.
"""


class GeminiService:
    def __init__(self) -> None:
        self.enabled = False
        self._model = None
        self.model_name = "gemini-1.5-flash"
        api_key = os.environ.get("GEMINI_API_KEY", "").strip()
        if api_key:
            self._init_client(api_key)

    def _init_client(self, api_key: str) -> bool:
        try:
            import google.generativeai as genai

            genai.configure(api_key=api_key)
            self._model = genai.GenerativeModel(
                model_name=self.model_name,
                system_instruction=TRIAGE_SYSTEM_INSTRUCTION,
            )
            self.enabled = True
            logger.info("Gemini live model successfully initialized with model %s", self.model_name)
            return True
        except Exception as exc:
            logger.warning("Gemini configuration failed: %s", exc)
            self.enabled = False
            self._model = None
            return False

    def set_api_key(self, api_key: str) -> Tuple[bool, str]:
        """Test and activate a user-provided Gemini API key, persisting it to .env."""
        clean_key = (api_key or "").strip()
        if not clean_key:
            self.enabled = False
            self._model = None
            os.environ["GEMINI_API_KEY"] = ""
            self._persist_key_to_env("")
            return True, "Gemini API key cleared. Operating in universal offline mode."

        try:
            import google.generativeai as genai

            genai.configure(api_key=clean_key)
            test_model = genai.GenerativeModel("gemini-1.5-flash")
            # Quick verification call
            resp = test_model.generate_content("Respond with: OK")
            if not resp or not resp.text:
                return False, "Gemini service did not return a valid verification response."

            os.environ["GEMINI_API_KEY"] = clean_key
            self._init_client(clean_key)
            self._persist_key_to_env(clean_key)
            return True, f"Successfully connected to Google Gemini AI ({self.model_name})."
        except Exception as exc:
            logger.error("Failed to authenticate Gemini API key: %s", exc)
            return False, f"Gemini connection failed: {str(exc)}"

    def get_status(self) -> Dict[str, Any]:
        return {
            "gemini_enabled": self.enabled,
            "has_api_key": bool(self.enabled and os.environ.get("GEMINI_API_KEY")),
            "model_name": self.model_name,
            "active_mode": "gemini_live" if self.enabled else "universal_clinical_fallback",
        }

    def _persist_key_to_env(self, api_key: str) -> None:
        try:
            env_file = Path(".env")
            if env_file.exists():
                text = env_file.read_text(encoding="utf-8")
                if re.search(r"^GEMINI_API_KEY=.*$", text, flags=re.MULTILINE):
                    text = re.sub(r"^GEMINI_API_KEY=.*$", f"GEMINI_API_KEY={api_key}", text, flags=re.MULTILINE)
                else:
                    text += f"\nGEMINI_API_KEY={api_key}\n"
                env_file.write_text(text, encoding="utf-8")
            else:
                env_file.write_text(f"GEMINI_API_KEY={api_key}\n", encoding="utf-8")
        except Exception as err:
            logger.warning("Could not persist API key to .env file: %s", err)

    def conduct_dynamic_triage_turn(
        self,
        patient_profile: Dict[str, Any],
        conversation_history: List[Dict[str, str]],
        current_message: str,
        extracted_flags: List[str],
        step_count: int,
    ) -> Optional[Dict[str, Any]]:
        """Conduct an empathetic dynamic intake turn using live Gemini network call."""
        if not self.enabled or self._model is None:
            return None

        prompt = self._build_dynamic_prompt(
            patient_profile, conversation_history, current_message, extracted_flags, step_count
        )

        try:
            response = self._model.generate_content(
                prompt,
                generation_config={"response_mime_type": "application/json", "temperature": 0.2},
            )
            raw_text = response.text.strip()
            # Clean possible markdown wrapping
            if raw_text.startswith("```json"):
                raw_text = raw_text[7:]
            if raw_text.startswith("```"):
                raw_text = raw_text[3:]
            if raw_text.endswith("```"):
                raw_text = raw_text[:-3]

            parsed = json.loads(raw_text.strip())
            logger.info("Gemini live triage turn successful: ready=%s", parsed.get("ready_for_triage"))
            return parsed
        except Exception as exc:
            logger.warning("Gemini live turn failed, falling back to universal clinical engine: %s", exc)
            return None

    def _build_dynamic_prompt(
        self,
        patient_profile: Dict[str, Any],
        conversation: List[Dict[str, str]],
        current_message: str,
        flags: List[str],
        step_count: int,
    ) -> str:
        # Build vitals summary
        vitals = patient_profile.get("vitals") or {}
        vitals_str = ", ".join(f"{k}: {v}" for k, v in vitals.items() if v is not None) or "None recorded"

        # Format past dialogue
        dialogue = []
        for turn in conversation[-8:]:  # last 8 turns for context
            role_label = "Patient" if turn.get("role") == "patient" else "Assistant"
            dialogue.append(f"{role_label}: {turn.get('message', '')}")
        dialogue_str = "\n".join(dialogue) if dialogue else "First interaction"

        return f"""PATIENT CLINICAL PROFILE:
- Name: {patient_profile.get('patient_name') or 'Not specified'}
- Age: {patient_profile.get('age') or 'Not specified'} | Sex: {patient_profile.get('sex') or 'Not specified'}
- Medical History: {patient_profile.get('medical_history') or 'None reported'}
- Known Allergies: {patient_profile.get('allergies') or 'None reported'}
- Vital Signs: {vitals_str}

CONVERSATION TRANSCRIPT:
{dialogue_str}

PATIENT'S LATEST MESSAGE:
"{current_message}"

INTAKE STATUS:
- Turn count: {step_count}
- Symptoms/Signals noted: {', '.join(flags) or 'Initial statement'}

TASK:
1. Formulate a warm, compassionate 1-2 sentence acknowledgement of what the patient just shared (comforting, bedside approach, NO robotic flag names).
2. Determine if we have sufficient clinical clarity or an acute red-flag emergency to conclude triage now:
   - If emergency red flag (e.g. anaphylaxis, severe cardiac chest pain radiating to arm, acute stroke signs, low oxygen SpO2 < 90, massive bleed) -> mark `ready_for_triage: true`.
   - If turn count >= 3 and primary symptoms, severity, and key red flags have been addressed -> mark `ready_for_triage: true`.
   - Otherwise -> mark `ready_for_triage: false`.
3. If `ready_for_triage` is false:
   - Ask ONE single, clear, empathetic follow-up clinical question.
   - Provide 3 to 4 multiple-choice options with `label` (short text) and `value` (full patient sentence).
4. If `ready_for_triage` is true:
   - Set `urgency_level` to "EMERGENCY" (life-threatening), "URGENT" (serious, prompt care), or "STANDARD" (routine/outpatient).
   - Set `recommended_department` to the most appropriate specialty (e.g. Emergency Medicine, Neurology, Allergy & Immunology, Pulmonology, Dermatology, Ophthalmology, Gastroenterology, Orthopedics, ENT, Urology, Psychiatry, General Medicine).
   - Set `reasoning` explaining the clinical rationale and acuity.
   - Set `triage_explanation` giving a warm, reassuring summary to the patient with next steps (no diagnosis).

Respond with valid JSON adhering to this schema:
{{
  "acknowledgement": "Warm, empathetic response to patient",
  "ready_for_triage": boolean,
  "current_question": string or null,
  "options": [
    {{"label": "Short button text", "value": "Detailed response"}}
  ],
  "urgency_level": "EMERGENCY" | "URGENT" | "STANDARD",
  "recommended_department": "Department Name",
  "reasoning": "Clinical justification",
  "triage_explanation": "Reassuring explanation for the patient"
}}"""

    def acknowledge_and_ask(
        self,
        patient_message: str,
        symptoms_identified: List[str],
        follow_up_questions: List[str],
        turn_count: int = 1,
    ) -> str:
        """Empathetic conversational response generator."""
        if self.enabled and self._model:
            try:
                clean_symptoms = self._clean_flags_for_patient(symptoms_identified)
                q_text = follow_up_questions[0] if follow_up_questions else ""
                prompt = (
                    f"Patient message: \"{patient_message}\"\n"
                    f"Intake conversation turn: {turn_count}\n"
                    f"Clinical facts noted: {clean_symptoms or 'patient report'}\n"
                    f"Next clinical question: {q_text}\n\n"
                    "Write a warm, compassionate, bedside-manner response (1-2 sentences). "
                    "Acknowledge the patient's specific statement with empathy and vary your phrasing dynamically. "
                    "Then naturally present the question without repeating robotic openings. "
                    "Do NOT list technical variable names. Do NOT diagnose."
                )
                response = self._model.generate_content(prompt)
                return response.text.strip()
            except Exception as exc:
                logger.warning("Gemini acknowledge call failed: %s", exc)

        return self._template_acknowledge(patient_message, symptoms_identified, follow_up_questions, turn_count)

    def explain_triage(self, triage_result: dict) -> str:
        """Generate patient-facing plain language explanation of the triage outcome."""
        if self.enabled and self._model:
            try:
                prompt = (
                    "Explain this triage recommendation to the patient in warm, comforting language. "
                    "Mention urgency level, recommended department, and that an attending medical team "
                    f"will evaluate them directly. Do NOT diagnose.\n\nTriage data: {triage_result}"
                )
                response = self._model.generate_content(prompt)
                return response.text.strip()
            except Exception as exc:
                logger.warning("Gemini explain call failed: %s", exc)

        return self._template_explain(triage_result)

    @staticmethod
    def _clean_flags_for_patient(symptoms: List[str]) -> str:
        """Transform internal boolean flags into human-friendly symptom descriptions."""
        internal_exclude = {
            "duration_given", "fever_checked", "severity_given", "no_severe_signs",
            "warning_signs_checked", "temperature_unknown", "oxygen_unknown",
            "injury_location_given", "abdominal_location_given", "no_breathing_difficulty",
            "no_chest_pain", "no_dizziness", "no_bleeding", "no_asthma_history",
            "no_vomiting", "no_swelling", "no_radiation", "no_gi_bleeding",
            "no_heart_history", "can_walk", "no_facial_throat_swelling", "unclear_input"
        }
        labels = []
        mapping = {
            "chest_pain": "chest discomfort",
            "breathing_difficulty": "breathing difficulty",
            "breathing_difficulty_severe": "severe shortness of breath",
            "chest_pain_radiating": "radiating chest discomfort",
            "abdominal_pain": "abdominal discomfort",
            "abdominal_pain_severe": "severe abdominal pain",
            "fever_over_103": "high fever",
            "fever_mild": "mild fever",
            "fever_over_5_days": "prolonged fever",
            "anaphylaxis_signs": "allergic reaction symptoms",
            "allergic_reaction_urgent": "allergic reaction",
            "facial_or_throat_swelling": "lip/throat swelling",
            "hives_or_rash": "hives or rash",
            "headache_thunderclap": "acute thunderclap headache",
            "migraine_severe": "severe migraine",
            "migraine_symptoms": "migraine symptoms",
            "neurological_signs": "neurological symptoms",
            "neurological_emergency": "acute neurological symptoms",
            "eye_chemical_or_trauma": "eye injury / chemical exposure",
            "acute_vision_loss": "acute vision changes",
            "burn_severe": "severe burn",
            "severe_skin_condition": "acute skin condition",
            "ent_urgent": "ear or throat distress",
            "urinary_urgent": "urinary symptoms",
            "hematuria_or_flank": "flank pain / urinary symptoms",
            "psychiatric_crisis": "acute distress",
            "low_oxygen": "low oxygen saturation",
            "cannot_walk": "difficulty walking",
            "severe_bleeding": "active bleeding",
            "deformity_or_swelling": "swelling",
            "back_pain": "back pain",
            "joint_pain": "joint pain",
            "vomiting": "nausea and vomiting",
            "general_symptoms_mild": "mild symptoms",
        }
        seen = set()
        for s in symptoms:
            if s in internal_exclude:
                continue
            lbl = mapping.get(s, s.replace("_", " "))
            if lbl not in seen:
                seen.add(lbl)
                labels.append(lbl)
        return ", ".join(labels[:2])

    @classmethod
    def _template_acknowledge(
        cls,
        patient_message: str,
        symptoms: List[str],
        questions: List[str],
        turn_count: int = 1,
    ) -> str:
        lowered = (patient_message or "").lower().strip()
        parts = []

        # 1. Detect if input was gibberish / keysmash / unclear
        has_vowel = bool(re.search(r"[aeiouy]", lowered))
        is_smash = bool(re.search(r"[bcdfghjklmnpqrstvwxz]{5,}", lowered))
        is_unclear = (len(lowered) > 4 and not has_vowel) or is_smash or "unclear_input" in symptoms

        # 2. Extract clinical complaint category keywords in the message
        clean_symptom = cls._clean_flags_for_patient(symptoms)

        # 3. Detect specific conversational responses
        is_severity = bool(re.search(r"\b(mild|moderate|severe|unbearable|excruciating|slight|bad|sharp|dull|[1-9]/10|10/10)\b", lowered))
        is_duration = bool(re.search(r"\b(today|yesterday|hours?|days?|weeks?|months?|just started|since|morning|afternoon|night|sudden|gradual)\b", lowered))
        is_no = bool(re.search(r"\b(no\b|none|not really|nope|negative|without|normal|denies|healthy)\b", lowered))
        is_yes = bool(re.search(r"\b(yes\b|yeah|yep|sure|present|positive|i do|i have)\b", lowered))

        if is_unclear:
            unclear_phrases = [
                "I didn't quite catch that, but let's work together to understand what you're experiencing.",
                "Thank you for bearing with me. Let's take it step by step to assess your condition.",
                "I understand it can be hard to describe symptoms right now. Let's focus on keeping you safe.",
                "Thank you. Let's make sure we check your symptoms carefully.",
            ]
            parts.append(unclear_phrases[(turn_count - 1) % len(unclear_phrases)])
        elif is_severity:
            if any(w in lowered for w in ["severe", "unbearable", "excruciating", "7", "8", "9", "10"]):
                parts.append("I understand your symptoms are intense and severe. We want to ensure you get prompt clinical attention.")
            elif "moderate" in lowered or any(w in lowered for w in ["4", "5", "6"]):
                parts.append("Thank you for letting me know this is moderately uncomfortable. That helps us gauge your priority.")
            else:
                parts.append("Thank you for noting that the discomfort is mild. We will still ensure it is evaluated properly.")
        elif is_duration:
            parts.append("Thank you for clarifying when this began. Having a clear timeline is very helpful for our clinical team.")
        elif is_no:
            no_phrases = [
                "Understood, that is reassuring and helps rule out urgent complications.",
                "Thank you for confirming that.",
                "Noted, I've recorded that for the evaluating clinician.",
            ]
            parts.append(no_phrases[(turn_count - 1) % len(no_phrases)])
        elif is_yes:
            yes_phrases = [
                "Thank you for confirming that with me.",
                "Understood, I am documenting that carefully for your care team.",
                "Noted. We will factor that into your clinical assessment.",
            ]
            parts.append(yes_phrases[(turn_count - 1) % len(yes_phrases)])
        elif clean_symptom:
            symptom_phrases = [
                f"Thank you for sharing that with me. I understand you are dealing with {clean_symptom}, and we want to ensure you receive prompt care.",
                f"I hear you, and {clean_symptom} can certainly be distressing. Let's evaluate this carefully.",
                f"Thank you for explaining your {clean_symptom}. We'll gather the key details for the clinical team.",
            ]
            parts.append(symptom_phrases[(turn_count - 1) % len(symptom_phrases)])
        else:
            openers = [
                "Thank you for reaching out. I'm here to assess your symptoms and guide you to the right care.",
                "Thank you for providing that detail. Let's continue assessing your condition.",
                "Understood. We are gathering the essential clinical details for the attending team.",
                "Thank you for bearing with me as we review these vital safety checks.",
            ]
            parts.append(openers[(turn_count - 1) % len(openers)])

        # Connect with the next question or conclusion
        if questions:
            q = questions[0]
            if len(parts) > 0 and not parts[0].endswith("?"):
                parts.append(f"{q}")
            else:
                parts.append(q)
        else:
            parts.append("I have collected the essential clinical information needed to complete your intake triage.")

        return " ".join(parts)

    @staticmethod
    def _template_explain(triage_result: dict) -> str:
        urgency = triage_result.get("urgency_level", "STANDARD")
        dept = triage_result.get("recommended_department", "General Medicine")
        if urgency == "EMERGENCY":
            return (
                f"Based on your symptoms, this intake has been classified as high priority ({urgency}) "
                f"and routed to {dept} for prompt, immediate attention. Please check in with the triage nurse immediately. "
                "This assessment is not a formal medical diagnosis — a clinician will examine you directly."
            )
        elif urgency == "URGENT":
            return (
                f"Your symptoms have been reviewed and classified as {urgency} priority, routed to {dept}. "
                "Our medical team will evaluate you shortly. This assessment is not a formal diagnosis — a medical professional will conduct a comprehensive evaluation."
            )
        return (
            f"Your case has been categorized as {urgency} priority and routed to {dept}. "
            "You will be seen in order of arrival. Please inform the staff if your symptoms worsen. "
            "A physician will evaluate you directly."
        )


_service_singleton: Optional[GeminiService] = None


def get_gemini_service() -> GeminiService:
    global _service_singleton
    if _service_singleton is None:
        _service_singleton = GeminiService()
    return _service_singleton
