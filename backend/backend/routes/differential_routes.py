"""
Differential Diagnosis Routes
-------------------------------
Uses Gemini AI to suggest possible diagnoses based on
patient complaints + medical history as a clinical decision support nudge.
"""

from flask import Blueprint, request, jsonify
import google.generativeai as genai
from config import Config
from audit import log_audit, AuditAction
import json
import re

differential_bp = Blueprint("differential", __name__)

genai.configure(api_key=Config.GEMINI_API_KEY)
_gemini_model = genai.GenerativeModel("gemini-2.5-flash")


@differential_bp.route("/suggest", methods=["POST"])
def suggest_diagnoses():
    """
    Generate AI differential diagnosis suggestions.

    Expects JSON body:
    {
        "patient_id": str,
        "complaints": str,
        "history": str (optional),
        "allergies": [str] (optional),
        "vitals": str (optional),
        "age": str (optional),
        "current_diagnosis": str (optional)
    }

    Returns JSON list of suggested diagnoses with reasoning.
    """
    try:
        data = request.get_json()
        if not data:
            return jsonify({"error": "No JSON body provided"}), 400

        complaints = data.get("complaints", "").strip()
        if not complaints or len(complaints) < 5:
            return jsonify({"error": "Complaints too short for analysis"}), 400

        patient_id = data.get("patient_id", "")
        history = data.get("history", "Not provided")
        allergies = data.get("allergies", [])
        vitals = data.get("vitals", "Not provided")
        age = data.get("age", "Not provided")
        current_dx = data.get("current_diagnosis", "")

        prompt = f"""You are an experienced clinical decision support system. Based on the 
patient information below, suggest a ranked differential diagnosis list.

RULES:
1. Provide 3-6 possible diagnoses ranked by likelihood.
2. For each diagnosis include: name, likelihood (high/moderate/low), key reasoning, 
   and one suggested confirmatory test or next step.
3. If the doctor already has a working diagnosis, include whether you agree and why.
4. Be evidence-based. Cite common clinical criteria where applicable.
5. This is a DECISION SUPPORT NUDGE -- final diagnosis is always the physician's call.
6. Return ONLY valid JSON -- no markdown, no explanation, no code fences.

PATIENT DATA:
- Age: {age}
- Chief Complaints: {complaints}
- Medical History: {history}
- Known Allergies: {", ".join(allergies) if allergies else "None reported"}
- Vitals: {vitals}
- Doctor's Working Diagnosis: {current_dx if current_dx else "Not yet determined"}

OUTPUT SCHEMA (follow exactly):
{{
  "differentials": [
    {{
      "rank": 1,
      "diagnosis": "<diagnosis name>",
      "likelihood": "high|moderate|low",
      "reasoning": "<brief clinical reasoning>",
      "next_step": "<suggested confirmatory test or action>"
    }}
  ],
  "agreement_with_current": "<if working diagnosis given: agree/disagree/partially + reason, else null>",
  "red_flags": ["<any urgent findings that need immediate attention>"],
  "note": "Clinical decision support only. Final diagnosis is the physician's responsibility."
}}

Return the JSON now.
"""

        response = _gemini_model.generate_content(prompt)

        cleaned = response.text.strip()
        cleaned = re.sub(r"```json\s*|\s*```", "", cleaned, flags=re.IGNORECASE | re.MULTILINE)
        result = json.loads(cleaned)

        # Ensure expected structure
        result.setdefault("differentials", [])
        result.setdefault("red_flags", [])
        result.setdefault("agreement_with_current", None)
        result.setdefault("note", "Clinical decision support only. Final diagnosis is the physician's responsibility.")

        log_audit(
            AuditAction.DIFFERENTIAL_DIAGNOSIS,
            patient_id=patient_id,
            details={
                "complaints_length": len(complaints),
                "suggestions_count": len(result.get("differentials", [])),
            },
        )

        return jsonify({"success": True, **result})

    except json.JSONDecodeError as e:
        print(f"Differential dx JSON error: {e}")
        return jsonify({"error": "AI returned invalid JSON"}), 500
    except Exception as e:
        print(f"Differential dx error: {e}")
        import traceback
        traceback.print_exc()
        return jsonify({"error": str(e)}), 500
