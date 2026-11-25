"""Measure how accurate SnapClass really is, and produce numbers for your report.

Folder layout (put your own photos in it):

    dataset/
      enroll/<person>/*.jpg      one or more clear photos of each registered person
      genuine/<person>/*.jpg     NEW photos of the same people (different light / angle)
      impostor/*.jpg             faces of people who are NOT registered
      nonface/*.jpg              animals, objects, scenery (must be rejected)

Run:
    python evaluation/evaluate.py --data dataset

Outputs (in evaluation/results/):
    threshold_sweep.csv, threshold_sweep.png, summary.txt
"""
import argparse
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import numpy as np

IMG_EXT = (".jpg", ".jpeg", ".png")


def list_images(folder):
    if not os.path.isdir(folder):
        return []
    return sorted(os.path.join(folder, f) for f in os.listdir(folder) if f.lower().endswith(IMG_EXT))


def compute_metrics(gallery_ids, gallery, probes, thresholds):
    """probes: list of (kind, true_id, embedding_or_None); kind = genuine | impostor | nonface.
    embedding None means the detector found no human face.

    Returns one dict per threshold with accuracy, FAR, FRR and non-face rejection rate."""
    rows = []
    for t in thresholds:
        correct = wrong_id = rejected = 0            # genuine outcomes
        false_accept = true_reject = 0               # impostor outcomes
        nonface_rejected = nonface_total = 0
        genuine_total = impostor_total = 0

        for kind, true_id, emb in probes:
            if kind == "nonface":
                nonface_total += 1
                nonface_rejected += emb is None      # no face found = correctly rejected
                continue

            best_id, best_d = (None, None)
            if emb is not None:
                d = np.linalg.norm(gallery - emb, axis=1)
                i = int(np.argmin(d))
                best_id, best_d = gallery_ids[i], float(d[i])
            accepted = best_d is not None and best_d <= t

            if kind == "genuine":
                genuine_total += 1
                if accepted and best_id == true_id:
                    correct += 1
                elif accepted:
                    wrong_id += 1
                else:
                    rejected += 1
            else:
                impostor_total += 1
                if accepted:
                    false_accept += 1
                else:
                    true_reject += 1

        decided = genuine_total + impostor_total
        rows.append({
            "threshold": round(float(t), 3),
            "accuracy_%": round(100 * (correct + true_reject) / decided, 2) if decided else 0.0,
            "FAR_%": round(100 * (false_accept + wrong_id) / decided, 2) if decided else 0.0,
            "FRR_%": round(100 * rejected / genuine_total, 2) if genuine_total else 0.0,
            "nonface_rejected_%": round(100 * nonface_rejected / nonface_total, 2) if nonface_total else float("nan"),
            "genuine": genuine_total, "impostor": impostor_total, "nonface": nonface_total,
        })
    return rows


def embed_folder(paths):
    from PIL import Image
    from src.pipelines import face_engine as fe
    out = []
    for path in paths:
        _, faces = fe.detect_faces(Image.open(path))
        if len(faces) == 1:
            out.append(faces[0]["embedding"])
        elif len(faces) > 1:                         # keep the most confident (largest score) face
            out.append(max(faces, key=lambda f: f["score"])["embedding"])
        else:
            out.append(None)
    return out


def main():
    import pandas as pd
    from src import settings

    parser = argparse.ArgumentParser()
    parser.add_argument("--data", default="dataset")
    parser.add_argument("--out", default=os.path.join(os.path.dirname(__file__), "results"))
    args = parser.parse_args()
    os.makedirs(args.out, exist_ok=True)

    gallery_ids, gallery = [], []
    for person in sorted(os.listdir(os.path.join(args.data, "enroll"))):
        for emb in embed_folder(list_images(os.path.join(args.data, "enroll", person))):
            if emb is not None:
                gallery_ids.append(person)
                gallery.append(emb)
    if not gallery:
        sys.exit("No usable enrollment faces found in dataset/enroll")
    gallery = np.vstack(gallery)

    probes = []
    genuine_dir = os.path.join(args.data, "genuine")
    if os.path.isdir(genuine_dir):
        for person in sorted(os.listdir(genuine_dir)):
            for emb in embed_folder(list_images(os.path.join(genuine_dir, person))):
                probes.append(("genuine", person, emb))
    for emb in embed_folder(list_images(os.path.join(args.data, "impostor"))):
        probes.append(("impostor", None, emb))
    for emb in embed_folder(list_images(os.path.join(args.data, "nonface"))):
        probes.append(("nonface", None, emb))

    thresholds = np.arange(0.30, 0.801, 0.05)
    table = pd.DataFrame(compute_metrics(gallery_ids, gallery, probes, thresholds))
    table.to_csv(os.path.join(args.out, "threshold_sweep.csv"), index=False)

    current = compute_metrics(gallery_ids, gallery, probes, [settings.MATCH_THRESHOLD])[0]
    summary = (f"SnapClass evaluation\n"
               f"Enrolled photos: {len(gallery_ids)} ({len(set(gallery_ids))} people)\n"
               f"Genuine probes: {current['genuine']}  Impostor probes: {current['impostor']}  "
               f"Non-face probes: {current['nonface']}\n"
               f"At threshold {settings.MATCH_THRESHOLD}: accuracy {current['accuracy_%']}%, "
               f"FAR {current['FAR_%']}%, FRR {current['FRR_%']}%, "
               f"non-face rejected {current['nonface_rejected_%']}%\n")
    print(table.to_string(index=False))
    print("\n" + summary)
    open(os.path.join(args.out, "summary.txt"), "w").write(summary)

    try:
        import matplotlib
        matplotlib.use("Agg")
        import matplotlib.pyplot as plt
        fig, ax = plt.subplots(figsize=(7, 4))
        ax.plot(table["threshold"], table["accuracy_%"], marker="o", label="Accuracy")
        ax.plot(table["threshold"], table["FAR_%"], marker="o", label="False accept rate")
        ax.plot(table["threshold"], table["FRR_%"], marker="o", label="False reject rate")
        ax.axvline(settings.MATCH_THRESHOLD, color="gray", linestyle="--", label="Chosen threshold")
        ax.set_xlabel("Distance threshold")
        ax.set_ylabel("Percent")
        ax.set_title("SnapClass: effect of the matching threshold")
        ax.legend()
        ax.grid(alpha=.3)
        fig.tight_layout()
        fig.savefig(os.path.join(args.out, "threshold_sweep.png"), dpi=160)
    except ImportError:
        print("matplotlib not installed - skipped the chart (pip install matplotlib)")


if __name__ == "__main__":
    main()
