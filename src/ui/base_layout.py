import streamlit as st


def style_background_home():
    st.markdown("""
    <style>
        .stApp {
            background:
                radial-gradient(900px 520px at 5% 0%, rgba(124,58,237,.55), transparent 60%),
                radial-gradient(800px 520px at 100% 15%, rgba(236,72,153,.38), transparent 55%),
                linear-gradient(160deg, #1E1B4B 0%, #312E81 100%) !important;
            background-attachment: fixed !important;
        }
        .stApp div[data-testid="stColumn"] {
            background: rgba(255,255,255,.96) !important;
            padding: 2.2rem 2rem !important;
            border-radius: 1.75rem !important;
            box-shadow: 0 28px 60px rgba(10,10,40,.38);
            transition: transform .3s ease, box-shadow .3s ease;
            text-align: center;
        }
        .stApp div[data-testid="stColumn"]:hover {
            transform: translateY(-8px);
            box-shadow: 0 36px 70px rgba(10,10,40,.5);
        }
        .stApp div[data-testid="stColumn"] h2 { color: #1E1B4B !important; margin-bottom: .6rem !important; }
        .stApp div[data-testid="stColumn"] [data-testid="stImage"] { display:flex; justify-content:center; margin-bottom: 1rem; }
    </style>
    """, unsafe_allow_html=True)


def style_background_dashboard():
    st.markdown("""
    <style>
        .stApp {
            background:
                radial-gradient(700px 300px at 100% 0%, rgba(99,102,241,.10), transparent 60%),
                #F5F6FB !important;
        }
        .stApp h1, .stApp h2, .stApp h3, .stApp h4 { color: #111827; }
        .stApp p, .stApp label, .stApp li { color: #374151; }
    </style>
    """, unsafe_allow_html=True)


def style_base_layout():
    st.markdown("""
    <style>
        @import url('https://fonts.googleapis.com/css2?family=Outfit:wght@300..700&family=Playfair+Display:wght@600;700;800&display=swap');

        #MainMenu, footer, header { visibility: hidden; }
        .block-container { padding-top: 1.5rem !important; max-width: 1120px !important; }

        html, body, .stApp, p, label, li, input, textarea, button {
            font-family: 'Outfit', sans-serif;
        }
        h1, h2, h3 {
            font-family: 'Playfair Display', serif !important;
            letter-spacing: -0.01em;
        }
        h1 { font-size: 3.2rem !important; line-height: 1.1 !important; }
        h2 { font-size: 1.9rem !important; line-height: 1.2 !important; }
        h3 { font-size: 1.35rem !important; }

        /* ---------------- Buttons ---------------- */
        [data-testid^="stBaseButton"], button[kind] {
            border-radius: 999px !important;
            padding: .55rem 1.4rem !important;
            font-weight: 600 !important;
            transition: transform .2s ease, box-shadow .2s ease, background .2s ease !important;
        }
        [data-testid="stBaseButton-primary"], button[kind="primary"] {
            background: linear-gradient(135deg, #4F46E5, #7C3AED) !important;
            color: #fff !important;
            border: none !important;
            box-shadow: 0 8px 22px rgba(79,70,229,.35);
        }
        [data-testid="stBaseButton-secondary"], button[kind="secondary"] {
            background: #fff !important;
            color: #4F46E5 !important;
            border: 1.5px solid #C7D2FE !important;
        }
        [data-testid="stBaseButton-tertiary"], button[kind="tertiary"] {
            background: transparent !important;
            color: #6B7280 !important;
            border: 1.5px solid #E5E7EB !important;
        }
        [data-testid^="stBaseButton"] *, button[kind] * { color: inherit !important; }
        [data-testid^="stBaseButton"]:hover, button[kind]:hover {
            transform: translateY(-2px);
            box-shadow: 0 12px 26px rgba(79,70,229,.28);
        }
        [data-testid="stBaseButton-secondary"]:hover { border-color: #4F46E5 !important; }
        [data-testid="stBaseButton-tertiary"]:hover  { border-color: #A5B4FC !important; color:#4F46E5 !important; }
        [data-testid="stBaseButton-primary"]:disabled,
        [data-testid="stBaseButton-secondary"]:disabled,
        [data-testid="stBaseButton-tertiary"]:disabled { opacity: .45; box-shadow: none; transform: none; }

        /* ---------------- Inputs & widgets ---------------- */
        div[data-baseweb="input"] > div, div[data-baseweb="select"] > div, div[data-baseweb="textarea"] {
            border-radius: 14px !important;
        }
        [data-testid="stCameraInput"] {
            border-radius: 22px; overflow: hidden;
            box-shadow: 0 14px 34px rgba(31,41,55,.14);
        }
        [data-testid="stImage"] img { border-radius: 16px; }
        div[role="dialog"] { border-radius: 26px !important; }
        [data-testid="stVerticalBlockBorderWrapper"] { border-radius: 22px !important; }
        [data-testid="stDataFrame"], [data-testid="stDataEditor"] {
            border-radius: 16px; overflow: hidden; box-shadow: 0 6px 20px rgba(31,41,55,.07);
        }
        [data-testid="stAlert"] { border-radius: 16px !important; }
        hr { border-color: #E5E7EB !important; }

        /* ---------------- Reusable SnapClass components ---------------- */
        .sc-section { margin: .4rem 0 1rem; }
        .sc-section .t { font-family:'Playfair Display',serif; font-size:1.75rem; font-weight:700; color:#111827; line-height:1.2; }
        .sc-section .s { color:#6B7280; font-size:1rem; margin-top:2px; }

        .sc-stats { display:grid; grid-template-columns:repeat(auto-fit,minmax(170px,1fr)); gap:16px; margin:.5rem 0 1.4rem; }
        .sc-stat {
            background:#fff; border-radius:20px; padding:18px 20px;
            border:1px solid #EEF0F6; box-shadow:0 10px 28px rgba(31,41,55,.07);
            transition: transform .25s ease, box-shadow .25s ease;
        }
        .sc-stat:hover { transform: translateY(-4px); box-shadow:0 16px 34px rgba(79,70,229,.16); }
        .sc-stat .i { font-size:1.4rem; }
        .sc-stat .v { font-family:'Playfair Display',serif; font-size:2rem; font-weight:700; color:#111827; line-height:1.2; }
        .sc-stat .l { color:#6B7280; font-size:.9rem; letter-spacing:.02em; }
        .sc-stat .h { font-size:.8rem; margin-top:4px; font-weight:600; }

        .sc-pill { display:inline-block; padding:4px 12px; border-radius:999px; font-size:.8rem; font-weight:600; margin:2px 4px 2px 0; }
        .sc-pill.indigo { background:#EEF2FF; color:#4F46E5; }
        .sc-pill.green  { background:#DCFCE7; color:#15803D; }
        .sc-pill.red    { background:#FEE2E2; color:#B91C1C; }
        .sc-pill.amber  { background:#FEF3C7; color:#B45309; }
        .sc-pill.glass  { background:rgba(255,255,255,.14); color:#E0E7FF; border:1px solid rgba(255,255,255,.25); }

        .sc-card {
            position:relative; overflow:hidden; background:#fff; border-radius:22px;
            padding:24px 28px; margin-bottom:18px; border:1px solid #EEF0F6;
            box-shadow:0 10px 30px rgba(31,41,55,.08); transition: transform .25s ease, box-shadow .25s ease;
        }
        .sc-card:hover { transform: translateY(-3px); box-shadow:0 18px 40px rgba(79,70,229,.15); }
        .sc-card .bar { position:absolute; left:0; top:0; bottom:0; width:6px; background:linear-gradient(180deg,#4F46E5,#EC4899); }

        .sc-progress { background:#EEF0F6; border-radius:999px; height:10px; overflow:hidden; margin:10px 0 4px; }
        .sc-progress > div { height:100%; border-radius:999px; }

        .sc-banner {
            border-radius:20px; padding:16px 22px; margin:.4rem 0 1.2rem;
            background:linear-gradient(135deg,#FEF3C7,#FDE68A); color:#78350F; border:1px solid #FCD34D;
        }
        .sc-banner.good { background:linear-gradient(135deg,#DCFCE7,#BBF7D0); color:#14532D; border-color:#86EFAC; }
        .sc-steps { display:flex; gap:10px; flex-wrap:wrap; margin:.2rem 0 1rem; }
    </style>
    """, unsafe_allow_html=True)
