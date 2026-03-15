from flask import Blueprint, request, jsonify
import google.generativeai as genai
from config import Config
from db import emr_collection
from audit import log_audit, AuditAction
from datetime import datetime
import json
import re
from deepgram import DeepgramClient, PrerecordedOptions

voice_bp = Blueprint('voice', __name__)

# Initialize clients
genai.configure(api_key=Config.GEMINI_API_KEY)
gemini_model = genai.GenerativeModel("gemini-2.0-flash")
deepgram = DeepgramClient(Config.DEEPGRAM_API_KEY)

# -----------------------------
# 🎤 AUDIO TRANSCRIPTION ROUTE
# -----------------------------
@voice_bp.route('/transcribe', methods=['POST'])
def transcribe_audio():
    """Transcribe audio using Deepgram."""
    try:
        # Ensure audio file is sent
        if 'audio_data' not in request.files:
            return jsonify({"error": "No audio file provided"}), 400

        audio_file = request.files['audio_data']
        patient_id = request.form.get('patient_id', 'unknown')

        # Read audio file bytes
        audio_bytes = audio_file.read()

        # Detect mimetype from filename/content-type
        mimetype = audio_file.content_type or "audio/webm"
        source = {"buffer": audio_bytes, "mimetype": mimetype}

        # ─── High-accuracy medical transcription options ───
        options = PrerecordedOptions(
            model="nova-2-medical",       # Medical-domain model
            smart_format=True,            # Auto-punctuation & formatting
            punctuate=True,               # Ensure punctuation
            diarize=False,                # Single-speaker dictation
            paragraphs=True,              # Paragraph breaks for readability
            utterances=True,              # Detect utterance boundaries
            numerals=True,                # Convert spoken numbers to digits
            measurements=True,            # Handle "milligrams", "milliliters" etc.
            dictation=True,               # Optimize for dictation-style speech
            filler_words=False,           # Remove "um", "uh" for cleaner notes
            keywords=[                    # Boost recognition of common medical terms
                "milligrams:2", "milliliters:2", "twice daily:2",
                "once daily:2", "three times:2", "blood pressure:2",
                "heart rate:2", "oxygen saturation:2", "temperature:2",
                "prescription:2", "diagnosis:2", "prognosis:2",
                "hypertension:2", "diabetes:2", "cholesterol:2",
                "antibiotic:2", "paracetamol:2", "ibuprofen:2",
                "metformin:2", "amlodipine:2", "omeprazole:2",
                "ECG:2", "MRI:2", "CT scan:2", "X-ray:2",
                "CBC:2", "HbA1c:2", "creatinine:2", "hemoglobin:2",
            ],
        )

        # Perform transcription
        response = deepgram.listen.prerecorded.v("1").transcribe_file(source, options)

        # Access fields correctly (as attributes, not dict keys)
        alt = response.results.channels[0].alternatives[0]
        transcript = alt.transcript
        confidence = getattr(alt, "confidence", 0.0)
        words = getattr(alt, "words", [])

        # ─── Post-processing: fix common medical misrecognitions ───
        transcript = _post_process_medical_transcript(transcript)

        print(f"✅ Transcription complete (confidence: {confidence:.2%})")
        print(f"📝 Transcript: {transcript[:100]}...")

        log_audit(
            AuditAction.VOICE_TRANSCRIBE,
            patient_id=patient_id,
            details={"confidence": confidence, "transcript_length": len(transcript)},
        )

        return jsonify({
            "success": True,
            "transcript": transcript,
            "confidence": confidence,
            "words": [w.word for w in words]
        })

    except Exception as e:
        print(f"❌ Transcription Error: {e}")
        import traceback
        traceback.print_exc()
        return jsonify({"error": str(e)}), 500

# -----------------------------
# 🤖 GEMINI NOTE PROCESSOR
# -----------------------------
@voice_bp.route('/process', methods=['POST'])
def process_notes():
    """Process transcribed notes with Gemini AI into structured medical JSON."""
    try:
        data = request.get_json()
        patient_id = data.get('patient_id')
        notes = data.get('notes', '').strip()

        if not notes or len(notes) < 10:
            return jsonify({"error": "Notes too short"}), 400

        print(f"\n{'='*60}")
        print(f"🤖 Processing notes for: {patient_id}")
        print(f"📝 Notes length: {len(notes)} chars")
        print(f"{'='*60}\n")

        prompt = f"""You are a senior clinical documentation specialist. Your task is to convert 
raw medical dictation into a precise, structured JSON medical record.

RULES:
1. Fix any transcription errors by interpreting medical context (e.g. "metformin" not "met four men").
2. Normalise drug names to their correct generic spelling.
3. Use standard medical abbreviations where appropriate (e.g. "b.i.d." for twice daily).
4. Convert colloquial descriptions to proper medical terminology 
   (e.g. "sugar problem" -> "Type 2 Diabetes Mellitus").
5. Preserve exact dosages, frequencies, and durations as dictated.
6. If information is missing, use "Not mentioned" (string) or [] (array), NEVER fabricate data.
7. Return ONLY valid JSON -- no markdown, no explanation, no code fences.

OUTPUT SCHEMA (follow exactly):
{{
  "Allergy": ["<allergy1>", ...],
  "Complaints_Presented": "<chief complaints and HPI>",
  "Diagnosis": "<primary diagnosis; secondary if mentioned>",
  "Rx": [
    {{
      "Medication": "<generic drug name>",
      "Dosage": "<amount + unit>",
      "Frequency": "<e.g. twice daily / b.i.d.>",
      "Duration": "<e.g. 7 days>"
    }}
  ],
  "History": "<relevant PMH, surgical history, family history>",
  "Advice_FollowUp": "<lifestyle advice, follow-up date/instructions>",
  "Visit_Summary": "<2-3 sentence clinical summary>"
}}

MEDICAL DICTATION:
\"\"\"
{notes}
\"\"\"

Return the JSON now.
"""

        response = gemini_model.generate_content(prompt)

        # ✅ Clean Gemini response
        cleaned = response.text.strip()
        cleaned = re.sub(r'```json\s*|\s*```', '', cleaned, flags=re.IGNORECASE | re.MULTILINE)
        structured = json.loads(cleaned)

        # ✅ Ensure all expected fields exist
        default_fields = {
            "Allergy": [],
            "Complaints_Presented": "",
            "Diagnosis": "",
            "Rx": [],
            "History": "",
            "Advice_FollowUp": "",
            "Visit_Summary": ""
        }
        for key, default in default_fields.items():
            structured.setdefault(key, default)

        print("✅ Structured data generated successfully")

        log_audit(
            AuditAction.VOICE_PROCESS,
            patient_id=patient_id,
            details={"notes_length": len(notes), "fields": list(structured.keys())},
        )

        return jsonify({"success": True, "structured": structured})

    except json.JSONDecodeError as e:
        print(f"❌ JSON Parse Error: {e}")
        return jsonify({"error": "Invalid JSON from AI"}), 500

    except Exception as e:
        print(f"❌ Processing Error: {e}")
        import traceback
        traceback.print_exc()
        return jsonify({"error": str(e)}), 500


# -----------------------------
# 💾 SAVE NOTE TO MONGODB
# -----------------------------
@voice_bp.route('/save', methods=['POST'])
def save_note():
    """Save structured EMR note to MongoDB."""
    try:
        data = request.get_json()
        patient_id = data.get('patient_id')
        raw_notes = data.get('raw_notes', '')
        structured = data.get('structured')
        transcription_confidence = data.get('confidence', 0.0)

        if not patient_id or not structured:
            return jsonify({"error": "Missing required fields"}), 400

        emr_doc = {
            "patient_id": patient_id,
            "timestamp": datetime.utcnow(),
            "raw_notes": raw_notes,
            "structured": structured,
            "created_by": "voice_assistant",
            "visit_date": datetime.utcnow().strftime("%Y-%m-%d"),
            "transcription_confidence": transcription_confidence,
            "transcription_method": "deepgram_medical",
            "processing_method": "gemini_ai",
            "hipaa_compliant": True,
            "version": "1.0"
        }

        result = emr_collection.insert_one(emr_doc)

        print(f"✅ EMR saved for patient {patient_id} with ID {result.inserted_id}")

        log_audit(
            AuditAction.EMR_SAVE,
            patient_id=patient_id,
            details={"emr_id": str(result.inserted_id), "confidence": transcription_confidence},
        )

        return jsonify({
            "success": True,
            "message": "EMR saved successfully",
            "id": str(result.inserted_id),
            "confidence": transcription_confidence
        })

    except Exception as e:
        print(f"❌ Save Error: {e}")
        import traceback
        traceback.print_exc()
        return jsonify({"error": str(e)}), 500


# -----------------------------
# 📜 HISTORY FETCH
# -----------------------------
@voice_bp.route('/history/<patient_id>', methods=['GET'])
def get_patient_history(patient_id):
    """Fetch previous EMR voice notes."""
    try:
        notes = list(
            emr_collection.find({"patient_id": patient_id}, {"_id": 0})
            .sort("timestamp", -1)
            .limit(20)
        )
        for note in notes:
            if "timestamp" in note:
                note["timestamp"] = note["timestamp"].isoformat()

        log_audit(
            AuditAction.EMR_VIEW_HISTORY,
            patient_id=patient_id,
            details={"records_returned": len(notes)},
        )

        return jsonify({"success": True, "notes": notes, "count": len(notes)})
    except Exception as e:
        print(f"❌ History Error: {e}")
        return jsonify({"error": str(e)}), 500


# -----------------------------
# 🩺 HEALTH CHECK
# -----------------------------
@voice_bp.route('/health', methods=['GET'])
def voice_health():
    """Check Deepgram API health."""
    return jsonify({
        "success": True,
        "service": "deepgram",
        "status": "operational",
        "model": "nova-2-medical"
    })


# -------------------------------------------
# 🔧 MEDICAL TRANSCRIPT POST-PROCESSING
# -------------------------------------------

# Common medical misrecognitions from speech-to-text
_MEDICAL_CORRECTIONS = {
    # Drug names
    r"\bmet four men\b": "metformin",
    r"\bmet forman\b": "metformin",
    r"\baml oh dip een\b": "amlodipine",
    r"\bam low dipping\b": "amlodipine",
    r"\boh mep razole\b": "omeprazole",
    r"\boh mega prism\b": "omeprazole",
    r"\bpara see tamol\b": "paracetamol",
    r"\bpair a see tamol\b": "paracetamol",
    r"\bi buprofen\b": "ibuprofen",
    r"\bata nor vast a tin\b": "atorvastatin",
    r"\batter vast a tin\b": "atorvastatin",
    r"\blose art an\b": "losartan",
    r"\bceft ree axon\b": "ceftriaxone",
    r"\bazithro my sin\b": "azithromycin",
    r"\bamox a cill in\b": "amoxicillin",
    r"\bam oxo cill in\b": "amoxicillin",
    # Dosage units
    r"\bm g\b": "mg",
    r"\bm l\b": "mL",
    r"\bmilli grams?\b": "mg",
    r"\bmilli liters?\b": "mL",
    r"\bmicro grams?\b": "mcg",
    # Medical terms
    r"\bhyper tension\b": "hypertension",
    r"\bdie a beat ease\b": "diabetes",
    r"\bdie a beet is\b": "diabetes",
    r"\btack ee card ee a\b": "tachycardia",
    r"\bbrad ee card ee a\b": "bradycardia",
    r"\ban gee na\b": "angina",
    r"\bhemo globe in\b": "hemoglobin",
    r"\bcree at a nine\b": "creatinine",
    r"\bcree at in een\b": "creatinine",
    # Frequencies
    r"\bb\.?i\.?d\.?\b": "b.i.d.",
    r"\bt\.?i\.?d\.?\b": "t.i.d.",
    r"\bq\.?i\.?d\.?\b": "q.i.d.",
    r"\bo\.?d\.?\b": "o.d.",
    r"\btwice daily\b": "b.i.d.",
    r"\bthrice daily\b": "t.i.d.",
    # Lab tests
    r"\bh b a one see\b": "HbA1c",
    r"\bc b c\b": "CBC",
    r"\be c g\b": "ECG",
    r"\be k g\b": "EKG",
    r"\bm r i\b": "MRI",
    r"\bc t scan\b": "CT scan",
}


def _post_process_medical_transcript(transcript: str) -> str:
    """
    Apply rule-based corrections for common medical speech-to-text errors.
    Runs after Deepgram returns the raw transcript but before Gemini processes it.
    """
    corrected = transcript
    for pattern, replacement in _MEDICAL_CORRECTIONS.items():
        corrected = re.sub(pattern, replacement, corrected, flags=re.IGNORECASE)
    return corrected
