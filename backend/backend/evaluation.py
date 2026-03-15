import os
import json
import re
import statistics
import numpy as np
from scipy.spatial import distance
from google import genai
from google.genai import types

# --- Configure your API key & client ---

client = genai.Client(api_key="AIzaSyC1PZzDeBSobLJYrNFwaI997SuFS5L-dZ8")

MODEL_ID = "gemini-2.0-flash-exp"
EMBED_MODEL_ID = "text-embedding-004"

# --- Load your test dataset ---
with open("cardio_ground_truth.json", "r") as f:
    test_data = json.load(f)


# --- Helper functions ---
def extract_json_block(text):
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        m = re.search(r"```json\s*([\s\S]*?)```", text, flags=re.IGNORECASE)
        if m:
            candidate = m.group(1)
        else:
            m2 = re.search(r"(\{[\s\S]*\})", text)
            candidate = m2.group(1) if m2 else text
        candidate = candidate.replace("'", '"')
        candidate = re.sub(r",\s*}", "}", candidate)
        candidate = re.sub(r",\s*]", "]", candidate)
        return json.loads(candidate)


def string_similarity(a, b):
    a_tokens = set(re.findall(r"\w+", a.lower())) if a else set()
    b_tokens = set(re.findall(r"\w+", b.lower())) if b else set()
    if not a_tokens and not b_tokens:
        return 1.0
    if not a_tokens or not b_tokens:
        return 0.0
    return len(a_tokens.intersection(b_tokens)) / len(a_tokens.union(b_tokens))


def list_similarity(l1, l2):
    a = set([x.lower() for x in (l1 or [])])
    b = set([x.lower() for x in (l2 or [])])
    if not a and not b:
        return 1.0
    inter = a.intersection(b)
    union = a.union(b)
    return len(inter) / len(union)


def rx_accuracy(rx_true, rx_pred):
    if not rx_true and not rx_pred:
        return 1.0
    total = len(rx_true) * 4
    if total == 0:
        return 1.0
    matches = 0
    for t in rx_true:
        best = None
        for p in rx_pred:
            if p.get("Medication", "").strip().lower() == t.get("Medication", "").strip().lower():
                best = p
                break
        if not best and rx_pred:
            best = rx_pred[0]
        if best:
            for f in ["Medication", "Dosage", "Frequency", "Duration"]:
                if str(t.get(f, "")).strip().lower() == str(best.get(f, "")).strip().lower():
                    matches += 1
    return matches / total


# --- New: Embedding-based similarity ---
def get_embedding(text):
    if not text:
        return np.zeros(768)
    result = client.models.embed_content(
        model=EMBED_MODEL_ID,
        contents=[text]
    )
    return np.array(result.embeddings[0].values)


def cosine_similarity(vec1, vec2):
    if np.all(vec1 == 0) and np.all(vec2 == 0):
        return 1.0
    if np.all(vec1 == 0) or np.all(vec2 == 0):
        return 0.0
    return 1 - distance.cosine(vec1, vec2)


def embedding_similarity(text1, text2):
    emb1 = get_embedding(text1)
    emb2 = get_embedding(text2)
    return cosine_similarity(emb1, emb2)


# --- Metrics accumulation ---
field_accs = []
med_accs = []
str_sim_accs = []
embed_accs = []
overall_accs = []

# --- For each sample ---
for item in test_data:
    speech = item["notes"]
    ground = item["expected"]

    prompt = f"""
    You are a medical documentation assistant. Convert the following doctor dictation into valid JSON with fields:
    Allergy (array), Complaints_Presented (string), Diagnosis (string), Rx (array of objects with Medication, Dosage, Frequency, Duration), History (string), Advice_FollowUp (string).
    If a field is missing, use empty list or empty string.
    Return JSON only.

    Dictation:
    \"\"\"{speech}\"\"\"
    """

    response = client.models.generate_content(
        model=MODEL_ID,
        contents=prompt,
        config=types.GenerateContentConfig(response_mime_type="application/json")
    )

    try:
        predicted = extract_json_block(response.text)
    except Exception as e:
        print(f"ERROR parsing JSON for sample id {item.get('id')}:", e)
        predicted = {}

    # Evaluate fields
    fa_scores = []
    # Allergy
    fa_scores.append(list_similarity(ground.get("Allergy", []), predicted.get("Allergy", [])))
    # Complaints
    fa_scores.append(string_similarity(ground.get("Complaints_Presented", ""), predicted.get("Complaints_Presented", "")))
    # Diagnosis
    fa_scores.append(string_similarity(ground.get("Diagnosis", ""), predicted.get("Diagnosis", "")))
    # History
    fa_scores.append(string_similarity(ground.get("History", ""), predicted.get("History", "")))
    # Advice
    fa_scores.append(string_similarity(ground.get("Advice_FollowUp", ""), predicted.get("Advice_FollowUp", "")))

    # Rx
    med_acc = rx_accuracy(ground.get("Rx", []), predicted.get("Rx", []))
    med_accs.append(med_acc * 100)

    # String similarity average
    text_fields = ["Complaints_Presented", "Diagnosis", "History", "Advice_FollowUp"]
    sim_scores = [string_similarity(ground.get(f, ""), predicted.get(f, "")) for f in text_fields]

    # Embedding similarity average
    embed_scores = [embedding_similarity(ground.get(f, ""), predicted.get(f, "")) for f in text_fields]
    embed_accs.append((sum(embed_scores) / len(embed_scores)) * 100)

    # Field accuracy (non-Rx)
    field_acc = (sum(fa_scores) / len(fa_scores))
    field_accs.append(field_acc * 100)

    # String sim
    str_sim_accs.append((sum(sim_scores) / len(sim_scores)) * 100)

    # Overall = combination of field accuracy, med accuracy, and embedding sim
    overall = (field_acc + med_acc + (sum(embed_scores) / len(embed_scores))) / 3
    overall_accs.append(overall * 100)

    print(f"Sample {item.get('id')} -> FieldAcc {field_acc*100:.2f}% | MedAcc {med_acc*100:.2f}% | StrSim {(sum(sim_scores)/len(sim_scores))*100:.2f}% | EmbedSim {(sum(embed_scores)/len(embed_scores))*100:.2f}% | Overall {overall*100:.2f}%")

# --- Print averages ---
print("\n=== AVERAGE SCORES ===")
print(f"Avg Field Accuracy        : {statistics.mean(field_accs):.2f}%")
print(f"Avg Medication Accuracy   : {statistics.mean(med_accs):.2f}%")
print(f"Avg String Similarity     : {statistics.mean(str_sim_accs):.2f}%")
print(f"Avg Embedding Similarity  : {statistics.mean(embed_accs):.2f}%")
print(f"Avg Overall Accuracy      : {statistics.mean(overall_accs):.2f}%")
