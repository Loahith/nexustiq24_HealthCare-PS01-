"""Pydantic models used across the API layer."""

from __future__ import annotations

from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field


class ChatRequest(BaseModel):
    case_id: Optional[str] = Field(
        default=None, description="Existing case id, omit to start a new case"
    )
    patient_id: Optional[str] = Field(default=None)
    message: str = Field(..., description="Patient's free-text message")
    patient_name: Optional[str] = None
    age: Optional[int] = None
    sex: Optional[str] = None
    medical_history: Optional[str] = None
    allergies: Optional[str] = None
    vitals: Optional[Dict[str, Any]] = None
    gemini_api_key: Optional[str] = None


class ApiKeyRequest(BaseModel):
    api_key: str


class SettingsResponse(BaseModel):
    model_config = {"protected_namespaces": ()}
    gemini_enabled: bool
    has_api_key: bool
    model_name: str
    active_mode: str  # "gemini_live" or "universal_clinical_fallback"


class QuestionOption(BaseModel):
    label: str
    value: str


class ChatResponse(BaseModel):
    case_id: str
    patient_id: str
    assistant_message: str
    current_question: Optional[str] = None
    options: List[QuestionOption] = []
    follow_up_questions: List[str] = []
    symptoms_identified: List[str] = []
    missing_information: List[str] = []
    ready_for_triage: bool = False
    triage: Optional[Dict[str, Any]] = None


class TriageRequest(BaseModel):
    case_id: str


class TriageRuleHit(BaseModel):
    rule_id: str
    description: str
    outcome: str


class TriageResult(BaseModel):
    case_id: str
    symptoms_identified: List[str]
    missing_information: List[str]
    urgency_level: str
    recommended_department: str
    triggered_rules: List[TriageRuleHit]
    reasoning: str
    evidence: List[Dict[str, str]] = []
    escalation_required: bool
    confidence: float
    timestamp: str


class CaseSummary(BaseModel):
    case_id: str
    patient_id: str
    chief_complaint: Optional[str]
    status: str
    urgency_level: Optional[str]
    department: Optional[str]
    escalation_required: bool
    created_at: str
    updated_at: str


class AnalyticsResponse(BaseModel):
    total_cases: int
    emergency_cases: int
    urgent_cases: int
    standard_cases: int
    escalated_cases: int
    department_distribution: Dict[str, int]
    urgency_over_time: List[Dict[str, Any]] = []
