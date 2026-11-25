"""Analytics dashboard + attendance records for teachers."""
import streamlit as st

from src import settings
from src.database.db import get_attendance_for_teacher, get_student_names
from src.ui.ui_kit import banner, section_title, stat_cards
from src.utils import analytics as an


def _load_df(teacher_id):
    records = get_attendance_for_teacher(teacher_id)
    if not records:
        return an.records_to_df([], {})
    names = get_student_names([r.get("student_id") for r in records])
    return an.records_to_df(records, names)


def _subject_filter(df, key):
    options = {"All subjects": None}
    subjects = df[["subject_id", "Subject", "Subject Code"]].drop_duplicates()
    for _, row in subjects.iterrows():
        options[f"{row['Subject']} ({row['Subject Code']})"] = row["subject_id"]
    label = st.selectbox("Subject", list(options.keys()), key=key)
    chosen = options[label]
    return df if chosen is None else df[df["subject_id"] == chosen]


def teacher_tab_analytics():
    section_title("Analytics dashboard", "Understand attendance trends and spot students who need attention")

    teacher_id = st.session_state.teacher_data["teacher_id"]
    df = _load_df(teacher_id)
    if df.empty:
        st.info("No attendance has been recorded yet. Take attendance first and your insights will appear here.")
        return

    df = _subject_filter(df, "analytics_subject")
    summary = an.student_summary(df)
    trend = an.session_trend(df)
    risky = an.at_risk(summary)

    stat_cards([
        ("🗓️", df["Session"].nunique(), "Class sessions"),
        ("🧑‍🎓", df["student_id"].nunique(), "Students tracked"),
        ("📈", f"{an.overall_percent(df):.0f}%", "Average attendance"),
        ("⚠️", len(risky), f"Below {settings.ATTENDANCE_WARN_PERCENT}%",
         "Needs attention" if len(risky) else "All good", "#DC2626" if len(risky) else "#16A34A"),
    ])

    c1, c2 = st.columns(2)
    with c1:
        st.subheader("Attendance by student")
        st.bar_chart(summary.set_index("Student")["Percent"], color="#6366F1", height=300)
    with c2:
        st.subheader("Trend across sessions")
        if len(trend) > 1:
            st.line_chart(trend.set_index("Session")["Percent"], color="#EC4899", height=300)
        else:
            st.info("Take attendance in at least two sessions to see a trend.")

    st.divider()
    if len(risky):
        banner(f"⚠️ <b>{len(risky)} student(s)</b> are below {settings.ATTENDANCE_WARN_PERCENT}% attendance.")
    else:
        banner("🎉 Every student is above the attendance requirement.", good=True)

    st.subheader("Student-wise attendance")
    table = summary.sort_values("Percent", ascending=True)
    st.dataframe(
        table, hide_index=True, width="stretch",
        column_config={
            "Percent": st.column_config.ProgressColumn("Attendance %", min_value=0, max_value=100, format="%.1f%%"),
            "Attended": st.column_config.NumberColumn("Attended"),
            "Total": st.column_config.NumberColumn("Total classes"),
        },
    )
    st.download_button("Download student report (CSV)", table.to_csv(index=False).encode("utf-8"),
                       file_name="student_attendance_report.csv", mime="text/csv",
                       icon=":material/download:")


def teacher_tab_attendance_records():
    section_title("Attendance records", "Every saved session, with a downloadable log")

    teacher_id = st.session_state.teacher_data["teacher_id"]
    df = _load_df(teacher_id)
    if df.empty:
        st.info("No attendance records yet.")
        return

    df = _subject_filter(df, "records_subject")

    sessions = (df.groupby(["Session", "Subject", "Subject Code"])
                  .agg(Present=("Present", "sum"), Total=("Present", "count"))
                  .reset_index().sort_values("Session", ascending=False))
    sessions["Rate"] = (100.0 * sessions["Present"] / sessions["Total"]).round(1)
    sessions["Time"] = sessions["Session"].dt.strftime("%d %b %Y, %I:%M %p")
    sessions["Attendance"] = ("✅ " + sessions["Present"].astype(int).astype(str) + " / "
                              + sessions["Total"].astype(str) + " students")

    st.dataframe(
        sessions[["Time", "Subject", "Subject Code", "Attendance", "Rate"]],
        hide_index=True, width="stretch",
        column_config={"Rate": st.column_config.ProgressColumn("Rate", min_value=0, max_value=100, format="%.0f%%")},
    )

    detail = df.sort_values("Session", ascending=False).copy()
    detail["Time"] = detail["Session"].dt.strftime("%Y-%m-%d %H:%M")
    detail["Status"] = detail["Present"].map({True: "Present", False: "Absent"})
    detail = detail[["Time", "Subject", "Subject Code", "Student", "Status"]]

    with st.expander("See every student's status per session"):
        st.dataframe(detail, hide_index=True, width="stretch")

    st.download_button("Download full attendance log (CSV)", detail.to_csv(index=False).encode("utf-8"),
                       file_name="attendance_log.csv", mime="text/csv", icon=":material/download:")
