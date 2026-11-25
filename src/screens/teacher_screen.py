import time
from datetime import datetime

import pandas as pd
import streamlit as st

from src import settings
from src.components.dialog_add_photo import add_photos_dialog
from src.components.dialog_attendance_results import attendance_result_dialog
from src.components.dialog_create_subject import create_subject_dialog
from src.components.dialog_share_subject import share_subject_dialog
from src.components.dialog_voice_attendance import voice_attendance_dialog
from src.components.footer import footer_dashboard
from src.components.header import header_dashboard
from src.components.subject_card import subject_card
from src.database.db import (check_teacher_exists, create_teacher, get_enrolled_students,
                             get_student_names, get_teacher_subjects, teacher_login)
from src.pipelines.face_engine import classify_distance, distance_to_confidence
from src.pipelines.face_pipeline import analyze_image, annotate
from src.screens.teacher_analytics import teacher_tab_analytics, teacher_tab_attendance_records
from src.ui.base_layout import style_background_dashboard, style_base_layout
from src.ui.ui_kit import section_title


def teacher_screen():
    style_background_dashboard()
    style_base_layout()

    if "teacher_data" in st.session_state:
        teacher_dashboard()
    elif "teacher_login_type" not in st.session_state or st.session_state.teacher_login_type == "login":
        teacher_screen_login()
    elif st.session_state.teacher_login_type == "register":
        teacher_screen_register()


# ----------------------------------------------------------------------------
# Dashboard
# ----------------------------------------------------------------------------
TABS = [
    ("take_attendance", "Take Attendance", ":material/ar_on_you:"),
    ("analytics", "Analytics", ":material/monitoring:"),
    ("attendance_records", "Records", ":material/cards_stack:"),
    ("manage_subjects", "Subjects", ":material/book_ribbon:"),
]


def teacher_dashboard():
    teacher_data = st.session_state.teacher_data
    c1, c2 = st.columns(2, vertical_alignment="center", gap="xxlarge")
    with c1:
        header_dashboard()
    with c2:
        st.subheader(f"Welcome, {teacher_data['name']} 👋")
        if st.button("Logout", type="secondary", key="loginbackbtn", shortcut="control+backspace"):
            st.session_state["is_logged_in"] = False
            del st.session_state.teacher_data
            st.rerun()

    st.space()

    if "current_teacher_tab" not in st.session_state:
        st.session_state.current_teacher_tab = "take_attendance"

    for column, (tab_id, label, icon) in zip(st.columns(len(TABS)), TABS):
        with column:
            kind = "primary" if st.session_state.current_teacher_tab == tab_id else "tertiary"
            if st.button(label, type=kind, width="stretch", icon=icon, key=f"tab_{tab_id}"):
                st.session_state.current_teacher_tab = tab_id
                st.rerun()

    st.divider()

    tab = st.session_state.current_teacher_tab
    if tab == "take_attendance":
        teacher_tab_take_attendance()
    elif tab == "analytics":
        teacher_tab_analytics()
    elif tab == "attendance_records":
        teacher_tab_attendance_records()
    elif tab == "manage_subjects":
        teacher_tab_manage_subjects()

    footer_dashboard()


# ----------------------------------------------------------------------------
# Take attendance
# ----------------------------------------------------------------------------
def run_face_analysis(images, subject_id):
    """Scans all photos and opens the review dialog (or shows a clear error)."""
    with st.spinner("Deep scanning classroom photos..."):
        analysed = [analyze_image(img) for img in images]

    total_faces = sum(a["num_faces"] for a in analysed)
    if total_faces == 0:
        st.error("🚫 **Cannot recognise face.** No human face was found in the uploaded photo(s). "
                 "Use a clear photo of people (animals and objects are ignored).")
        return

    no_face_photos = [i + 1 for i, a in enumerate(analysed) if a["num_faces"] == 0]
    if no_face_photos:
        st.warning("No human face found in: " + ", ".join(f"Photo {i}" for i in no_face_photos))

    enrolled = get_enrolled_students(subject_id)
    if not enrolled:
        st.warning("No students enrolled in this course")
        return

    matched_ids = {sid for a in analysed for sid in a["matches"]}
    names = get_student_names(matched_ids | {n["students"]["student_id"] for n in enrolled})

    best = {}      # student_id -> {distance, sources}
    for idx, result in enumerate(analysed, start=1):
        for sid, info in result["matches"].items():
            entry = best.setdefault(sid, {"distance": info["distance"], "sources": []})
            entry["distance"] = min(entry["distance"], info["distance"])
            entry["sources"].append(f"Photo {idx}")

    timestamp = datetime.now().strftime("%Y-%m-%dT%H:%M:%S")
    rows, logs = [], []
    for node in enrolled:
        student = node["students"]
        sid = int(student["student_id"])
        hit = best.get(sid)
        present = hit is not None

        status = classify_distance(hit["distance"]) if hit else None
        confidence = distance_to_confidence(hit["distance"]) if hit else None

        rows.append({
            "Present": present,
            "Name": student["name"],
            "ID": sid,
            "Confidence": f"{confidence:.0f}%" if hit else "-",
            "Seen in": ", ".join(hit["sources"]) if hit else "-",
            "Check": "⚠️ Review" if status == "review" else ("✔️" if present else ""),
        })
        logs.append({"student_id": sid, "subject_id": subject_id, "timestamp": timestamp, "is_present": present})

    enrolled_ids = {int(n["students"]["student_id"]) for n in enrolled}
    unknown_faces = sum(1 for a in analysed for f in a["faces"] if f["student_id"] is None)
    outsiders = sorted(sid for sid in matched_ids if int(sid) not in enrolled_ids)

    notes = []
    if unknown_faces:
        notes.append(f"{unknown_faces} face(s) did not match any registered student (red boxes).")
    if outsiders:
        notes.append("Recognised but not enrolled in this subject: "
                     + ", ".join(str(names.get(s, s)) for s in outsiders) + ".")
    if any(r["Check"] == "⚠️ Review" for r in rows):
        notes.append("Some matches are borderline (⚠️ Review). Please verify them before saving.")

    annotated = [annotate(a, names) for a in analysed if a["num_faces"] > 0]
    attendance_result_dialog(pd.DataFrame(rows), logs, annotated=annotated, extra_info="  \n".join(notes) or None)


def teacher_tab_take_attendance():
    teacher_id = st.session_state.teacher_data["teacher_id"]
    section_title("Take AI attendance", "Scan a class photo or use voice, then review and save")

    if "attendance_images" not in st.session_state:
        st.session_state.attendance_images = []

    subjects = get_teacher_subjects(teacher_id)
    if not subjects:
        st.warning("You haven't created any subjects yet! Please create one to begin!")
        return

    subject_options = {f"{s['name']} - {s['subject_code']}": s["subject_id"] for s in subjects}

    col1, col2 = st.columns([3, 1], vertical_alignment="bottom")
    with col1:
        selected_label = st.selectbox("Select Subject", options=list(subject_options.keys()))
    with col2:
        if st.button("Add Photos", type="primary", icon=":material/photo_prints:", width="stretch"):
            add_photos_dialog()

    selected_subject_id = subject_options[selected_label]
    st.divider()

    if st.session_state.attendance_images:
        st.subheader("Added photos")
        gallery = st.columns(4)
        for idx, img in enumerate(st.session_state.attendance_images):
            with gallery[idx % 4]:
                st.image(img, width="stretch", caption=f"Photo {idx + 1}")
    else:
        st.info("Add one or more classroom photos, or use voice attendance.")

    has_photos = bool(st.session_state.attendance_images)
    c1, c2, c3 = st.columns(3)

    with c1:
        if st.button("Clear all photos", width="stretch", type="tertiary", icon=":material/delete:",
                     disabled=not has_photos):
            st.session_state.attendance_images = []
            st.rerun()

    with c2:
        if st.button("Run Face Analysis", width="stretch", type="primary", icon=":material/analytics:",
                     disabled=not has_photos):
            run_face_analysis(st.session_state.attendance_images, selected_subject_id)

    with c3:
        if st.button("Use Voice Attendance", type="secondary", width="stretch", icon=":material/mic:"):
            voice_attendance_dialog(selected_subject_id)


# ----------------------------------------------------------------------------
# Manage subjects
# ----------------------------------------------------------------------------
def teacher_tab_manage_subjects():
    teacher_id = st.session_state.teacher_data["teacher_id"]
    col1, col2 = st.columns(2, vertical_alignment="bottom")
    with col1:
        section_title("Manage subjects", "Create subjects and share the join code with students")
    with col2:
        if st.button("Create New Subject", type="primary", width="stretch", icon=":material/add:"):
            create_subject_dialog(teacher_id)

    subjects = get_teacher_subjects(teacher_id)
    if not subjects:
        st.info("No subjects found. Create one above.")
        return

    cols = st.columns(2)
    for i, sub in enumerate(subjects):
        stats = [("🫂", "Students", sub["total_students"]), ("🕰️", "Classes", sub["total_classes"])]

        def share_btn(sub=sub):
            if st.button(f"Share code: {sub['name']}", key=f"share_{sub['subject_code']}",
                         icon=":material/share:", type="secondary"):
                share_subject_dialog(sub["name"], sub["subject_code"])

        with cols[i % 2]:
            subject_card(name=sub["name"], code=sub["subject_code"], section=sub["section"],
                         stats=stats, footer_callback=share_btn)


# ----------------------------------------------------------------------------
# Login / register
# ----------------------------------------------------------------------------
def login_teacher(username, password):
    if not username or not password:
        return False
    teacher = teacher_login(username, password)
    if teacher:
        st.session_state.user_role = "teacher"
        st.session_state.teacher_data = teacher
        st.session_state.is_logged_in = True
        return True
    return False


def _locked_seconds():
    return max(0, int(st.session_state.get("login_locked_until", 0) - time.time()))


def teacher_screen_login():
    c1, c2 = st.columns(2, vertical_alignment="center", gap="xxlarge")
    with c1:
        header_dashboard()
    with c2:
        if st.button("Go back to Home", type="secondary", key="loginbackbtn", shortcut="control+backspace"):
            st.session_state["login_type"] = None
            st.rerun()

    st.header("Teacher login", text_alignment="center")
    st.space()

    username = st.text_input("Username", placeholder="ananyaroy")
    password = st.text_input("Password", type="password", placeholder="Enter password")
    st.divider()

    btn1, btn2 = st.columns(2)
    with btn1:
        if st.button("Login", icon=":material/passkey:", shortcut="control+enter", width="stretch", type="primary"):
            wait = _locked_seconds()
            if wait:
                st.error(f"Too many failed attempts. Try again in {wait} seconds.")
            elif login_teacher(username, password):
                st.session_state.login_failures = 0
                st.toast("Welcome back!", icon="👋")
                time.sleep(1)
                st.rerun()
            else:
                failures = st.session_state.get("login_failures", 0) + 1
                st.session_state.login_failures = failures
                if failures >= settings.MAX_LOGIN_ATTEMPTS:
                    st.session_state.login_locked_until = time.time() + settings.LOCKOUT_SECONDS
                    st.session_state.login_failures = 0
                    st.error(f"Too many failed attempts. Locked for {settings.LOCKOUT_SECONDS} seconds.")
                else:
                    st.error(f"Invalid username and password combination "
                             f"({settings.MAX_LOGIN_ATTEMPTS - failures} attempts left).")
    with btn2:
        if st.button("Register instead", type="secondary", icon=":material/person_add:", width="stretch"):
            st.session_state.teacher_login_type = "register"
            st.rerun()

    footer_dashboard()


def register_teacher(username, name, password, password_confirm):
    username, name = username.strip(), name.strip()
    if not username or not name or not password:
        return False, "All fields are required!"
    if len(password) < settings.MIN_PASSWORD_LENGTH:
        return False, f"Password must be at least {settings.MIN_PASSWORD_LENGTH} characters."
    if password != password_confirm:
        return False, "Passwords don't match"
    if check_teacher_exists(username):
        return False, "Username already taken"

    try:
        create_teacher(username, password, name)
        return True, "Successfully created! Login now"
    except Exception:
        return False, "Unexpected error!"


def teacher_screen_register():
    c1, c2 = st.columns(2, vertical_alignment="center", gap="xxlarge")
    with c1:
        header_dashboard()
    with c2:
        if st.button("Go back to Home", type="secondary", key="loginbackbtn", shortcut="control+backspace"):
            st.session_state["login_type"] = None
            st.rerun()

    st.header("Register your teacher profile", text_alignment="center")
    st.space()

    username = st.text_input("Username", placeholder="ananyaroy")
    name = st.text_input("Full name", placeholder="Ananya Roy")
    password = st.text_input("Password", type="password", placeholder=f"At least {settings.MIN_PASSWORD_LENGTH} characters")
    password_confirm = st.text_input("Confirm your password", type="password", placeholder="Repeat password")
    st.divider()

    btn1, btn2 = st.columns(2)
    with btn1:
        if st.button("Register now", icon=":material/passkey:", shortcut="control+enter", width="stretch", type="primary"):
            success, message = register_teacher(username, name, password, password_confirm)
            if success:
                st.success(message)
                time.sleep(2)
                st.session_state.teacher_login_type = "login"
                st.rerun()
            else:
                st.error(message)
    with btn2:
        if st.button("Login instead", type="secondary", icon=":material/login:", width="stretch"):
            st.session_state.teacher_login_type = "login"
            st.rerun()

    footer_dashboard()
