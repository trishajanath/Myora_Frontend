from flask import Flask, jsonify
from flask_cors import CORS
from pymongo.errors import ServerSelectionTimeoutError
from db import inpatients
from config import Config
import os

app = Flask(__name__)

# ✅ Allow CORS for your frontend and admin URLs
CORS(app, origins=["http://localhost:5173", "http://localhost:5174"])

# ✅ Import and register blueprints
from routes.patients import patients_bp
from routes.voice_routes import voice_bp
from routes.consultant_notes import consultant_bp

app.register_blueprint(patients_bp, url_prefix="/api/patients")
app.register_blueprint(voice_bp, url_prefix="/api/voice")
app.register_blueprint(consultant_bp, url_prefix="/api/consultant")


@app.route("/")
def index():
    return jsonify({
        "message": "🩺 IMRS Backend Active",
        "version": "2.0",
        "voice_api": "Deepgram",
        "endpoints": {
            "patients": "/api/patients",
            "voice": "/api/voice",
            "consultant": "/api/consultant"
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
    print("🚀 IMSR Backend Starting...")
    print("="*70)
    print(f"📍 API Server: http://0.0.0.0:{port}")
    print(f"🌐 CORS Origins: http://localhost:5173, http://localhost:5174")
    print(f"🎙️  Voice Transcription: /api/voice/transcribe (Deepgram)")
    print(f"🤖 AI Processing: /api/voice/process (Gemini)")
    print(f"💾 Save EMR: /api/voice/save")
    print(f"📋 Consultant Notes: /api/consultant")
    print("="*70)
    
    # Validate configuration
    if Config.validate():
        print("✅ Configuration valid\n")
    else:
        print("❌ Configuration incomplete - check .env file\n")
        exit(1)
    
    app.run(
        host="0.0.0.0",
        port=port,
        debug=True
    )