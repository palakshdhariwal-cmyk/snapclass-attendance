# SnapClass – AI Attendance System

Face + voice based attendance built with **Streamlit, dlib and Supabase**.
A teacher photographs the class (or records audio), the AI marks who is present, the teacher
reviews it, and attendance analytics are available instantly.

## What's new in this version

| Feature | Where |
|---|---|
| **Only real human faces are accepted.** Animals / objects give *“Cannot recognise face”* (detection score, minimum size, and landmark geometry checks) | `src/pipelines/face_engine.py` |
| **Liveness check (anti photo-spoofing).** Login needs an eyes-open photo then an eyes-closed photo (eye-aspect-ratio from 68 landmarks) and both must be the same person | `face_engine.check_liveness`, `student_screen.py` |
| **Teacher can correct the AI** before saving (tick / untick *Present*) | `dialog_attendance_results.py` |
| **Match confidence + “⚠️ Review” flag** for borderline matches | `face_pipeline.analyze_image` |
| **Annotated class photos** – green/amber/red boxes with names | `face_engine.draw_annotations` |
| **Analytics dashboard** – KPIs, per-student bars, trend line, at-risk (<75%) students | `teacher_analytics.py`, `utils/analytics.py` |
| **CSV export** of results, records, student reports and a student's own history | download buttons |
| **Duplicate-session guard** – warns if attendance for the subject was already saved today | `db.attendance_taken_today` |
| **Student dashboard** with overall %, progress bars and low-attendance alert | `student_screen.py` |
| **Security** – password length rule, login lockout after 5 wrong attempts, privacy note | `teacher_screen.py` |
| **Nearest-neighbour matching** (replaces SVM + distance check, works even with 1 student) | `face_pipeline.py` |
| **Accuracy evaluation tool** – accuracy, FAR, FRR, threshold chart | `evaluation/evaluate.py` |
| **New classy UI** – design system, gradient home, stat cards, progress bars | `ui/base_layout.py`, `ui/ui_kit.py` |
| Bug fixes | only the last subject was shown in *Manage Subjects*; duplicate button IDs when unenrolling; RGBA/rotated phone photos; crash when nobody is enrolled; empty audio crash |

## Setup

```bash
python -m venv .venv
.venv\Scripts\activate          # Windows   (Mac/Linux: source .venv/bin/activate)
pip install -r requirements.txt

copy .streamlit\secrets.toml.example .streamlit\secrets.toml     # then add your Supabase URL + key
streamlit run app.py
```

### Database tables (unchanged – no migration needed)

`teachers(teacher_id, username, password, name)` ·
`students(student_id, name, face_embedding, voice_embedding)` ·
`subjects(subject_id, subject_code, name, section, teacher_id)` ·
`subject_students(student_id, subject_id)` ·
`attendance_logs(student_id, subject_id, timestamp, is_present)`

## Tuning (everything is in `src/settings.py`)

| Problem | Change |
|---|---|
| An animal/object is still accepted as a face | raise `MIN_FACE_SCORE` (0.8–1.2) |
| Real faces missed in big group photos | lower `MIN_FACE_SCORE`, `MIN_FACE_SIZE` |
| Wrong person recognised | lower `MATCH_THRESHOLD` (0.55 / 0.5) |
| Genuine students rejected | raise `MATCH_THRESHOLD` (max ~0.65) |
| Liveness too strict / too easy | `MIN_OPEN_EAR`, `CLOSED_EAR_RATIO` |
| Turn liveness off for a quick demo | `LIVENESS_REQUIRED = False` |

## Measure your accuracy (great for the report)

```
dataset/
  enroll/<person>/*.jpg     clear photos of each registered person
  genuine/<person>/*.jpg    new photos of the same people (different light / angle)
  impostor/*.jpg            people who are NOT registered
  nonface/*.jpg             animals, objects, scenery
```
```bash
python evaluation/evaluate.py --data dataset
```
Creates `evaluation/results/threshold_sweep.csv`, `threshold_sweep.png`, `summary.txt`
(accuracy, false-accept rate, false-reject rate, % of non-face images rejected).

## Tests

```bash
python tests/test_logic.py                 # geometry, liveness, matching, analytics, metrics
python tests/test_pipeline_integration.py  # pipeline with stubbed dlib / database
```

## Project structure

```
app.py                     entry point
src/settings.py            all thresholds and rules
src/pipelines/             face_engine (pure logic) · face_pipeline (DB glue) · voice_pipeline
src/screens/               home · student · teacher · teacher_analytics
src/components/            dialogs, header, footer, subject card
src/ui/                    base_layout (CSS) · ui_kit (stat cards, pills, progress bars)
src/utils/analytics.py     pandas helpers for the dashboard
evaluation/evaluate.py     accuracy / FAR / FRR report
tests/                     unit + integration tests
```

## Honest limitations (mention these in your report)

* Liveness is a **basic** eye-closure challenge. It stops printed photos and static screenshots,
  not a determined attacker with a video of the person.
* dlib's frontal detector works best for faces that look roughly at the camera, in decent light.
* Twins / very similar faces and heavy masks reduce accuracy.
* Only face *signatures* are stored in the database, never the photos.

## Future scope

Email alerts for low attendance · multi-photo enrollment · QR fallback · mobile app ·
deep-learning detector (e.g. RetinaFace) and ArcFace embeddings.
