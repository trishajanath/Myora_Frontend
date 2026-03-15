# -*- coding: utf-8 -*-
"""
routes/consultant_notes.py
----------------------------------------------------------
Handles Consultant Notes Extraction from multiple image uploads
using Gemini 2.5 Flash and stores structured JSON in MongoDB.
----------------------------------------------------------
"""

import io
import re
import json
from datetime import datetime
from flask import Blueprint, request, jsonify
from PIL import Image, ImageEnhance, ImageFilter, ImageOps
import google.generativeai as genai
from config import Config
from db import db
from audit import log_audit, AuditAction
from utils.ocr_quality import (
    score_image_quality,
    adaptive_enhance,
    get_enhancement_strategies,
    apply_enhancement_strategy,
    detect_document_regions,
)

# ---------------- Configuration ----------------
consultant_bp = Blueprint("consultant_bp", __name__)
collection = db["extracted_notes"]

# ---------------- Gemini Setup ----------------
genai.configure(api_key=Config.GEMINI_API_KEY)
GEMINI_MODEL = genai.GenerativeModel("gemini-2.5-flash")

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


def preprocess_image(img: Image.Image) -> Image.Image:
    """Enhance image for better handwriting recognition."""
    # Auto-orient based on EXIF data
    img = ImageOps.exif_transpose(img)

    # Upscale small images — larger = more readable for the model
    min_dim = 2000
    w, h = img.size
    if max(w, h) < min_dim:
        scale = min_dim / max(w, h)
        img = img.resize((int(w * scale), int(h * scale)), Image.LANCZOS)

    # Convert to grayscale for cleaner text
    gray = img.convert("L")

    # Denoise: slight blur to reduce speckle before sharpening
    gray = gray.filter(ImageFilter.MedianFilter(size=3))

    # Increase contrast strongly to make ink stand out
    gray = ImageEnhance.Contrast(gray).enhance(2.5)

    # Sharpen aggressively to restore edge detail
    gray = gray.filter(ImageFilter.SHARPEN)
    gray = gray.filter(ImageFilter.SHARPEN)
    gray = ImageEnhance.Sharpness(gray).enhance(2.0)

    # Auto-contrast to use full dynamic range
    gray = ImageOps.autocontrast(gray, cutoff=1)

    # Back to RGB (required by Gemini)
    return gray.convert("RGB")


def prepare_original_image(img: Image.Image) -> Image.Image:
    """Prepare the original image (no heavy processing) for cross-reference."""
    img = ImageOps.exif_transpose(img)

    # Only upscale if very small
    min_dim = 1800
    w, h = img.size
    if max(w, h) < min_dim:
        scale = min_dim / max(w, h)
        img = img.resize((int(w * scale), int(h * scale)), Image.LANCZOS)

    if img.mode != "RGB":
        img = img.convert("RGB")
    return img


def extract_medical_notes_from_image(img: Image.Image, quality_report: dict = None):
    """Extract structured data from any medical document image using Gemini.
    Uses quality-aware adaptive enhancement + multi-pass OCR strategy.
    Sends both the original and an enhanced version for cross-referencing."""

    original = prepare_original_image(img)

    # Use adaptive enhancement if quality report is available
    if quality_report:
        enhanced = adaptive_enhance(img, quality_report)
    else:
        enhanced = preprocess_image(img)

    prompt = """You are an expert medical document OCR specialist with years of experience reading doctors' handwriting with extremely high accuracy.

**IMAGES PROVIDED:**
You are given TWO versions of the same document:
- Image 1: The original image in full color
- Image 2: An enhanced/sharpened version for better text visibility
Cross-reference BOTH images when reading. If a letter is unclear in one, check the other.

**YOUR TASK:**
Carefully read this medical document image. It likely contains handwritten text by a doctor or hospital staff. Transcribe EVERY piece of visible text with maximum accuracy.

**HANDWRITING READING RULES (critical for accuracy):**
1. Read EACH word letter by letter, slowly. Do NOT guess whole words from the first few letters.
2. Use MEDICAL CONTEXT to resolve ambiguous letters:
   - If a word looks like gibberish, think about what medical term fits the context.
   - Common misreads: "a" vs "o", "e" vs "c", "n" vs "m", "u" vs "v", "r" vs "n", "h" vs "b", "i" vs "l",  "t" vs "f"
   - Examples: "Sciatpu" -> "Sciatica", "Erymmen" -> "Erythema", "Serome" -> "Syndrome"
3. Common medical abbreviations (KEEP as-is, do not expand): BP, HR, RR, SpO2, OPD, IPD, OT, ICU, IV, IM, PO, BD, TDS, QID, PRN, SOS, Rx, Dx, Hx, c/o, h/o, k/c/o, s/p, etc.
4. For PATIENT NAMES and PROPER NOUNS: read letter by letter from the image. Slashes in names (like "Kishore/Kumar") usually mean "son/daughter of" -- preserve them.
5. For DATES: look for patterns DD/MM/YY or DD/MM/YYYY. Numbers that look odd are probably dates.
6. For MEDICATIONS: match partial readings to real drug names:
   - "Amoxclv" -> "Amoxiclav", "Pantprzl" -> "Pantoprazole", "Ceftxm" -> "Ceftriaxone"
   - "Azithro" -> "Azithromycin", "Metfrmn" -> "Metformin", "Atorvst" -> "Atorvastatin"
   - "Paractml" -> "Paracetamol", "Ibuprfn" -> "Ibuprofen", "Omeprzl" -> "Omeprazole"
7. For DIAGNOSES: match to real medical conditions:
   - "IVDP" -> "IVDP (Intervertebral Disc Prolapse)", "LBA" -> "Low Back Ache"
   - "HTN" -> "Hypertension", "DM" -> "Diabetes Mellitus", "CAD" -> "Coronary Artery Disease"
8. If a word is STILL unclear after checking both images, write your best reading and add [?] after it.
9. NEVER output random characters, Greek letters, or symbols. Always produce readable English text.
10. For NUMBERS (vitals, doses, lab values): read each digit carefully. Distinguish 1/7, 3/8, 5/6, 0/6/9.

**VERIFICATION STEP:**
After your first reading, re-read each field and verify:
- Do all drug names correspond to real medications?
- Do diagnoses correspond to real medical conditions?
- Are dates in a valid format?
- Do patient details (age, sex) look reasonable?
Correct any errors before producing the final output.

**DOCUMENT ANALYSIS:**
1. First identify the document type (OPD Summary, Consultant Notes, Prescription, Medical Certificate, Lab Report, Discharge Summary, Referral Letter, Progress Notes, etc.)
2. Extract EVERY visible section, field, and value -- do not skip anything
3. Preserve the structure (tables, rows, columns, sections)
4. For tabular data, represent each row as a separate section entry

**OUTPUT FORMAT:**
Return ONLY valid JSON (no text before or after):
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
      "title": "section heading",
      "content": "fully transcribed text content of this section"
    }
  ],
  "investigations": "any investigations/tests mentioned or null",
  "diagnosis": "diagnosis if present or null",
  "prescription": "medications/treatment with dosages if present or null",
  "notes": "any additional notes or null"
}

Return ONLY the JSON, no explanations."""

    try:
        # Send both images for cross-referencing
        response = GEMINI_MODEL.generate_content(
            [original, enhanced, prompt],
            generation_config={
                "temperature": 0.1,
                "max_output_tokens": 16384
            }
        )

        if not response or not response.text:
            return {"document_type": "unknown", "sections": [], "error": "No response from model"}

        cleaned_json = clean_json_response(response.text)

        if not cleaned_json:
            # Retry with slightly higher temperature if first attempt failed to produce JSON
            response = GEMINI_MODEL.generate_content(
                [original, enhanced, prompt + "\n\nIMPORTANT: You MUST return valid JSON only."],
                generation_config={
                    "temperature": 0.3,
                    "max_output_tokens": 16384
                }
            )
            if response and response.text:
                cleaned_json = clean_json_response(response.text)

            if not cleaned_json:
                return {"document_type": "unknown", "sections": [], "raw_text": response.text if response else ""}

        return json.loads(cleaned_json)

    except Exception as e:
        print("Gemini extraction failed:", e)
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
    Now includes quality scoring, adaptive enhancement, multi-pass OCR,
    and region-of-interest detection. Does NOT save to DB.
    """
    try:
        if "files" not in request.files:
            return jsonify({"error": "At least one image file is required"}), 400

        images = request.files.getlist("files")
        all_extracted_data = {}
        quality_reports = []
        region_data = []

        for img_file in images:
            img = Image.open(img_file.stream)
            if img.mode not in ("RGB", "L"):
                img = img.convert("RGB")

            # ── Step 1: Quality scoring ──
            quality_report = score_image_quality(img)
            quality_reports.append({
                "filename": img_file.filename,
                **quality_report,
            })
            print(f"Image quality: {quality_report['quality_rating']} "
                  f"({quality_report['overall_score']}/100)")

            # ── Step 2: Region-of-interest detection ──
            regions = detect_document_regions(img)
            region_data.append({
                "filename": img_file.filename,
                "regions": regions,
            })

            # ── Step 3: Adaptive enhancement + extraction ──
            extracted = extract_medical_notes_from_image(img, quality_report)

            # ── Step 4: Multi-pass OCR for poor quality images ──
            if quality_report["overall_score"] < 60:
                print("Low quality image -- attempting multi-pass OCR")
                strategies = get_enhancement_strategies(quality_report)
                best_result = extracted
                best_section_count = len(extracted.get("sections", []))

                for strategy in strategies[1:]:  # Skip first (already done)
                    try:
                        alt_enhanced = apply_enhancement_strategy(
                            img, strategy["name"], quality_report
                        )
                        alt_img_pil = alt_enhanced
                        alt_original = prepare_original_image(img)

                        alt_response = GEMINI_MODEL.generate_content(
                            [alt_original, alt_img_pil,
                             "Extract all text from this medical document as structured JSON. "
                             "Return ONLY valid JSON with keys: document_type, patient_info, "
                             "sections, investigations, diagnosis, prescription, notes."],
                            generation_config={
                                "temperature": 0.1,
                                "max_output_tokens": 16384,
                            },
                        )
                        if alt_response and alt_response.text:
                            alt_json = clean_json_response(alt_response.text)
                            if alt_json:
                                alt_data = json.loads(alt_json)
                                alt_sections = len(alt_data.get("sections", []))
                                if alt_sections > best_section_count:
                                    best_result = alt_data
                                    best_section_count = alt_sections
                                    print(f"  Strategy '{strategy['name']}' "
                                          f"found {alt_sections} sections (better)")
                    except Exception as strat_err:
                        print(f"  Strategy '{strategy['name']}' failed: {strat_err}")

                extracted = best_result

            all_extracted_data = merge_day_data(all_extracted_data, extracted)

        log_audit(
            AuditAction.OCR_EXTRACT,
            details={
                "images_count": len(images),
                "document_type": all_extracted_data.get("document_type"),
                "avg_quality": round(
                    sum(q["overall_score"] for q in quality_reports) / max(len(quality_reports), 1), 1
                ),
            },
        )

        return jsonify({
            "message": "Extraction successful",
            "extracted_json": all_extracted_data,
            "quality_reports": quality_reports,
            "regions": region_data,
        })

    except Exception as e:
        print("extract_notes error:", e)
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

        log_audit(
            AuditAction.OCR_SAVE,
            patient_id=patient_id,
            details={"mongo_id": str(result.inserted_id)},
        )

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

    log_audit(
        AuditAction.OCR_VIEW,
        patient_id=patient_id,
        details={"records_returned": len(results)},
    )

    if not results:
        return jsonify({"message": "No records found"}), 404
    return jsonify(results)
