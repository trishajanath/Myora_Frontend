# from flask import Blueprint, jsonify, request
# from utils.patient_utils import add_patient, get_all_patients, delete_patient, edit_patient

# patients_bp = Blueprint("patients", __name__)

# @patients_bp.route("/", methods=["GET", "POST", "DELETE", "PUT"])
# def handle_patients():
#     if request.method == "POST":
#         data = request.json
#         response = add_patient(data)
#         return jsonify(response)

#     elif request.method == "GET":
#         response = get_all_patients()
#         return jsonify(response)

#     elif request.method == "DELETE":
#         identifier = request.args.get("name")
#         response = delete_patient(identifier)
#         return jsonify(response)

#     elif request.method == "PUT":
#         identifier = request.args.get("name")
#         new_data = request.json
#         response = edit_patient(identifier, new_data)
#         return jsonify(response)


from flask import Blueprint, jsonify, request
from utils.patient_utils import add_patient, get_all_patients, delete_patient, edit_patient
from audit import log_audit, AuditAction

patients_bp = Blueprint("patients", __name__)

@patients_bp.route("/", methods=["GET", "POST", "DELETE", "PUT"])
def handle_patients():
    if request.method == "POST":
        result = add_patient(request.json)
        log_audit(
            AuditAction.PATIENT_CREATE,
            patient_id=request.json.get("name"),
            details={"fields": list(request.json.keys())},
        )
        return jsonify(result)

    elif request.method == "GET":
        result = get_all_patients()
        log_audit(AuditAction.PATIENT_VIEW_ALL)
        return jsonify(result)

    elif request.method == "DELETE":
        identifier = request.args.get("name")
        result = delete_patient(identifier)
        log_audit(AuditAction.PATIENT_DELETE, patient_id=identifier)
        return jsonify(result)

    elif request.method == "PUT":
        identifier = request.args.get("name")
        result = edit_patient(identifier, request.json)
        log_audit(
            AuditAction.PATIENT_UPDATE,
            patient_id=identifier,
            details={"fields_changed": list(request.json.keys())},
        )
        return jsonify(result)
