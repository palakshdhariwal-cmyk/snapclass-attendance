import streamlit as st

from src import settings

LOGO_URL = "https://i.ibb.co/YTYGn5qV/logo.png"


def header_home():
    st.markdown(f"""
        <div style="display:flex; flex-direction:column; align-items:center; text-align:center; margin:30px 0 34px">
            <img src='{LOGO_URL}' style='height:96px; filter:drop-shadow(0 10px 20px rgba(0,0,0,.35));' />
            <h1 style='text-align:center; color:#fff; margin-top:10px; letter-spacing:.04em'>SNAP<span style="color:#F9A8D4">CLASS</span></h1>
            <p style='color:#C7D2FE; font-size:1.15rem; margin:6px 0 16px'>{settings.TAGLINE}</p>
            <div>
                <span class="sc-pill glass">🧑‍💻 Face recognition</span>
                <span class="sc-pill glass">👁️ Liveness check</span>
                <span class="sc-pill glass">🎙️ Voice attendance</span>
                <span class="sc-pill glass">📊 Live analytics</span>
            </div>
        </div>
    """, unsafe_allow_html=True)


def header_dashboard():
    st.markdown(f"""
        <div style="display:flex; align-items:center; justify-content:center; gap:12px">
            <img src='{LOGO_URL}' style='height:72px;' />
            <h2 style='text-align:left; color:#4F46E5; margin:0'>SNAP<br/><span style="color:#EC4899">CLASS</span></h2>
        </div>
    """, unsafe_allow_html=True)
