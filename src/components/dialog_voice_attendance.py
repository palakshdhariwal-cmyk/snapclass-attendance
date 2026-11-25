import streamlit as st
import pandas as pd
from datetime import datetime

from src.pipelines.voice_pipeline import process_bulk_audio
from src.database.config import supabase
from src.components.dialog_attendance_results import show_attendance_result


@st.dialog("Voice Attendance", width="large")
def voice_attendance_dialog(selected_subject_id):
    st.write("Record the class saying **“I am present”**. The AI will recognise each student's voice.")

    audio_data = st.audio_input("Record classroom audio")

    if st.button("Analyze Audio", width="stretch", type="primary"):
        if audio_data is None:
            st.warning("Please record some audio first.")
            return

        with st.spinner("Processing audio..."):
            full = (supabase.table("subject_students").select("*, students(*)")
                    .eq("subject_id", selected_subject_id).execute().data)

            if not full:
                st.warning("No students enrolled in this course")
                return

            candidates = {s["students"]["student_id"]: s["students"]["voice_embedding"]
                          for s in full if s["students"].get("voice_embedding")}

            if not candidates:
                st.error("No enrolled students have voice profiles registered")
                return

            scores = process_bulk_audio(audio_data.read(), candidates)
            timestamp = datetime.now().strftime("%Y-%m-%dT%H:%M:%S")

            rows, logs = [], []
            for node in full:
                student = node["students"]
                score = scores.get(student["student_id"], 0.0)
                is_present = bool(score > 0)
                rows.append({
                    "Present": is_present,
                    "Name": student["name"],
                    "ID": student["student_id"],
                    "Voice match": f"{float(score):.2f}" if is_present else "-",
                })
                logs.append({
                    "student_id": student["student_id"],
                    "subject_id": selected_subject_id,
                    "timestamp": timestamp,
                    "is_present": is_present,
                })
            st.session_state.voice_attendance_results = (pd.DataFrame(rows), logs)

    if st.session_state.get("voice_attendance_results"):
        st.divider()
        df_results, logs = st.session_state.voice_attendance_results
        show_attendance_result(df_results, logs, key="voice")
