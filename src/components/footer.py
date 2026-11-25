import streamlit as st

LOGO_URL = "https://i.ibb.co/4r5X1FY/apnacollege.png"


def _footer(color):
    st.markdown(f"""
        <div style="margin-top:2.5rem; display:flex; gap:8px; justify-content:center; align-items:center; opacity:.9">
            
            
        </div>
    """, unsafe_allow_html=True)


def footer_home():
    _footer("#E0E7FF")


def footer_dashboard():
    _footer("#374151")
