import streamlit as st

from src.database.db import create_attendance, attendance_taken_today
from src.ui.ui_kit import stat_cards


def show_attendance_result(df, logs, annotated=None, extra_info=None, key="att"):
    """Review step before saving.

    df         - table with a boolean 'Present' column (the teacher can tick / untick it)
    logs       - rows ready to insert into attendance_logs
    annotated  - optional list of PIL images (photos with names drawn on faces)
    extra_info - optional text shown under the numbers (e.g. unknown faces)
    """
    edited = st.data_editor(
        df,
        hide_index=True,
        width="stretch",
        key=f"{key}_editor",
        disabled=[c for c in df.columns if c != "Present"],
        column_config={"Present": st.column_config.CheckboxColumn("Present", help="Tick or untick to correct the AI")},
    )

    present = int(edited["Present"].sum())
    total = len(edited)
    stat_cards([
        ("✅", present, "Present"),
        ("❌", total - present, "Absent"),
        ("📈", f"{(100 * present / total) if total else 0:.0f}%", "Class attendance"),
    ])
    st.caption("The AI can make mistakes. Tick or untick **Present** to correct it, then confirm.")
    if extra_info:
        st.info(extra_info)

    if annotated:
        with st.expander(f"🔍 See what the AI detected ({len(annotated)} photo{'s' if len(annotated) != 1 else ''})"):
            for i, image in enumerate(annotated, start=1):
                st.image(image, caption=f"Photo {i}  ·  green = sure, amber = please review, red = unknown",
                         width="stretch")

    subject_ids = {log["subject_id"] for log in logs}
    already_taken = False
    try:
        already_taken = any(attendance_taken_today(sid) for sid in subject_ids)
    except Exception:
        pass

    allow_duplicate = True
    if already_taken:
        st.warning("Attendance for this subject was already saved today.")
        allow_duplicate = st.checkbox("Save anyway as a second session", key=f"{key}_dup")

    c1, c2, c3 = st.columns(3)
    with c1:
        st.download_button("Download CSV", edited.to_csv(index=False).encode("utf-8"),
                           file_name="attendance_preview.csv", mime="text/csv",
                           width="stretch", icon=":material/download:", key=f"{key}_csv")
    with c2:
        if st.button("Discard", width="stretch", key=f"{key}_discard"):
            st.session_state.voice_attendance_results = None
            st.session_state.attendance_images = []
            st.rerun()
    with c3:
        if st.button("Confirm & Save", width="stretch", type="primary", key=f"{key}_save",
                     disabled=not allow_duplicate):
            present_map = {int(i): bool(p) for i, p in zip(edited["ID"], edited["Present"])}
            final_logs = [dict(log, is_present=present_map.get(int(log["student_id"]), bool(log["is_present"])))
                          for log in logs]
            try:
                create_attendance(final_logs)
                st.toast("Attendance saved ✅")
                st.session_state.attendance_images = []
                st.session_state.voice_attendance_results = None
                st.rerun()
            except Exception:
                st.error("Could not save attendance. Please try again.")


@st.dialog("Review attendance", width="large")
def attendance_result_dialog(df, logs, annotated=None, extra_info=None):
    show_attendance_result(df, logs, annotated=annotated, extra_info=extra_info, key="face")
