"""Run with:  python tests/test_logic.py   (no streamlit / dlib / database needed)"""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))  # project root

import numpy as np
from PIL import Image

from src.pipelines import face_engine as fe
from src.utils import analytics as an


def human_landmarks(eye_open=True):
    pts = np.full((68, 2), 60.0)
    pts[0], pts[16], pts[8] = (0, 40), (130, 40), (65, 130)
    dy = 4 if eye_open else 1                      # eyelid gap
    right = [(20, 40), (30, 40 - dy), (40, 40 - dy), (50, 40), (40, 40 + dy), (30, 40 + dy)]
    left = [(80, 40), (90, 40 - dy), (100, 40 - dy), (110, 40), (100, 40 + dy), (90, 40 + dy)]
    pts[36:42], pts[42:48] = right, left
    pts[30] = (65, 70)
    pts[48:68] = (65, 100)
    return pts


def test_ear():
    open_ear = fe.eye_aspect_ratio(human_landmarks(True)[36:42])
    closed_ear = fe.eye_aspect_ratio(human_landmarks(False)[36:42])
    assert 0.25 < open_ear < 0.35, open_ear
    assert closed_ear < open_ear * 0.5, (open_ear, closed_ear)


def test_human_landmarks():
    good = human_landmarks()
    assert fe.landmarks_look_human(good)
    flipped = good.copy()
    flipped[:, 1] = 130 - flipped[:, 1]            # upside-down "face"
    assert not fe.landmarks_look_human(flipped)
    squashed = good.copy()
    squashed[36:48, 0] = 65 + (squashed[36:48, 0] - 65) * 0.2   # eyes crammed together
    assert not fe.landmarks_look_human(squashed)
    assert not fe.landmarks_look_human(np.zeros((10, 2)))


def test_liveness():
    emb = np.random.RandomState(0).rand(128)
    open_f = {"ear": 0.30, "embedding": emb}
    assert fe.check_liveness(open_f, {"ear": 0.12, "embedding": emb + 0.01})[0]
    assert not fe.check_liveness(open_f, {"ear": 0.29, "embedding": emb})[0]            # eyes never closed (photo)
    assert not fe.check_liveness({"ear": 0.10, "embedding": emb}, {"ear": 0.05, "embedding": emb})[0]
    assert not fe.check_liveness(open_f, {"ear": 0.12, "embedding": emb + 5})[0]        # different person


def test_matching():
    gallery = np.array([[0.0] * 128, [1.0] * 128])
    ids = [10, 20]
    sid, d = fe.match_embedding(np.full(128, 0.001), ids, gallery)
    assert sid == 10 and d < 0.05
    assert fe.match_embedding(np.zeros(128), [], np.empty((0, 128))) == (None, None)
    assert fe.classify_distance(0.3) == "match"
    assert fe.classify_distance(0.55) == "review"
    assert fe.classify_distance(0.9) == "unknown"
    assert fe.classify_distance(None) == "unknown"
    assert fe.distance_to_confidence(0) == 100.0
    assert fe.distance_to_confidence(0.6) == 50.0
    assert fe.distance_to_confidence(None) == 0.0


def test_images():
    rgba = np.zeros((20, 30, 4), dtype=np.uint8)
    gray = np.zeros((20, 30), dtype=np.uint8)
    assert fe.to_rgb_array(rgba).shape == (20, 30, 3)
    assert fe.to_rgb_array(gray).shape == (20, 30, 3)
    assert fe.to_rgb_array(Image.new("RGBA", (10, 8))).shape == (8, 10, 3)
    big = np.zeros((3000, 2000, 3), dtype=np.uint8)
    assert max(fe.shrink(big, 1600).shape[:2]) == 1600
    out = fe.draw_annotations(np.zeros((300, 400, 3), dtype=np.uint8),
                              [{"box": (50, 50, 150, 150), "label": "Asha 92%", "status": "match"},
                               {"box": (200, 60, 300, 160), "label": "Unknown", "status": "unknown"}])
    assert out.size == (400, 300)


def test_analytics():
    records = []
    for day, present in [("2026-11-24T10:00:00", {1: True, 2: False}),
                         ("2026-11-25T10:00:00", {1: True, 2: False}),
                         ("2026-11-26T10:00:00", {1: False, 2: True})]:
        for sid, p in present.items():
            records.append({"student_id": sid, "subject_id": 7, "timestamp": day, "is_present": p,
                            "subjects": {"name": "Maths", "subject_code": "M1"}})
    df = an.records_to_df(records, {1: "Asha", 2: "Ravi"})
    summary = an.student_summary(df)
    assert dict(zip(summary["Student"], summary["Percent"])) == {"Asha": 66.7, "Ravi": 33.3}
    assert list(an.at_risk(summary)["Student"]) == ["Ravi", "Asha"]
    trend = an.session_trend(df)
    assert list(trend["Percent"]) == [50.0, 50.0, 50.0] and len(trend) == 3
    assert an.overall_percent(df) == 50.0
    empty = an.records_to_df([], {})
    assert an.student_summary(empty).empty and an.session_trend(empty).empty and an.overall_percent(empty) == 0.0
    # timestamps with microseconds / timezone must not crash
    odd = an.records_to_df([{"student_id": 1, "subject_id": 1, "timestamp": "2026-11-26T10:00:00.123456+00:00",
                             "is_present": True, "subjects": {}}], {})
    assert len(odd) == 1


def test_evaluation_metrics():
    sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "evaluation"))
    from evaluate import compute_metrics
    gallery = np.array([[0.0] * 128, [1.0] * 128])
    ids = ["asha", "ravi"]
    probes = [
        ("genuine", "asha", np.full(128, 0.001)),     # close to asha
        ("genuine", "ravi", np.full(128, 0.999)),     # close to ravi
        ("genuine", "ravi", np.full(128, 0.45)),      # far from both -> rejected
        ("impostor", None, np.full(128, 0.5)),        # ~5.6 away -> rejected
        ("impostor", None, np.full(128, 0.0006)),     # looks like asha -> false accept at big thresholds
        ("nonface", None, None),                      # animal, correctly gives no face
        ("nonface", None, np.zeros(128)),             # animal wrongly detected as a face
    ]
    row = compute_metrics(ids, gallery, probes, [0.5])[0]
    assert row["genuine"] == 3 and row["impostor"] == 2 and row["nonface"] == 2
    assert row["nonface_rejected_%"] == 50.0
    assert row["FRR_%"] == 33.33
    assert row["FAR_%"] == 20.0                        # 1 of 5 genuine+impostor probes wrongly accepted
    assert row["accuracy_%"] == 60.0                   # 2 correct + 1 impostor rejected = 3/5


if __name__ == "__main__":
    tests = [v for k, v in sorted(globals().items()) if k.startswith("test_")]
    for t in tests:
        t()
        print("PASS", t.__name__)
    print(f"\nAll {len(tests)} test groups passed.")
