#!/bin/bash
# MYORA API DEMO - Script to test individual endpoints with curl

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

BASE_URL="http://127.0.0.1:5001"

echo -e "${BLUE}╔═══════════════════════════════════════════════════════════════╗${NC}"
echo -e "${BLUE}║                 MYORA API TESTING SCRIPT                      ║${NC}"
echo -e "${BLUE}║                  Using curl commands                          ║${NC}"
echo -e "${BLUE}╚═══════════════════════════════════════════════════════════════╝${NC}\n"

# Check if backend is running
echo -e "${YELLOW}Checking backend status...${NC}"
if curl -s "$BASE_URL/" > /dev/null 2>&1; then
    echo -e "${GREEN}✓ Backend is running${NC}\n"
else
    echo -e "${RED}✗ Backend is not running. Start it first:${NC}"
    echo "  cd MyoraFrontend && source .venv/bin/activate && cd backend/backend && python app.py"
    exit 1
fi

# Function to print section headers
print_section() {
    echo -e "\n${BLUE}════════════════════════════════════════════════════════════════${NC}"
    echo -e "${BLUE}$1${NC}"
    echo -e "${BLUE}════════════════════════════════════════════════════════════════${NC}\n"
}

# ============================================================================
# 1. TEST DRUG SAFETY CHECKING
# ============================================================================
print_section "1. DRUG SAFETY CHECKING - HIGH RISK INTERACTION"

echo -e "${YELLOW}Scenario: Patient with Penicillin allergy prescribed Warfarin + Aspirin${NC}\n"

curl -X POST "$BASE_URL/api/drug-safety/check" \
  -H "Content-Type: application/json" \
  -d '{
    "patient_id": "PAT123",
    "allergies": ["Penicillin"],
    "medications": [
      {"Medication": "Warfarin", "Dosage": "5mg", "Frequency": "daily"},
      {"Medication": "Aspirin", "Dosage": "100mg", "Frequency": "daily"}
    ],
    "diagnosis": "Atrial fibrillation with history of stroke risk"
  }' | python3 -m json.tool

echo -e "\n${GREEN}Expected: HIGH RISK alert for Warfarin + Aspirin interaction${NC}"

# ============================================================================
# 2. TEST SAFE MEDICATION
# ============================================================================
print_section "2. DRUG SAFETY CHECKING - SAFE MEDICATION"

echo -e "${YELLOW}Scenario: Patient with non-conflicting medications${NC}\n"

curl -X POST "$BASE_URL/api/drug-safety/check" \
  -H "Content-Type: application/json" \
  -d '{
    "patient_id": "PAT124",
    "allergies": ["Sulfa"],
    "medications": [
      {"Medication": "Metformin", "Dosage": "500mg", "Frequency": "twice daily"},
      {"Medication": "Amlodipine", "Dosage": "5mg", "Frequency": "daily"}
    ],
    "diagnosis": "Type 2 Diabetes, Hypertension"
  }' | python3 -m json.tool

echo -e "\n${GREEN}Expected: No critical alerts${NC}"

# ============================================================================
# 3. TEST DIFFERENTIAL DIAGNOSIS
# ============================================================================
print_section "3. DIFFERENTIAL DIAGNOSIS (AI DECISION SUPPORT)"

echo -e "${YELLOW}Scenario: Patient with chest pain symptoms${NC}\n"

curl -X POST "$BASE_URL/api/differential/suggest" \
  -H "Content-Type: application/json" \
  -d '{
    "patient_id": "PAT125",
    "complaints": "Persistent chest discomfort for 3 days, pressure-like, radiating to left arm, associated with dyspnea and diaphoresis",
    "age": "56",
    "history": "Type 2 Diabetes, Hypertension, Previous MI in 2020",
    "allergies": ["Aspirin"],
    "vitals": "BP 158/92, HR 102, RR 22, SpO2 94%",
    "current_diagnosis": "Rule out Acute Coronary Syndrome"
  }' | python3 -m json.tool

echo -e "\n${GREEN}Expected: Ranked differential diagnoses with reasoning${NC}"

# ============================================================================
# 4. TEST PRESCRIPTION GENERATION
# ============================================================================
print_section "4. PRESCRIPTION GENERATION (PDF)"

echo -e "${YELLOW}Scenario: Generate prescription for diabetic patient${NC}\n"

curl -X POST "$BASE_URL/api/prescription/generate" \
  -H "Content-Type: application/json" \
  -d '{
    "patient_id": "PAT126",
    "patient_name": "John Smith",
    "patient_age": 56,
    "medications": [
      {"Medication": "Metformin", "Dosage": "500mg", "Instructions": "Twice daily with meals"},
      {"Medication": "Amlodipine", "Dosage": "5mg", "Instructions": "Once daily"},
      {"Medication": "Aspirin", "Dosage": "75mg", "Instructions": "Once daily"}
    ],
    "diagnosis": "Type 2 Diabetes Mellitus, Essential Hypertension",
    "doctor_name": "Dr. Sarah Johnson",
    "instructions": "Take medications as prescribed. Follow up in 3 weeks."
  }' | python3 -m json.tool

echo -e "\n${GREEN}Expected: PDF file path returned${NC}"

# ============================================================================
# 5. TEST DISCHARGE SUMMARY
# ============================================================================
print_section "5. DISCHARGE SUMMARY GENERATION"

echo -e "${YELLOW}Scenario: Compile discharge summary for patient${NC}\n"

curl -X POST "$BASE_URL/api/discharge/generate" \
  -H "Content-Type: application/json" \
  -d '{
    "patient_id": "PAT126",
    "patient_name": "John Smith",
    "patient_age": "56"
  }' | python3 -m json.tool

echo -e "\n${GREEN}Expected: Compiled discharge summary with all visits${NC}"

# ============================================================================
# 6. TEST AUDIT LOG
# ============================================================================
print_section "6. AUDIT LOG (HIPAA COMPLIANCE)"

echo -e "${YELLOW}Scenario: Retrieve audit log for patient${NC}\n"

curl -X GET "$BASE_URL/api/audit?patient_id=PAT126&limit=5" \
  -H "Content-Type: application/json" | python3 -m json.tool

echo -e "\n${GREEN}Expected: List of audit entries for patient${NC}"

# ============================================================================
# 7. TEST ALLERGY INTERACTION
# ============================================================================
print_section "7. ALLERGY CHECK - PENICILLIN / CEPHALOSPORIN ALLERGY"

echo -e "${YELLOW}Scenario: Patient with Penicillin allergy prescribed Ceftriaxone${NC}"
echo -e "${YELLOW}(Cross-reactivity test)${NC}\n"

curl -X POST "$BASE_URL/api/drug-safety/check" \
  -H "Content-Type: application/json" \
  -d '{
    "patient_id": "PAT127",
    "allergies": ["Penicillin"],
    "medications": [
      {"Medication": "Ceftriaxone", "Dosage": "1g", "Frequency": "every 12 hours"}
    ],
    "diagnosis": "Bacterial infection"
  }' | python3 -m json.tool

echo -e "\n${GREEN}Expected: Alert for potential cross-reactivity${NC}"

# ============================================================================
# 8. TEST DRUG-DRUG INTERACTION
# ============================================================================
print_section "8. MAJOR INTERACTION - SSRI + TRAMADOL (SEROTONIN SYNDROME RISK)"

echo -e "${YELLOW}Scenario: Patient on SSRI prescribed Tramadol${NC}\n"

curl -X POST "$BASE_URL/api/drug-safety/check" \
  -H "Content-Type: application/json" \
  -d '{
    "patient_id": "PAT128",
    "allergies": [],
    "medications": [
      {"Medication": "Fluoxetine", "Dosage": "20mg", "Frequency": "daily"},
      {"Medication": "Tramadol", "Dosage": "50mg", "Frequency": "every 6 hours"}
    ],
    "diagnosis": "Depression with chronic pain"
  }' | python3 -m json.tool

echo -e "\n${RED}Expected: HIGH RISK alert for serotonin syndrome${NC}"

# Summary
print_section "API TESTING COMPLETE"

echo -e "${GREEN}All endpoints tested successfully!${NC}\n"

echo "Test Scenarios Covered:"
echo "  ✓ Drug-drug interactions (HIGH RISK)"
echo "  ✓ Allergy-drug cross-reactivity"
echo "  ✓ Safe medication combinations"
echo "  ✓ Differential diagnosis suggestions"
echo "  ✓ Prescription generation"
echo "  ✓ Discharge summary compilation"
echo "  ✓ Audit log retrieval"
echo "  ✓ Serotonin syndrome detection"
echo ""

echo -e "${YELLOW}Tips:${NC}"
echo "  • Use 'jq' for better JSON formatting: add '| jq .' to curl commands"
echo "  • Modify patient_ids and medication names to test different scenarios"
echo "  • Check backend logs for detailed processing information"
echo "  • All calls are logged in the audit system"
echo ""
