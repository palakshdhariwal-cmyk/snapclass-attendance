"""Streamlit + database side of face recognition.
The heavy lifting lives in face_engine.py."""
import numpy as np
import streamlit as st

from src.database.db import get_all_students
from src.pipelines import face_engine as engine
from src.pipelines.face_engine import check_liveness  # noqa: F401  (re-exported for the screens)


def get_face_embeddings(image):
    """List of 128-d embeddings, one per REAL human face (animals are filtered out)."""
    _, faces = engine.detect_faces(image)
    return [f["embedding"] for f in faces]


@st.cache_resource(show_spinner=False)
def get_trained_model():
    """Loads every enrolled embedding once and keeps it in memory."""
    ids, vectors = [], []
    for student in get_all_students() or []:
        embedding = student.get("face_embedding")
        if embedding:
            ids.append(int(student["student_id"]))
            vectors.append(np.array(embedding, dtype=float))

    if not vectors:
        return None
    return {"ids": ids, "X": np.vstack(vectors)}


def train_classifier():
    """Call after a new student registers so the in-memory gallery is refreshed."""
    get_trained_model.clear()
    return get_trained_model() is not None


def analyze_image(image):
    """Full analysis of one photo.

    Returns a dict:
      image      - RGB array that was analysed (possibly shrunk)
      num_faces  - number of REAL human faces found (0 for animals / objects)
      faces      - list of faces, each with box, student_id, distance,
                   confidence, status ('match' | 'review' | 'unknown'), ear, embedding
      matches    - best result per student: {student_id: {distance, confidence, status}}
    """
    img, raw_faces = engine.detect_faces(image)
    model = get_trained_model()

    faces, matches = [], {}
    for face in raw_faces:
        student_id, distance = (None, None)
        if model:
            student_id, distance = engine.match_embedding(face["embedding"], model["ids"], model["X"])

        status = engine.classify_distance(distance)
        if status == "unknown":
            student_id = None

        item = dict(face, student_id=student_id, distance=distance,
                    confidence=engine.distance_to_confidence(distance), status=status)
        faces.append(item)

        if student_id is not None:
            best = matches.get(student_id)
            if best is None or distance < best["distance"]:
                matches[student_id] = {"distance": distance, "confidence": item["confidence"], "status": status}

    return {"image": img, "num_faces": len(faces), "faces": faces, "matches": matches}


def predict_attendance(image):
    """Backward compatible helper -> (detected {id: True}, all enrolled ids, num_faces)."""
    result = analyze_image(image)
    model = get_trained_model()
    all_ids = sorted(set(model["ids"])) if model else []
    return {sid: True for sid in result["matches"]}, all_ids, result["num_faces"]


def annotate(result, names):
    """Draws coloured boxes + names on an analysed photo. names: {student_id: name}."""
    labelled = []
    for face in result["faces"]:
        if face["student_id"] is None:
            label = "Unknown"
        else:
            label = f"{names.get(face['student_id'], face['student_id'])} {face['confidence']:.0f}%"
        labelled.append({"box": face["box"], "label": label, "status": face["status"]})
    return engine.draw_annotations(result["image"], labelled)
