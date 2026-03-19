from flask import Blueprint, request, jsonify
from PIL import Image, ImageOps, ImageEnhance, ImageFilter
import pytesseract
import re
import io

ocr_bp = Blueprint("ocr_bp", __name__)


def _preprocess_image(image: Image.Image) -> Image.Image:
    """Apply lightweight OCR-focused preprocessing with PIL."""
    image = ImageOps.exif_transpose(image)

    # Upscale small images to improve OCR accuracy.
    w, h = image.size
    min_side = 1400
    if min(w, h) < min_side:
        scale = min_side / float(min(w, h))
        image = image.resize((int(w * scale), int(h * scale)), Image.LANCZOS)

    gray = image.convert("L")
    gray = ImageOps.autocontrast(gray, cutoff=1)
    gray = ImageEnhance.Contrast(gray).enhance(1.8)
    gray = gray.filter(ImageFilter.MedianFilter(size=3))

    # Simple binarization to reduce background noise.
    bw = gray.point(lambda px: 255 if px > 160 else 0, mode="1")
    return bw.convert("RGB")


def _safe_confidence(values):
    scores = []
    for value in values:
        try:
            score = float(value)
            if score >= 0:
                scores.append(score)
        except (TypeError, ValueError):
            continue
    return round(sum(scores) / len(scores), 2) if scores else 0.0


def _extract_medical_key_values(text: str):
    """Parse common lab/value patterns from OCR text."""
    patterns = {
        "hemoglobin": r"(?i)\b(?:hemoglobin|haemoglobin|hb)\b\s*[:=-]?\s*(\d+(?:\.\d+)?)\s*(g/dl|gm/dl|g%)?",
        "glucose": r"(?i)\b(?:glucose|blood\s*sugar|fbs|rbs)\b\s*[:=-]?\s*(\d+(?:\.\d+)?)\s*(mg/dl)?",
        "creatinine": r"(?i)\bcreatinine\b\s*[:=-]?\s*(\d+(?:\.\d+)?)\s*(mg/dl)?",
        "urea": r"(?i)\b(?:urea|blood\s*urea)\b\s*[:=-]?\s*(\d+(?:\.\d+)?)\s*(mg/dl)?",
        "platelets": r"(?i)\bplatelets?\b\s*[:=-]?\s*(\d+(?:\.\d+)?)",
    }

    extracted = {}
    for key, pattern in patterns.items():
        match = re.search(pattern, text)
        if match:
            extracted[key] = {
                "value": match.group(1),
                "unit": (match.group(2) if len(match.groups()) > 1 else None) or None,
            }
    return extracted


def _to_emr_fhir_like(parsed_fields):
    """Create a compact FHIR-like observation list for EMR integration."""
    observations = []
    for name, payload in parsed_fields.items():
        observations.append({
            "resourceType": "Observation",
            "status": "final",
            "code": {"text": name},
            "valueQuantity": {
                "value": float(payload["value"]),
                "unit": payload.get("unit"),
            },
        })

    return {
        "resourceType": "Bundle",
        "type": "collection",
        "entry": observations,
    }


@ocr_bp.route("/extract", methods=["POST"])
def extract_ocr_text():
    """
    Accept an uploaded medical image, preprocess with PIL,
    extract text using Tesseract, and return JSON.
    """
    try:
        if "file" not in request.files:
            return jsonify({"success": False, "error": "No file uploaded. Use form-data key 'file'."}), 400

        file = request.files["file"]
        if not file or not file.filename:
            return jsonify({"success": False, "error": "Invalid file."}), 400

        image_bytes = file.read()
        image = Image.open(io.BytesIO(image_bytes)).convert("RGB")
        processed = _preprocess_image(image)

        data = pytesseract.image_to_data(
            processed,
            output_type=pytesseract.Output.DICT,
            config="--oem 3 --psm 6",
        )

        lines = []
        for text in data.get("text", []):
            clean = (text or "").strip()
            if clean:
                lines.append(clean)
        extracted_text = " ".join(lines).strip()

        confidence = _safe_confidence(data.get("conf", []))
        parsed_fields = _extract_medical_key_values(extracted_text)
        fhir_payload = _to_emr_fhir_like(parsed_fields)

        return jsonify({
            "success": True,
            "filename": file.filename,
            "extracted_text": extracted_text,
            "confidence_score": confidence,
            "medical_fields": parsed_fields,
            "emr_fhir": fhir_payload,
        })

    except pytesseract.TesseractNotFoundError:
        return jsonify({
            "success": False,
            "error": "Tesseract binary not found. Install with: brew install tesseract",
        }), 500
    except Exception as exc:
        return jsonify({"success": False, "error": str(exc)}), 500
