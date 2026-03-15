"""
HIPAA Audit Logging System
----------------------------------------------------------
Tracks all access to Protected Health Information (PHI):
- Who accessed/modified/deleted records
- What action was performed
- When it happened
- What data was affected
- IP address and user agent of the requester

Logs are stored in MongoDB (audit_logs collection) and are
immutable — no update/delete operations are exposed.
----------------------------------------------------------
"""

from datetime import datetime
from flask import request
from db import db

audit_collection = db["audit_logs"]

# Create TTL index (optional: auto-delete after 7 years per HIPAA retention)
# and indexes for efficient querying
audit_collection.create_index("timestamp")
audit_collection.create_index("action")
audit_collection.create_index("patient_id")
audit_collection.create_index("user")


class AuditAction:
    """Constants for audit action types."""
    # Patient records
    PATIENT_VIEW = "PATIENT_VIEW"
    PATIENT_VIEW_ALL = "PATIENT_VIEW_ALL"
    PATIENT_CREATE = "PATIENT_CREATE"
    PATIENT_UPDATE = "PATIENT_UPDATE"
    PATIENT_DELETE = "PATIENT_DELETE"

    # Voice / EMR
    VOICE_TRANSCRIBE = "VOICE_TRANSCRIBE"
    VOICE_PROCESS = "VOICE_PROCESS"
    EMR_SAVE = "EMR_SAVE"
    EMR_VIEW_HISTORY = "EMR_VIEW_HISTORY"

    # Consultant notes / OCR
    OCR_EXTRACT = "OCR_EXTRACT"
    OCR_SAVE = "OCR_SAVE"
    OCR_VIEW = "OCR_VIEW"


def log_audit(action: str, patient_id: str = None, details: dict = None,
              user: str = "system", success: bool = True):
    """
    Write an immutable audit log entry.

    Parameters
    ----------
    action : str
        One of the AuditAction constants.
    patient_id : str, optional
        The patient identifier affected.
    details : dict, optional
        Extra context (e.g. fields changed, confidence score).
    user : str
        The user/service performing the action.
    success : bool
        Whether the operation succeeded.
    """
    try:
        ip_address = None
        user_agent = None
        try:
            ip_address = request.remote_addr
            user_agent = request.headers.get("User-Agent", "")
        except RuntimeError:
            # Outside request context (e.g. startup)
            pass

        entry = {
            "timestamp": datetime.utcnow(),
            "action": action,
            "patient_id": patient_id,
            "user": user,
            "success": success,
            "ip_address": ip_address,
            "user_agent": user_agent,
            "details": details or {},
        }

        audit_collection.insert_one(entry)
    except Exception as e:
        # Audit logging must never crash the main application
        print(f"⚠️  Audit log write failed: {e}")
