"""Generates the structured triage PDF report using reportlab."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Dict

from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import cm
from reportlab.platypus import (
    Paragraph,
    SimpleDocTemplate,
    Spacer,
    Table,
    TableStyle,
)

URGENCY_COLORS = {
    "EMERGENCY": colors.HexColor("#dc2626"),
    "URGENT": colors.HexColor("#d97706"),
    "STANDARD": colors.HexColor("#16a34a"),
    "UNDETERMINED": colors.HexColor("#6b7280"),
}


def _kv_table(data: Dict[str, str]) -> Table:
    rows = [[k, v] for k, v in data.items()]
    table = Table(rows, colWidths=[5 * cm, 11 * cm])
    table.setStyle(
        TableStyle(
            [
                ("FONTNAME", (0, 0), (0, -1), "Helvetica-Bold"),
                ("FONTSIZE", (0, 0), (-1, -1), 9.5),
                ("VALIGN", (0, 0), (-1, -1), "TOP"),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 6),
                ("LINEBELOW", (0, 0), (-1, -1), 0.4, colors.HexColor("#e5e7eb")),
            ]
        )
    )
    return table


def generate_report_pdf(report_data: Dict[str, Any], output_path: str) -> str:
    Path(output_path).parent.mkdir(parents=True, exist_ok=True)
    doc = SimpleDocTemplate(
        output_path, pagesize=A4, topMargin=1.5 * cm, bottomMargin=1.5 * cm
    )
    styles = getSampleStyleSheet()
    title_style = ParagraphStyle(
        "TitleCustom", parent=styles["Title"], fontSize=18, textColor=colors.HexColor("#1e3a8a")
    )
    h2 = ParagraphStyle("H2Custom", parent=styles["Heading2"], fontSize=12, spaceBefore=12)
    body = styles["BodyText"]

    urgency = report_data.get("urgency_level", "UNDETERMINED")
    urgency_color = URGENCY_COLORS.get(urgency, colors.grey)

    story = [
        Paragraph("Patient Intake Triage Report", title_style),
        Paragraph("NexusTiq24 Hackathon &mdash; PS01 Healthcare Triage Assistant", body),
        Spacer(1, 0.5 * cm),
    ]

    story.append(Paragraph("Case Overview", h2))
    story.append(
        _kv_table(
            {
                "Case ID": report_data.get("case_id", ""),
                "Timestamp": report_data.get("timestamp", ""),
                "Chief Complaint": report_data.get("chief_complaint", "") or "-",
            }
        )
    )

    story.append(Paragraph("Patient Statements", h2))
    for stmt in report_data.get("patient_statements", []):
        story.append(Paragraph(f"&bull; {stmt}", body))
    if not report_data.get("patient_statements"):
        story.append(Paragraph("None recorded.", body))

    story.append(Paragraph("Follow-up Responses", h2))
    for turn in report_data.get("follow_up_responses", []):
        story.append(Paragraph(f"&bull; {turn}", body))
    if not report_data.get("follow_up_responses"):
        story.append(Paragraph("None recorded.", body))

    story.append(Paragraph("Symptoms Identified", h2))
    story.append(Paragraph(", ".join(report_data.get("symptoms_identified", [])) or "None", body))

    story.append(Paragraph("Missing Information", h2))
    story.append(Paragraph(", ".join(report_data.get("missing_information", [])) or "None", body))

    story.append(Paragraph("Triage Outcome", h2))
    urgency_style = ParagraphStyle(
        "Urgency", parent=body, textColor=urgency_color, fontName="Helvetica-Bold", fontSize=13
    )
    story.append(Paragraph(f"Urgency Level: {urgency}", urgency_style))
    story.append(
        _kv_table(
            {
                "Recommended Department": report_data.get("recommended_department", ""),
                "Escalation Required": "Yes" if report_data.get("escalation_required") else "No",
                "Confidence": f"{report_data.get('confidence', 0):.0%}",
            }
        )
    )

    story.append(Paragraph("Triggered Rules", h2))
    rules = report_data.get("triggered_rules", [])
    if rules:
        rows = [["Rule ID", "Description", "Outcome"]] + [
            [r["rule_id"], r["description"], r["outcome"]] for r in rules
        ]
        t = Table(rows, colWidths=[2 * cm, 11 * cm, 3 * cm])
        t.setStyle(
            TableStyle(
                [
                    ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#1e3a8a")),
                    ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
                    ("FONTSIZE", (0, 0), (-1, -1), 9),
                    ("GRID", (0, 0), (-1, -1), 0.4, colors.HexColor("#e5e7eb")),
                    ("VALIGN", (0, 0), (-1, -1), "TOP"),
                ]
            )
        )
        story.append(t)
    else:
        story.append(Paragraph("No deterministic rule was matched.", body))

    story.append(Paragraph("Reasoning", h2))
    story.append(Paragraph(report_data.get("reasoning", ""), body))

    story.append(Paragraph("Evidence / Guideline References", h2))
    evidence = report_data.get("evidence", [])
    if evidence:
        for ev in evidence:
            story.append(Paragraph(f"&bull; ({ev.get('source')}) {ev.get('text')}", body))
    else:
        story.append(Paragraph("No supporting guideline evidence retrieved.", body))

    doc.build(story)
    return output_path


def generate_report_json(report_data: Dict[str, Any], output_path: str) -> str:
    Path(output_path).parent.mkdir(parents=True, exist_ok=True)
    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(report_data, f, indent=2, default=str)
    return output_path
