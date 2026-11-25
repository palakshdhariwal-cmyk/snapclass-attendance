import hashlib
import time

import pandas as pd
import streamlit as st
from PIL import Image, ImageOps

from src import settings
from src.components.dialog_enroll import enroll_dialog
from src.components.footer import footer_dashboard
from src.components.header import header_dashboard
from src.components.subject_card import subject_card
from src.database.db import (create_student, get_student, get_student_attendance,
                             get_student_subjects, unenroll_student_to_subject)
from src.pipelines.face_pipeline import analyze_image, check_liveness, train_classifier
from src.pipelines.voice_pipeline import get_voice_embedding
from src.ui.base_layout import style_background_dashboard, style_base_layout
from src.ui.ui_kit import banner, section_title, stat_cards, steps


# ----------------------------------------------------------------------------
# Dashboard (after login)
# ----------------------------------------------------------------------------
def student_dashboard():
    student_data = st.session_state.student_data
    student_id = student_data["student_id"]

    c1, c2 = st.columns(2, vertical_alignment="center", gap="xxlarge")
    with c1:
        header_dashboard()
    with c2:
        st.subheader(f"Welcome, {student_data['name']} 👋")
        if st.button("Logout", type="secondary", key="loginbackbtn", shortcut="control+backspace"):
            st.session_state["is_logged_in"] = False
            del st.session_state.student_data
            st.rerun()

    st.space()

    with st.spinner("Loading your subjects..."):
        subjects = get_student_subjects(student_id)
        logs = get_student_attendance(student_id)

    stats_map = {}
    for log in logs:
        entry = stats_map.setdefault(log["subject_id"], {"total": 0, "attended": 0})
        entry["total"] += 1
        if log.get("is_present"):
            entry["attended"] += 1

    total = sum(v["total"] for v in stats_map.values())
    attended = sum(v["attended"] for v in stats_map.values())
    overall = round(100 * attended / total, 1) if total else 0.0

    low_subjects = []
    for node in subjects:
        sid = node["subjects"]["subject_id"]
        s = stats_map.get(sid)
        if s and s["total"] and 100 * s["attended"] / s["total"] < settings.ATTENDANCE_WARN_PERCENT:
            low_subjects.append(node["subjects"]["name"])

    hint = ("On track" if overall >= settings.ATTENDANCE_WARN_PERCENT else "Below target") if total else "No classes yet"
    hint_color = "#16A34A" if (total and overall >= settings.ATTENDANCE_WARN_PERCENT) else "#DC2626" if total else "#6B7280"
    stat_cards([
        ("📚", len(subjects), "Subjects enrolled"),
        ("🗓️", total, "Classes held"),
        ("✅", attended, "Classes attended"),
        ("📈", f"{overall:.0f}%", "Overall attendance", hint, hint_color),
    ])

    if low_subjects:
        banner(f"⚠️ <b>Attendance alert:</b> you are below {settings.ATTENDANCE_WARN_PERCENT}% in "
               f"<b>{', '.join(low_subjects)}</b>. Try not to miss the next classes.")
    elif total:
        banner("🎉 Great job! Your attendance is above the required level in every subject.", good=True)

    c1, c2 = st.columns(2, vertical_alignment="bottom")
    with c1:
        section_title("Your enrolled subjects", "Tap enroll and enter the code from your teacher")
    with c2:
        if st.button("Enroll in Subject", type="primary", width="stretch", icon=":material/add:"):
            enroll_dialog()

    if not subjects:
        st.info("You are not enrolled in any subject yet. Click **Enroll in Subject** to begin.")

    cols = st.columns(2)
    for i, sub_node in enumerate(subjects):
        sub = sub_node["subjects"]
        sid = sub["subject_id"]
        stats = stats_map.get(sid, {"total": 0, "attended": 0})
        percent = (100 * stats["attended"] / stats["total"]) if stats["total"] else None

        def unenroll_button(sid=sid, name=sub["name"]):
            if st.button("Unenroll from this course", type="tertiary", width="stretch",
                         icon=":material/delete_forever:", key=f"unenroll_{sid}"):
                unenroll_student_to_subject(student_id, sid)
                st.toast(f"Unenrolled from {name}")
                st.rerun()

        with cols[i % 2]:
            subject_card(
                name=sub["name"], code=sub["subject_code"], section=sub["section"],
                stats=[("📅", "Total", stats["total"]), ("✅", "Attended", stats["attended"])],
                footer_callback=unenroll_button, percent=percent,
            )

    if logs:
        with st.expander("🕘 My attendance history"):
            history = pd.DataFrame([{
                "Date": pd.to_datetime(l.get("timestamp"), errors="coerce"),
                "Subject": (l.get("subjects") or {}).get("name", ""),
                "Status": "✅ Present" if l.get("is_present") else "❌ Absent",
            } for l in logs]).sort_values("Date", ascending=False)
            st.dataframe(history, hide_index=True, width="stretch")
            st.download_button("Download my attendance (CSV)", history.to_csv(index=False).encode("utf-8"),
                               file_name="my_attendance.csv", mime="text/csv", icon=":material/download:")

    footer_dashboard()


# ----------------------------------------------------------------------------
# Face login
# ----------------------------------------------------------------------------
def _analyze_upload(file):
    """Analyse a camera photo once and remember the result (Streamlit reruns a lot)."""
    cache = st.session_state.setdefault("_face_cache", {})
    key = hashlib.md5(file.getvalue()).hexdigest()
    if key not in cache:
        image = ImageOps.exif_transpose(Image.open(file)).convert("RGB")
        cache[key] = analyze_image(image)
        while len(cache) > 4:                    # keep only the latest few photos in memory
            cache.pop(next(iter(cache)))
    return cache[key]


def _login_user(student):
    st.session_state.is_logged_in = True
    st.session_state.user_role = "student"
    st.session_state.student_data = student
    st.toast(f"Welcome back {student['name']}!")
    time.sleep(1)
    st.rerun()


def _registration_form(face):
    with st.container(border=True):
        st.header("Register new profile")
        st.caption("Your photo is **not stored**. Only a mathematical face signature is saved.")
        new_name = st.text_input("Enter your name", placeholder="E.g. Hamza Rizvi")

        st.subheader("Optional: voice enrollment")
        st.info("Enroll your voice for voice-only attendance")

        audio_data = None
        try:
            audio_data = st.audio_input("Record a short phrase like: I am present, my name is Akash.")
        except Exception:
            st.error("Audio recording failed!")

        if st.button("Create Account", type="primary"):
            name = new_name.strip()
            if len(name) < 2:
                st.warning("Please enter your name!")
                return
            with st.spinner("Creating profile..."):
                voice_emb = get_voice_embedding(audio_data.read()) if audio_data else None
                response = create_student(name, face_embedding=face["embedding"].tolist(), voice_embedding=voice_emb)
                if response:
                    train_classifier()
                    st.session_state.is_logged_in = True
                    st.session_state.user_role = "student"
                    st.session_state.student_data = response[0]
                    st.toast(f"Profile created! Hi {name}!")
                    time.sleep(1)
                    st.rerun()
                else:
                    st.error("Could not create the profile. Please try again.")


def _face_login_flow():
    photo_open = st.camera_input("Step 1: look straight at the camera, eyes open", key="cam_open")
    if not photo_open:
        return

    with st.spinner("AI is scanning..."):
        first = _analyze_upload(photo_open)

    if first["num_faces"] == 0:
        st.error("🚫 **Cannot recognise face.** No human face was detected. "
                 "Make sure your face is visible, well lit and facing the camera (animals and objects are not accepted).")
        return
    if first["num_faces"] > 1:
        st.warning("Multiple faces found. Only one person can log in at a time.")
        return

    face = first["faces"][0]

    if settings.LIVENESS_REQUIRED:
        st.success("Face detected ✅  One more step to prove it is really you.")
        photo_closed = st.camera_input("Step 2: now CLOSE your eyes and capture", key="cam_closed")
        if not photo_closed:
            return
        with st.spinner("Checking liveness..."):
            second = _analyze_upload(photo_closed)
        if second["num_faces"] != 1:
            st.error("🚫 **Cannot recognise face** in the second photo. Keep your face in the frame and retake.")
            return
        ok, message = check_liveness(first["faces"][0], second["faces"][0])
        if not ok:
            st.error(f"🛡️ Liveness check failed: {message}")
            return
        st.success("Liveness verified ✅")

    if face["student_id"] is not None:
        student = get_student(face["student_id"])
        if student:
            _login_user(student)
            return

    st.info("Face not recognised. You might be a new student, create your profile below.")
    _registration_form(face)


def student_screen():
    style_background_dashboard()
    style_base_layout()
    st.markdown("""
        <style>
        video {
            transform: scaleX(-1) !important;
        }
        </style>
    """, unsafe_allow_html=True)

    if "student_data" in st.session_state:
        student_dashboard()
        return

    c1, c2 = st.columns(2, vertical_alignment="center", gap="xxlarge")
    with c1:
        header_dashboard()
    with c2:
        if st.button("Go back to Home", type="secondary", key="loginbackbtn", shortcut="control+backspace"):
            st.session_state["login_type"] = None
            st.rerun()

    st.header("Login using FaceID", text_alignment="center")
    steps(["① Look at the camera", "② Close your eyes", "③ You're in"] if settings.LIVENESS_REQUIRED
          else ["① Look at the camera", "② You're in"])
    st.space()

    _face_login_flow()
    footer_dashboard()
