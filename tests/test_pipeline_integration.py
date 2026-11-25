"""Pipeline integration test with streamlit, the database and dlib replaced by stubs.
Run:  python tests/test_pipeline_integration.py"""
import os
import sys
import types

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import numpy as np

# ---- stub streamlit (only what face_pipeline needs)
st = types.ModuleType("streamlit")


def cache_resource(*a, **k):
    def deco(fn):
        store = {}

        def wrapper(*args):
            if "v" not in store:
                store["v"] = fn(*args)
            return store["v"]
        wrapper.clear = lambda: store.clear()
        return wrapper
    return deco(a[0]) if a and callable(a[0]) else deco


st.cache_resource = cache_resource
sys.modules["streamlit"] = st

# ---- stub database
rng = np.random.RandomState(1)
EMB = {1: rng.rand(128), 2: rng.rand(128)}
db = types.ModuleType("src.database.db")
db.get_all_students = lambda: [{"student_id": 1, "face_embedding": EMB[1].tolist()},
                               {"student_id": 2, "face_embedding": EMB[2].tolist()},
                               {"student_id": 3, "face_embedding": None}]
sys.modules["src.database"] = types.ModuleType("src.database")
sys.modules["src.database.db"] = db

from src.pipelines import face_engine as fe      # noqa: E402
from src.pipelines import face_pipeline as fp    # noqa: E402

BLANK = np.zeros((10, 10, 3), dtype=np.uint8)


def face(box, emb, ear=0.3):
    return {"box": box, "score": 1.5, "ear": ear, "embedding": emb}


def set_faces(faces):
    fe.detect_faces = lambda image, compute_embeddings=True: (np.zeros((200, 300, 3), dtype=np.uint8), faces)


def test_class_photo():
    stranger = np.random.RandomState(9).rand(128) * 3
    noisy2 = EMB[2] + np.full(128, 0.045)            # distance ~0.51 -> "review" band
    set_faces([face((10, 10, 60, 60), EMB[1]), face((100, 10, 150, 60), noisy2), face((200, 10, 250, 60), stranger)])
    res = fp.analyze_image(BLANK)
    assert res["num_faces"] == 3
    assert res["matches"][1]["status"] == "match" and res["matches"][1]["confidence"] == 100.0
    assert res["matches"][2]["status"] == "review"
    assert [f["student_id"] for f in res["faces"]] == [1, 2, None]      # stranger stays unknown

    detected, all_ids, n = fp.predict_attendance(BLANK)
    assert detected == {1: True, 2: True} and all_ids == [1, 2] and n == 3
    assert fp.annotate(res, {1: "Asha", 2: "Ravi"}).size == (300, 200)


def test_animal_photo_gives_no_face():
    set_faces([])
    res = fp.analyze_image(BLANK)
    assert res["num_faces"] == 0 and res["matches"] == {}
    detected, _, n = fp.predict_attendance(BLANK)
    assert detected == {} and n == 0


def test_best_distance_kept():
    set_faces([face((0, 0, 50, 50), EMB[1] + 0.03), face((60, 0, 110, 50), EMB[1])])
    res = fp.analyze_image(BLANK)
    assert res["matches"][1]["distance"] < 1e-9


def test_gallery_refresh_after_registration():
    fp.get_all_students = lambda: [{"student_id": 5, "face_embedding": EMB[1].tolist()}]
    assert fp.train_classifier() is True
    assert fp.get_trained_model()["ids"] == [5]
    fp.get_all_students = lambda: []
    assert fp.train_classifier() is False                                # nobody enrolled


if __name__ == "__main__":
    tests = [v for k, v in sorted(globals().items()) if k.startswith("test_")]
    for t in tests:
        t()
        print("PASS", t.__name__)
    print(f"\nAll {len(tests)} integration tests passed.")
