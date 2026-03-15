"""
utils/drug_safety.py
----------------------------------------------------------
Drug Interaction, Allergy Cross-Check & Contraindication Engine
----------------------------------------------------------
Uses OpenFDA API for drug interaction lookups, plus a built-in
knowledge base for common allergy-drug cross-reactivity,
duplicate therapy detection, and diagnosis-based contraindications.
----------------------------------------------------------
"""

import re
import requests
from typing import List, Dict, Optional
from urllib.parse import quote

# ─────────────────────────────────────────────
# ALLERGY - DRUG CROSS-REACTIVITY MAP
# ─────────────────────────────────────────────
# Maps known allergies to drugs that should be avoided.
ALLERGY_DRUG_MAP = {
    "penicillin": [
        "amoxicillin", "ampicillin", "flucloxacillin", "piperacillin",
        "amoxiclav", "augmentin", "co-amoxiclav", "penicillin v",
        "penicillin g", "benzylpenicillin", "phenoxymethylpenicillin",
    ],
    "sulfa": [
        "sulfamethoxazole", "trimethoprim-sulfamethoxazole", "co-trimoxazole",
        "bactrim", "septra", "sulfasalazine", "sulfadiazine", "dapsone",
    ],
    "aspirin": [
        "aspirin", "ibuprofen", "naproxen", "diclofenac", "piroxicam",
        "indomethacin", "ketorolac", "mefenamic acid", "celecoxib",
    ],
    "nsaid": [
        "ibuprofen", "naproxen", "diclofenac", "piroxicam", "aspirin",
        "indomethacin", "ketorolac", "mefenamic acid", "celecoxib",
    ],
    "cephalosporin": [
        "ceftriaxone", "cefuroxime", "cefixime", "cephalexin", "cefazolin",
        "ceftazidime", "cefotaxime", "cefepime", "cefpodoxime",
    ],
    "morphine": [
        "morphine", "codeine", "tramadol", "oxycodone", "hydrocodone",
        "fentanyl", "methadone",
    ],
    "codeine": [
        "codeine", "morphine", "tramadol", "oxycodone", "hydrocodone",
        "dihydrocodeine",
    ],
    "egg": ["influenza vaccine", "yellow fever vaccine"],
    "latex": ["certain surgical products"],
    "iodine": ["iodinated contrast", "povidone-iodine", "amiodarone"],
    "ace inhibitor": [
        "enalapril", "lisinopril", "ramipril", "captopril", "perindopril",
        "trandolapril", "benazepril", "fosinopril", "quinapril",
    ],
    "statin": [
        "atorvastatin", "rosuvastatin", "simvastatin", "pravastatin",
        "fluvastatin", "lovastatin", "pitavastatin",
    ],
}

# ─────────────────────────────────────────────
# COMMON DRUG-DRUG INTERACTIONS (BUILT-IN)
# ─────────────────────────────────────────────
# High-risk pairs. Each entry: (drug_a, drug_b, severity, description)
KNOWN_INTERACTIONS = [
    ("warfarin", "aspirin", "high", "Increased bleeding risk — combined anticoagulant + antiplatelet effect"),
    ("warfarin", "ibuprofen", "high", "NSAIDs increase bleeding risk with warfarin"),
    ("warfarin", "naproxen", "high", "NSAIDs increase bleeding risk with warfarin"),
    ("metformin", "contrast dye", "high", "Risk of lactic acidosis — hold metformin 48h around contrast"),
    ("methotrexate", "trimethoprim", "high", "Additive folate antagonism -> severe bone marrow suppression"),
    ("methotrexate", "nsaid", "high", "NSAIDs reduce methotrexate clearance -> toxicity"),
    ("lithium", "ibuprofen", "high", "NSAIDs increase lithium levels -> toxicity"),
    ("lithium", "naproxen", "high", "NSAIDs increase lithium levels -> toxicity"),
    ("simvastatin", "clarithromycin", "high", "CYP3A4 inhibition -> rhabdomyolysis risk"),
    ("simvastatin", "erythromycin", "high", "CYP3A4 inhibition -> rhabdomyolysis risk"),
    ("atorvastatin", "clarithromycin", "moderate", "CYP3A4 inhibition -> increased statin levels"),
    ("clopidogrel", "omeprazole", "moderate", "Omeprazole reduces clopidogrel activation via CYP2C19"),
    ("clopidogrel", "esomeprazole", "moderate", "Esomeprazole reduces clopidogrel activation"),
    ("amlodipine", "simvastatin", "moderate", "Amlodipine increases simvastatin exposure — limit to 20mg"),
    ("digoxin", "amiodarone", "high", "Amiodarone increases digoxin levels -> toxicity"),
    ("digoxin", "verapamil", "high", "Verapamil increases digoxin levels -> toxicity"),
    ("spironolactone", "potassium", "high", "Combined use -> dangerous hyperkalemia"),
    ("ace inhibitor", "spironolactone", "moderate", "Hyperkalemia risk — monitor potassium closely"),
    ("ssri", "tramadol", "high", "Serotonin syndrome risk"),
    ("ssri", "maoi", "high", "Serotonin syndrome — CONTRAINDICATED combination"),
    ("metformin", "alcohol", "moderate", "Increased lactic acidosis risk"),
    ("ciprofloxacin", "theophylline", "high", "Ciprofloxacin inhibits theophylline metabolism -> toxicity"),
    ("ciprofloxacin", "tizanidine", "high", "Dramatically increases tizanidine levels -> hypotension"),
    ("fluoxetine", "tramadol", "high", "Serotonin syndrome & seizure risk"),
    ("carbamazepine", "erythromycin", "high", "Increased carbamazepine -> toxicity"),
    ("sildenafil", "nitrate", "high", "Severe hypotension — CONTRAINDICATED"),
    ("potassium", "enalapril", "moderate", "Hyperkalemia risk — monitor levels"),
    ("potassium", "lisinopril", "moderate", "Hyperkalemia risk — monitor levels"),
    ("potassium", "ramipril", "moderate", "Hyperkalemia risk — monitor levels"),
]

# ─────────────────────────────────────────────
# DRUG CLASS MAPPING
# ─────────────────────────────────────────────
DRUG_CLASSES = {
    "nsaid": ["ibuprofen", "naproxen", "diclofenac", "aspirin", "piroxicam",
              "indomethacin", "ketorolac", "mefenamic acid", "celecoxib"],
    "ace inhibitor": ["enalapril", "lisinopril", "ramipril", "captopril",
                      "perindopril", "trandolapril", "benazepril", "fosinopril"],
    "arb": ["losartan", "valsartan", "telmisartan", "irbesartan", "candesartan",
            "olmesartan", "azilsartan"],
    "statin": ["atorvastatin", "rosuvastatin", "simvastatin", "pravastatin",
               "fluvastatin", "lovastatin"],
    "ssri": ["fluoxetine", "sertraline", "paroxetine", "citalopram",
             "escitalopram", "fluvoxamine"],
    "ppi": ["omeprazole", "esomeprazole", "pantoprazole", "rabeprazole",
            "lansoprazole", "dexlansoprazole"],
    "beta blocker": ["metoprolol", "atenolol", "propranolol", "bisoprolol",
                     "carvedilol", "nebivolol", "labetalol"],
    "calcium channel blocker": ["amlodipine", "nifedipine", "diltiazem",
                                "verapamil", "felodipine"],
    "anticoagulant": ["warfarin", "heparin", "enoxaparin", "rivaroxaban",
                      "apixaban", "dabigatran", "edoxaban"],
    "antiplatelet": ["aspirin", "clopidogrel", "ticagrelor", "prasugrel"],
    "nitrate": ["nitroglycerin", "isosorbide mononitrate", "isosorbide dinitrate"],
    "maoi": ["phenelzine", "tranylcypromine", "isocarboxazid", "selegiline"],
    "opioid": ["morphine", "codeine", "tramadol", "oxycodone", "hydrocodone",
               "fentanyl", "methadone", "buprenorphine"],
    "benzodiazepine": ["diazepam", "lorazepam", "alprazolam", "clonazepam",
                       "midazolam", "temazepam"],
    "sulfonamide": ["sulfamethoxazole", "co-trimoxazole", "sulfasalazine",
                    "sulfadiazine"],
    "fluoroquinolone": ["ciprofloxacin", "levofloxacin", "moxifloxacin",
                        "ofloxacin", "norfloxacin"],
    "macrolide": ["azithromycin", "clarithromycin", "erythromycin"],
    "diuretic": ["furosemide", "hydrochlorothiazide", "spironolactone",
                 "chlorthalidone", "indapamide", "bumetanide", "torsemide"],
    "insulin": ["insulin glargine", "insulin lispro", "insulin aspart",
                "insulin detemir", "insulin regular", "insulin nph"],
    "sulfonylurea": ["glimepiride", "gliclazide", "glipizide", "glyburide",
                     "glibenclamide"],
}

# ─────────────────────────────────────────────
# DIAGNOSIS - CONTRAINDICATION MAP
# ─────────────────────────────────────────────
DIAGNOSIS_CONTRAINDICATIONS = {
    "asthma": ["propranolol", "atenolol", "metoprolol", "nadolol",
               "timolol", "aspirin"],
    "renal failure": ["metformin", "nsaid", "lithium", "spironolactone",
                      "gentamicin", "vancomycin"],
    "chronic kidney disease": ["metformin", "nsaid", "lithium",
                               "spironolactone"],
    "liver failure": ["paracetamol", "acetaminophen", "methotrexate",
                      "statin", "valproate"],
    "hepatic impairment": ["paracetamol", "acetaminophen", "statin",
                           "methotrexate"],
    "peptic ulcer": ["nsaid", "aspirin", "corticosteroid",
                     "prednisolone", "dexamethasone"],
    "gi bleed": ["nsaid", "aspirin", "warfarin", "anticoagulant",
                 "antiplatelet"],
    "heart failure": ["nsaid", "verapamil", "diltiazem", "thiazolidinedione",
                      "pioglitazone", "rosiglitazone"],
    "bradycardia": ["beta blocker", "digoxin", "verapamil", "diltiazem",
                    "amiodarone"],
    "pregnancy": ["warfarin", "methotrexate", "ace inhibitor", "arb",
                  "statin", "isotretinoin", "valproate", "lithium",
                  "tetracycline", "ciprofloxacin"],
    "gout": ["hydrochlorothiazide", "thiazide", "furosemide", "aspirin"],
    "diabetes": [],  # No absolute contraindications, but monitor
    "hypokalemia": ["digoxin", "furosemide", "hydrochlorothiazide"],
    "hyperkalemia": ["spironolactone", "ace inhibitor", "arb",
                     "potassium", "trimethoprim"],
    "myasthenia gravis": ["aminoglycoside", "gentamicin", "fluoroquinolone",
                          "beta blocker", "lithium"],
    "glaucoma": ["atropine", "ipratropium", "tricyclic antidepressant"],
}


def _normalize(name: str) -> str:
    """Lowercase, strip whitespace, remove common suffixes."""
    return re.sub(r"\s+", " ", name.strip().lower())


def _get_drug_classes(drug_name: str) -> List[str]:
    """Return all class names a drug belongs to."""
    drug = _normalize(drug_name)
    classes = []
    for cls, members in DRUG_CLASSES.items():
        if drug in members:
            classes.append(cls)
    return classes


def _match_drug(drug_a: str, drug_b: str) -> bool:
    """Check if two drug identifiers match (including class-level matching)."""
    a, b = _normalize(drug_a), _normalize(drug_b)
    if a == b:
        return True
    # Check if one is a class name the other belongs to
    if a in DRUG_CLASSES and b in DRUG_CLASSES.get(a, []):
        return True
    if b in DRUG_CLASSES and a in DRUG_CLASSES.get(b, []):
        return True
    # Check if they share a class when one side is a class name
    classes_a = _get_drug_classes(a)
    if b in classes_a:
        return True
    classes_b = _get_drug_classes(b)
    if a in classes_b:
        return True
    return False


# ══════════════════════════════════════════════
# PUBLIC API
# ══════════════════════════════════════════════

def check_allergy_conflicts(
    allergies: List[str],
    medications: List[Dict],
) -> List[Dict]:
    """
    Cross-check patient allergies against prescribed medications.

    Parameters
    ----------
    allergies : list of str
        Known patient allergies (e.g. ["Penicillin", "Sulfa"])
    medications : list of dict
        Rx list with at minimum a "Medication" key.

    Returns
    -------
    list of dict
        Each dict has: medication, allergy, severity, message
    """
    alerts = []
    if not allergies or not medications:
        return alerts

    for allergy_raw in allergies:
        allergy = _normalize(allergy_raw)
        if not allergy or allergy in ("none", "nkda", "nil", "no known", "not mentioned", ""):
            continue

        # Direct allergy-drug map lookup
        flagged_drugs = ALLERGY_DRUG_MAP.get(allergy, [])
        # Also check for the allergy string being a drug class
        if allergy in DRUG_CLASSES:
            flagged_drugs = list(set(flagged_drugs + DRUG_CLASSES[allergy]))

        for med in medications:
            med_name = _normalize(med.get("Medication", ""))
            if not med_name:
                continue

            # Direct match: allergy IS the drug name
            if allergy in med_name or med_name in allergy:
                alerts.append({
                    "type": "allergy_conflict",
                    "severity": "critical",
                    "medication": med.get("Medication"),
                    "allergy": allergy_raw,
                    "message": f"CRITICAL: Patient is allergic to {allergy_raw} — "
                               f"{med.get('Medication')} is contraindicated",
                })
                continue

            # Map-based match
            if med_name in flagged_drugs or any(
                med_name in d for d in flagged_drugs
            ):
                alerts.append({
                    "type": "allergy_cross_reactivity",
                    "severity": "high",
                    "medication": med.get("Medication"),
                    "allergy": allergy_raw,
                    "message": f"HIGH RISK: {med.get('Medication')} may cross-react "
                               f"with {allergy_raw} allergy",
                })

    return alerts


def check_drug_interactions(
    medications: List[Dict],
) -> List[Dict]:
    """
    Check for drug-drug interactions among the prescribed medications
    using the built-in knowledge base + OpenFDA fallback.

    Parameters
    ----------
    medications : list of dict
        Each entry must have at least a "Medication" key.

    Returns
    -------
    list of dict
        Each dict has: drug_a, drug_b, severity, message
    """
    alerts = []
    if not medications or len(medications) < 2:
        return alerts

    med_names = [
        _normalize(m.get("Medication", "")) for m in medications if m.get("Medication")
    ]

    checked = set()
    for i, name_a in enumerate(med_names):
        for j, name_b in enumerate(med_names):
            if i >= j:
                continue
            pair_key = tuple(sorted([name_a, name_b]))
            if pair_key in checked:
                continue
            checked.add(pair_key)

            # Check built-in interactions
            for drug_x, drug_y, severity, desc in KNOWN_INTERACTIONS:
                if (_match_drug(name_a, drug_x) and _match_drug(name_b, drug_y)) or \
                   (_match_drug(name_a, drug_y) and _match_drug(name_b, drug_x)):
                    alerts.append({
                        "type": "drug_interaction",
                        "severity": severity,
                        "drug_a": medications[i].get("Medication"),
                        "drug_b": medications[j].get("Medication"),
                        "message": desc,
                    })
                    break

    # OpenFDA fallback for pairs not caught above
    for i, name_a in enumerate(med_names):
        for j, name_b in enumerate(med_names):
            if i >= j:
                continue
            pair_key = tuple(sorted([name_a, name_b]))
            already_flagged = any(
                _normalize(a.get("drug_a", "")) in pair_key and
                _normalize(a.get("drug_b", "")) in pair_key
                for a in alerts if a["type"] == "drug_interaction"
            )
            if already_flagged:
                continue
            fda_alert = _check_openfda_interaction(name_a, name_b)
            if fda_alert:
                fda_alert["drug_a"] = medications[i].get("Medication")
                fda_alert["drug_b"] = medications[j].get("Medication")
                alerts.append(fda_alert)

    return alerts


def check_duplicate_therapy(
    medications: List[Dict],
) -> List[Dict]:
    """
    Detect duplicate therapy — multiple drugs from the same therapeutic class.

    Returns list of alerts with: drugs, drug_class, severity, message
    """
    alerts = []
    if not medications or len(medications) < 2:
        return alerts

    class_members: Dict[str, List[str]] = {}
    for med in medications:
        med_name = _normalize(med.get("Medication", ""))
        if not med_name:
            continue
        for cls in _get_drug_classes(med_name):
            class_members.setdefault(cls, []).append(med.get("Medication"))

    for cls, members in class_members.items():
        if len(members) >= 2:
            alerts.append({
                "type": "duplicate_therapy",
                "severity": "moderate",
                "drug_class": cls,
                "drugs": members,
                "message": f"Duplicate therapy: {', '.join(members)} are "
                           f"both {cls}s — review if both are needed",
            })

    return alerts


def check_diagnosis_contraindications(
    diagnosis: str,
    medications: List[Dict],
) -> List[Dict]:
    """
    Flag medications that are contraindicated for the patient's diagnosis.

    Parameters
    ----------
    diagnosis : str
        The primary diagnosis text.
    medications : list of dict
        Rx list.

    Returns
    -------
    list of dict
    """
    alerts = []
    if not diagnosis or not medications:
        return alerts

    diag_lower = _normalize(diagnosis)

    for condition, contra_drugs in DIAGNOSIS_CONTRAINDICATIONS.items():
        if condition not in diag_lower:
            continue
        for med in medications:
            med_name = _normalize(med.get("Medication", ""))
            if not med_name:
                continue
            for contra in contra_drugs:
                if _match_drug(med_name, contra) or contra in med_name:
                    alerts.append({
                        "type": "contraindication",
                        "severity": "high",
                        "medication": med.get("Medication"),
                        "condition": condition,
                        "message": f"{med.get('Medication')} is contraindicated in "
                                   f"{condition} — review prescription",
                    })
                    break

    return alerts


def run_full_safety_check(
    allergies: List[str],
    medications: List[Dict],
    diagnosis: str = "",
) -> Dict:
    """
    Run all drug safety checks and return a consolidated report.

    Returns
    -------
    dict with keys:
        safe (bool), alert_count (int), alerts (list),
        allergy_alerts, interaction_alerts, duplicate_alerts, contraindication_alerts
    """
    allergy_alerts = check_allergy_conflicts(allergies, medications)
    interaction_alerts = check_drug_interactions(medications)
    duplicate_alerts = check_duplicate_therapy(medications)
    contra_alerts = check_diagnosis_contraindications(diagnosis, medications)

    all_alerts = allergy_alerts + interaction_alerts + duplicate_alerts + contra_alerts

    # Determine overall safety
    has_critical = any(a["severity"] == "critical" for a in all_alerts)
    has_high = any(a["severity"] == "high" for a in all_alerts)

    return {
        "safe": len(all_alerts) == 0,
        "alert_count": len(all_alerts),
        "has_critical": has_critical,
        "has_high": has_high,
        "severity_summary": {
            "critical": sum(1 for a in all_alerts if a["severity"] == "critical"),
            "high": sum(1 for a in all_alerts if a["severity"] == "high"),
            "moderate": sum(1 for a in all_alerts if a["severity"] == "moderate"),
        },
        "alerts": all_alerts,
        "allergy_alerts": allergy_alerts,
        "interaction_alerts": interaction_alerts,
        "duplicate_alerts": duplicate_alerts,
        "contraindication_alerts": contra_alerts,
    }


# ─────────────────────────────────────────────
# OPENFDA INTEGRATION
# ─────────────────────────────────────────────
OPENFDA_BASE = "https://api.fda.gov/drug/label.json"


def _check_openfda_interaction(drug_a: str, drug_b: str) -> Optional[Dict]:
    """
    Query the OpenFDA API to see if drug_a's label mentions drug_b
    in the drug_interactions field.
    """
    try:
        url = (
            f"{OPENFDA_BASE}?search=openfda.generic_name:"
            f'"{quote(drug_a)}"'
            f"&limit=1"
        )
        resp = requests.get(url, timeout=5)
        if resp.status_code != 200:
            return None

        data = resp.json()
        results = data.get("results", [])
        if not results:
            return None

        label = results[0]
        interactions_text = " ".join(label.get("drug_interactions", []))

        if drug_b in interactions_text.lower():
            return {
                "type": "drug_interaction",
                "severity": "moderate",
                "source": "OpenFDA",
                "message": f"FDA label for {drug_a} warns about interaction "
                           f"with {drug_b} — review prescribing information",
            }

    except (requests.RequestException, ValueError, KeyError):
        # Non-critical — silently skip if FDA API is unreachable
        pass

    return None
