"""
Discharge Summary Routes
-------------------------
Endpoints for generating and approving discharge summaries.
Uses Gemini AI to produce a polished narrative from compiled records,
which the doctor then reviews and approves.
"""

from flask import Blueprint, request, jsonify
import google.generativeai as genai
from config import Config
from db import db
from audit import log_audit, AuditAction
from utils.discharge_summary import compile_discharge_data
import json
import re

discharge_bp = Blueprint("discharge", __name__)

genai.configure(api_key=Config.GEMINI_API_KEY)
_gemini_model = genai.GenerativeModel("gemini-2.5-flash")

discharge_collection = db["discharge_summaries"]


@discharge_bp.route("/generate", methods=["POST"])
def generate_discharge_summary():
    """
    Compile all patient records and generate a formatted discharge summary draft.

    Expects JSON body:
    {
        "patient_id": str,
        "patient_name": str,
        "patient_age": str (optional)
    }

    Returns compiled data + AI-formatted narrative.
    """
    try:
        data = request.get_json()
        if not data:
            return jsonify({"error": "No JSON body provided"}), 400

        patient_id = data.get("patient_id", "")
        patient_name = data.get("patient_name", "")
        patient_age = data.get("patient_age", "")

        if not patient_id and not patient_name:
            return jsonify({"error": "Patient ID or name required"}), 400

        # Use name as ID if no separate ID
        if not patient_id:
            patient_id = patient_name

        compiled = compile_discharge_data(patient_id, patient_name, patient_age)

        if compiled["total_visits"] == 0 and compiled["total_consultant_notes"] == 0:
            return jsonify({
                "error": "No records found for this patient",
                "patient_id": patient_id,
            }), 404

        # Generate AI narrative summary
        narrative = _generate_narrative(compiled)
        compiled["narrative_summary"] = narrative

        log_audit(
            AuditAction.DISCHARGE_GENERATE,
            patient_id=patient_id,
            details={
                "total_visits": compiled["total_visits"],
                "total_consultant_notes": compiled["total_consultant_notes"],
                "diagnoses_count": len(compiled["diagnoses"]),
            },
        )

        return jsonify({"success": True, "discharge_summary": compiled})

    except Exception as e:
        print(f"Discharge summary error: {e}")
        import traceback
        traceback.print_exc()
        return jsonify({"error": str(e)}), 500


@discharge_bp.route("/approve", methods=["POST"])
def approve_discharge_summary():
    """
    Save the approved discharge summary to the database.

    Expects JSON body:
    {
        "patient_id": str,
        "patient_name": str,
        "summary": dict (the full discharge summary object),
        "approved_by": str (doctor name, optional)
    }
    """
    try:
        data = request.get_json()
        if not data:
            return jsonify({"error": "No JSON body provided"}), 400

        patient_id = data.get("patient_id", "")
        patient_name = data.get("patient_name", "")
        summary = data.get("summary", {})
        approved_by = data.get("approved_by", "Attending Physician")

        if not summary:
            return jsonify({"error": "No summary data provided"}), 400

        from datetime import datetime

        doc = {
            "patient_id": patient_id or patient_name,
            "patient_name": patient_name,
            "summary": summary,
            "status": "approved",
            "approved_by": approved_by,
            "approved_at": datetime.utcnow(),
            "created_at": datetime.utcnow(),
        }

        result = discharge_collection.insert_one(doc)

        log_audit(
            AuditAction.DISCHARGE_APPROVE,
            patient_id=patient_id or patient_name,
            details={"discharge_id": str(result.inserted_id), "approved_by": approved_by},
        )

        return jsonify({
            "success": True,
            "message": "Discharge summary approved and saved",
            "id": str(result.inserted_id),
        })

    except Exception as e:
        print(f"Discharge approve error: {e}")
        import traceback
        traceback.print_exc()
        return jsonify({"error": str(e)}), 500


def _generate_narrative(compiled: dict) -> str:
    """Use Gemini to produce a polished discharge narrative from compiled data."""
    try:
        meds_text = ""
        for m in compiled.get("medications_at_discharge", []):
            if isinstance(m, dict):
                name = m.get("Medication", m.get("medication", ""))
                dose = m.get("Dosage", m.get("dosage", ""))
                freq = m.get("Frequency", m.get("frequency", ""))
                dur = m.get("Duration", m.get("duration", ""))
                meds_text += f"  - {name} {dose} {freq} x {dur}\n"
            elif isinstance(m, str):
                meds_text += f"  - {m}\n"

        prompt = f"""You are a medical documentation specialist. Write a concise, professional 
discharge summary narrative based on the following compiled patient data.

RULES:
1. Write in formal medical prose (not bullet points).
2. Include: reason for admission, hospital course summary, diagnoses,
   medications at discharge, allergies, and follow-up instructions.
3. Keep it concise -- 1-2 paragraphs maximum.
4. Do NOT add any information that is not in the data below.
5. Return ONLY the narrative text, no JSON, no markdown formatting.

PATIENT DATA:
- Name: {compiled.get('patient_name', 'N/A')}
- Age: {compiled.get('patient_age', 'N/A')}
- Admission Date: {compiled.get('admission_date', 'N/A')}
- Discharge Date: {compiled.get('discharge_date', 'N/A')}
- Diagnoses: {', '.join(compiled.get('diagnoses', [])) or 'N/A'}
- Complaints: {'; '.join(compiled.get('complaints', [])) or 'N/A'}
- Allergies: {', '.join(compiled.get('allergies', [])) or 'None reported'}
- Medications at Discharge:
{meds_text or '  None'}
- Visit Summaries: {'; '.join(compiled.get('visit_summaries', [])) or 'N/A'}
- Follow-Up Advice: {'; '.join(compiled.get('advice_followup', [])) or 'N/A'}

Write the discharge summary narrative now.
"""

        response = _gemini_model.generate_content(prompt)
        return response.text.strip()

    except Exception as e:
        print(f"Narrative generation failed: {e}")
        return "Unable to generate narrative summary. Please compose manually."
