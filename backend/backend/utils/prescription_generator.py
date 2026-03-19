"""
Auto-Prescription PDF Generator
---------------------------------
Generates printable PDF prescriptions from structured EMR data.
Includes: patient info, doctor info, Rx table, QR verification code.
Uses fpdf2 for PDF generation and qrcode for QR codes.
"""

import io
import json
import hashlib
from datetime import datetime

from fpdf import FPDF
import qrcode


class PrescriptionPDF(FPDF):
    """Custom PDF class for medical prescriptions."""

    def __init__(self, clinic_name="Myora Healthcare", clinic_address="", clinic_phone=""):
        super().__init__()
        self.clinic_name = clinic_name
        self.clinic_address = clinic_address
        self.clinic_phone = clinic_phone

    def header(self):
        self.set_font("Helvetica", "B", 16)
        self.cell(0, 10, self.clinic_name, ln=True, align="C")
        if self.clinic_address:
            self.set_font("Helvetica", "", 9)
            self.cell(0, 5, self.clinic_address, ln=True, align="C")
        if self.clinic_phone:
            self.set_font("Helvetica", "", 9)
            self.cell(0, 5, self.clinic_phone, ln=True, align="C")
        self.set_draw_color(0, 0, 0)
        self.line(10, self.get_y() + 3, 200, self.get_y() + 3)
        self.ln(8)

    def footer(self):
        self.set_y(-25)
        self.set_draw_color(180, 180, 180)
        self.line(10, self.get_y(), 200, self.get_y())
        self.ln(3)
        self.set_font("Helvetica", "I", 7)
        self.cell(0, 4, "This is a computer-generated prescription.", ln=True, align="C")
        self.cell(0, 4, f"Generated on {datetime.now().strftime('%Y-%m-%d %H:%M')} via Myora Healthcare Platform", ln=True, align="C")
        self.cell(0, 4, f"Page {self.page_no()}", ln=True, align="C")


def _generate_qr_bytes(data_str: str) -> bytes:
    """Generate QR code image bytes from string data."""
    qr = qrcode.QRCode(version=1, box_size=4, border=2)
    qr.add_data(data_str)
    qr.make(fit=True)
    img = qr.make_image(fill_color="black", back_color="white")
    buf = io.BytesIO()
    img.save(buf, format="PNG")
    buf.seek(0)
    return buf.read()


def _build_verification_hash(patient_name: str, rx_list: list, timestamp: str) -> str:
    """Build a short verification hash for the prescription."""
    payload = json.dumps({
        "patient": patient_name,
        "rx": rx_list,
        "ts": timestamp,
    }, sort_keys=True)
    return hashlib.sha256(payload.encode()).hexdigest()[:16].upper()


def generate_prescription_pdf(
    patient_name: str,
    patient_age: str = "",
    patient_id: str = "",
    diagnosis: str = "",
    allergies: list = None,
    medications: list = None,
    advice: str = "",
    doctor_name: str = "Attending Physician",
    clinic_name: str = "Myora Healthcare",
    clinic_address: str = "",
    clinic_phone: str = "",
) -> bytes:
    """
    Generate a PDF prescription and return raw bytes.

    Parameters
    ----------
    patient_name : str
    patient_age : str
    patient_id : str
    diagnosis : str
    allergies : list of str
    medications : list of dict  (keys: Medication, Dosage, Frequency, Duration)
    advice : str
    doctor_name : str
    clinic_name : str

    Returns
    -------
    bytes : Raw PDF content
    """
    allergies = allergies or []
    medications = medications or []
    now = datetime.now()
    timestamp_str = now.strftime("%Y-%m-%d %H:%M")

    pdf = PrescriptionPDF(clinic_name=clinic_name, clinic_address=clinic_address, clinic_phone=clinic_phone)
    pdf.add_page()
    pdf.set_auto_page_break(auto=True, margin=30)

    # --- Patient Info Block ---
    pdf.set_font("Helvetica", "B", 11)
    pdf.cell(0, 7, "PRESCRIPTION", ln=True)
    pdf.ln(2)

    pdf.set_font("Helvetica", "", 10)
    pdf.cell(95, 6, f"Patient: {patient_name}", ln=False)
    pdf.cell(95, 6, f"Date: {now.strftime('%d %b %Y')}", ln=True, align="R")

    if patient_age:
        pdf.cell(95, 6, f"Age: {patient_age}", ln=False)
    else:
        pdf.cell(95, 6, "", ln=False)
    pdf.cell(95, 6, f"ID: {patient_id or 'N/A'}", ln=True, align="R")

    pdf.ln(2)

    # --- Diagnosis ---
    if diagnosis:
        pdf.set_font("Helvetica", "B", 10)
        pdf.cell(25, 6, "Diagnosis: ", ln=False)
        pdf.set_font("Helvetica", "", 10)
        pdf.multi_cell(0, 6, diagnosis)
        pdf.ln(1)

    # --- Allergies ---
    if allergies:
        pdf.set_font("Helvetica", "B", 10)
        pdf.cell(25, 6, "Allergies: ", ln=False)
        pdf.set_font("Helvetica", "", 10)
        allergy_text = ", ".join(allergies) if isinstance(allergies, list) else str(allergies)
        pdf.cell(0, 6, allergy_text, ln=True)
        pdf.ln(1)

    # --- Rx Header ---
    pdf.ln(3)
    pdf.set_font("Helvetica", "B", 12)
    pdf.cell(0, 8, "Rx", ln=True)
    pdf.ln(1)

    if medications:
        # Table header
        pdf.set_font("Helvetica", "B", 9)
        pdf.set_fill_color(230, 230, 230)
        col_widths = [10, 60, 30, 40, 40]
        headers = ["#", "Medication", "Dosage", "Frequency", "Duration"]
        for i, h in enumerate(headers):
            pdf.cell(col_widths[i], 7, h, border=1, fill=True, align="C")
        pdf.ln()

        # Table rows
        pdf.set_font("Helvetica", "", 9)
        for idx, med in enumerate(medications, 1):
            med_name = med.get("Medication", med.get("medication", ""))
            dosage = med.get("Dosage", med.get("dosage", ""))
            freq = med.get("Frequency", med.get("frequency", ""))
            dur = med.get("Duration", med.get("duration", ""))

            pdf.cell(col_widths[0], 7, str(idx), border=1, align="C")
            pdf.cell(col_widths[1], 7, str(med_name)[:35], border=1)
            pdf.cell(col_widths[2], 7, str(dosage)[:18], border=1, align="C")
            pdf.cell(col_widths[3], 7, str(freq)[:22], border=1, align="C")
            pdf.cell(col_widths[4], 7, str(dur)[:22], border=1, align="C")
            pdf.ln()
    else:
        pdf.set_font("Helvetica", "I", 10)
        pdf.cell(0, 7, "No medications prescribed.", ln=True)

    # --- Advice ---
    if advice:
        pdf.ln(5)
        pdf.set_font("Helvetica", "B", 10)
        pdf.cell(0, 6, "Advice / Follow-Up:", ln=True)
        pdf.set_font("Helvetica", "", 9)
        pdf.multi_cell(0, 5, advice)

    # --- Doctor signature area ---
    pdf.ln(12)
    pdf.set_font("Helvetica", "", 10)
    pdf.cell(0, 6, f"Prescribing Physician: Dr. {doctor_name}", ln=True, align="R")
    pdf.ln(8)
    pdf.line(130, pdf.get_y(), 200, pdf.get_y())
    pdf.ln(1)
    pdf.set_font("Helvetica", "I", 8)
    pdf.cell(0, 5, "Signature / E-Sign", ln=True, align="R")

    # --- QR Verification Code ---
    verification_hash = _build_verification_hash(patient_name, medications, timestamp_str)
    qr_data = json.dumps({
        "type": "myora_prescription",
        "patient": patient_name,
        "hash": verification_hash,
        "date": timestamp_str,
        "rx_count": len(medications),
    })
    qr_bytes = _generate_qr_bytes(qr_data)

    # Write QR to a temp file in memory and embed
    import tempfile, os
    tmp = tempfile.NamedTemporaryFile(suffix=".png", delete=False)
    tmp.write(qr_bytes)
    tmp.close()
    try:
        pdf.ln(5)
        pdf.set_font("Helvetica", "B", 8)
        pdf.cell(0, 5, f"Verification: {verification_hash}", ln=True)
        pdf.image(tmp.name, x=10, y=pdf.get_y(), w=25, h=25)
    finally:
        os.unlink(tmp.name)

    # Output as bytes
    return pdf.output()
