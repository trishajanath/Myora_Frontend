"""
routes/drug_safety_routes.py
----------------------------------------------------------
REST API endpoints for drug interaction & allergy checking.
----------------------------------------------------------
"""

from flask import Blueprint, request, jsonify
from utils.drug_safety import run_full_safety_check
from audit import log_audit, AuditAction

drug_safety_bp = Blueprint("drug_safety", __name__)


@drug_safety_bp.route("/check", methods=["POST"])
def safety_check():
    """
    Run a full drug-safety analysis.

    POST JSON body:
    {
        "allergies": ["Penicillin", ...],
        "medications": [{"Medication": "...", "Dosage": "...", ...}, ...],
        "diagnosis": "optional diagnosis text",
        "patient_id": "optional patient id"
    }

    Returns:
    {
        "success": true,
        "safety_report": { ... }
    }
    """
    try:
        data = request.get_json(silent=True) or {}

        allergies = data.get("allergies", [])
        medications = data.get("medications", [])
        diagnosis = data.get("diagnosis", "")
        patient_id = data.get("patient_id")

        if not medications:
            return jsonify({
                "success": True,
                "safety_report": {
                    "safe": True,
                    "alert_count": 0,
                    "alerts": [],
                    "message": "No medications to check",
                },
            })

        report = run_full_safety_check(allergies, medications, diagnosis)

        log_audit(
            AuditAction.DRUG_SAFETY_CHECK,
            patient_id=patient_id,
            details={
                "medication_count": len(medications),
                "allergy_count": len(allergies),
                "alert_count": report["alert_count"],
                "has_critical": report["has_critical"],
            },
        )

        return jsonify({"success": True, "safety_report": report})

    except Exception as e:
        import traceback
        traceback.print_exc()
        return jsonify({"error": str(e)}), 500
