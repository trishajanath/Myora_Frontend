"""
Prescription Routes
-------------------
Endpoints for generating and downloading PDF prescriptions.
"""

from flask import Blueprint, request, jsonify, send_file
from audit import log_audit, AuditAction
from utils.prescription_generator import generate_prescription_pdf
import io

prescription_bp = Blueprint("prescription", __name__)


@prescription_bp.route("/generate", methods=["POST"])
def generate_prescription():
    """
    Generate a PDF prescription from structured EMR data.

    Expects JSON body:
    {
        "patient_name": str,
        "patient_age": str (optional),
        "patient_id": str (optional),
        "diagnosis": str,
        "allergies": [str],
        "medications": [{"Medication":..., "Dosage":..., "Frequency":..., "Duration":...}],
        "advice": str (optional),
        "doctor_name": str (optional)
    }

    Returns: PDF file as attachment.
    """
    try:
        data = request.get_json()
        if not data:
            return jsonify({"error": "No JSON body provided"}), 400

        patient_name = data.get("patient_name", "Unknown Patient")
        medications = data.get("medications", [])

        if not medications:
            return jsonify({"error": "No medications to prescribe"}), 400

        pdf_bytes = generate_prescription_pdf(
            patient_name=patient_name,
            patient_age=data.get("patient_age", ""),
            patient_id=data.get("patient_id", ""),
            diagnosis=data.get("diagnosis", ""),
            allergies=data.get("allergies", []),
            medications=medications,
            advice=data.get("advice", ""),
            doctor_name=data.get("doctor_name", "Attending Physician"),
        )

        log_audit(
            AuditAction.PRESCRIPTION_GENERATE,
            patient_id=patient_name,
            details={"rx_count": len(medications)},
        )

        # Return PDF as downloadable file
        safe_name = "".join(c for c in patient_name if c.isalnum() or c in " _-")[:30]
        filename = f"Rx_{safe_name}.pdf"

        return send_file(
            io.BytesIO(pdf_bytes),
            mimetype="application/pdf",
            as_attachment=True,
            download_name=filename,
        )

    except Exception as e:
        print(f"Prescription generation error: {e}")
        import traceback
        traceback.print_exc()
        return jsonify({"error": str(e)}), 500
