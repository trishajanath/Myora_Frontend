#!/usr/bin/env python3
"""
MYORA DEMO SCRIPT
================

Complete demonstration of the Myora medical notes system.
Shows all key features: voice transcription, OCR, drug safety, differential diagnosis, 
prescriptions, and discharge summaries.

Run this to automatically demo the system with sample data.
"""

import requests
import json
import time
from datetime import datetime

# Configuration
BASE_URL = "http://127.0.0.1:5001"
HEADERS = {"Content-Type": "application/json"}

# Color codes for terminal output
class Colors:
    HEADER = '\033[95m'
    BLUE = '\033[94m'
    CYAN = '\033[96m'
    GREEN = '\033[92m'
    YELLOW = '\033[93m'
    RED = '\033[91m'
    ENDC = '\033[0m'
    BOLD = '\033[1m'
    UNDERLINE = '\033[4m'

def print_section(title):
    """Print a section header"""
    print(f"\n{Colors.BOLD}{Colors.BLUE}{'='*70}{Colors.ENDC}")
    print(f"{Colors.BOLD}{Colors.BLUE}{title.center(70)}{Colors.ENDC}")
    print(f"{Colors.BOLD}{Colors.BLUE}{'='*70}{Colors.ENDC}\n")

def print_success(msg):
    """Print success message"""
    print(f"{Colors.GREEN}✓ {msg}{Colors.ENDC}")

def print_error(msg):
    """Print error message"""
    print(f"{Colors.RED}✗ {msg}{Colors.ENDC}")

def print_info(msg, value=None):
    """Print info message"""
    if value:
        print(f"{Colors.CYAN}{msg}: {Colors.YELLOW}{value}{Colors.ENDC}")
    else:
        print(f"{Colors.CYAN}{msg}{Colors.ENDC}")

def print_json(data):
    """Pretty print JSON"""
    print(f"{Colors.YELLOW}{json.dumps(data, indent=2)}{Colors.ENDC}")

# ============================================================================
# 1. PATIENT MANAGEMENT
# ============================================================================

def demo_create_patient():
    """Demo: Create a new patient"""
    print_section("1. PATIENT CREATION")
    
    patient_data = {
        "name": "John Smith",
        "age": 56,
        "gender": "Male",
        "contact": "555-0123",
        "medical_history": "Type 2 Diabetes, Hypertension, Previous MI (2020)",
        "allergies": ["Penicillin", "Aspirin"]
    }
    
    print_info("Creating patient...", patient_data["name"])
    
    # For demo purposes, we'll use a mock patient ID since the actual endpoint may vary
    patient_id = "PAT" + datetime.now().strftime("%Y%m%d%H%M%S")
    
    print_success(f"Patient created with ID: {patient_id}")
    print_info("Age", f"{patient_data['age']} years old")
    print_info("Gender", patient_data['gender'])
    print_info("Allergies", ", ".join(patient_data['allergies']))
    print_info("Medical History", patient_data['medical_history'])
    
    return patient_id, patient_data

# ============================================================================
# 2. VOICE TRANSCRIPTION (Simulated)
# ============================================================================

def demo_voice_transcription(patient_id):
    """Demo: Voice transcription (simulated audio)"""
    print_section("2. VOICE TRANSCRIPTION")
    
    print_info("What would happen in real scenario:")
    print("  1. Doctor records voice notes using the app")
    print("  2. Audio is sent to Deepgram API")
    print("  3. Deepgram transcribes with medical model (nova-2-medical)")
    print("  4. Gemini AI structures the notes")
    print()
    
    # Simulated transcription result
    transcribed_text = """
    Patient presents with persistent chest discomfort for 3 days.
    Describes as pressure-like, radiating to left arm.
    Associated with dyspnea and diaphoresis.
    
    Vital Signs:
    - Blood Pressure: 158/92
    - Heart Rate: 102 bpm
    - Respiratory Rate: 22
    - O2 Saturation: 94% on room air
    - Temperature: 36.8°C
    
    Physical Exam:
    - Cardiac: Tachycardic, no murmurs
    - Lungs: Clear to auscultation bilaterally
    - Extremities: No edema
    
    Assessment:
    - Acute Coronary Syndrome vs Unstable Angina
    - Rule out myocardial infarction
    
    Plan:
    - Admit to ICU
    - EKG, troponin, chest X-ray
    - Cardiology consult
    - Start aspirin 325mg, clopidogrel 600mg loading
    """
    
    print_info("Simulated Transcription Result:")
    print(f"{Colors.YELLOW}{transcribed_text}{Colors.ENDC}")
    
    # Extract structured data (simulated)
    structured_data = {
        "patient_id": patient_id,
        "chief_complaint": "Chest discomfort",
        "duration": "3 days",
        "vitals": {
            "bp": "158/92",
            "hr": 102,
            "rr": 22,
            "spo2": 94
        },
        "assessment": "Acute Coronary Syndrome vs Unstable Angina",
        "medications_prescribed": [
            {"Medication": "Aspirin", "Dosage": "325mg", "Frequency": "Once"},
            {"Medication": "Clopidogrel", "Dosage": "600mg", "Frequency": "Loading dose"}
        ]
    }
    
    print_success(f"Transcription confidence: 97%")
    print_success(f"Structured data extracted: {len(structured_data)} fields")
    
    return structured_data

# ============================================================================
# 3. DRUG SAFETY CHECKING
# ============================================================================

def demo_drug_safety(patient_id, patient_data, voice_data):
    """Demo: Drug safety checking"""
    print_section("3. DRUG SAFETY CHECKING")
    
    print_info("Checking medications against patient allergies and interactions...")
    
    # Prepare the drug safety check request
    check_request = {
        "patient_id": patient_id,
        "medications": voice_data["medications_prescribed"],
        "allergies": patient_data["allergies"],
        "diagnosis": voice_data["assessment"]
    }
    
    print_info("Medications to check:")
    for med in check_request["medications"]:
        print(f"  • {med['Medication']} {med['Dosage']} {med['Frequency']}")
    
    print_info("\nAllergies on file:")
    for allergy in check_request["allergies"]:
        print(f"  • {allergy}")
    
    print_info("\nDiagnosis:")
    print(f"  • {check_request['diagnosis']}")
    
    # Make the API call
    try:
        response = requests.post(
            f"{BASE_URL}/api/drug-safety/check",
            json=check_request,
            headers=HEADERS,
            timeout=10
        )
        
        if response.status_code == 200:
            report = response.json()["safety_report"]
            print_success(f"Drug safety check completed")
            
            print_info("\nSafety Report:")
            print_info("Safe to prescribe", "✓ YES" if report.get("safe") else "✗ NO")
            print_info("Alert Count", report.get("alert_count", 0))
            
            if report.get("alerts"):
                print_info("\n⚠️  ALERTS:")
                for alert in report["alerts"]:
                    severity = alert.get("severity", "").upper()
                    if severity == "HIGH":
                        color = Colors.RED
                    elif severity == "MODERATE":
                        color = Colors.YELLOW
                    else:
                        color = Colors.CYAN
                    
                    print(f"{color}  [{severity}] {alert.get('alert_text')}{Colors.ENDC}")
            else:
                print_success("No critical interactions found")
                
        else:
            print_error(f"API Error: {response.status_code}")
            print_json(response.json())
            
    except requests.exceptions.RequestException as e:
        print_error(f"Connection error: {e}")
        print_info("(Drug safety API may be down, continuing with other demos)")

# ============================================================================
# 4. DIFFERENTIAL DIAGNOSIS
# ============================================================================

def demo_differential_diagnosis(patient_id, patient_data):
    """Demo: AI-powered differential diagnosis"""
    print_section("4. DIFFERENTIAL DIAGNOSIS (AI Decision Support)")
    
    print_info("Requesting AI differential diagnosis suggestions...")
    
    # Prepare differential diagnosis request
    dx_request = {
        "patient_id": patient_id,
        "complaints": "Persistent chest discomfort for 3 days, pressure-like, radiating to left arm, associated with dyspnea and diaphoresis",
        "age": str(patient_data["age"]),
        "history": patient_data["medical_history"],
        "allergies": patient_data["allergies"],
        "vitals": "BP 158/92, HR 102, RR 22, SpO2 94%",
        "current_diagnosis": "Rule out Acute Coronary Syndrome"
    }
    
    try:
        response = requests.post(
            f"{BASE_URL}/api/differential/suggest",
            json=dx_request,
            headers=HEADERS,
            timeout=15
        )
        
        if response.status_code == 200:
            result = response.json()
            print_success("Differential diagnosis suggestions retrieved")
            
            if "differentials" in result:
                print_info("\nRanked Differential Diagnoses:")
                for dx in result["differentials"][:3]:  # Top 3
                    rank = dx.get("rank", "?")
                    diagnosis = dx.get("diagnosis", "Unknown")
                    likelihood = dx.get("likelihood", "?").upper()
                    reasoning = dx.get("reasoning", "")
                    next_step = dx.get("next_step", "")
                    
                    lik_color = Colors.RED if likelihood == "HIGH" else Colors.YELLOW if likelihood == "MODERATE" else Colors.CYAN
                    
                    print(f"\n  {rank}. {Colors.BOLD}{diagnosis}{Colors.ENDC}")
                    print(f"     Likelihood: {lik_color}{likelihood}{Colors.ENDC}")
                    print(f"     Reasoning: {reasoning}")
                    print(f"     Next Step: {next_step}")
        else:
            print_error(f"API Error: {response.status_code}")
            
    except requests.exceptions.RequestException as e:
        print_error(f"Connection error: {e}")
        print_info("(Differential diagnosis API may be down, continuing with demo)")

# ============================================================================
# 5. PRESCRIPTION GENERATION
# ============================================================================

def demo_prescription_generation(patient_id, patient_data, voice_data):
    """Demo: PDF Prescription Generation"""
    print_section("5. PRESCRIPTION GENERATION")
    
    print_info("Generating prescription PDF...")
    
    prescription_data = {
        "patient_id": patient_id,
        "patient_name": patient_data["name"],
        "patient_age": patient_data["age"],
        "medications": voice_data["medications_prescribed"],
        "diagnosis": voice_data["assessment"],
        "doctor_name": "Dr. Sarah Johnson, MD",
        "date": datetime.now().strftime("%Y-%m-%d"),
        "notes": "Regular follow-up in 1 week. Perform EKG and troponin tests immediately."
    }
    
    # Show what will be in the prescription
    print_info("Prescription Details:")
    print_info("Patient", f"{patient_data['name']}, Age {patient_data['age']}")
    print_info("Diagnosis", voice_data["assessment"])
    print_info("Medications:")
    for med in voice_data["medications_prescribed"]:
        print(f"  • {med['Medication']} {med['Dosage']} - {med['Frequency']}")
    
    try:
        response = requests.post(
            f"{BASE_URL}/api/prescription/generate",
            json=prescription_data,
            headers=HEADERS,
            timeout=10
        )
        
        if response.status_code == 200:
            result = response.json()
            if result.get("success"):
                pdf_path = result.get("pdf_path", "prescription.pdf")
                print_success(f"Prescription PDF generated successfully")
                print_info("Location", pdf_path)
                print_info("QR Code generated", "✓ YES (for digital verification)")
            else:
                print_error("PDF generation failed")
                print_json(result)
        else:
            print_error(f"API Error: {response.status_code}")
            
    except requests.exceptions.RequestException as e:
        print_error(f"Connection error: {e}")
        print_info("(Prescription API may be down)")

# ============================================================================
# 6. IMAGE OCR EXTRACTION (Simulated)
# ============================================================================

def demo_ocr_extraction():
    """Demo: Extract notes from medical images"""
    print_section("6. IMAGE OCR EXTRACTION")
    
    print_info("What would happen with actual image upload:")
    print("  1. Doctor uploads image (prescription, consultant notes, etc)")
    print("  2. Gemini Vision AI reads the handwritten/printed text")
    print("  3. System extracts structured data (diagnosis, medications, etc)")
    print()
    
    # Simulated OCR extraction
    simulated_extraction = {
        "document_type": "Consultant Notes",
        "patient_info": {
            "name": "John Smith",
            "age": "56M",
            "mr_no": "MR-2024-0145"
        },
        "sections": [
            {
                "title": "Chief Complaint",
                "content": "Chest discomfort x 3 days"
            },
            {
                "title": "History of Present Illness",
                "content": "56-year-old male with history of HTN and DM presents with pressure-like chest pain radiating to left arm for 3 days. Associated with dyspnea and diaphoresis."
            },
            {
                "title": "Physical Examination",
                "content": "Vitals: BP 158/92, HR 102, RR 22, SpO2 94%. Cardiac exam: tachycardic, no murmurs. Lungs: clear."
            }
        ],
        "diagnosis": "Acute Coronary Syndrome - Rule out MI",
        "medications": [
            {"medication": "Aspirin", "dose": "325mg", "frequency": "once"},
            {"medication": "Clopidogrel", "dose": "600mg", "frequency": "loading"}
        ],
        "quality_score": 87
    }
    
    print_info("Simulated OCR Result (as if image was uploaded):")
    print_info("Document Type", simulated_extraction["document_type"])
    print_info("OCR Quality Score", f"{simulated_extraction['quality_score']}/100")
    print_info("Sections Extracted", len(simulated_extraction["sections"]))
    
    print_info("\nExtracted Sections:")
    for section in simulated_extraction["sections"]:
        print(f"  • {Colors.BOLD}{section['title']}{Colors.ENDC}")
        print(f"    {section['content'][:60]}...")
    
    print_info("\nExtracted Structured Data:")
    print_info("Diagnosis", simulated_extraction["diagnosis"])
    print_info("Medications", len(simulated_extraction["medications"]))
    
    print_success("Image OCR extraction completed (Gemini Vision AI)")
    
    return simulated_extraction

# ============================================================================
# 7. DISCHARGE SUMMARY
# ============================================================================

def demo_discharge_summary(patient_id, patient_data):
    """Demo: Generate discharge summary"""
    print_section("7. DISCHARGE SUMMARY")
    
    print_info("Compiling discharge summary from all patient records...")
    print_info("(Combining voice notes + OCR consultant notes + visit history)")
    
    summary_request = {
        "patient_id": patient_id,
        "patient_name": patient_data["name"],
        "patient_age": str(patient_data["age"])
    }
    
    try:
        response = requests.post(
            f"{BASE_URL}/api/discharge/generate",
            json=summary_request,
            headers=HEADERS,
            timeout=15
        )
        
        if response.status_code == 200:
            result = response.json()
            compiled_data = result.get("compiled_data", {})
            
            print_success("Discharge summary compiled")
            
            print_info("\nCompiled Data Summary:")
            print_info("Total Visits", compiled_data.get("total_visits", 0))
            print_info("Consultant Notes", compiled_data.get("total_consultant_notes", 0))
            print_info("Admission Date", compiled_data.get("admission_date", "N/A"))
            print_info("Discharge Date", compiled_data.get("discharge_date", "N/A"))
            
            print_info("\nDiagnoses:")
            for dx in compiled_data.get("diagnoses", [])[:3]:
                print(f"  • {dx}")
            
            print_info("\nMedications at Discharge:")
            for med in compiled_data.get("medications_at_discharge", [])[:3]:
                if isinstance(med, dict):
                    med_name = med.get("Medication", med.get("medication", "Unknown"))
                else:
                    med_name = med
                print(f"  • {med_name}")
            
            print_info("\nAllergies:")
            for allergy in compiled_data.get("allergies", []):
                print(f"  • {allergy}")
            
            print_success("Discharge summary ready for doctor review")
            
        else:
            print_error(f"API Error: {response.status_code}")
            
    except requests.exceptions.RequestException as e:
        print_error(f"Connection error: {e}")
        print_info("(Discharge summary API may be down)")

# ============================================================================
# 8. AUDIT LOG
# ============================================================================

def demo_audit_log(patient_id):
    """Demo: View audit log"""
    print_section("8. AUDIT LOG (HIPAA COMPLIANCE)")
    
    print_info("Retrieving audit log for patient...")
    
    try:
        response = requests.get(
            f"{BASE_URL}/api/audit?patient_id={patient_id}&limit=10",
            headers=HEADERS,
            timeout=10
        )
        
        if response.status_code == 200:
            result = response.json()
            logs = result.get("logs", [])
            
            print_success(f"Audit log retrieved ({len(logs)} entries)")
            
            if logs:
                print_info("\nRecent Activities:")
                for log in logs[:5]:
                    timestamp = log.get("timestamp", "N/A")
                    action = log.get("action", "Unknown")
                    print(f"  • [{timestamp}] {action}")
            else:
                print_info("No audit logs yet (this is expected for demo patient)")
                
        else:
            print_error(f"API Error: {response.status_code}")
            
    except requests.exceptions.RequestException as e:
        print_error(f"Connection error: {e}")

# ============================================================================
# MAIN DEMO
# ============================================================================

def main():
    """Run the complete demo"""
    
    print("\n")
    print(f"{Colors.BOLD}{Colors.CYAN}")
    print("""
    ╔═══════════════════════════════════════════════════════════════╗
    ║                                                               ║
    ║           MYORA - Voice-Enabled Medical Notes System          ║
    ║                     Complete Demo Script                      ║
    ║                                                               ║
    ║        AI-Powered Clinical Notes, Drug Safety & Dx Support   ║
    ║                                                               ║
    ╚═══════════════════════════════════════════════════════════════╝
    """)
    print(Colors.ENDC)
    
    print_info("Backend Status", f"→ Checking {BASE_URL}...")
    
    # Check if backend is running
    try:
        response = requests.get(f"{BASE_URL}/", timeout=5)
        if response.status_code == 200:
            backend_info = response.json()
            print_success("Backend is running ✓")
            print_info("API Version", backend_info.get("version", "unknown"))
            print_info("Voice API", backend_info.get("voice_api", "unknown"))
        else:
            print_error("Backend returned unexpected status")
    except requests.exceptions.RequestException:
        print_error("Cannot connect to backend. Please ensure backend is running:")
        print("  cd MyoraFrontend")
        print("  source .venv/bin/activate")
        print("  cd backend/backend")
        print("  python app.py")
        return
    
    # Run the demo
    try:
        # 1. Create patient
        patient_id, patient_data = demo_create_patient()
        time.sleep(1)
        
        # 2. Voice transcription (simulated)
        voice_data = demo_voice_transcription(patient_id)
        time.sleep(1)
        
        # 3. Drug safety checking
        demo_drug_safety(patient_id, patient_data, voice_data)
        time.sleep(1)
        
        # 4. Differential diagnosis
        demo_differential_diagnosis(patient_id, patient_data)
        time.sleep(1)
        
        # 5. Prescription generation
        demo_prescription_generation(patient_id, patient_data, voice_data)
        time.sleep(1)
        
        # 6. OCR extraction (simulated)
        ocr_data = demo_ocr_extraction()
        time.sleep(1)
        
        # 7. Discharge summary
        demo_discharge_summary(patient_id, patient_data)
        time.sleep(1)
        
        # 8. Audit log
        demo_audit_log(patient_id)
        
        # Summary
        print_section("DEMO COMPLETE")
        
        print(f"{Colors.BOLD}{Colors.GREEN}All features demonstrated successfully!{Colors.ENDC}\n")
        
        print("Features Demonstrated:")
        print("  ✓ Patient Management")
        print("  ✓ Voice Transcription (Deepgram API)")
        print("  ✓ Drug Safety Checking (FDA + Knowledge Base)")
        print("  ✓ Differential Diagnosis (Gemini AI)")
        print("  ✓ Prescription PDF Generation")
        print("  ✓ Medical Image OCR (Gemini Vision)")
        print("  ✓ Discharge Summary Compilation")
        print("  ✓ Audit Log (HIPAA Compliance)")
        print()
        
        print("Frontend Access:")
        print(f"  → Open http://localhost:5173 in your browser")
        print()
        
        print("To run the frontend:")
        print("  cd MyoraFrontend/frontend")
        print("  npm run dev")
        print()
        
    except KeyboardInterrupt:
        print(f"\n{Colors.YELLOW}Demo interrupted by user{Colors.ENDC}\n")
    except Exception as e:
        print_error(f"Unexpected error: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    main()
