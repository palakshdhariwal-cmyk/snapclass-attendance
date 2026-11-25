"""Pure pandas helpers for the analytics dashboard (no streamlit / database)."""
import pandas as pd

from src import settings


def records_to_df(records, name_map=None):
    """Turns raw attendance_logs rows into a tidy DataFrame."""
    name_map = name_map or {}
    rows = []
    for r in records or []:
        subject = r.get("subjects") or {}
        sid = r.get("student_id")
        rows.append({
            "student_id": sid,
            "Student": name_map.get(sid, f"ID {sid}"),
            "subject_id": r.get("subject_id"),
            "Subject": subject.get("name", ""),
            "Subject Code": subject.get("subject_code", ""),
            "timestamp": r.get("timestamp"),
            "Present": bool(r.get("is_present", False)),
        })

    df = pd.DataFrame(rows, columns=["student_id", "Student", "subject_id", "Subject",
                                     "Subject Code", "timestamp", "Present"])
    if df.empty:
        df["Session"] = pd.Series(dtype="datetime64[ns]")
        return df

    parsed = pd.to_datetime(df["timestamp"], errors="coerce", utc=True).dt.tz_convert(None)
    df["Session"] = parsed.dt.floor("s")
    return df.dropna(subset=["Session"])


def student_summary(df):
    """One row per student: classes attended, total classes, percentage."""
    if df.empty:
        return pd.DataFrame(columns=["Student", "Attended", "Total", "Percent"])
    summary = (df.groupby("Student")
                 .agg(Attended=("Present", "sum"), Total=("Present", "count"))
                 .reset_index())
    summary["Attended"] = summary["Attended"].astype(int)
    summary["Percent"] = (100.0 * summary["Attended"] / summary["Total"]).round(1)
    return summary.sort_values(["Percent", "Student"]).reset_index(drop=True)


def session_trend(df):
    """One row per class session: how many were present and the percentage."""
    if df.empty:
        return pd.DataFrame(columns=["Session", "Present", "Total", "Percent"])
    trend = (df.groupby("Session")
               .agg(Present=("Present", "sum"), Total=("Present", "count"))
               .reset_index())
    trend["Present"] = trend["Present"].astype(int)
    trend["Percent"] = (100.0 * trend["Present"] / trend["Total"]).round(1)
    return trend.sort_values("Session").reset_index(drop=True)


def at_risk(summary, threshold=None):
    threshold = settings.ATTENDANCE_WARN_PERCENT if threshold is None else threshold
    return summary[summary["Percent"] < threshold].reset_index(drop=True)


def overall_percent(df):
    if df.empty:
        return 0.0
    return round(100.0 * float(df["Present"].mean()), 1)
