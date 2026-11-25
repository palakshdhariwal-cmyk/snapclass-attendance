"""Pure face logic: detection, human-face validation, matching, liveness.

This file deliberately has NO streamlit / database imports so that it can be
used (and tested) on its own, for example by evaluation/evaluate.py.
dlib is imported lazily, only when a model is really needed.
"""
from functools import lru_cache

import numpy as np
from PIL import Image, ImageDraw, ImageFont, ImageOps

from src import settings


# --------------------------------------------------------------------------
# Models
# --------------------------------------------------------------------------
@lru_cache(maxsize=1)
def load_models():
    import dlib
    import face_recognition_models

    detector = dlib.get_frontal_face_detector()
    sp = dlib.shape_predictor(face_recognition_models.pose_predictor_model_location())      # 68 landmarks
    facerec = dlib.face_recognition_model_v1(face_recognition_models.face_recognition_model_location())
    return detector, sp, facerec


# --------------------------------------------------------------------------
# Image helpers
# --------------------------------------------------------------------------
def to_rgb_array(image):
    """PIL image / numpy array (gray, RGB, RGBA) -> contiguous uint8 RGB array."""
    if isinstance(image, Image.Image):
        image = ImageOps.exif_transpose(image).convert("RGB")
        return np.ascontiguousarray(np.array(image, dtype=np.uint8))

    arr = np.asarray(image)
    if arr.ndim == 2:
        arr = np.stack([arr] * 3, axis=-1)
    arr = arr[:, :, :3]
    if arr.dtype != np.uint8:
        arr = arr.astype(np.uint8)
    return np.ascontiguousarray(arr)


def shrink(img, max_side):
    h, w = img.shape[:2]
    longest = max(h, w)
    if longest <= max_side:
        return img
    scale = max_side / longest
    resized = Image.fromarray(img).resize((int(w * scale), int(h * scale)), Image.LANCZOS)
    return np.ascontiguousarray(np.array(resized, dtype=np.uint8))


# --------------------------------------------------------------------------
# Geometry checks (pure maths, easy to unit-test)
# --------------------------------------------------------------------------
def eye_aspect_ratio(eye):
    """EAR from the 6 landmarks of one eye. Open eye ~0.25-0.35, closed ~0.10-0.18."""
    eye = np.asarray(eye, dtype=float)
    vertical_1 = np.linalg.norm(eye[1] - eye[5])
    vertical_2 = np.linalg.norm(eye[2] - eye[4])
    horizontal = np.linalg.norm(eye[0] - eye[3])
    if horizontal == 0:
        return 0.0
    return float((vertical_1 + vertical_2) / (2.0 * horizontal))


def landmarks_look_human(pts):
    """Sanity-check the 68 landmarks. Animals / objects that fool the detector
    usually produce landmarks that are not arranged like a human face."""
    pts = np.asarray(pts, dtype=float)
    if pts.shape[0] < 68:
        return False

    eyes_y = pts[36:48, 1].mean()
    nose_y = pts[30, 1]
    mouth_y = pts[48:68, 1].mean()
    chin_y = pts[8, 1]
    if not (eyes_y < nose_y < mouth_y < chin_y):       # eyes above nose above mouth above chin
        return False

    jaw_width = np.linalg.norm(pts[0] - pts[16])
    eye_width = np.linalg.norm(pts[36] - pts[45])
    if jaw_width <= 0 or eye_width <= 0:
        return False
    if not (0.45 <= eye_width / jaw_width <= 1.0):     # eyes sit at a human-like spacing
        return False

    eye_tilt = abs(pts[36, 1] - pts[45, 1]) / eye_width
    return bool(eye_tilt < 0.6)                         # eyes roughly level


# --------------------------------------------------------------------------
# Detection
# --------------------------------------------------------------------------
def detect_faces(image, compute_embeddings=True):
    """Return (rgb_image_used, faces). Each face is a dict with
    box, score, ear and embedding (128-d numpy array)."""
    img = shrink(to_rgb_array(image), settings.MAX_DETECT_SIDE)
    detector, sp, facerec = load_models()

    rects, scores, _ = detector.run(img, 1, 0.0)

    faces = []
    for rect, score in zip(rects, scores):
        if score < settings.MIN_FACE_SCORE:
            continue
        if rect.width() < settings.MIN_FACE_SIZE or rect.height() < settings.MIN_FACE_SIZE:
            continue

        shape = sp(img, rect)
        pts = np.array([[p.x, p.y] for p in shape.parts()])

        if settings.CHECK_HUMAN_LANDMARKS and not landmarks_look_human(pts):
            continue

        ear = (eye_aspect_ratio(pts[36:42]) + eye_aspect_ratio(pts[42:48])) / 2.0
        embedding = None
        if compute_embeddings:
            embedding = np.array(facerec.compute_face_descriptor(img, shape, 1))

        faces.append({
            "box": (rect.left(), rect.top(), rect.right(), rect.bottom()),
            "score": float(score),
            "ear": float(ear),
            "embedding": embedding,
        })
    return img, faces


# --------------------------------------------------------------------------
# Matching
# --------------------------------------------------------------------------
def match_embedding(embedding, ids, gallery):
    """Nearest neighbour search. Returns (student_id, distance) or (None, None)."""
    if gallery is None or len(gallery) == 0:
        return None, None
    distances = np.linalg.norm(np.asarray(gallery) - np.asarray(embedding), axis=1)
    best = int(np.argmin(distances))
    return int(ids[best]), float(distances[best])


def classify_distance(distance):
    """'match' (sure), 'review' (teacher should double-check) or 'unknown'."""
    if distance is None or distance > settings.MATCH_THRESHOLD:
        return "unknown"
    if distance > settings.REVIEW_THRESHOLD:
        return "review"
    return "match"


def distance_to_confidence(distance):
    """Friendly 0-100 number. distance 0 -> 100 %, threshold -> 50 %."""
    if distance is None:
        return 0.0
    value = 100.0 - (distance / settings.MATCH_THRESHOLD) * 50.0
    return round(float(max(0.0, min(100.0, value))), 1)


# --------------------------------------------------------------------------
# Liveness
# --------------------------------------------------------------------------
def check_liveness(open_face, closed_face):
    """Photo 1 = eyes open, photo 2 = eyes closed, same person.
    A printed photo or a phone screenshot cannot close its eyes on request."""
    if open_face["ear"] < settings.MIN_OPEN_EAR:
        return False, "Keep your eyes wide open in the first photo."

    if closed_face["ear"] > open_face["ear"] * settings.CLOSED_EAR_RATIO:
        return False, "Eyes did not close in the second photo. Close them fully and retake."

    gap = float(np.linalg.norm(np.asarray(open_face["embedding"]) - np.asarray(closed_face["embedding"])))
    if gap > settings.LIVENESS_SAME_PERSON_DISTANCE:
        return False, "The two photos do not show the same person."

    return True, "Liveness verified."


# --------------------------------------------------------------------------
# Drawing
# --------------------------------------------------------------------------
STATUS_COLORS = {"match": (34, 197, 94), "review": (245, 158, 11), "unknown": (239, 68, 68)}


def draw_annotations(img, labelled_faces):
    """labelled_faces: list of {box, label, status}. Returns a PIL image."""
    canvas = Image.fromarray(img).convert("RGB")
    draw = ImageDraw.Draw(canvas)
    width = max(2, int(max(canvas.size) / 400))
    size = max(14, int(max(canvas.size) / 45))
    try:
        font = ImageFont.load_default(size=size)
    except TypeError:                                   # very old Pillow
        font = ImageFont.load_default()

    for face in labelled_faces:
        left, top, right, bottom = face["box"]
        color = STATUS_COLORS.get(face.get("status"), (99, 102, 241))
        draw.rectangle([left, top, right, bottom], outline=color, width=width)

        text = face.get("label", "")
        if text:
            text_box = draw.textbbox((0, 0), text, font=font)
            tw, th = text_box[2] - text_box[0], text_box[3] - text_box[1]
            y0 = max(0, top - th - 10)
            draw.rectangle([left, y0, left + tw + 12, y0 + th + 10], fill=color)
            draw.text((left + 6, y0 + 3), text, fill=(255, 255, 255), font=font)
    return canvas
