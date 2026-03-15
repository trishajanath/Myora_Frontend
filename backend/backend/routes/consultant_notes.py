# """
# routes/consultant_notes.py
# ----------------------------------------------------------
# Handles Consultant Notes Extraction from multiple image uploads
# using Gemini 2.0 Flash and stores structured JSON in MongoDB.
# ----------------------------------------------------------
# """

# import io
# import re
# import base64
# import json
# from datetime import datetime
# from flask import Blueprint, request, jsonify
# from PIL import Image
# import google.generativeai as genai
# from config import Config
# from db import db

# # ---------------- Configuration ----------------
# consultant_bp = Blueprint("consultant_bp", __name__)
# collection = db["extracted_notes"]

# # Gemini setup
# genai.configure(api_key=Config.GEMINI_API_KEY)
# GEMINI_MODEL = genai.GenerativeModel("gemini-2.0-flash")

# # ---------------- Helper Functions ----------------
# def clean_json_response(response_text):
#     """Extract valid JSON from Gemini response text."""
#     if not response_text:
#         return None
#     response_text = response_text.strip().replace('```json', '').replace('```', '')
#     start_idx, end_idx = response_text.find('{'), response_text.rfind('}')
#     if start_idx != -1 and end_idx != -1:
#         json_str = response_text[start_idx:end_idx + 1]
#         json_str = re.sub(r',\s*}', '}', json_str)
#         json_str = re.sub(r',\s*]', ']', json_str)
#         return json_str
#     return None


# def extract_medical_notes_from_image(img):
#     """Extract structured consultant notes from an image using Gemini."""
#     buf = io.BytesIO()
#     img.save(buf, format="PNG")
#     img_b64 = base64.b64encode(buf.getvalue()).decode()

#     prompt = """You are a medical data extraction expert. Analyze this CONSULTANT NOTES table and extract ALL information.

# **TABLE STRUCTURE:**
# This table has these columns:
# - "No. of DAYS" (shows DAY 1, DAY 2, DAY 3, DAY 4)
# - "Date:" field at the start of each row
# - "CONSULTANT NOTES" (main column with handwritten doctor's notes)
# - "INV." (Investigations column)
# - "PLAN" (Plan column)

# **INSTRUCTIONS:**
# 1. Extract data for EACH DAY visible in the table (DAY 1, DAY 2, DAY 3, DAY 4)
# 2. For each day, extract:
#    - Day number
#    - Date (if written in Date: field)
#    - Everything written in CONSULTANT NOTES column
#    - Everything written in INV. column  
#    - Everything written in PLAN column
# 3. This is doctor's handwriting - make your BEST effort to read it and try to replace it with respect to the surrounding context words if found wrong
# 4. If uncertain about a word, add [check] after it
# 5. DO NOT skip illegible text - try to read it and mark uncertain words

# **OUTPUT FORMAT:**
# Return ONLY valid JSON in this exact format:
# {
#   "days": [
#     {
#       "day_number": 1,
#       "date": "date as written or null",
#       "consultant_notes": "everything from consultant notes column",
#       "investigations": "everything from INV column or null",
#       "plan": "everything from PLAN column or null"
#     },
#     {
#       "day_number": 2,
#       "date": "date as written or null",
#       "consultant_notes": "everything from consultant notes column",
#       "investigations": "everything from INV column or null",
#       "plan": "everything from PLAN column or null"
#     }
#   ]
# }
# Extract ALL days now. Return ONLY the JSON, no explanations."""

#     response = GEMINI_MODEL.generate_content(
#         [
#             {"inline_data": {"data": img_b64, "mime_type": "image/png"}},
#             {"text": prompt}
#         ],
#         generation_config={"temperature": 0.2, "max_output_tokens": 8192}
#     )

#     if response and response.text:
#         response_text = response.text.strip()
#         cleaned_json = clean_json_response(response_text)
#         if cleaned_json:
#             try:
#                 return json.loads(cleaned_json)
#             except json.JSONDecodeError:
#                 pass
#     return {"days": []}


# def merge_day_data(existing_data, new_data):
#     """Merge day-wise consultant note data."""
#     all_days = {day["day_number"]: day for day in existing_data.get("days", [])}

#     for day_info in new_data.get("days", []):
#         day_num = day_info.get("day_number")
#         if day_num not in all_days:
#             all_days[day_num] = day_info
#         else:
#             # Merge non-empty fields
#             for key, val in day_info.items():
#                 if val and not all_days[day_num].get(key):
#                     all_days[day_num][key] = val

#     return {"days": list(all_days.values())}


# @consultant_bp.route("/extract_notes", methods=["POST"])
# def extract_notes():
#     """
#     POST: Extract day-wise consultant notes from images.
#     Does NOT save to DB.
#     """
#     try:
#         if "files" not in request.files:
#             return jsonify({"error": "At least one image file is required"}), 400

#         images = request.files.getlist("files")
#         all_extracted_data = {"days": []}

#         for img_file in images:
#             img = Image.open(img_file.stream)
#             if img.mode not in ("RGB", "L"):
#                 img = img.convert("RGB")
#             extracted = extract_medical_notes_from_image(img)
#             all_extracted_data = merge_day_data(all_extracted_data, extracted)

#         return jsonify({
#             "message": "Extraction successful",
#             "extracted_json": all_extracted_data
#         })
#     # except Exception as e:
#     #     return jsonify({"error": f"Extraction failed: {str(e)}"}), 500
#     except Exception as e:
#         print("❌ extract_notes crashed")
#         print("Error:", e)
#         import traceback
#         traceback.print_exc()
#         return jsonify({"error": str(e)}), 500


# @consultant_bp.route("/save_notes", methods=["POST"])
# def save_notes():
#     """
#     POST: Save extracted notes JSON to MongoDB.
#     Requires: patient_id + extracted_json
#     """
#     try:
#         data = request.get_json()

#         patient_id = data.get("patient_id")
#         extracted_json = data.get("extracted_json")

#         if not patient_id:
#             return jsonify({"error": "patient_id is required"}), 400
#         if not extracted_json:
#             return jsonify({"error": "extracted_json is required"}), 400

#         output_doc = {
#             "patient_id": patient_id,
#             "uploaded_at": datetime.now().isoformat(),
#             "total_days_extracted": len(extracted_json.get("days", [])),
#             "data": extracted_json
#         }

#         inserted_id = collection.insert_one(output_doc).inserted_id

#         return jsonify({
#             "message": "Saved to DB",
#             "mongo_id": str(inserted_id)
#         })
#     except Exception as e:
#         return jsonify({"error": f"Save failed: {str(e)}"}), 500

# @consultant_bp.route("/get_notes/<patient_id>", methods=["GET"])
# def get_notes(patient_id):
#     """Fetch all extracted consultant notes for a patient."""
#     results = list(collection.find({"patient_id": patient_id}, {"_id": 0}))
#     if not results:
#         return jsonify({"message": "No records found"}), 404
#     return jsonify(results)





"""
routes/consultant_notes.py
----------------------------------------------------------
Handles Consultant Notes Extraction from multiple image uploads
using Gemini 2.0 Flash and stores structured JSON in MongoDB.
----------------------------------------------------------
"""

import io
import re
import json
from datetime import datetime
from flask import Blueprint, request, jsonify
from PIL import Image
import google.generativeai as genai
from config import Config
from db import db

# ---------------- Configuration ----------------
consultant_bp = Blueprint("consultant_bp", __name__)
collection = db["extracted_notes"]

# ---------------- Gemini Setup ----------------
genai.configure(api_key=Config.GEMINI_API_KEY)
GEMINI_MODEL = genai.GenerativeModel("gemini-2.0-flash")

# ---------------- Helper Functions ----------------
def clean_json_response(response_text: str):
    """Extract valid JSON from Gemini response text."""
    if not response_text:
        return None

    response_text = response_text.strip()
    response_text = response_text.replace("```json", "").replace("```", "")

    start_idx = response_text.find("{")
    end_idx = response_text.rfind("}")

    if start_idx == -1 or end_idx == -1:
        return None

    json_str = response_text[start_idx:end_idx + 1]

    # Remove trailing commas (LLM safety)
    json_str = re.sub(r",\s*}", "}", json_str)
    json_str = re.sub(r",\s*]", "]", json_str)

    return json_str


def extract_medical_notes_from_image(img: Image.Image):
    """Extract structured data from any medical document image using Gemini."""

    prompt = """
You are a medical data extraction expert. Analyze this medical document image and extract ALL visible information.

**INSTRUCTIONS:**
1. Identify the document type (e.g. OPD Summary, Consultant Notes, Prescription, Lab Report, Discharge Summary, etc.)
2. Extract every field, section, and value visible in the document
3. For handwritten text, make your best effort to read it; mark uncertain words with [check]
4. Do NOT skip any section - extract everything

**OUTPUT FORMAT:**
Return ONLY valid JSON with this structure (adapt sections to match whatever is in the document):
{
  "document_type": "type of document",
  "patient_info": {
    "name": "patient name or null",
    "age": "age or null",
    "sex": "sex or null",
    "mr_no": "MR/patient ID or null",
    "date": "document date or null",
    "doctor": "doctor name or null",
    "hospital": "hospital name or null"
  },
  "sections": [
    {
      "title": "section heading (e.g. HISTORY, EXAMINATION, DIAGNOSIS, PRESCRIPTION, etc.)",
      "content": "all text content in this section as a string"
    }
  ],
  "investigations": "any investigations/tests mentioned or null",
  "diagnosis": "diagnosis if present or null",
  "prescription": "medications/treatment if present or null",
  "notes": "any additional notes or null"
}

Return ONLY the JSON. No explanations.
"""

    try:
        response = GEMINI_MODEL.generate_content(
            [img, prompt],
            generation_config={
                "temperature": 0.2,
                "max_output_tokens": 8192
            }
        )

        if not response or not response.text:
            return {"document_type": "unknown", "sections": [], "error": "No response from model"}

        cleaned_json = clean_json_response(response.text)

        if not cleaned_json:
            return {"document_type": "unknown", "sections": [], "raw_text": response.text}

        return json.loads(cleaned_json)

    except Exception as e:
        print("❌ Gemini extraction failed:", e)
        import traceback
        traceback.print_exc()
        return {"document_type": "unknown", "sections": [], "error": str(e)}



def merge_day_data(existing_data, new_data):
    """Merge extracted data from multiple images."""
    if not existing_data.get("sections") and not existing_data.get("document_type"):
        return new_data

    existing_sections = existing_data.get("sections", [])
    new_sections = new_data.get("sections", [])

    existing_titles = {s["title"] for s in existing_sections}
    for section in new_sections:
        if section["title"] not in existing_titles:
            existing_sections.append(section)

    existing_data["sections"] = existing_sections
    return existing_data


# ---------------- Routes ----------------
@consultant_bp.route("/extract_notes", methods=["POST"])
def extract_notes():
    """
    POST: Extract day-wise consultant notes from uploaded images.
    Does NOT save to DB.
    """
    try:
        if "files" not in request.files:
            return jsonify({"error": "At least one image file is required"}), 400

        images = request.files.getlist("files")
        all_extracted_data = {}

        for img_file in images:
            img = Image.open(img_file.stream)
            if img.mode not in ("RGB", "L"):
                img = img.convert("RGB")

            extracted = extract_medical_notes_from_image(img)
            all_extracted_data = merge_day_data(all_extracted_data, extracted)

        return jsonify({
            "message": "Extraction successful",
            "extracted_json": all_extracted_data
        })

    except Exception as e:
        print("❌ extract_notes crashed:", e)
        import traceback
        traceback.print_exc()
        return jsonify({"error": str(e)}), 500


@consultant_bp.route("/save_notes", methods=["POST"])
def save_notes():
    """
    POST: Save extracted consultant notes to MongoDB.
    """
    try:
        data = request.get_json(silent=True)

        if not data:
            return jsonify({"error": "Invalid JSON body"}), 400

        patient_id = data.get("patient_id")
        extracted_json = data.get("extracted_json")

        if not patient_id:
            return jsonify({"error": "patient_id is required"}), 400
        if not extracted_json:
            return jsonify({"error": "extracted_json is required"}), 400

        doc = {
            "patient_id": patient_id,
            "uploaded_at": datetime.utcnow().isoformat(),
            "total_days_extracted": len(extracted_json.get("days", [])),
            "data": extracted_json
        }

        result = collection.insert_one(doc)

        return jsonify({
            "message": "Saved successfully",
            "mongo_id": str(result.inserted_id)
        })

    except Exception as e:
        return jsonify({"error": f"Save failed: {str(e)}"}), 500


@consultant_bp.route("/get_notes/<patient_id>", methods=["GET"])
def get_notes(patient_id):
    """Fetch extracted consultant notes for a patient."""
    results = list(collection.find({"patient_id": patient_id}, {"_id": 0}))
    if not results:
        return jsonify({"message": "No records found"}), 404
    return jsonify(results)
