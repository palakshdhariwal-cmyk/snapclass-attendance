import html

import streamlit as st

from src.ui.ui_kit import progress_html, percent_color


def subject_card(name, code, section, stats=None, footer_callback=None, percent=None):
    """percent (0-100) is optional; when given a coloured progress bar is shown."""
    body = f"""
    <div class="sc-card">
        <div class="bar"></div>
        <h3 style="margin:0; color:#111827;">{html.escape(str(name))}</h3>
        <p style="color:#6B7280; margin:10px 0 14px;">
            Code <span class="sc-pill indigo">{html.escape(str(code))}</span>
            &nbsp;·&nbsp; Section {html.escape(str(section))}
        </p>
    """
    if stats:
        body += '<div style="display:flex; gap:10px; flex-wrap:wrap;">'
        for icon, label, value in stats:
            body += (f'<div style="background:#F5F6FB; padding:6px 14px; border-radius:999px; '
                     f'font-size:.9rem; color:#374151;">{icon} <b>{value}</b> {html.escape(str(label))}</div>')
        body += "</div>"

    if percent is not None:
        color = percent_color(percent)
        body += (f'<div style="margin-top:14px; display:flex; justify-content:space-between; font-size:.9rem;">'
                 f'<span style="color:#6B7280">Attendance</span>'
                 f'<b style="color:{color}">{percent:.0f}%</b></div>' + progress_html(percent))

    body += "</div>"
    st.markdown(body, unsafe_allow_html=True)

    if footer_callback:
        footer_callback()
