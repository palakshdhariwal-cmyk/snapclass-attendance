"""Small HTML building blocks shared by every screen."""
import html

import streamlit as st

from src import settings


def section_title(title, subtitle=""):
    sub = f'<div class="s">{html.escape(subtitle)}</div>' if subtitle else ""
    st.markdown(f'<div class="sc-section"><div class="t">{html.escape(title)}</div>{sub}</div>',
                unsafe_allow_html=True)


def stat_cards(cards):
    """cards: list of (icon, value, label, hint, hint_color_hex)."""
    parts = ['<div class="sc-stats">']
    for icon, value, label, *rest in cards:
        hint = rest[0] if rest else ""
        color = rest[1] if len(rest) > 1 else "#6B7280"
        hint_html = f'<div class="h" style="color:{color}">{html.escape(str(hint))}</div>' if hint else ""
        parts.append(
            f'<div class="sc-stat"><div class="i">{icon}</div>'
            f'<div class="v">{html.escape(str(value))}</div>'
            f'<div class="l">{html.escape(str(label))}</div>{hint_html}</div>'
        )
    parts.append("</div>")
    st.markdown("".join(parts), unsafe_allow_html=True)


def pill(text, kind="indigo"):
    return f'<span class="sc-pill {kind}">{html.escape(text)}</span>'


def pills(items, kind="indigo"):
    st.markdown("".join(pill(t, kind) for t in items), unsafe_allow_html=True)


def percent_color(percent):
    if percent >= settings.ATTENDANCE_WARN_PERCENT:
        return "#22C55E"
    if percent >= settings.ATTENDANCE_WARN_PERCENT - 15:
        return "#F59E0B"
    return "#EF4444"


def progress_html(percent):
    percent = max(0, min(100, percent))
    return (f'<div class="sc-progress"><div style="width:{percent}%;'
            f'background:{percent_color(percent)}"></div></div>')


def banner(message, good=False):
    cls = "sc-banner good" if good else "sc-banner"
    st.markdown(f'<div class="{cls}">{message}</div>', unsafe_allow_html=True)


def steps(items):
    st.markdown('<div class="sc-steps">' + "".join(pill(t, "indigo") for t in items) + "</div>",
                unsafe_allow_html=True)
