"""
Deterministic, keyword-based symptom/fact extraction.

This module NEVER diagnoses. It only turns free-text patient statements
into a set of boolean "flags" and numeric facts that the rule engine
(src/triage/engine.py) can evaluate. Extraction is intentionally
keyword/regex based (not LLM-based) so it is reproducible and auditable.
The optional Gemini service is used only to phrase natural-language
follow-up questions and summaries -- never to decide urgency.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from typing import Dict, List, Set

COMPLAINT_CATEGORIES = {
    "chest_pain": [
        "chest pain", "chest tightness", "chest pressure", "chest discomfort", "heart pain", "tight chest",
        "crushing chest", "chest hurts", "angina", "racing heart", "palpitations"
    ],
    "fever": [
        "fever", "temperature", "high temp", "feverish", "chills", "shivering", "sweating", "hot and cold",
        "body aches", "flu"
    ],
    "injury": [
        "injury", "injured", "sprain", "fracture", "fell", "fall", "twisted", "hit my", "hurt my",
        "back pain", "back ache", "back hurts", "neck pain", "shoulder pain", "knee pain", "ankle pain",
        "leg pain", "foot pain", "wrist pain", "hand pain", "arm pain", "elbow pain", "hip pain",
        "spine", "joint pain", "muscle pain", "cut my", "bleeding from", "bruise", "broken bone"
    ],
    "breathing_difficulty": [
        "shortness of breath", "breathing difficulty", "can't breathe", "cannot breathe", "difficulty breathing",
        "breathless", "wheezing", "cough", "coughing", "asthma", "gasping", "congested", "trouble breathing"
    ],
    "abdominal_pain": [
        "abdominal pain", "stomach pain", "stomach ache", "belly pain", "abdomen hurts", "tummy ache",
        "nausea", "vomiting", "throwing up", "diarrhea", "cramps", "upset stomach", "stomach cramps"
    ],
    "allergy": [
        "allergy", "allergic", "hives", "swelling in face", "lip swelling", "swollen lip",
        "swollen tongue", "anaphylaxis", "peanut", "bee sting", "food allergy", "itchy rash", "welts"
    ],
    "neurology": [
        "headache", "migraine", "head hurts", "head ache", "vision change", "numbness",
        "facial droop", "slurred speech", "weakness on one side", "thunderclap", "dizzy", "dizziness",
        "vertigo", "spinning", "lightheaded", "faint", "fainted", "tingling", "confusion"
    ],
    "dermatology": [
        "rash", "skin rash", "burn", "burned", "blister", "blisters", "itching", "itchy",
        "skin peeling", "skin infection", "eczema", "red spot", "skin sore", "boil"
    ],
    "ophthalmology": [
        "eye pain", "eye injury", "chemical splash", "vision loss", "blurry vision",
        "red eye", "pink eye", "swollen eye", "eye irritation", "chemical in eye", "eye hurts"
    ],
    "ent": [
        "ear pain", "earache", "sore throat", "throat pain", "ear infection", "difficulty swallowing",
        "swollen tonsils", "swollen throat", "ear discharge", "sinus pain", "ear hurts"
    ],
    "urology": [
        "pain urinating", "burning when urinating", "blood in urine", "flank pain",
        "kidney pain", "frequent urination", "dysuria", "hematuria", "pain peeing", "burning pee"
    ],
    "psychiatry": [
        "panic attack", "severe anxiety", "cannot calm down", "anxiety attack",
        "overwhelmed", "mental breakdown", "hyperventilating", "extreme distress", "panic"
    ],
}

FLAG_KEYWORDS = {
    "chest_pain": ["chest pain", "chest tightness", "chest pressure", "chest discomfort"],
    "breathing_difficulty": ["shortness of breath", "breathing difficulty", "can't breathe",
                             "cannot breathe", "difficulty breathing", "breathless", "wheezing"],
    "breathing_difficulty_severe": ["severe breathing", "can't breathe at all", "gasping", "turning blue"],
    "dizziness": ["dizzy", "dizziness", "lightheaded", "light-headed", "faint", "fainted"],
    "injury": ["injury", "injured", "sprain", "fracture", "fell", "fall", "twisted", "hit my", "hurt my"],
    "severe_bleeding": ["heavy bleeding", "severe bleeding", "won't stop bleeding", "bleeding a lot",
                         "blood everywhere", "uncontrolled bleeding"],
    "minor_bleeding": ["minor bleeding", "mild bleeding", "slight bleeding", "controlled bleeding",
                       "small cut", "scraped", "scratch", "bleeding slightly"],
    "cannot_walk": ["can't walk", "cannot walk", "unable to walk", "not able to walk", "can not walk"],
    "can_walk": ["i can walk", "walking fine", "walking normally", "can walk fine", "can walk normally", "can walk", "able to walk"],
    "deformity_or_swelling": ["deformity", "deformed", "very swollen", "severe swelling", "swollen badly", "swelling", "swollen"],
    "abdominal_pain": ["abdominal pain", "stomach pain", "stomach ache", "belly pain", "abdomen hurts"],
    "abdominal_pain_severe": ["severe abdominal pain", "excruciating stomach pain", "unbearable stomach pain",
                              "severe stomach pain"],
    "abdominal_pain_mild": ["mild abdominal pain", "mild stomach pain", "slight stomach pain"],
    "vomiting": ["vomiting", "throwing up", "vomited", "nausea and vomiting"],
    "asthma_history": ["asthma", "history of asthma", "asthmatic"],
    "low_oxygen": ["oxygen level is low", "spo2", "oxygen saturation", "low oxygen"],
    "chest_pain_radiating": ["radiat", "radiates", "radiating to arm", "radiating to jaw", "spread to arm", "left arm pain", "shoulder and jaw"],
    "no_radiation": ["no radiation", "does not radiate", "doesn't radiate", "stays in chest"],
    "gi_bleeding": ["blood in vomit", "throwing up blood", "bloody stool", "black stool", "blood in stool", "rigid abdomen", "rock hard abdomen"],
    "no_gi_bleeding": ["no blood", "no bleeding in stool", "soft abdomen"],
    "neurological_signs": ["confusion", "confused", "stiff neck", "neck is stiff", "lethargic", "unresponsive", "altered mental"],
    "heart_history": ["history of heart", "heart disease", "prior heart attack", "cardiac history", "heart condition", "angina"],
    "no_heart_history": ["no heart history", "no prior heart", "no heart disease"],
    "worsening_rapidly": ["getting worse rapidly", "getting much worse", "worsening quickly", "sudden and severe", "rapidly worsening"],
    "general_symptoms_mild": ["mild fatigue", "general fatigue", "mild weakness", "mild malaise", "just unwell"],
    # Universal specialty flags
    "facial_or_throat_swelling": ["swelling in face", "lip swelling", "swollen lip", "swollen tongue", "throat swelling", "swollen throat", "tight throat"],
    "no_facial_throat_swelling": ["no lip swelling", "no throat swelling", "no facial swelling", "airway is clear"],
    "hives_or_rash": ["hives", "welts", "allergic rash", "itchy hives"],
    "headache_thunderclap": ["thunderclap", "worst headache of my life", "sudden explosive headache", "sudden and severe headache"],
    "focal_neurological_deficit": ["facial droop", "slurred speech", "weakness on one side", "paralysis", "arm numbness"],
    "migraine_symptoms": ["migraine", "sensitive to light", "photophobia", "throbbing head", "aura"],
    "eye_chemical_or_trauma": ["chemical splash", "acid in eye", "bleach in eye", "chemical in eye", "penetrating eye", "stabbed in eye", "eye trauma"],
    "acute_vision_loss": ["vision loss", "sudden blindness", "cannot see", "loss of vision"],
    "burn_severe": ["severe burn", "second degree burn", "third degree burn", "blistered burn", "scalding"],
    "dysphagia_severe": ["cannot swallow", "unable to swallow", "choking feeling", "severe difficulty swallowing"],
    "hematuria_or_flank": ["blood in urine", "bloody urine", "severe flank pain", "kidney stone", "excruciating side pain"],
    "panic_severe": ["severe panic attack", "extreme panic", "cannot breathe from anxiety", "terrified", "severe mental distress"],
    "no_severe_signs": [],  # derived, not keyword based
}

NEGATION_MARKERS = ["no ", "not ", "none", "denies", "denying", "negative for", "without", "n't"]

# Maps a positive flag to the flag recorded when the same keyword phrase is
# found negated (e.g. "No breathing difficulty" -> no_breathing_difficulty,
# not breathing_difficulty). Flags with no entry are simply skipped when negated.
NEGATIVE_FLAG_MAP = {
    "chest_pain": "no_chest_pain",
    "breathing_difficulty": "no_breathing_difficulty",
    "dizziness": "no_dizziness",
    "severe_bleeding": "no_bleeding",
    "asthma_history": "no_asthma_history",
    "vomiting": "no_vomiting",
    "deformity_or_swelling": "no_swelling",
    "chest_pain_radiating": "no_radiation",
    "gi_bleeding": "no_gi_bleeding",
    "heart_history": "no_heart_history",
}

WORD_TO_NUM = {
    "one": 1, "two": 2, "three": 3, "four": 4, "five": 5,
    "six": 6, "seven": 7, "eight": 8, "nine": 9, "ten": 10,
}
DAYS_RE = re.compile(r"\b(\d+|one|two|three|four|five|six|seven|eight|nine|ten)\s*days?\b", re.IGNORECASE)
TEMP_F_RE = re.compile(r"(\d{2,3}(?:\.\d)?)\s*(?:°|deg(?:rees)?)?\s*f\b", re.IGNORECASE)
TEMP_C_RE = re.compile(r"(\d{2,3}(?:\.\d)?)\s*(?:°|deg(?:rees)?)?\s*c\b", re.IGNORECASE)


@dataclass
class ExtractionState:
    """Accumulates flags/facts across an entire conversation for one case."""

    flags: Set[str] = field(default_factory=set)
    facts: Dict[str, float] = field(default_factory=dict)
    categories: Set[str] = field(default_factory=set)
    raw_statements: List[str] = field(default_factory=list)
    asked_questions: List[str] = field(default_factory=list)
    turn_count: int = 0

    def merge_text(self, text: str) -> None:
        self.raw_statements.append(text)
        self.turn_count += 1
        lowered = text.lower().strip()

        has_vowel = bool(re.search(r"[aeiouy]", lowered))
        is_smash = bool(re.search(r"[bcdfghjklmnpqrstvwxz]{5,}", lowered))
        if (len(lowered) > 4 and not has_vowel) or is_smash:
            self.flags.add("unclear_input")
        else:
            self.flags.discard("unclear_input")

        for category, keywords in COMPLAINT_CATEGORIES.items():
            for kw in keywords:
                pos = lowered.find(kw)
                if pos == -1:
                    continue
                window = lowered[max(0, pos - 20):pos]
                if any(marker in window for marker in NEGATION_MARKERS):
                    continue
                self.categories.add(category)
                break

        for flag, keywords in FLAG_KEYWORDS.items():
            if not keywords:
                continue
            for kw in keywords:
                pos = lowered.find(kw)
                if pos == -1:
                    continue
                window = lowered[max(0, pos - 20):pos]
                negated = any(marker in window for marker in NEGATION_MARKERS)
                if negated:
                    neg_flag = NEGATIVE_FLAG_MAP.get(flag)
                    if neg_flag:
                        self.flags.add(neg_flag)
                else:
                    self.flags.add(flag)
                break

        # numeric facts
        days_match = DAYS_RE.search(lowered)
        if days_match:
            raw_d = days_match.group(1).lower()
            self.facts["duration_days"] = float(WORD_TO_NUM.get(raw_d, raw_d))

        temp_f = TEMP_F_RE.search(lowered)
        temp_c = TEMP_C_RE.search(lowered)
        if temp_f:
            self.facts["temperature_f"] = float(temp_f.group(1))
        elif temp_c:
            self.facts["temperature_f"] = float(temp_c.group(1)) * 9 / 5 + 32
        elif re.search(r"\b(10[3-9]|1[1-9]\d)\b", lowered) and "fever" in lowered:
            # bare number like "104 fever"
            m = re.search(r"\b(10[3-9]|1[1-9]\d)\b", lowered)
            if m:
                self.facts["temperature_f"] = float(m.group(1))

        # conversational answer extraction
        if re.search(r"\b(mild|moderate|severe|unbearable|excruciating|slight|bad|sharp|dull)\b", lowered):
            self.flags.add("severity_given")
            if "severe" in lowered:
                if "breathing_difficulty" in self.categories:
                    self.flags.add("breathing_difficulty_severe")
                if "abdominal_pain" in self.categories:
                    self.flags.add("abdominal_pain_severe")
            elif "mild" in lowered:
                if "abdominal_pain" in self.categories:
                    self.flags.add("abdominal_pain_mild")

        if days_match or re.search(r"\b(today|yesterday|hours?|weeks?|months?|just started|since|morning|afternoon|night)\b", lowered):
            self.flags.add("duration_given")

        if re.search(r"\b(leg|ankle|wrist|arm|knee|foot|feet|hand|shoulder|finger|toe|head|elbow|back|hip|neck|ribs?|face|thigh|shin)\b", lowered) or "on my" in lowered or "in my" in lowered:
            self.flags.add("injury_location_given")

        if re.search(r"\b(no bleeding|not bleeding|without bleeding|no bleed)\b", lowered) or "no bleeding" in lowered:
            self.flags.add("no_bleeding")
        elif re.search(r"\b(heavy bleeding|severe bleeding|won't stop bleeding|bleeding a lot|blood everywhere|uncontrolled bleeding)\b", lowered):
            self.flags.add("severe_bleeding")
        elif "bleed" in lowered:
            self.flags.add("minor_bleeding")

        if re.search(r"\b(lower right|lower left|upper right|upper left|lower|upper|belly button|navel|side|stomach|middle|central|all over|around|epigastric|quadrant)\b", lowered):
            self.flags.add("abdominal_location_given")

        if re.search(r"\b(no fever|not feverish|no temp|temperature normal|temp normal|without fever)\b", lowered) or "fever" in self.categories:
            self.flags.add("fever_checked")

        if re.search(r"\b(temperature unknown|temp unknown|not measured|haven't measured|have not measured|no thermometer|unknown temperature|don't have a thermometer)\b", lowered):
            self.flags.add("temperature_unknown")
            self.flags.add("fever_checked")

        if re.search(r"\b(radiat|arm|jaw|shoulder|neck|spread to)\b", lowered):
            if any(m in lowered for m in ["no radiat", "does not radiat", "doesn't radiat", "not radiat", "stays in", "just in chest", "localized", "none of these"]):
                self.flags.add("no_radiation")
            else:
                self.flags.add("chest_pain_radiating")
        elif "no radiation" in lowered or "stays in chest" in lowered:
            self.flags.add("no_radiation")

        if re.search(r"\b(blood in vomit|vomiting blood|bloody stool|black stool|blood in stool|rigid|rock hard)\b", lowered):
            if any(m in lowered for m in ["no blood", "no bloody", "soft"]):
                self.flags.add("no_gi_bleeding")
            else:
                self.flags.add("gi_bleeding")
        elif "no blood" in lowered or "soft abdomen" in lowered:
            self.flags.add("no_gi_bleeding")

        if re.search(r"\b(confusion|confused|stiff neck|lethargic|drowsy|unresponsive)\b", lowered):
            if any(m in lowered for m in ["no confu", "no stiff", "no drowsy", "none of these", "no warning signs"]):
                self.flags.add("warning_signs_checked")
            else:
                self.flags.add("neurological_signs")
        elif "no warning signs" in lowered or "none of the warning" in lowered:
            self.flags.add("warning_signs_checked")

        if re.search(r"\b(heart disease|prior heart|cardiac|heart attack|angina|hypertension|high blood pressure)\b", lowered):
            if any(m in lowered for m in ["no heart", "no prior heart", "no cardiac", "healthy heart"]):
                self.flags.add("no_heart_history")
            else:
                self.flags.add("heart_history")
        elif "no heart history" in lowered or "no cardiac" in lowered:
            self.flags.add("no_heart_history")

        if re.search(r"\b(unknown|don't know|do not know|not sure|haven't checked|have not checked|no oximeter|no spo2|not known|unmeasured)\b", lowered):
            self.flags.add("oxygen_unknown")
        spo2_m = re.search(r"\b(?:spo2|oxygen|o2)\D*?(\d{2,3})\b", lowered)
        if spo2_m:
            val = float(spo2_m.group(1))
            self.facts["spo2"] = val
            if val < 90:
                self.flags.add("low_oxygen")
            else:
                self.flags.add("oxygen_unknown")

        self._derive_composite_flags()

    def _derive_composite_flags(self) -> None:
        temp = self.facts.get("temperature_f")
        if temp is not None:
            if temp > 103:
                self.flags.add("fever_over_103")
            elif temp <= 100.4:
                pass
            else:
                self.flags.add("fever_mild")
        elif "temperature_unknown" in self.flags and "fever" in self.categories:
            duration = self.facts.get("duration_days")
            if duration is None or duration <= 3:
                self.flags.add("fever_mild")

        duration = self.facts.get("duration_days")
        if duration is not None and "fever" in self.categories:
            if duration > 5:
                self.flags.add("fever_over_5_days")
            elif duration <= 3 and "fever_over_103" not in self.flags:
                self.flags.add("fever_mild")

        if "injury" in self.categories:
            if "cannot_walk" not in self.flags and "severe_bleeding" not in self.flags \
                    and "deformity_or_swelling" not in self.flags and "can_walk" in self.flags:
                self.flags.add("no_severe_signs")

        # Allergy / Anaphylaxis
        if "allergy" in self.categories or "hives_or_rash" in self.flags or "facial_or_throat_swelling" in self.flags:
            raw_text = " ".join(self.raw_statements).lower()
            if ("breathing_difficulty" in self.flags or "breathing_difficulty_severe" in self.flags
                    or "facial_or_throat_swelling" in self.flags or "anaphylaxis" in raw_text):
                self.flags.add("anaphylaxis_signs")
            elif "severity_given" in self.flags and "mild" in raw_text and "hives_or_rash" not in self.flags:
                self.flags.add("mild_allergic_condition")
            else:
                self.flags.add("allergic_reaction_urgent")

        # Neurology
        if "neurology" in self.categories:
            raw_text = " ".join(self.raw_statements).lower()
            if "headache_thunderclap" in self.flags or "focal_neurological_deficit" in self.flags or "stroke" in raw_text:
                self.flags.add("neurological_emergency")
            elif "migraine_symptoms" in self.flags or "severe" in raw_text or "vomiting" in self.flags:
                self.flags.add("migraine_severe")
            elif "mild" in raw_text or "general_symptoms_mild" in self.flags:
                self.flags.add("mild_headache")
            else:
                self.flags.add("migraine_severe")

        # Ophthalmology
        if "ophthalmology" in self.categories:
            raw_text = " ".join(self.raw_statements).lower()
            if "eye_chemical_or_trauma" in self.flags or "acute_vision_loss" in self.flags or "severe" in raw_text:
                self.flags.add("eye_emergency")
            else:
                self.flags.add("mild_eye_condition")

        # Dermatology
        if "dermatology" in self.categories:
            raw_text = " ".join(self.raw_statements).lower()
            if "burn_severe" in self.flags or "blister" in raw_text or "severe" in raw_text or "peeling" in raw_text:
                self.flags.add("severe_skin_condition")
            else:
                self.flags.add("mild_skin_condition")

        # ENT
        if "ent" in self.categories:
            raw_text = " ".join(self.raw_statements).lower()
            if "dysphagia_severe" in self.flags or "severe" in raw_text or "breathing_difficulty" in self.flags:
                self.flags.add("ent_urgent")
            else:
                self.flags.add("mild_ent_condition")

        # Urology
        if "urology" in self.categories:
            raw_text = " ".join(self.raw_statements).lower()
            if "hematuria_or_flank" in self.flags or "severe" in raw_text or "fever" in self.categories:
                self.flags.add("urinary_urgent")
            else:
                self.flags.add("mild_urinary_condition")

        # Psychiatry
        if "psychiatry" in self.categories:
            self.flags.add("psychiatric_crisis")

        if "general_symptoms_mild" in self.flags or ("severity_given" in self.flags and not self.categories):
            self.flags.add("general_symptoms_mild")

    def required_questions(self) -> List[str]:
        """Return follow-up questions needed to evaluate the seriousness of the issue."""
        questions: List[str] = []

        if not self.categories:
            if not any("primary symptom" in q.lower() for q in self.asked_questions):
                questions.append("Which of the following best describes your primary symptom?")
            if "severity_given" not in self.flags and not any("severe" in q.lower() for q in self.asked_questions):
                questions.append("How severe are your symptoms on a scale from mild to severe?")
            if "duration_given" not in self.flags and not any("how long" in q.lower() for q in self.asked_questions):
                questions.append("How long have you been experiencing these symptoms?")
            if not ({"breathing_difficulty", "no_breathing_difficulty"} & self.flags) and not any("breathing" in q.lower() for q in self.asked_questions):
                questions.append("Is there any breathing difficulty?")
            if not ({"chest_pain", "no_chest_pain"} & self.flags) and not any("chest pain" in q.lower() for q in self.asked_questions):
                questions.append("Is there any chest pain?")
            return [q for q in questions if q not in self.asked_questions]

        if "allergy" in self.categories:
            if not ({"facial_or_throat_swelling", "no_facial_throat_swelling"} & self.flags):
                questions.append("Are you experiencing any swelling in your lips, tongue, or throat, or any difficulty breathing?")
            if not ({"hives_or_rash"} & self.flags):
                questions.append("Are there widespread hives, itching, or swelling on your body?")
            if "duration_given" not in self.flags:
                questions.append("How rapidly did these allergic symptoms develop?")
            if "severity_given" not in self.flags:
                questions.append("How severe are your symptoms (mild, moderate, or severe)?")

        if "neurology" in self.categories:
            if not ({"headache_thunderclap"} & self.flags):
                questions.append("Did this headache come on suddenly like a thunderclap, or has it built up gradually?")
            if not ({"focal_neurological_deficit", "migraine_symptoms"} & self.flags):
                questions.append("Are you experiencing any vision changes, sensitivity to light, or weakness/numbness on one side?")
            if "severity_given" not in self.flags:
                questions.append("How severe is the head pain on a scale from mild to severe?")
            if not ({"vomiting", "no_vomiting"} & self.flags):
                questions.append("Is there any vomiting or nausea?")

        if "dermatology" in self.categories:
            if not ({"burn_severe"} & self.flags):
                questions.append("Is there any blistering, skin peeling, open burns, or rapid spreading?")
            if "severity_given" not in self.flags:
                questions.append("How severe is the burning, pain, or itching?")
            if not ({"fever", "fever_checked"} & (self.categories | self.flags)):
                questions.append("Do you have any accompanying fever or chills?")

        if "ophthalmology" in self.categories:
            if not ({"eye_chemical_or_trauma"} & self.flags):
                questions.append("Did any chemical, foreign object, or high-impact trauma strike the eye?")
            if not ({"acute_vision_loss"} & self.flags):
                questions.append("Is there any sudden loss or blurring of vision, or severe eye pain?")
            if "severity_given" not in self.flags:
                questions.append("Is there noticeable redness, drainage, or discharge from the eye?")

        if "ent" in self.categories:
            if not ({"dysphagia_severe"} & self.flags):
                questions.append("Are you experiencing any severe difficulty swallowing, breathing, or speaking?")
            if "severity_given" not in self.flags:
                questions.append("How severe is the throat or ear pain (mild, moderate, or severe)?")
            if not ({"fever", "fever_checked"} & (self.categories | self.flags)):
                questions.append("Is there any fever, dizziness, or fluid discharge from the ear?")

        if "urology" in self.categories:
            if not ({"hematuria_or_flank"} & self.flags):
                questions.append("Is there any visible blood in the urine, or severe pain in your lower back or flank?")
            if "severity_given" not in self.flags:
                questions.append("How severe is the burning sensation or pain when urinating?")
            if not ({"fever", "fever_checked"} & (self.categories | self.flags)):
                questions.append("Are you having any fever, chills, or nausea?")

        if "psychiatry" in self.categories:
            if "severity_given" not in self.flags:
                questions.append("How severe is the distress or anxiety right now?")
            if not ({"breathing_difficulty", "chest_pain"} & self.flags):
                questions.append("Are you having chest tightness, rapid heart rate, or shortness of breath?")
            questions.append("Are you in a safe environment right now?")

        if "fever" in self.categories:
            if "temperature_f" not in self.facts and "temperature_unknown" not in self.flags:
                questions.append("What is the patient's current temperature?")
            if "duration_days" not in self.facts and "duration_given" not in self.flags:
                questions.append("How many days has the fever lasted?")
            if "severity_given" not in self.flags:
                questions.append("How severe are the symptoms (mild, moderate, or severe weakness)?")
            if not ({"breathing_difficulty", "no_breathing_difficulty"} & self.flags):
                questions.append("Is there any breathing difficulty?")
            if not ({"warning_signs_checked", "neurological_signs"} & self.flags):
                questions.append("Are there any warning signs such as confusion, stiff neck, or inability to keep fluids down?")

        if "injury" in self.categories:
            if "injury_location" not in self.facts and "injury_location_given" not in self.flags:
                questions.append("Where is the injury located?")
            if "severity_given" not in self.flags:
                questions.append("How severe is the pain on a scale from mild to severe?")
            if not ({"severe_bleeding", "no_bleeding", "minor_bleeding"} & self.flags):
                questions.append("Is there any bleeding?")
            if not ({"cannot_walk", "can_walk"} & self.flags):
                questions.append("Can the patient walk?")
            if not ({"deformity_or_swelling", "no_severe_signs", "no_swelling"} & self.flags):
                questions.append("Is there any swelling or visible deformity?")

        if "chest_pain" in self.categories:
            if "severity_given" not in self.flags:
                questions.append("How severe is the chest pain (mild/moderate/severe)?")
            if "duration_days" not in self.facts and "duration_given" not in self.flags:
                questions.append("How long has the chest pain been occurring?")
            if not ({"chest_pain_radiating", "no_radiation"} & self.flags):
                questions.append("Does the chest pain radiate to your left arm, shoulder, or jaw?")
            if not ({"breathing_difficulty", "no_breathing_difficulty"} & self.flags):
                questions.append("Is there any breathing difficulty along with the chest pain?")
            if not ({"dizziness", "no_dizziness"} & self.flags):
                questions.append("Is the patient feeling dizzy or lightheaded?")
            if not ({"heart_history", "no_heart_history"} & self.flags):
                questions.append("Do you have a personal history of heart disease or high blood pressure?")

        if "abdominal_pain" in self.categories:
            if "severity_given" not in self.flags:
                questions.append("How severe is the abdominal pain (mild/moderate/severe)?")
            if "abdominal_location_given" not in self.flags:
                questions.append("Where exactly is the abdominal pain located?")
            if "duration_days" not in self.facts and "duration_given" not in self.flags:
                questions.append("How long has the abdominal pain lasted?")
            if not ({"vomiting", "no_vomiting"} & self.flags):
                questions.append("Is there any vomiting?")
            if not ({"gi_bleeding", "no_gi_bleeding", "fever", "fever_checked"} & (self.categories | self.flags)):
                questions.append("Is there any fever, or any blood in vomit or stool?")

        if "breathing_difficulty" in self.categories:
            if "severity_given" not in self.flags:
                questions.append("How severe is the breathing difficulty (mild/moderate/severe)?")
            if "duration_days" not in self.facts and "duration_given" not in self.flags:
                questions.append("Did the breathing difficulty start suddenly, and is it getting worse?")
            if not ({"asthma_history", "no_asthma_history"} & self.flags):
                questions.append("Does the patient have a history of asthma?")
            if not ({"chest_pain", "no_chest_pain"} & self.flags):
                questions.append("Is there any chest pain?")
            if "low_oxygen" not in self.facts and "low_oxygen" not in self.flags \
                    and "oxygen_unknown" not in self.flags:
                questions.append("If known, what is the patient's oxygen saturation (SpO2) level?")

        # de-duplicate while preserving order AND filtering out questions already asked
        seen = set()
        unique = []
        for q in questions:
            if q not in seen and q not in self.asked_questions:
                seen.add(q)
                unique.append(q)
        return unique
