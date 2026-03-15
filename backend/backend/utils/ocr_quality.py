"""
utils/ocr_quality.py
----------------------------------------------------------
Image quality scoring and adaptive enhancement for OCR.
- Blur detection (Laplacian variance)
- Contrast ratio analysis
- Resolution check
- Brightness analysis
- Adaptive enhancement pipeline based on quality assessment
- Multi-pass OCR with escalating enhancement strategies
- Region-of-interest detection for document layout
----------------------------------------------------------
"""

import io
import math
from typing import Dict, List, Tuple, Optional
from PIL import Image, ImageEnhance, ImageFilter, ImageOps, ImageStat


# ═══════════════════════════════════════════════
# IMAGE QUALITY SCORING
# ═══════════════════════════════════════════════

def _laplacian_variance(img: Image.Image) -> float:
    """
    Compute Laplacian variance as a blur metric.
    Higher value = sharper image. Typical thresholds:
      < 50  -> very blurry
      50-100 -> somewhat blurry
      100-300 -> acceptable
      > 300  -> sharp
    """
    gray = img.convert("L")
    # Apply Laplacian kernel (edge detection)
    laplacian = gray.filter(ImageFilter.Kernel(
        size=(3, 3),
        kernel=[-1, -1, -1, -1, 8, -1, -1, -1, -1],
        scale=1,
        offset=128,
    ))
    stat = ImageStat.Stat(laplacian)
    # Variance of the Laplacian
    variance = stat.var[0]
    return variance


def _contrast_ratio(img: Image.Image) -> float:
    """
    Compute RMS contrast of the image.
    Higher = better contrast for text reading.
    Typical thresholds:
      < 30  -> very low contrast
      30-60 -> low
      60-100 -> acceptable
      > 100  -> good contrast
    """
    gray = img.convert("L")
    stat = ImageStat.Stat(gray)
    return stat.stddev[0]


def _brightness_score(img: Image.Image) -> float:
    """
    Average brightness (0-255). Ideal for documents: 180-230.
    Too dark (<100) or too bright (>240) hurts OCR.
    """
    gray = img.convert("L")
    stat = ImageStat.Stat(gray)
    return stat.mean[0]


def _resolution_score(img: Image.Image) -> Dict:
    """
    Assess resolution adequacy for OCR.
    Minimum for good OCR: ~1500px on the longest side.
    Optimal: 2000-4000px.
    """
    w, h = img.size
    longest = max(w, h)
    total_pixels = w * h

    if longest >= 3000:
        rating = "excellent"
        score = 100
    elif longest >= 2000:
        rating = "good"
        score = 85
    elif longest >= 1500:
        rating = "acceptable"
        score = 65
    elif longest >= 1000:
        rating = "low"
        score = 40
    else:
        rating = "very_low"
        score = 20

    return {
        "width": w,
        "height": h,
        "longest_side": longest,
        "total_pixels": total_pixels,
        "rating": rating,
        "score": score,
    }


def _text_density_score(img: Image.Image) -> float:
    """
    Estimate text density using edge detection.
    Higher density -> more text content -> better for OCR.
    """
    gray = img.convert("L")
    edges = gray.filter(ImageFilter.FIND_EDGES)
    stat = ImageStat.Stat(edges)
    return stat.mean[0]


def score_image_quality(img: Image.Image) -> Dict:
    """
    Compute a comprehensive quality report for an image
    before sending to OCR.

    Returns
    -------
    dict with keys:
        overall_score (0-100), quality_rating, blur, contrast,
        brightness, resolution, text_density, issues, recommendations
    """
    blur = _laplacian_variance(img)
    contrast = _contrast_ratio(img)
    brightness = _brightness_score(img)
    resolution = _resolution_score(img)
    text_density = _text_density_score(img)

    issues = []
    recommendations = []
    scores = []

    # ── Blur assessment ──
    if blur < 50:
        blur_score = 20
        issues.append("Image is very blurry")
        recommendations.append("Use a clearer image or enable camera stabilization")
    elif blur < 100:
        blur_score = 50
        issues.append("Image is somewhat blurry")
        recommendations.append("Try recapturing with better focus")
    elif blur < 300:
        blur_score = 80
    else:
        blur_score = 100
    scores.append(blur_score * 0.30)  # 30% weight

    # ── Contrast assessment ──
    if contrast < 30:
        contrast_score = 20
        issues.append("Very low contrast — text hard to distinguish")
        recommendations.append("Improve lighting and avoid shadows on the document")
    elif contrast < 60:
        contrast_score = 50
        issues.append("Low contrast")
        recommendations.append("Better lighting may improve results")
    elif contrast < 100:
        contrast_score = 80
    else:
        contrast_score = 100
    scores.append(contrast_score * 0.25)  # 25% weight

    # ── Brightness assessment ──
    if brightness < 80:
        brightness_score = 30
        issues.append("Image is too dark")
        recommendations.append("Increase lighting when capturing")
    elif brightness < 140:
        brightness_score = 60
        issues.append("Image is somewhat dark")
    elif brightness <= 230:
        brightness_score = 100
    else:
        brightness_score = 50
        issues.append("Image is overexposed")
        recommendations.append("Reduce lighting to avoid washout")
    scores.append(brightness_score * 0.15)  # 15% weight

    # ── Resolution assessment ──
    scores.append(resolution["score"] * 0.20)  # 20% weight
    if resolution["score"] < 50:
        issues.append(f"Low resolution ({resolution['width']}x{resolution['height']})")
        recommendations.append("Use a higher resolution camera or move closer")

    # ── Text density ──
    if text_density < 5:
        density_score = 30
        issues.append("Very little text content detected")
    elif text_density < 15:
        density_score = 60
    else:
        density_score = 100
    scores.append(density_score * 0.10)  # 10% weight

    overall = sum(scores)

    if overall >= 80:
        quality_rating = "excellent"
    elif overall >= 60:
        quality_rating = "good"
    elif overall >= 40:
        quality_rating = "fair"
    else:
        quality_rating = "poor"

    return {
        "overall_score": round(overall, 1),
        "quality_rating": quality_rating,
        "blur": {
            "variance": round(blur, 2),
            "score": blur_score,
            "label": "sharp" if blur >= 300 else "acceptable" if blur >= 100 else "blurry",
        },
        "contrast": {
            "rms": round(contrast, 2),
            "score": contrast_score,
            "label": "good" if contrast >= 100 else "acceptable" if contrast >= 60 else "low",
        },
        "brightness": {
            "mean": round(brightness, 2),
            "score": brightness_score,
            "label": "good" if 140 <= brightness <= 230 else "dark" if brightness < 140 else "overexposed",
        },
        "resolution": resolution,
        "text_density": {
            "value": round(text_density, 2),
            "score": density_score,
        },
        "issues": issues,
        "recommendations": recommendations,
    }


# ═══════════════════════════════════════════════
# ADAPTIVE ENHANCEMENT STRATEGIES
# ═══════════════════════════════════════════════

def _enhance_for_blur(img: Image.Image) -> Image.Image:
    """Extra sharpening for blurry images."""
    img = img.filter(ImageFilter.SHARPEN)
    img = img.filter(ImageFilter.SHARPEN)
    img = img.filter(ImageFilter.SHARPEN)
    img = ImageEnhance.Sharpness(img).enhance(3.0)
    # Unsharp mask for fine detail recovery
    img = img.filter(ImageFilter.UnsharpMask(radius=2, percent=150, threshold=3))
    return img


def _enhance_for_low_contrast(img: Image.Image) -> Image.Image:
    """Boost contrast for washed-out images."""
    img = ImageOps.autocontrast(img, cutoff=2)
    img = ImageEnhance.Contrast(img).enhance(3.0)
    return img


def _enhance_for_dark(img: Image.Image) -> Image.Image:
    """Brighten dark images while preserving text."""
    img = ImageEnhance.Brightness(img).enhance(1.6)
    img = ImageOps.autocontrast(img, cutoff=1)
    img = ImageEnhance.Contrast(img).enhance(1.8)
    return img


def _enhance_for_overexposed(img: Image.Image) -> Image.Image:
    """Recover detail from bright images."""
    img = ImageEnhance.Brightness(img).enhance(0.7)
    img = ImageEnhance.Contrast(img).enhance(2.0)
    img = ImageOps.autocontrast(img, cutoff=2)
    return img


def _upscale_image(img: Image.Image, target_min: int = 2500) -> Image.Image:
    """Upscale to a minimum resolution for better OCR."""
    w, h = img.size
    if max(w, h) < target_min:
        scale = target_min / max(w, h)
        img = img.resize((int(w * scale), int(h * scale)), Image.LANCZOS)
    return img


def adaptive_enhance(img: Image.Image, quality_report: Dict) -> Image.Image:
    """
    Apply enhancement filters adapted to the specific quality issues detected.
    """
    # Always start with EXIF transpose + upscale
    img = ImageOps.exif_transpose(img)
    img = _upscale_image(img)

    if img.mode != "L":
        img = img.convert("L")

    # Apply targeted enhancements based on detected issues
    blur_score = quality_report["blur"]["score"]
    contrast_score = quality_report["contrast"]["score"]
    brightness_score = quality_report["brightness"]["score"]

    if blur_score < 60:
        img = _enhance_for_blur(img)

    if contrast_score < 60:
        img = _enhance_for_low_contrast(img)
    else:
        # Standard moderate contrast boost
        img = ImageEnhance.Contrast(img).enhance(2.0)

    if brightness_score < 50 and quality_report["brightness"]["mean"] < 140:
        img = _enhance_for_dark(img)
    elif brightness_score < 70 and quality_report["brightness"]["mean"] > 230:
        img = _enhance_for_overexposed(img)

    # Standard cleanup
    img = img.filter(ImageFilter.MedianFilter(size=3))
    img = img.filter(ImageFilter.SHARPEN)
    img = ImageOps.autocontrast(img, cutoff=1)

    return img.convert("RGB")


# ═══════════════════════════════════════════════
# MULTI-PASS ENHANCEMENT STRATEGIES
# ═══════════════════════════════════════════════

def get_enhancement_strategies(quality_report: Dict) -> List[Dict]:
    """
    Return a list of progressively more aggressive enhancement strategies
    based on the quality assessment.

    Each strategy has a name and an enhancement function.
    """
    strategies = []

    # Strategy 1: Adaptive enhancement (always included)
    strategies.append({
        "name": "adaptive",
        "description": "Quality-aware adaptive enhancement",
    })

    # Strategy 2: High-contrast binary for poor quality images
    if quality_report["overall_score"] < 60:
        strategies.append({
            "name": "high_contrast",
            "description": "Aggressive contrast + threshold for difficult images",
        })

    # Strategy 3: Edge-preserving denoise + sharpen for blurry images
    if quality_report["blur"]["score"] < 60:
        strategies.append({
            "name": "deblur_aggressive",
            "description": "Aggressive deblur with edge recovery",
        })

    # Strategy 4: Inverted for very dark images (white text on dark bg)
    if quality_report["brightness"]["mean"] < 80:
        strategies.append({
            "name": "inverted",
            "description": "Inverted colors for dark background documents",
        })

    return strategies


def apply_enhancement_strategy(
    img: Image.Image, strategy_name: str, quality_report: Dict
) -> Image.Image:
    """Apply a specific enhancement strategy to an image."""
    img = ImageOps.exif_transpose(img)
    img = _upscale_image(img)

    if strategy_name == "adaptive":
        return adaptive_enhance(img, quality_report)

    if strategy_name == "high_contrast":
        gray = img.convert("L")
        gray = ImageOps.autocontrast(gray, cutoff=5)
        gray = ImageEnhance.Contrast(gray).enhance(4.0)
        gray = gray.filter(ImageFilter.SHARPEN)
        gray = gray.filter(ImageFilter.UnsharpMask(radius=2, percent=200, threshold=2))
        # Apply threshold for near-binary
        gray = gray.point(lambda x: 0 if x < 128 else 255)
        return gray.convert("RGB")

    if strategy_name == "deblur_aggressive":
        gray = img.convert("L")
        gray = gray.filter(ImageFilter.UnsharpMask(radius=3, percent=250, threshold=2))
        gray = gray.filter(ImageFilter.SHARPEN)
        gray = gray.filter(ImageFilter.SHARPEN)
        gray = gray.filter(ImageFilter.SHARPEN)
        gray = ImageEnhance.Sharpness(gray).enhance(4.0)
        gray = ImageEnhance.Contrast(gray).enhance(2.5)
        gray = ImageOps.autocontrast(gray, cutoff=1)
        return gray.convert("RGB")

    if strategy_name == "inverted":
        gray = img.convert("L")
        gray = ImageOps.invert(gray)
        gray = ImageOps.autocontrast(gray, cutoff=2)
        gray = ImageEnhance.Contrast(gray).enhance(2.5)
        gray = gray.filter(ImageFilter.SHARPEN)
        return gray.convert("RGB")

    # Fallback: standard adaptive
    return adaptive_enhance(img, quality_report)


# ═══════════════════════════════════════════════
# REGION-OF-INTEREST DETECTION
# ═══════════════════════════════════════════════

def detect_document_regions(img: Image.Image) -> List[Dict]:
    """
    Heuristically detect regions of interest in a medical document.
    Uses horizontal/vertical density analysis to find:
    - Header region (top ~15% — usually patient info, hospital, dates)
    - Body region (middle ~60% — clinical notes, findings)
    - Prescription region (bottom ~25% — Rx, dosages, follow-up)

    Returns list of dicts with: region_name, bbox (x1,y1,x2,y2), description
    """
    w, h = img.size
    regions = []

    # Header: top 15%
    header_h = int(h * 0.15)
    regions.append({
        "region_name": "header",
        "bbox": (0, 0, w, header_h),
        "description": "Patient info, hospital, doctor, date",
    })

    # Body: middle 55%
    body_top = header_h
    body_bottom = int(h * 0.70)
    regions.append({
        "region_name": "body",
        "bbox": (0, body_top, w, body_bottom),
        "description": "Clinical notes, diagnosis, findings, history",
    })

    # Prescription/Footer: bottom 30%
    rx_top = body_bottom
    regions.append({
        "region_name": "prescription",
        "bbox": (0, rx_top, w, h),
        "description": "Prescription, medications, follow-up, signatures",
    })

    # Try to find a more precise split by looking at horizontal ink density
    gray = img.convert("L")
    pixels = gray.load()

    # Compute horizontal density (dark pixel ratio per row band)
    band_height = max(1, h // 20)
    density_bands = []
    for band in range(20):
        y_start = band * band_height
        y_end = min(y_start + band_height, h)
        dark_count = 0
        total = 0
        for y in range(y_start, y_end, 2):  # Sample every 2nd row
            for x in range(0, w, 4):  # Sample every 4th column
                total += 1
                if pixels[x, y] < 128:
                    dark_count += 1
        density = dark_count / max(total, 1)
        density_bands.append({"band": band, "density": round(density, 4)})

    # Find empty bands (likely section separators)
    separators = []
    for i, band in enumerate(density_bands):
        if band["density"] < 0.02 and 3 < i < 17:
            separators.append(i)

    if separators:
        regions.append({
            "region_name": "detected_separators",
            "separator_bands": separators,
            "description": "Potential section breaks detected via density analysis",
        })

    return regions
