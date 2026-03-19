"""
Discharge Summary Generator
----------------------------
Pulls all visit records (EMR voice notes + consultant notes),
compiles diagnoses, medications, and advice into a formatted
discharge summary. Doctor reviews and approves.
"""

from datetime import datetime
from db import emr_collection, consultant_notes


def gather_patient_records(patient_id: str) -> dict:
    """
    Collect all EMR voice notes and consultant notes for a patient.

    Returns
    -------
    dict with keys: emr_records, consultant_records, record_count
    """
    # EMR voice notes
    emr_docs = list(
        emr_collection.find({"patient_id": patient_id})
        .sort("timestamp", -1)
    )
    for doc in emr_docs:
        doc["_id"] = str(doc["_id"])
        if "timestamp" in doc:
            doc["timestamp"] = doc["timestamp"].isoformat()

    # Consultant (OCR) notes
    consult_docs = list(
        consultant_notes.find({"patient_id": patient_id})
        .sort("timestamp", -1)
    )
    for doc in consult_docs:
        doc["_id"] = str(doc["_id"])
        if "timestamp" in doc:
            doc["timestamp"] = doc["timestamp"].isoformat()

    return {
        "emr_records": emr_docs,
        "consultant_records": consult_docs,
        "record_count": len(emr_docs) + len(consult_docs),
    }


def compile_discharge_data(patient_id: str, patient_name: str = "",
                           patient_age: str = "") -> dict:
    """
    Compile all patient records into a structured discharge summary draft.
    The doctor reviews and approves before finalizing.

    Returns a dict ready for Gemini summarization or direct display.
    """
    records = gather_patient_records(patient_id)

    # Extract key fields from all EMR records
    all_diagnoses = []
    all_medications = []
    all_allergies = set()
    all_complaints = []
    all_advice = []
    all_summaries = []
    visit_dates = []

    for rec in records["emr_records"]:
        structured = rec.get("structured", {})
        if isinstance(structured, dict):
            dx = structured.get("Diagnosis", "")
            if dx and dx != "Not mentioned":
                all_diagnoses.append(dx)

            rx = structured.get("Rx", [])
            if isinstance(rx, list):
                all_medications.extend(rx)

            allergies = structured.get("Allergy", [])
            if isinstance(allergies, list):
                all_allergies.update(allergies)
            elif isinstance(allergies, str) and allergies != "Not mentioned":
                all_allergies.add(allergies)

            complaints = structured.get("Complaints_Presented", "")
            if complaints and complaints != "Not mentioned":
                all_complaints.append(complaints)

            advice = structured.get("Advice_FollowUp", "")
            if advice and advice != "Not mentioned":
                all_advice.append(advice)

            summary = structured.get("Visit_Summary", "")
            if summary and summary != "Not mentioned":
                all_summaries.append(summary)

        visit_date = rec.get("visit_date", "")
        if visit_date:
            visit_dates.append(visit_date)

    # Extract from consultant notes
    for rec in records["consultant_records"]:
        extracted = rec.get("extracted_json", {})
        if isinstance(extracted, dict):
            dx = extracted.get("Diagnosis", extracted.get("diagnosis", ""))
            if dx:
                all_diagnoses.append(dx)
            rx = extracted.get("Rx", extracted.get("medications", []))
            if isinstance(rx, list):
                all_medications.extend(rx)

    # Deduplicate medications by name
    seen_meds = set()
    unique_medications = []
    for med in all_medications:
        med_name = ""
        if isinstance(med, dict):
            med_name = med.get("Medication", med.get("medication", "")).lower().strip()
        elif isinstance(med, str):
            med_name = med.lower().strip()
        if med_name and med_name not in seen_meds:
            seen_meds.add(med_name)
            unique_medications.append(med)

    # Deduplicate diagnoses
    unique_diagnoses = list(dict.fromkeys(all_diagnoses))
    unique_advice = list(dict.fromkeys(all_advice))

    admission_date = visit_dates[-1] if visit_dates else ""
    discharge_date = datetime.now().strftime("%Y-%m-%d")

    return {
        "patient_name": patient_name,
        "patient_age": patient_age,
        "patient_id": patient_id,
        "admission_date": admission_date,
        "discharge_date": discharge_date,
        "diagnoses": unique_diagnoses,
        "medications_at_discharge": unique_medications,
        "allergies": list(all_allergies),
        "complaints": all_complaints,
        "visit_summaries": all_summaries,
        "advice_followup": unique_advice,
        "total_visits": len(records["emr_records"]),
        "total_consultant_notes": len(records["consultant_records"]),
        "status": "draft",
    }
