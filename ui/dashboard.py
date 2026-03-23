import streamlit as st

def setup_dashboard_styles():
    """
    Injects Tailwind CSS, fonts, and custom CSS classes to override Streamlit defaults 
    and apply the Luminal (Stitch) template styling rules.
    """
    st.markdown(
        """
        <link href="https://fonts.googleapis.com/css2?family=Manrope:wght@400;600;700;800&family=Inter:wght@400;500;600&display=swap" rel="stylesheet">
        <link href="https://fonts.googleapis.com/css2?family=Material+Symbols+Outlined:wght,FILL@100..700,0..1&display=swap" rel="stylesheet">
        <script src="https://cdn.tailwindcss.com"></script>
        
        <style>
            /* Base reset and layout covering main application canvas */
            @import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;600&family=Manrope:wght@700;800&display=swap');

            .stApp {
                background: linear-gradient(135deg, #0a0f14 0%, #0d1218 50%, #0a0f14 100%) !important;
                color: #eaeef6 !important;
                font-family: 'Inter', sans-serif;
            }

            /* Custom Styling Blocks */
            .glass-panel {
                background: rgba(20, 26, 32, 0.4);
                backdrop-filter: blur(16px);
                border: 1px solid rgba(129, 236, 255, 0.04);
            }
            .glow-border {
                position: relative;
            }

            /* Custom CSS Overrides for Streamlit Elements to fit Stitch constraints */
            /* 1. Sidebar adjustments */
            section[data-testid="stSidebar"] {
                background-color: #0e1419 !important;
                border-right: 1px solid rgba(67, 72, 78, 0.06);
                width: 260px !important;
            }
            
            section[data-testid="stSidebar"] .stButton > button {
                background-color: transparent;
                border: 1px solid rgba(255, 255, 255, 0.05);
                color: #a7abb2;
                border-radius: 0.75rem;
                padding: 0.75rem 1rem;
                width: 100%;
                text-align: left;
                justify-content: flex-start;
                font-family: 'Inter', sans-serif;
                font-size: 0.875rem;
                transition: all 0.2s;
            }
            section[data-testid="stSidebar"] .stButton > button:hover {
                background-color: rgba(31, 38, 46, 0.6) !important;
                color: #ffffff;
                border-color: rgba(129, 236, 255, 0.1);
            }
            section[data-testid="stSidebar"] .stButton > button:active {
                background-color: rgba(129, 236, 255, 0.05);
                border-color: #81ecff;
                color: #81ecff;
            }

            /* Hiding Streamlit header footer artifacts for dashboard look */
            header[data-testid="stHeader"] {
                background: rgba(10, 15, 20, 0.8) !important;
                backdrop-filter: blur(16px);
                border-bottom: 1px solid rgba(255, 255, 255, 0.03);
            }

            /* 2. Metrics & Cards styling native override */
            div[data-testid="stMetric"] {
                background: rgba(20, 26, 32, 0.4);
                border: 1px solid rgba(129, 236, 255, 0.05);
                padding: 1.25rem;
                border-radius: 1rem;
                backdrop-filter: blur(16px);
            }
            
            div[data-testid="stMetricValue"] {
                font-family: 'Manrope', sans-serif;
                font-size: 2rem !important;
                font-weight: 800;
                color: #ffffff;
            }

            div[data-testid="stMetricLabel"] {
                font-family: 'Inter', sans-serif;
                font-size: 0.75rem;
                text-transform: uppercase;
                letter-spacing: 0.1em;
                color: #a7abb2;
            }

            /* 3. Streamlit DataFrame/Table Style */
            div[data-testid="stDataFrame"] {
                background: #141a20;
                border-radius: 0.75rem;
                border: 1px solid rgba(255,255,255,0.05);
                padding: 0.5rem;
            }

            /* 4. Selectbox / Slider Streamlit Style overlap */
            div[data-baseweb="select"] {
                background-color: #1f262e !important;
                border-radius: 0.5rem;
                border: 1px solid rgba(67, 72, 78, 0.15) !important;
            }
            
            div[role="listbox"] {
                background-color: #141a20 !important;
                border: 1px solid rgba(67, 72, 78, 0.2) !important;
            }

            input {
                background-color: #141a20 !important;
                color: #fff !important;
            }

            /* Tab sets styling */
            div[data-testid="stTab"] {
                color: #a7abb2;
                background-color: transparent !important;
                font-family: 'Inter', sans-serif;
                font-weight: 600;
                font-size: 0.875rem;
            }
            div[data-testid="stTab"][aria-selected="true"] {
                color: #81ecff !important;
                border-bottom: 2px solid #81ecff !important;
            }

            /* Primary buttons following Stitch */
            div.stButton > button[kind="primary"] {
                background: linear-gradient(135deg, #81ecff 0%, #00e3fd 100%) !important;
                color: #003840 !important;
                font-weight: 700 !important;
                border-radius: 0.5rem !important;
                border: none !important;
                box-shadow: 0 0 15px rgba(129, 236, 255, 0.2) !important;
                transition: scale 0.2s, box-shadow 0.2s !important;
            }
            div.stButton > button[kind="primary"]:hover {
                box-shadow: 0 0 25px rgba(129, 236, 255, 0.4) !important;
                transform: scale(1.02);
            }

            /* 5. Hide Sidebar Radio dots to treat as list menu item */
            div[data-testid="stSidebar"] div[data-testid="stRadio"] label div:first-child {
                display: none !important;
            }
            
            section[data-testid="stSidebar"] div[data-testid="stRadio"] label {
                background-color: transparent;
                border: 1px solid rgba(255, 255, 255, 0.02);
                border-radius: 0.75rem;
                padding: 0.625rem 1rem;
                margin-bottom: 0.4rem;
                width: 100%;
                font-family: 'Inter', sans-serif;
                font-size: 0.875rem;
                color: #a7abb2 !important;
                transition: all 0.2s;
                cursor: pointer;
            }
            
            section[data-testid="stSidebar"] div[data-testid="stRadio"] label:hover {
                background-color: rgba(31, 38, 46, 0.6) !important;
                color: #ffffff !important;
                border-color: rgba(129, 236, 255, 0.08);
            }
            
            section[data-testid="stSidebar"] div[data-testid="stRadio"] div[aria-checked="true"] label {
                background-color: rgba(129, 236, 255, 0.05) !important;
                border-color: rgba(129, 236, 255, 0.2) !important;
                color: #81ecff !important;
                font-weight: 600;
            }

            /* 6. Uploader styling */
            div[data-testid="stFileUploader"] {
                background-color: rgba(20, 26, 32, 0.4) !important;
                border: 1px dashed rgba(129, 236, 255, 0.1) !important;
                border-radius: 0.75rem !important;
                padding: 1rem !important;
            }
            div[data-testid="stFileUploader"] section {
                background: transparent !important;
                border: none !important;
            }
            div[data-testid="stFileUploader"] button {
                background: rgba(129, 236, 255, 0.1) !important;
                border: 1px solid rgba(129, 236, 255, 0.2) !important;
                color: #81ecff !important;
            }
        </style>
        """,
        unsafe_allow_html=True,
    )

def render_top_navbar():
    """Renders the top navigation bar matching Stitch layout."""
    html = """
    <header style="display: flex; align-items: center; justify-content: space-between; width: 100%; padding: 0 2rem; gap: 3rem; height: 4rem; position: sticky; top: 0; z-index: 50; background: rgba(10, 15, 20, 0.85); backdrop-filter: blur(16px); border-bottom: 1px solid rgba(255, 255, 255, 0.03);">
        <div style="display: flex; align-items: center; gap: 2rem; flex: 1;">
            <span style="font-size: 0.875rem; font-weight: bold; font-family: 'Manrope', sans-serif; letter-spacing: 0.3em; text-transform: uppercase; color: rgba(255,255,255,0.4);">Synthetic Platform</span>
            <div style="position: relative; width: 100%; max-width: 24rem;">
                <span class="material-symbols-outlined" style="position: absolute; left: 0.75rem; top: 50%; transform: translateY(-50%); color: #a7abb2; font-size: 1rem;">search</span>
                <input style="width: 100%; background: rgba(31, 38, 46, 0.3); border: 1px solid rgba(67, 72, 78, 0.1); border-radius: 9999px; padding: 0.375rem 1rem 0.375rem 2.5rem; font-size: 0.75rem; color: #white; outline: none;" placeholder="Search clusters..." type="text"/>
            </div>
        </div>
        <div style="display: flex; align-items: center; gap: 1.25rem;">
            <button style="width: 2rem; height: 2rem; display: flex; align-items: center; justify-content: center; color: #94a3b8; background: transparent; border: none; cursor: pointer; border-radius: 9999px;">
                <span class="material-symbols-outlined" style="font-size: 1.25rem;">dark_mode</span>
            </button>
            <button style="width: 2rem; height: 2rem; display: flex; align-items: center; justify-content: center; color: #94a3b8; background: transparent; border: none; cursor: pointer; border-radius: 9999px; position: relative;">
                <span class="material-symbols-outlined" style="font-size: 1.25rem;">notifications</span>
                <span style="position: absolute; top: 0.5rem; right: 0.5rem; width: 0.375rem; height: 0.375rem; background: #81ecff; border-radius: 9999px; box-shadow: 0 0 8px rgba(129, 236, 255, 0.6);"></span>
            </button>
            <div style="width: 2.25rem; height: 2.25rem; border-radius: 9999px; background: #1f262e; border: 1px solid rgba(255,255,255,0.1); overflow: hidden; display: flex; align-items: center; justify-content: center;">
                <img alt="User Avatar" style="width: 100%; height: 100%; object-fit: cover; border-radius: 9999px;" src="https://lh3.googleusercontent.com/aida-public/AB6AXuAcJQ7bi2mYCQqzLipd9KC43bZBYUMNuPibKHVevOGIOSXAjXAFq1oMxG8_fBK8QA378MTjGHeSdpK7zNSn00nu7SQKRacpTZ7kBNDabO9zP4oDZOrEWYMLjgrnKWp75jB5aSiVIQ6ObsIzO0TycyYrgJt9YFK74xdhc5NVNUuMLUlqA-u4phQsKs-sAvMLBOZ_VQ9sUkVf84IkkOfaUC-AyaRo6m9GoFppL_KdymNIpHmHpQ4FjL1E-Ia6WC4nPvzaYfPd00roMN0"/>
            </div>
        </div>
    </header>
    """
    st.markdown(html, unsafe_allow_html=True)

def render_sidebar_header():
    """Renders visual header for sidebar using Stitch template elements."""
    html = """
    <div class="mb-10 px-2">
        <div class="text-xl font-bold tracking-tighter text-[#81ecff] font-headline flex items-center gap-2">
            <span class="material-symbols-outlined text-[#81ecff] text-2xl font-bold">polymer</span>
            Luminal
        </div>
        <div class="text-[9px] uppercase tracking-[0.2em] text-[#a7abb2] font-label mt-1 opacity-70">Synthetic Engine</div>
    </div>
    """
    st.sidebar.markdown(html, unsafe_allow_html=True)

def sidebar_nav_links(active_section: str):
    """
    Renders clickable navigation items inside standard Streamlit sidebar,
    but customized style using CSS and HTML anchors rendered before elements.
    Wait, to allow Streamlit clicks, we must inject Streamlit buttons and style them,
    which we set up in setup_dashboard_styles().
    This function will render the headers or supporting labels if any.
    """
    pass

def render_page_header(title: str, subtitle: str):
    """Visual page header according to Stitch templates rules."""
    html = f"""
    <div class="mb-10 flex flex-col items-start gap-1">
        <h1 class="font-headline text-3xl font-extrabold tracking-tight text-white">{title}</h1>
        <p class="text-[#a7abb2] text-sm max-w-2xl font-body opacity-80 leading-relaxed">{subtitle}</p>
    </div>
    """
    st.markdown(html, unsafe_allow_html=True)
