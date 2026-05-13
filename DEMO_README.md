# MYORA DEMO SCRIPT

Complete demonstration of the Myora medical notes system with all features.

## Quick Start

### 1. Start the Backend
```bash
cd /Users/trishajanath/MyoraFrontend
source .venv/bin/activate
cd backend/backend
python app.py
```

Backend will run on: `http://127.0.0.1:5001`

### 2. Run the Demo
```bash
# In a new terminal
cd /Users/trishajanath/MyoraFrontend
python DEMO_SCRIPT.py
```

## What the Demo Shows

The script automatically demonstrates all major features:

### 1. **Patient Creation**
- Creates a sample patient (John Smith, 56M)
- Sets up allergies, medical history
- Generates patient ID

### 2. **Voice Transcription**
- Simulates voice recording and Deepgram transcription
- Shows extracted vital signs, assessment, medications
- Demonstrates 97% confidence score

### 3. **Drug Safety Checking**
- Checks medications against:
  - Patient allergies (e.g., Penicillin)
  - Drug-drug interactions (e.g., Warfarin + Aspirin)
  - Diagnosis contraindications
- Shows severity levels: HIGH, MODERATE, LOW

### 4. **Differential Diagnosis (AI)**
- Uses Gemini AI for clinical decision support
- Provides ranked differentials with:
  - Likelihood (high/moderate/low)
  - Clinical reasoning
  - Suggested confirmatory tests

### 5. **Prescription Generation**
- Generates formatted prescription with:
  - Patient details
  - Medications with dosages
  - Diagnosis
  - Doctor notes
- Creates PDF with QR code

### 6. **Image OCR Extraction**
- Simulates extracting data from medical images
- Shows structured data extraction:
  - Document type
  - Patient info
  - Clinical sections
  - Diagnosis and medications

### 7. **Discharge Summary**
- Compiles all patient records
- Combines voice notes + OCR consultant notes
- Generates complete discharge narrative
- Ready for doctor review

### 8. **Audit Log**
- Shows HIPAA-compliant activity tracking
- Displays all actions taken (timestamps, actions)

## Expected Output

```
====================================================================
              1. PATIENT CREATION
====================================================================

✓ Patient created with ID: PAT20260324075430
  Age: 56 years old
  Gender: Male
  Allergies: Penicillin, Aspirin
  Medical History: Type 2 Diabetes, Hypertension, Previous MI (2020)

====================================================================
              2. VOICE TRANSCRIPTION
====================================================================

  Simulated Transcription Result:
  
  Patient presents with persistent chest discomfort for 3 days...
  
✓ Transcription confidence: 97%
✓ Structured data extracted: 6 fields

[... continues with all features ...]

====================================================================
                 DEMO COMPLETE
====================================================================

All features demonstrated successfully!
```

## API Endpoints Being Called

| Feature | Endpoint | Method |
|---------|----------|--------|
| Drug Safety | `/api/drug-safety/check` | POST |
| Differential Dx | `/api/differential/suggest` | POST |
| Prescription | `/api/prescription/generate` | POST |
| Discharge Summary | `/api/discharge/generate` | POST |
| Audit Log | `/api/audit` | GET |

## Customizing the Demo

You can edit `DEMO_SCRIPT.py` to:
- Change patient details (name, age, allergies)
- Modify complaints/symptoms
- Add different medications
- Test specific drug interactions

### Example: Test Different Drug Interactions

In the `demo_voice_transcription()` function, change:
```python
"medications_prescribed": [
    {"Medication": "Warfarin", "Dosage": "5mg", "Frequency": "daily"},
    {"Medication": "Aspirin", "Dosage": "100mg", "Frequency": "daily"}
]
```

This will trigger the HIGH RISK alert for Warfarin + Aspirin interaction.

## Troubleshooting

### "Cannot connect to backend"
- Make sure Flask backend is running on `http://127.0.0.1:5001`
- Check terminal where you ran `python app.py`
- Verify port 5001 is not blocked

### API returns errors
- Some features require valid API keys (GEMINI_API_KEY, DEEPGRAM_API_KEY)
- Check `.env` file in `backend/backend/`
- Drug safety checking requires OpenFDA API access

### Missing features
- Image OCR extraction is simulated (no actual image upload)
- Voice transcription shows sample output
- To use real features, run the actual web frontend

## Frontend Demo

To see features in the UI:

```bash
cd MyoraFrontend/frontend
npm run dev
```

Then open `http://localhost:5173` in browser to:
- Record voice notes in real-time
- Upload medical images for OCR
- View extracted notes
- Generate prescriptions
- See discharge summaries

## Key Features Highlighted

✅ **Voice-to-AI**: Deepgram → Gemini structured extraction  
✅ **Drug Safety**: 100+ interactions + allergy checking  
✅ **AI Decision Support**: Differential diagnoses  
✅ **Prescription PDFs**: Auto-generated with QR codes  
✅ **Medical Vision AI**: Extract handwritten notes from images  
✅ **Discharge Summaries**: Compile all visit records  
✅ **HIPAA Compliant**: Full audit logging  
✅ **Real-time API**: Flask backend with MongoDB storage  

---

**Questions?** Check the main README or contact the development team.
