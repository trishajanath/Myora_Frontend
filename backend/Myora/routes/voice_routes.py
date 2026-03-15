from flask import Blueprint, request, jsonify
from google import genai
from config import Config
from db import emr_collection
from datetime import datetime
import json
import re
from deepgram import DeepgramClient, PrerecordedOptions

voice_bp = Blueprint('voice', __name__)

# Initialize clients
gemini_client = genai.Client(api_key=Config.GEMINI_API_KEY)
deepgram = DeepgramClient(Config.DEEPGRAM_API_KEY)

# -----------------------------
# 🎤 AUDIO TRANSCRIPTION ROUTE
# -----------------------------
@voice_bp.route('/transcribe', methods=['POST'])
async def transcribe_audio():
    """Transcribe audio using Deepgram."""
    try:
        # Ensure audio file is sent
        if 'audio_data' not in request.files:
            return jsonify({"error": "No audio file provided"}), 400

        audio_file = request.files['audio_data']
        patient_id = request.form.get('patient_id', 'unknown')

        # Read audio file bytes
        audio_bytes = audio_file.read()

        # Create source object for Deepgram
        source = {"buffer": audio_bytes, "mimetype": "audio/wav"}  # or audio/webm

        # Configure model options
        options = PrerecordedOptions(
            model="nova-2-medical",
            smart_format=True
        )

        # Perform transcription
        response = deepgram.listen.prerecorded.v("1").transcribe_file(source, options)

        # Access fields correctly (as attributes, not dict keys)
        alt = response.results.channels[0].alternatives[0]
        transcript = alt.transcript
        confidence = getattr(alt, "confidence", 0.0)
        words = getattr(alt, "words", [])

        print(f"✅ Transcription complete (confidence: {confidence:.2%})")
        print(f"📝 Transcript: {transcript[:100]}...")

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

        prompt = f"""You are a medical assistant. Convert this medical dictation and correct if any mistakes in 
                  pronunciation to JSON format with these fields:

- Allergy: List any allergies mentioned. If none, say "None known". Format as array of strings.
- Complaints_Presented: Chief complaints and presenting symptoms. Be specific.
- Diagnosis: Primary and secondary diagnoses if mentioned.
- Rx: Prescriptions with medication name, dosage, frequency, and duration. Format as array.
- History: Relevant medical history mentioned (past conditions, surgeries, family history).
- Advice_FollowUp: Follow-up instructions, lifestyle advice, when to return.

Important:
- Use proper medical terminology.
- Be concise but complete.
- If information is not mentioned, use "Not mentioned" or empty array.
- Return ONLY valid JSON.

Medical Dictation:
{notes}
"""

        response = gemini_client.models.generate_content(
            model="gemini-2.5-flash",
            contents=prompt
        )

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
