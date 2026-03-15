from db import inpatients
from bson.objectid import ObjectId

# Utility to add a new patient
def add_patient(data):
    try:
        result = inpatients.insert_one(data)
        return {"status": "success", "id": str(result.inserted_id)}
    except Exception as e:
        return {"status": "error", "message": str(e)}


# Utility to fetch all patients
def get_all_patients():
    try:
        patients = list(inpatients.find({}, {"_id": 0}))
        return {"status": "success", "data": patients}
    except Exception as e:
        return {"status": "error", "message": str(e)}


# Utility to delete a patient by name
def delete_patient(identifier):
    try:
        result = inpatients.delete_one({"name": identifier})
        if result.deleted_count == 0:
            return {"status": "error", "message": "No patient found"}
        return {"status": "success", "message": "Patient deleted"}
    except Exception as e:
        return {"status": "error", "message": str(e)}


# Utility to edit patient details
def edit_patient(identifier, new_data):
    """
    identifier: patient name (string)
    new_data: dictionary of fields to update
    """
    try:
        update_data = {"$set": new_data}
        result = inpatients.update_one({"name": identifier}, update_data)

        if result.matched_count == 0:
            return {"status": "error", "message": "Patient not found"}
        if result.modified_count == 0:
            return {"status": "warning", "message": "No changes made"}
        return {"status": "success", "message": "Patient details updated"}
    except Exception as e:
        return {"status": "error", "message": str(e)}


