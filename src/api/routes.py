"""API route definitions for the Patient Intake Triage Assistant."""

from __future__ import annotations

import logging
import os
import uuid
from pathlib import Path

from fastapi import APIRouter, HTTPException
from fastapi.responses import FileResponse

from src.models.schemas import (
    AnalyticsResponse,
    ApiKeyRequest,
    ChatRequest,
    ChatResponse,
    QuestionOption,
    SettingsResponse,
    TriageRequest,
)
from src.services.gemini_service import get_gemini_service
from src.services.pdf_service import generate_report_json, generate_report_pdf
from src.triage import case_service

logger = logging.getLogger("nexustiq24.api")
router = APIRouter()

REPORTS_DIR = Path("data/generated_reports")


@router.get("/settings", response_model=SettingsResponse)
def get_settings() -> SettingsResponse:
    gemini = get_gemini_service()
    return SettingsResponse(**gemini.get_status())


@router.post("/settings/ai-key")
def update_ai_key(req: ApiKeyRequest) -> dict:
    gemini = get_gemini_service()
    success, message = gemini.set_api_key(req.api_key)
    return {"success": success, "message": message, "status": gemini.get_status()}


@router.post("/chat", response_model=ChatResponse)
def chat(req: ChatRequest) -> ChatResponse:
    if not req.message or not req.message.strip():
        raise HTTPException(status_code=400, detail="message must not be empty")

    gemini = get_gemini_service()

    # Optional runtime key passed with request
    if req.gemini_api_key and not gemini.enabled:
        gemini.set_api_key(req.gemini_api_key)

    patient_id = case_service.get_or_create_patient(
        patient_id=req.patient_id,
        name=req.patient_name,
        age=req.age,
        sex=req.sex,
        medical_history=req.medical_history,
        allergies=req.allergies,
        vitals=req.vitals,
    )
    case_id = case_service.get_or_create_case(req.case_id, patient_id, chief_complaint=req.message)

    state = case_service.process_patient_message(
        case_id=case_id,
        message=req.message,
        vitals=req.vitals,
        medical_history=req.medical_history,
        allergies=req.allergies,
    )

    # Build patient clinical profile for AI assessment
    patient_profile = {
        "patient_name": req.patient_name,
        "age": req.age,
        "sex": req.sex,
        "medical_history": req.medical_history,
        "allergies": req.allergies,
        "vitals": req.vitals or {},
    }

    detail = case_service.get_case_detail(case_id)
    conversation_history = detail.get("conversation", []) if detail else []
    step_count = len([t for t in conversation_history if t.get("role") == "patient"])

    # Attempt dynamic AI triage turn via live Gemini network
    ai_turn = gemini.conduct_dynamic_triage_turn(
        patient_profile=patient_profile,
        conversation_history=conversation_history,
        current_message=req.message,
        extracted_flags=sorted(state.flags),
        step_count=step_count,
    )

    if ai_turn:
        ready = bool(ai_turn.get("ready_for_triage"))
        urgency = ai_turn.get("urgency_level") or "STANDARD"
        dept = ai_turn.get("recommended_department") or "General Medicine"
        reasoning = ai_turn.get("reasoning") or ""

        if ready:
            triage_payload = case_service.run_triage(
                case_id=case_id,
                override_urgency=urgency,
                override_department=dept,
                override_reasoning=reasoning,
            )
            explanation = ai_turn.get("triage_explanation") or gemini.explain_triage(triage_payload)
            assistant_message = f"{ai_turn.get('acknowledgement', '')}\n\n{explanation}".strip()
            current_q = None
            options = []
            follow_ups = []
        else:
            triage_payload = None
            current_q = ai_turn.get("current_question")
            if current_q and current_q not in state.asked_questions:
                state.asked_questions.append(current_q)
            options_data = ai_turn.get("options") or []
            options = [QuestionOption(label=opt["label"], value=opt["value"]) for opt in options_data]
            follow_ups = [current_q] if current_q else []
            ack = ai_turn.get("acknowledgement", "").strip()
            assistant_message = f"{ack} {current_q}".strip() if current_q else ack

        case_service.log_assistant_turn(case_id, assistant_message, question=current_q)

        return ChatResponse(
            case_id=case_id,
            patient_id=patient_id,
            assistant_message=assistant_message,
            current_question=current_q,
            options=options,
            follow_up_questions=follow_ups,
            symptoms_identified=sorted(state.flags),
            missing_information=follow_ups,
            ready_for_triage=ready,
            triage=triage_payload,
        )

    # Universal Clinical Offline Fallback
    follow_ups = state.required_questions()
    ready = case_service.should_triage_now(state)

    current_q = None
    options = []
    if not ready and follow_ups:
        current_q = follow_ups[0]
        if current_q not in state.asked_questions:
            state.asked_questions.append(current_q)
        options_data = case_service.get_question_options(current_q)
        options = [QuestionOption(label=opt["label"], value=opt["value"]) for opt in options_data]

    assistant_message = gemini.acknowledge_and_ask(
        patient_message=req.message,
        symptoms_identified=sorted(state.flags),
        follow_up_questions=[current_q] if current_q else [],
        turn_count=state.turn_count,
    )

    triage_payload = None
    if ready:
        triage_payload = case_service.run_triage(case_id)
        explanation = gemini.explain_triage(triage_payload)
        assistant_message = f"{assistant_message}\n\n{explanation}"

    case_service.log_assistant_turn(case_id, assistant_message, question=current_q)

    return ChatResponse(
        case_id=case_id,
        patient_id=patient_id,
        assistant_message=assistant_message,
        current_question=current_q,
        options=options,
        follow_up_questions=follow_ups,
        symptoms_identified=sorted(state.flags),
        missing_information=follow_ups,
        ready_for_triage=ready,
        triage=triage_payload,
    )


@router.post("/triage")
def triage(req: TriageRequest) -> dict:
    detail = case_service.get_case_detail(req.case_id)
    if not detail:
        raise HTTPException(status_code=404, detail="case not found")
    result = case_service.run_triage(req.case_id)
    return result


@router.get("/cases")
def get_cases(limit: int = 200) -> list:
    return case_service.list_cases(limit=limit)


@router.get("/cases/{case_id}")
def get_case(case_id: str) -> dict:
    detail = case_service.get_case_detail(case_id)
    if not detail:
        raise HTTPException(status_code=404, detail="case not found")
    return detail


@router.get("/reports")
def list_reports() -> list:
    from src.database.db import get_cursor

    with get_cursor() as cur:
        cur.execute("SELECT * FROM reports ORDER BY created_at DESC")
        return [dict(r) for r in cur.fetchall()]


@router.get("/analytics", response_model=AnalyticsResponse)
def analytics() -> AnalyticsResponse:
    return AnalyticsResponse(**case_service.get_analytics())


def _build_report_payload(case_id: str) -> dict:
    detail = case_service.get_case_detail(case_id)
    if not detail:
        raise HTTPException(status_code=404, detail="case not found")

    case = detail["case"]
    triage = detail["triage"] or {}
    conv = detail["conversation"]

    import json as _json

    patient_statements = [c["message"] for c in conv if c["role"] == "patient"]
    follow_up_responses = patient_statements[1:]  # first message is the chief complaint

    return {
        "case_id": case_id,
        "chief_complaint": case.get("chief_complaint"),
        "patient_statements": patient_statements,
        "follow_up_responses": follow_up_responses,
        "symptoms_identified": _json.loads(triage.get("symptoms_identified") or "[]"),
        "missing_information": _json.loads(triage.get("missing_information") or "[]"),
        "urgency_level": triage.get("urgency_level") or case.get("urgency_level") or "UNDETERMINED",
        "recommended_department": triage.get("recommended_department") or case.get("department"),
        "triggered_rules": _json.loads(triage.get("triggered_rules") or "[]"),
        "reasoning": triage.get("reasoning") or "",
        "evidence": _json.loads(triage.get("evidence") or "[]"),
        "escalation_required": bool(triage.get("escalation_required", case.get("escalation_required"))),
        "confidence": triage.get("confidence") or 0,
        "timestamp": triage.get("created_at") or case.get("updated_at"),
    }


@router.post("/export/pdf")
def export_pdf(payload: dict) -> FileResponse:
    case_id = payload.get("case_id")
    if not case_id:
        raise HTTPException(status_code=400, detail="case_id is required")
    report_data = _build_report_payload(case_id)

    report_id = f"rep-{uuid.uuid4().hex[:10]}"
    out_path = REPORTS_DIR / f"{report_id}.pdf"
    generate_report_pdf(report_data, str(out_path))

    from src.database.db import get_cursor

    with get_cursor() as cur:
        cur.execute(
            "INSERT INTO reports (report_id, case_id, format, file_path, created_at) VALUES (?, ?, 'pdf', ?, ?)",
            (report_id, case_id, str(out_path), report_data["timestamp"]),
        )

    return FileResponse(out_path, media_type="application/pdf", filename=f"triage_report_{case_id}.pdf")


@router.post("/export/json")
def export_json(payload: dict) -> FileResponse:
    case_id = payload.get("case_id")
    if not case_id:
        raise HTTPException(status_code=400, detail="case_id is required")
    report_data = _build_report_payload(case_id)

    report_id = f"rep-{uuid.uuid4().hex[:10]}"
    out_path = REPORTS_DIR / f"{report_id}.json"
    generate_report_json(report_data, str(out_path))

    from src.database.db import get_cursor

    with get_cursor() as cur:
        cur.execute(
            "INSERT INTO reports (report_id, case_id, format, file_path, created_at) VALUES (?, ?, 'json', ?, ?)",
            (report_id, case_id, str(out_path), report_data["timestamp"]),
        )

    return FileResponse(out_path, media_type="application/json", filename=f"triage_report_{case_id}.json")
