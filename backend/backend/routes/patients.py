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

patients_bp = Blueprint("patients", __name__)

@patients_bp.route("/", methods=["GET", "POST", "DELETE", "PUT"])
def handle_patients():
    if request.method == "POST":
        return jsonify(add_patient(request.json))

    elif request.method == "GET":
        return jsonify(get_all_patients())

    elif request.method == "DELETE":
        identifier = request.args.get("name")
        return jsonify(delete_patient(identifier))

    elif request.method == "PUT":
        identifier = request.args.get("name")
        return jsonify(edit_patient(identifier, request.json))
