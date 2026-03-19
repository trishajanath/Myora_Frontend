import sys
import os

# Ensure UTF-8 output on Windows terminals
if sys.stdout.encoding != 'utf-8':
    sys.stdout.reconfigure(encoding='utf-8')
if sys.stderr.encoding != 'utf-8':
    sys.stderr.reconfigure(encoding='utf-8')

from flask import Flask, jsonify, request
from flask_cors import CORS
from pymongo.errors import ServerSelectionTimeoutError
from db import inpatients
from config import Config

app = Flask(__name__)

# Allow CORS for your frontend and admin URLs
CORS(app, origins=["http://localhost:5173", "http://localhost:5174"])

# Import and register blueprints
from routes.patients import patients_bp
from routes.voice_routes import voice_bp
from routes.consultant_notes import consultant_bp
from routes.drug_safety_routes import drug_safety_bp
from routes.ocr_routes import ocr_bp

app.register_blueprint(patients_bp, url_prefix="/api/patients")
app.register_blueprint(voice_bp, url_prefix="/api/voice")
app.register_blueprint(consultant_bp, url_prefix="/api/consultant")
app.register_blueprint(drug_safety_bp, url_prefix="/api/drug-safety")
app.register_blueprint(ocr_bp, url_prefix="/api/ocr")


# Audit log viewer endpoint
@app.route("/api/audit", methods=["GET"])
def get_audit_logs():
    """Retrieve audit log entries. Query params: patient_id, action, limit."""
    from db import audit_logs

    query = {}
    if request.args.get("patient_id"):
        query["patient_id"] = request.args["patient_id"]
    if request.args.get("action"):
        query["action"] = request.args["action"]

    limit = min(int(request.args.get("limit", 100)), 500)

    logs = list(
        audit_logs.find(query, {"_id": 0})
        .sort("timestamp", -1)
        .limit(limit)
    )
    for log in logs:
        if "timestamp" in log:
            log["timestamp"] = log["timestamp"].isoformat()

    return jsonify({"success": True, "logs": logs, "count": len(logs)})


@app.route("/")
def index():
    return jsonify({
        "message": "IMRS Backend Active",
        "version": "2.0",
        "voice_api": "Deepgram",
        "endpoints": {
            "patients": "/api/patients",
            "voice": "/api/voice",
            "consultant": "/api/consultant",
            "ocr": "/api/ocr/extract"
        }
    })

@app.route("/health")
def health():
    """Health check endpoint."""
    try:
        # Test MongoDB connection
        inpatients.find_one()
        db_status = "connected"
    except ServerSelectionTimeoutError:
        db_status = "disconnected"
    
    return jsonify({
        "status": "healthy",
        "database": db_status,
        "deepgram": "enabled" if Config.DEEPGRAM_API_KEY else "missing"
    })

if __name__ == "__main__":
    port = int(os.getenv("PORT", "5001"))

    print("\n" + "="*70)
    print("IMSR Backend Starting...")
    print("="*70)
    print(f"API Server: http://0.0.0.0:{port}")
    print(f"CORS Origins: http://localhost:5173, http://localhost:5174")
    print(f"Voice Transcription: /api/voice/transcribe (Deepgram)")
    print(f"AI Processing: /api/voice/process (Gemini)")
    print(f"Save EMR: /api/voice/save")
    print(f"Consultant Notes: /api/consultant")
    print(f"Drug Safety: /api/drug-safety")
    print(f"OCR (Tesseract): /api/ocr/extract")
    print("="*70)
    
    # Validate configuration
    if Config.validate():
        print("Configuration valid\n")
    else:
        print("Configuration incomplete - check .env file\n")
        exit(1)
    
    app.run(
        host="0.0.0.0",
        port=port,
        debug=True
    )