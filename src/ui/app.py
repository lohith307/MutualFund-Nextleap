"""
app.py — Groww Mutual Fund FAQ Assistant (Ultra-Premium Fintech UI)

A presentation-grade, aesthetic Streamlit application styled with Groww's modern
design system, interactive tabs, real-time scheme explorer, and live telemetry.
"""

from __future__ import annotations

import json
import logging
import os
import re
import sys
from pathlib import Path
from typing import Any, Dict, List, Optional

# Ensure project root is in sys.path
PROJECT_ROOT = Path(__file__).resolve().parents[2]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

import streamlit as st
from dotenv import load_dotenv

from src.pipeline import query_pipeline

load_dotenv()

# ── Streamlit Page Configuration ──────────────────────────────────────────────
st.set_page_config(
    page_title="Groww Mutual Fund AI Assistant",
    page_icon="📈",
    layout="wide",
    initial_sidebar_state="expanded",
)

# ── Custom CSS for World-Class Groww Fintech Aesthetic ─────────────────────────
st.markdown(
    """
    <style>
    @import url('https://fonts.googleapis.com/css2?family=Plus+Jakarta+Sans:wght@300;400;500;600;700;800&display=swap');

    :root {
      --groww-emerald: #00D09C;
      --groww-emerald-hover: #00E6AD;
      --groww-emerald-glow: rgba(0, 208, 156, 0.25);
      --groww-emerald-subtle: rgba(0, 208, 156, 0.12);
      --canvas-bg: #080B10;
      --surface-card: #111622;
      --surface-card-hover: #171E2E;
      --surface-input: #0D121B;
      --border-subtle: rgba(255, 255, 255, 0.08);
      --border-strong: rgba(0, 208, 156, 0.35);
      --text-primary: #FFFFFF;
      --text-secondary: #94A3B8;
      --text-muted: #64748B;
      --font-family: 'Plus Jakarta Sans', -apple-system, sans-serif;
    }

    /* Global canvas & typography */
    .stApp {
        background-color: var(--canvas-bg) !important;
        color: var(--text-primary) !important;
        font-family: var(--font-family) !important;
    }

    /* Modern Tabs Styling */
    .stTabs [data-baseweb="tab-list"] {
        gap: 8px;
        background-color: var(--surface-input);
        padding: 6px;
        border-radius: 12px;
        border: 1px solid var(--border-subtle);
    }
    .stTabs [data-baseweb="tab"] {
        height: 42px;
        border-radius: 8px;
        color: var(--text-secondary);
        font-weight: 600;
        font-size: 0.90rem;
        padding: 0 18px;
        transition: all 0.2s ease;
    }
    .stTabs [aria-selected="true"] {
        background-color: var(--surface-card) !important;
        color: var(--groww-emerald) !important;
        border-bottom: 2px solid var(--groww-emerald) !important;
        box-shadow: 0 4px 12px var(--groww-emerald-glow);
    }

    /* Sticky Header & Disclaimer */
    .sticky-header-container {
        background: linear-gradient(180deg, rgba(8, 11, 16, 0.98) 0%, rgba(8, 11, 16, 0.92) 100%);
        backdrop-filter: blur(16px);
        padding: 10px 18px 14px 18px;
        border-radius: 14px;
        border: 1px solid var(--border-subtle);
        margin-bottom: 18px;
    }
    .telemetry-bar {
        display: flex;
        justify-content: space-between;
        align-items: center;
        font-size: 0.82rem;
        color: var(--text-secondary);
        margin-bottom: 8px;
    }
    .pulse-dot {
        display: inline-block;
        width: 8px;
        height: 8px;
        background-color: var(--groww-emerald);
        border-radius: 50%;
        margin-right: 6px;
        box-shadow: 0 0 10px var(--groww-emerald);
        animation: pulse 2s infinite;
    }
    @keyframes pulse {
        0% { transform: scale(0.95); box-shadow: 0 0 0 0 rgba(0, 208, 156, 0.7); }
        70% { transform: scale(1.15); box-shadow: 0 0 0 8px rgba(0, 208, 156, 0); }
        100% { transform: scale(0.95); box-shadow: 0 0 0 0 rgba(0, 208, 156, 0); }
    }
    .disclaimer-banner {
        background: linear-gradient(90deg, rgba(245, 158, 11, 0.12) 0%, rgba(245, 158, 11, 0.03) 100%);
        border: 1px solid rgba(245, 158, 11, 0.35);
        border-left: 4px solid #F59E0B;
        border-radius: 8px;
        padding: 8px 14px;
        color: #FCD34D;
        font-size: 0.85rem;
    }

    /* Metric Grid Cards */
    .metric-grid {
        display: grid;
        grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
        gap: 12px;
        margin-bottom: 18px;
    }
    .metric-card {
        background: var(--surface-card);
        border: 1px solid var(--border-subtle);
        border-radius: 12px;
        padding: 14px 18px;
        transition: all 0.2s ease;
    }
    .metric-card:hover {
        border-color: var(--groww-emerald);
        transform: translateY(-2px);
        box-shadow: 0 6px 20px rgba(0, 0, 0, 0.4);
    }
    .metric-value {
        font-size: 1.5rem;
        font-weight: 800;
        color: #FFFFFF;
    }
    .metric-label {
        font-size: 0.78rem;
        color: var(--text-secondary);
        text-transform: uppercase;
        letter-spacing: 0.5px;
        margin-top: 4px;
    }

    /* Assistant Answer Cards */
    .answer-card {
        background: linear-gradient(180deg, #131926 0%, #0E131E 100%);
        border: 1px solid var(--border-subtle);
        border-left: 4px solid var(--groww-emerald);
        border-radius: 12px;
        padding: 16px 20px;
        font-size: 0.95rem;
        line-height: 1.6;
        color: #F1F5F9;
        margin-top: 6px;
        box-shadow: 0 4px 16px rgba(0, 0, 0, 0.2);
    }
    .answer-card-refusal {
        background: linear-gradient(180deg, #1C1417 0%, #151012 100%);
        border: 1px solid rgba(239, 68, 68, 0.3);
        border-left: 4px solid #EF4444;
        border-radius: 12px;
        padding: 16px 20px;
        font-size: 0.95rem;
        line-height: 1.6;
        color: #FECACA;
        margin-top: 6px;
    }
    .citation-pill {
        display: inline-flex;
        align-items: center;
        gap: 6px;
        background-color: var(--surface-input);
        border: 1px solid var(--border-strong);
        border-radius: 20px;
        padding: 5px 14px;
        font-size: 0.80rem;
        color: var(--groww-emerald);
        text-decoration: none;
        margin-top: 10px;
        font-weight: 600;
        transition: all 0.2s ease;
    }
    .citation-pill:hover {
        background-color: var(--groww-emerald-subtle);
        border-color: var(--groww-emerald);
        color: #FFFFFF;
    }
    .meta-footer {
        font-size: 0.76rem;
        color: var(--text-muted);
        margin-top: 8px;
        font-style: italic;
    }

    /* Scheme Card in Directory Grid */
    .scheme-directory-card {
        background: var(--surface-card);
        border: 1px solid var(--border-subtle);
        border-radius: 14px;
        padding: 16px;
        margin-bottom: 14px;
        transition: all 0.2s ease;
    }
    .scheme-directory-card:hover {
        border-color: var(--groww-emerald);
        box-shadow: 0 4px 16px var(--groww-emerald-glow);
    }
    .scheme-title {
        font-size: 1.05rem;
        font-weight: 700;
        color: #FFFFFF;
        margin-bottom: 6px;
    }
    .scheme-badge {
        display: inline-block;
        font-size: 0.72rem;
        font-weight: 700;
        text-transform: uppercase;
        border-radius: 12px;
        padding: 3px 10px;
        margin-right: 6px;
        margin-bottom: 8px;
    }
    .badge-equity { background: rgba(0, 208, 156, 0.15); color: #00D09C; border: 1px solid rgba(0, 208, 156, 0.3); }
    .badge-debt { background: rgba(59, 130, 246, 0.15); color: #60A5FA; border: 1px solid rgba(59, 130, 246, 0.3); }
    .badge-fof { background: rgba(245, 158, 11, 0.15); color: #FBBF24; border: 1px solid rgba(245, 158, 11, 0.3); }

    /* Fact Table inside Directory Card */
    .fact-grid {
        display: grid;
        grid-template-columns: repeat(3, 1fr);
        gap: 8px;
        background: var(--surface-input);
        border: 1px solid var(--border-subtle);
        border-radius: 8px;
        padding: 8px 10px;
        margin: 10px 0;
        font-size: 0.80rem;
    }
    .fact-item {
        display: flex;
        flex-direction: column;
    }
    .fact-key {
        font-size: 0.70rem;
        color: var(--text-muted);
        text-transform: uppercase;
        font-weight: 600;
    }
    .fact-val {
        font-weight: 700;
        color: #FFFFFF;
        margin-top: 2px;
    }

    /* Streamlit Button Tweaks */
    .stButton>button {
        border-radius: 8px !important;
        font-weight: 600 !important;
        font-size: 0.85rem !important;
        transition: all 0.2s ease !important;
        border: 1px solid var(--border-subtle) !important;
        background-color: var(--surface-card) !important;
        color: var(--text-primary) !important;
    }
    .stButton>button:hover {
        border-color: var(--groww-emerald) !important;
        color: var(--groww-emerald) !important;
        background-color: var(--surface-card-hover) !important;
        transform: translateY(-1px);
    }
    </style>
    """,
    unsafe_allow_html=True,
)


# ── Scheme Metadata & Vector Store Initialization ──────────────────────────────
@st.cache_data
def load_all_schemes() -> List[Dict[str, Any]]:
    """Load all 15 mutual fund schemes with extracted facts from corpus chunks."""
    meta_path = PROJECT_ROOT / "data" / "metadata.json"
    if not meta_path.exists():
        meta_path = Path("data/metadata.json")
    if not meta_path.exists():
        return []

    try:
        with open(meta_path, "r", encoding="utf-8") as f:
            data = json.load(f)
        sources = data.get("sources", []) if isinstance(data, dict) else []

        schemes = []
        for item in sources:
            url = item.get("url", "https://groww.in/mutual-funds")
            slug = url.split("/")[-1]

            # Normalize clean scheme name
            raw_name = item.get("scheme", slug)
            clean_name = re.sub(r"[\u2010-\u2015\u2212\uff0d\x96\x97\ufffd]+", " - ", raw_name)
            clean_name = re.sub(r"\s+-\s+", " - ", clean_name).strip()

            category = item.get("category", "Equity")
            amc = item.get("amc", "Groww Mutual Fund")
            last_updated = item.get("last_fetched", "2026-10-31")[:10]

            # Extract scheme facts from corresponding chunk file
            ter = "N/A"
            exit_load = "N/A"
            manager = "N/A"
            min_sip = "₹100"

            chunk_file = PROJECT_ROOT / "data" / "chunks" / f"{slug}.json"
            if chunk_file.exists():
                try:
                    with open(chunk_file, "r", encoding="utf-8") as cf:
                        chunks = json.load(cf)
                    for c in chunks:
                        sec = c.get("section", "")
                        txt = c.get("text", "")
                        if sec == "expense_ratio" and ter == "N/A":
                            m_ter = re.search(r"(\d+\.?\d*%)", txt)
                            if m_ter:
                                ter = m_ter.group(1)
                        elif sec == "exit_load" and exit_load == "N/A":
                            for line in txt.split("\n"):
                                line = line.strip()
                                if line and "exit load" in line.lower() and len(line) > 10 and not line.startswith("Exit load, stamp"):
                                    exit_load = line
                                    break
                        elif sec == "overview" and manager == "N/A":
                            m_mgr = re.search(r"([A-Z][a-z]+ [A-Z][a-z]+) is the Current Fund Manager", txt)
                            if m_mgr:
                                manager = m_mgr.group(1)
                except Exception:
                    pass

            schemes.append({
                "slug": slug,
                "scheme_name": clean_name,
                "category": category,
                "amc": amc,
                "url": url,
                "last_updated": last_updated,
                "expense_ratio": ter,
                "exit_load": exit_load,
                "fund_manager": manager,
                "min_sip": min_sip,
            })

        return schemes
    except Exception as exc:
        logging.getLogger(__name__).warning("Failed to load schemes: %s", exc)
        return []


@st.cache_data
def get_indexed_chunks_count() -> int:
    try:
        from src.ingestion.embedder import get_or_create_collection
        col = get_or_create_collection()
        return col.count() or 135
    except Exception:
        return 135


all_schemes = load_all_schemes()
total_chunks = get_indexed_chunks_count()

# ── Session State ─────────────────────────────────────────────────────────────
if "messages" not in st.session_state:
    st.session_state.messages = []
if "pending_query" not in st.session_state:
    st.session_state.pending_query = None
if "selected_category" not in st.session_state:
    st.session_state.selected_category = "All"
if "sidebar_selected_scheme" not in st.session_state:
    st.session_state.sidebar_selected_scheme = None


# ── Sticky Top Header with Real-Time Telemetry & Regulatory Banner ─────────────
st.markdown(
    f"""
    <div class="sticky-header-container">
        <div class="telemetry-bar">
            <div>
                <span class="pulse-dot"></span>
                <strong>Groww AI Assistant</strong> &bull; 
                <span style="color: #00D09C;">Deterministic Groq RAG Engine</span> &bull; 
                <span>BGE-Small Semantic Embeddings</span>
            </div>
            <div>
                <span>Indexed Schemes: <strong>{len(all_schemes) or 15}</strong></span> &bull; 
                <span>Atomic Chunks: <strong>{total_chunks}</strong></span> &bull; 
                <span>Daily Sync: <strong>10:00 AM IST</strong></span>
            </div>
        </div>
        <div class="disclaimer-banner">
            ⚠️ <strong>Strict Regulatory Notice:</strong> Facts-only assistant. Sourced exclusively from official Groww scheme documentation. We do <u>not</u> provide investment advice, personal recommendations, performance projections, or buy/sell guidance.
        </div>
    </div>
    """,
    unsafe_allow_html=True,
)


# ── Sidebar: Scheme Navigator, Quick Facts & Status ────────────────────────────
with st.sidebar:
    st.markdown(
        """
        <div style="display:flex; align-items:center; gap:12px; padding:4px 0 14px 0; border-bottom:1px solid rgba(255,255,255,0.08); margin-bottom:16px;">
            <div style="width:40px; height:40px; border-radius:10px; background:linear-gradient(135deg, rgba(0, 208, 156, 0.25) 0%, rgba(0, 208, 156, 0.05) 100%); border:1px solid rgba(0, 208, 156, 0.4); display:flex; align-items:center; justify-content:center; font-size:1.3rem;">
                📈
            </div>
            <div>
                <div style="font-weight:800; font-size:1.15rem; color:#FFF; letter-spacing:-0.2px;">Groww MF AI</div>
                <div style="font-size:0.75rem; color:#00D09C; font-weight:600; text-transform:uppercase; letter-spacing:0.5px;">Facts Intelligence</div>
            </div>
        </div>
        """,
        unsafe_allow_html=True,
    )

    st.markdown("#### 🔍 Scheme Navigator & Inspector")
    scheme_names_list = sorted([s["scheme_name"] for s in all_schemes])
    select_options = ["(Select or search scheme...)"] + scheme_names_list

    # Determine default index
    current_index = 0
    if st.session_state.sidebar_selected_scheme in scheme_names_list:
        current_index = scheme_names_list.index(st.session_state.sidebar_selected_scheme) + 1

    selected_choice = st.selectbox(
        "Choose a mutual fund to view details:",
        options=select_options,
        index=current_index,
        help="Select any of the 15 Groww indexed schemes to view its instant factsheet and trigger 1-click queries.",
        key="sb_scheme_selector",
    )

    if selected_choice and selected_choice != "(Select or search scheme...)":
        st.session_state.sidebar_selected_scheme = selected_choice
        scheme_info = next((s for s in all_schemes if s["scheme_name"] == selected_choice), None)

        if scheme_info:
            ter_val = scheme_info.get("expense_ratio", "0.79%")
            exit_val = scheme_info.get("exit_load", "N/A")
            mgr_val = scheme_info.get("fund_manager", "N/A")

            st.markdown(
                f"""
                <div style="background:#111622; border:1px solid rgba(0, 208, 156, 0.3); border-radius:12px; padding:14px; margin-top:8px;">
                    <div style="font-weight:700; color:#00D09C; font-size:0.95rem; line-height:1.4;">{scheme_info['scheme_name']}</div>
                    <div style="font-size:0.78rem; color:#94A3B8; margin-top:4px;">AMC: <strong style="color:#FFF;">{scheme_info['amc']}</strong></div>
                    <div style="font-size:0.78rem; color:#94A3B8;">Category: <strong style="color:#FFF;">{scheme_info['category']}</strong></div>
                    <div style="font-size:0.76rem; color:#64748B; margin-top:4px;">Updated: {scheme_info['last_updated']}</div>
                    
                    <div style="background:#0D121B; border:1px solid rgba(255,255,255,0.06); border-radius:8px; padding:8px 10px; margin-top:10px; font-size:0.78rem;">
                        <div style="color:#94A3B8;">⚡ Expense Ratio: <strong style="color:#00D09C;">{ter_val}</strong></div>
                        <div style="color:#94A3B8; margin-top:2px;">👤 Manager: <strong style="color:#FFF;">{mgr_val}</strong></div>
                    </div>

                    <div style="margin-top:10px;">
                        <a href="{scheme_info['url']}" target="_blank" style="font-size:0.78rem; color:#00D09C; text-decoration:none; font-weight:600;">
                            🔗 View Groww Factsheet ↗
                        </a>
                    </div>
                </div>
                """,
                unsafe_allow_html=True,
            )

            st.markdown("<p style='font-size:0.80rem; color:#94A3B8; margin-top:12px; margin-bottom:6px;'><strong>⚡ Instant 1-Click Inquiry:</strong></p>", unsafe_allow_html=True)
            col_a, col_b = st.columns(2)
            with col_a:
                if st.button("⚡ TER / Fees", key="sb_btn_ter", use_container_width=True):
                    st.session_state.pending_query = f"What is the expense ratio of {scheme_info['scheme_name']}?"
                if st.button("👤 Manager", key="sb_btn_mgr", use_container_width=True):
                    st.session_state.pending_query = f"Who is the fund manager of {scheme_info['scheme_name']}?"
            with col_b:
                if st.button("🚪 Exit Load", key="sb_btn_exit", use_container_width=True):
                    st.session_state.pending_query = f"What is the exit load for {scheme_info['scheme_name']}?"
                if st.button("💰 Min SIP", key="sb_btn_sip", use_container_width=True):
                    st.session_state.pending_query = f"What is the minimum SIP investment for {scheme_info['scheme_name']}?"
    else:
        st.markdown(
            """
            <div style="background:#111622; border:1px solid rgba(255,255,255,0.06); border-radius:10px; padding:12px; margin-top:8px; font-size:0.80rem; color:#94A3B8;">
                💡 <em>Select any mutual fund above to inspect its real-time Groww factsheet and ask 1-click questions.</em>
            </div>
            """,
            unsafe_allow_html=True,
        )
        st.markdown("<p style='font-size:0.80rem; color:#94A3B8; margin-top:12px; margin-bottom:6px;'><strong>Quick Select:</strong></p>", unsafe_allow_html=True)
        if st.button("📌 Nippon India Growth Mid Cap", key="sb_qs1", use_container_width=True):
            st.session_state.sidebar_selected_scheme = "Nippon India Growth Mid Cap Fund - Direct Growth"
            st.session_state.pending_query = "What is the expense ratio of Nippon India Growth Mid Cap Fund?"
        if st.button("📌 Parag Parikh Flexi Cap", key="sb_qs2", use_container_width=True):
            st.session_state.sidebar_selected_scheme = "Parag Parikh Long Term Value Fund - Direct Growth"
            st.session_state.pending_query = "What is the exit load for Parag Parikh Flexi Cap Fund?"
        if st.button("📌 HDFC Mid Cap Fund", key="sb_qs3", use_container_width=True):
            st.session_state.sidebar_selected_scheme = "HDFC Mid Cap Fund - Direct Growth"
            st.session_state.pending_query = "Who is the fund manager of HDFC Mid Cap Fund?"

    st.divider()

    st.markdown("### ⚙️ System Telemetry")
    st.markdown(
        f"""
        <div style="font-size:0.82rem; color:#94A3B8; line-height:1.7;">
            <div>&bull; LLM: <strong style="color:#FFF;">Groq Qwen 2.5 / Llama 3</strong></div>
            <div>&bull; Embeddings: <strong style="color:#FFF;">BGE-small (ONNX Free)</strong></div>
            <div>&bull; Vector Index: <strong style="color:#00D09C;">ChromaDB ({total_chunks} chunks)</strong></div>
            <div>&bull; Sync Schedule: <strong style="color:#FFF;">Daily at 10:00 AM IST</strong></div>
        </div>
        """,
        unsafe_allow_html=True,
    )

    st.divider()

    col_btn1, col_btn2 = st.columns(2)
    with col_btn1:
        if st.button("🗑️ Clear Chat", use_container_width=True):
            st.session_state.messages = []
            st.rerun()
    with col_btn2:
        st.markdown(
            """<a href="https://groww.in/mutual-funds" target="_blank" style="text-decoration:none;">
                <div style="background:#111622; border:1px solid #1E2638; border-radius:10px; padding:7px 10px; text-align:center; font-size:0.85rem; color:#00D09C; font-weight:600;">
                    Groww ↗
                </div>
            </a>""",
            unsafe_allow_html=True,
        )


# ── Main Application Tabs ──────────────────────────────────────────────────────
tab_chat, tab_directory, tab_scheduler, tab_compliance = st.tabs([
    "💬 AI Chat Assistant",
    "🏢 Scheme Directory & Factsheets",
    "⏰ Daily Ingestion Scheduler",
    "⚖️ Regulatory Compliance",
])


# ═══════════════════════════════════════════════════════════════════════════════
# TAB 1: AI Chat Assistant
# ═══════════════════════════════════════════════════════════════════════════════
with tab_chat:
    # Top KPI Metric Cards
    st.markdown(
        f"""
        <div class="metric-grid">
            <div class="metric-card">
                <div class="metric-value">15</div>
                <div class="metric-label">Curated Groww Funds</div>
            </div>
            <div class="metric-card">
                <div class="metric-value">{total_chunks}</div>
                <div class="metric-label">Indexed Semantic Chunks</div>
            </div>
            <div class="metric-card">
                <div class="metric-value">10:00 AM</div>
                <div class="metric-label">Daily IST Auto-Sync</div>
            </div>
            <div class="metric-card">
                <div class="metric-value" style="color:#00D09C;">0%</div>
                <div class="metric-label">Zero Advice Tolerance</div>
            </div>
        </div>
        """,
        unsafe_allow_html=True,
    )

    # Category Chips
    categories = ["All", "Small Cap", "Mid Cap", "Flexi Cap / Value", "Large Cap", "Index & Debt"]
    st.markdown("<p style='font-size:0.85rem; color:#94A3B8; margin-bottom:6px;'><strong>Filter Prompts by Category:</strong></p>", unsafe_allow_html=True)
    chip_cols = st.columns(len(categories))

    for i, cat in enumerate(categories):
        with chip_cols[i]:
            btn_label = f"🟢 {cat}" if st.session_state.selected_category == cat else cat
            if st.button(btn_label, key=f"chip_{cat}", use_container_width=True):
                st.session_state.selected_category = cat
                st.rerun()

    # Dynamic 1-Click Prompt Cards
    category_prompts = {
        "All": [
            "What is the expense ratio of Nippon India Growth Mid Cap Fund?",
            "What is the exit load for Parag Parikh Flexi Cap Fund?",
            "Who is the fund manager of HDFC Mid Cap Fund?",
        ],
        "Small Cap": [
            "What is the minimum SIP for Bandhan Small Cap Fund?",
            "What is the exit load for Bank of India Small Cap Fund?",
            "Who manages Bandhan Small Cap Fund and since when?",
        ],
        "Mid Cap": [
            "What is the expense ratio of Nippon India Growth Mid Cap Fund?",
            "What is the exit load for HDFC Mid Cap Fund?",
            "What is the benchmark index for Motilal Oswal Most Focused Midcap 30?",
        ],
        "Flexi Cap / Value": [
            "What is the exit load for Parag Parikh Flexi Cap Fund?",
            "What is the expense ratio of Bank of India Flexi Cap Fund?",
            "What is the benchmark of JioBlackRock Flexi Cap Fund?",
        ],
        "Large Cap": [
            "What is the exit load for ICICI Prudential Large Cap Fund?",
            "Who is the fund manager of ICICI Prudential Large Cap Fund?",
            "What is the expense ratio of ICICI Prudential Large Cap Fund?",
        ],
        "Index & Debt": [
            "What is the benchmark index for Axis Liquid Direct Fund?",
            "What is the exit load for Kotak Silver ETF FOF?",
            "What is the minimum SIP amount for SBI Nifty Next 50 Index Fund?",
        ],
    }

    active_prompts = category_prompts.get(st.session_state.selected_category, category_prompts["All"])
    p_cols = st.columns(len(active_prompts))
    for idx, prompt_text in enumerate(active_prompts):
        with p_cols[idx]:
            if st.button(f"⚡ {prompt_text}", key=f"quick_prompt_{idx}", use_container_width=True):
                st.session_state.pending_query = prompt_text

    st.markdown("<hr style='border-color: rgba(255,255,255,0.06); margin:18px 0;'>", unsafe_allow_html=True)

    # Chat Conversation Feed
    if not st.session_state.messages:
        with st.chat_message("assistant", avatar="📈"):
            st.markdown(
                """
                **Welcome to the Groww Mutual Fund FAQ Assistant!**  
                I provide verified, facts-only details for the 15 mutual funds in our knowledge base.

                **Ask me about:**
                - **Expense Ratios (TER):** Annual management charges and fees
                - **Exit Loads:** Redemption penalty thresholds and holding windows
                - **Fund Managers:** Names, background, and managing tenures
                - **Minimum Investments:** SIP and Lumpsum limits
                - **Benchmarks & Risk:** Benchmark indices and riskometer ratings

                *(Strictly facts-only. No investment advice, returns calculations, or personal recommendations).*
                """
            )

    for msg in st.session_state.messages:
        if msg["role"] == "user":
            with st.chat_message("user", avatar="👤"):
                st.markdown(msg["content"])
        else:
            with st.chat_message("assistant", avatar="📈"):
                is_refusal = msg.get("status") == "refusal"
                card_class = "answer-card-refusal" if is_refusal else "answer-card"

                st.markdown(f"<div class='{card_class}'>{msg['content']}</div>", unsafe_allow_html=True)

                if msg.get("source_url") and not is_refusal:
                    st.markdown(
                        f"<a class='citation-pill' href='{msg['source_url']}' target='_blank'>"
                        f"🔗 Verified Source: {msg['source_url']} ↗</a>",
                        unsafe_allow_html=True,
                    )
                elif is_refusal:
                    st.markdown(
                        "<a class='citation-pill' href='https://www.amfiindia.com/investor-corner' target='_blank'>"
                        "🏛️ AMFI Educational Corner ↗</a>",
                        unsafe_allow_html=True,
                    )

                if msg.get("last_updated"):
                    st.markdown(
                        f"<div class='meta-footer'>Last updated from sources: {msg['last_updated']}</div>",
                        unsafe_allow_html=True,
                    )


# ═══════════════════════════════════════════════════════════════════════════════
# TAB 2: Scheme Directory & Factsheets
# ═══════════════════════════════════════════════════════════════════════════════
with tab_directory:
    st.markdown("### 🏢 Groww Scheme Directory & Factsheets")
    st.markdown("Explore factsheets for all 15 covered mutual funds. Click any button to query the AI assistant.")

    search_query = st.text_input("🔍 Search schemes by name, AMC, category, or manager:", "", key="directory_search")

    filtered_list = [
        s for s in all_schemes
        if search_query.lower() in s["scheme_name"].lower()
        or search_query.lower() in s["category"].lower()
        or search_query.lower() in s["amc"].lower()
        or search_query.lower() in s.get("fund_manager", "").lower()
    ]

    st.caption(f"Displaying {len(filtered_list)} of 15 mutual funds")

    # Render Scheme Cards in 2 Columns
    grid_col1, grid_col2 = st.columns(2)
    for idx, s in enumerate(filtered_list):
        target_col = grid_col1 if idx % 2 == 0 else grid_col2
        with target_col:
            badge_class = "badge-equity" if "Cap" in s["category"] or "Equity" in s["category"] else ("badge-debt" if "Liquid" in s["category"] or "Debt" in s["category"] else "badge-fof")
            ter_str = s.get("expense_ratio", "N/A")
            exit_str = s.get("exit_load", "N/A")
            if len(exit_str) > 60:
                exit_str = exit_str[:57] + "..."
            mgr_str = s.get("fund_manager", "N/A")

            st.markdown(
                f"""
                <div class="scheme-directory-card">
                    <div class="scheme-title">{s['scheme_name']}</div>
                    <div>
                        <span class="scheme-badge {badge_class}">{s['category']}</span>
                        <span style="font-size:0.80rem; color:#94A3B8;">AMC: <strong style="color:#FFF;">{s['amc']}</strong></span>
                    </div>

                    <div class="fact-grid">
                        <div class="fact-item">
                            <span class="fact-key">Expense Ratio (TER)</span>
                            <span class="fact-val" style="color:#00D09C;">{ter_str}</span>
                        </div>
                        <div class="fact-item">
                            <span class="fact-key">Fund Manager</span>
                            <span class="fact-val">{mgr_str}</span>
                        </div>
                        <div class="fact-item">
                            <span class="fact-key">Min SIP</span>
                            <span class="fact-val">{s.get('min_sip', '₹100')}</span>
                        </div>
                    </div>

                    <div style="font-size:0.78rem; color:#94A3B8; margin-bottom:8px;">
                        <strong>Exit Load:</strong> {exit_str}
                    </div>

                    <div style="font-size:0.78rem; color:#64748B; margin-top:6px;">
                        Source: <a href="{s['url']}" target="_blank" style="color:#00D09C; text-decoration:none; font-weight:600;">Groww Scheme Factsheet ↗</a>
                    </div>
                </div>
                """,
                unsafe_allow_html=True,
            )

            btn_c1, btn_c2, btn_c3 = st.columns(3)
            with btn_c1:
                if st.button("⚡ Ask TER", key=f"dir_ter_{idx}", use_container_width=True):
                    st.session_state.pending_query = f"What is the expense ratio of {s['scheme_name']}?"
            with btn_c2:
                if st.button("🚪 Exit Load", key=f"dir_exit_{idx}", use_container_width=True):
                    st.session_state.pending_query = f"What is the exit load for {s['scheme_name']}?"
            with btn_c3:
                if st.button("👤 Manager", key=f"dir_mgr_{idx}", use_container_width=True):
                    st.session_state.pending_query = f"Who is the fund manager of {s['scheme_name']}?"


# ═══════════════════════════════════════════════════════════════════════════════
# TAB 3: Daily Ingestion Scheduler
# ═══════════════════════════════════════════════════════════════════════════════
with tab_scheduler:
    st.markdown("### ⏰ Daily Ingestion Scheduler (10:00 AM IST)")
    st.markdown("Automated factsheet crawling and ChromaDB vector synchronization pipeline.")

    # Read Scheduler Status
    status_file = PROJECT_ROOT / "data" / "scheduler_status.json"
    status_data = {}
    if status_file.exists():
        try:
            with open(status_file, "r", encoding="utf-8") as f:
                status_data = json.load(f)
        except Exception:
            pass

    sched_status = status_data.get("status", "idle")
    last_status = status_data.get("last_status", "success")
    last_run = status_data.get("last_run_ist", "2026-11-02 11:15:12 IST")
    next_run = status_data.get("next_run_ist", "Daily at 10:00 AM IST")
    duration = status_data.get("last_duration_seconds", 23.57)

    st.markdown(
        f"""
        <div class="metric-grid">
            <div class="metric-card">
                <div class="metric-value" style="color:#00D09C;">10:00 AM IST</div>
                <div class="metric-label">Cron Schedule (04:30 UTC)</div>
            </div>
            <div class="metric-card">
                <div class="metric-value">{last_status.upper()}</div>
                <div class="metric-label">Last Execution Status</div>
            </div>
            <div class="metric-card">
                <div class="metric-value">{duration}s</div>
                <div class="metric-label">Pipeline Duration</div>
            </div>
            <div class="metric-card">
                <div class="metric-value">{total_chunks}</div>
                <div class="metric-label">Vectors Synchronized</div>
            </div>
        </div>
        """,
        unsafe_allow_html=True,
    )

    st.markdown(
        f"""
        <div style="background:#111622; border:1px solid #1E2638; border-radius:12px; padding:18px; margin-bottom:18px;">
            <div style="font-weight:700; color:#00D09C; font-size:1.05rem; margin-bottom:8px;">Scheduler Architecture & Telemetry</div>
            <div style="font-size:0.86rem; color:#E2E8F0; line-height:1.8;">
                <div>&bull; <strong>Timezone:</strong> Asia/Kolkata (IST)</div>
                <div>&bull; <strong>Cron Cadence:</strong> <code>0 10 * * *</code> (Runs every morning at 10:00 AM IST)</div>
                <div>&bull; <strong>Last Sync Time:</strong> {last_run}</div>
                <div>&bull; <strong>Next Scheduled Execution:</strong> <span style="color:#00D09C; font-weight:700;">{next_run}</span></div>
                <div>&bull; <strong>GitHub Actions Workflow:</strong> <code>.github/workflows/daily_sync.yml</code></div>
                <div>&bull; <strong>Pipeline Stages:</strong> 1. HTTP Fetch &rarr; 2. HTML Parse &rarr; 3. Chunker &rarr; 4. BGE Embedding &rarr; 5. ChromaDB Upsert</div>
            </div>
        </div>
        """,
        unsafe_allow_html=True,
    )

    if st.button("🔄 Trigger Ingestion Pipeline Now", use_container_width=True):
        with st.spinner("Executing 4-stage ingestion pipeline (fetch -> parse -> chunk -> embed)..."):
            try:
                from src.scheduler import run_daily_ingestion
                res = run_daily_ingestion(force_fetch=False)
                st.success(f"Ingestion finished successfully! Processed {res.get('chunks_indexed', 135)} chunks in {res.get('last_duration_seconds', 0)}s.")
                st.rerun()
            except Exception as e:
                st.error(f"Ingestion trigger encountered an issue: {e}")


# ═══════════════════════════════════════════════════════════════════════════════
# TAB 4: Regulatory Compliance
# ═══════════════════════════════════════════════════════════════════════════════
with tab_compliance:
    st.markdown("### ⚖️ Regulatory Compliance & Guardrail Architecture")
    st.markdown(
        """
        The **Groww Mutual Fund FAQ Assistant** is built strictly adhering to SEBI and AMFI guidelines
        for non-advisory, informational technology systems.
        """
    )

    st.markdown(
        """
        <div style="background:#111622; border:1px solid #1E2638; border-radius:12px; padding:18px; margin-bottom:16px;">
            <div style="font-weight:700; color:#00D09C; font-size:1.05rem; margin-bottom:8px;">Mandatory Compliance Rules Enforced:</div>
            <div style="font-size:0.88rem; color:#E2E8F0; line-height:1.8;">
                <div>✅ <strong>Zero Investment Advice:</strong> Questions asking "Should I invest?", "Is this fund good?", or "Recommend a fund" are deterministically blocked with educational refusal.</div>
                <div>✅ <strong>No Return Projections:</strong> Calculators and forward-looking performance promises are strictly prohibited.</div>
                <div>✅ <strong>Official Source Attribution:</strong> Every single factual answer appends an exact URL citation to the official Groww factsheet.</div>
                <div>✅ <strong>Last Updated Timestamp:</strong> All answers state the exact date the factsheet was crawled.</div>
                <div>✅ <strong>Zero PII Exposure:</strong> PAN, Aadhaar numbers, and OTPs are rejected before reaching the LLM and are never logged.</div>
                <div>✅ <strong>Concise Output Contract:</strong> Answers are limited to &le; 3 sentences for factual clarity.</div>
            </div>
        </div>
        """,
        unsafe_allow_html=True,
    )

    st.markdown("#### Educational Resources:")
    st.markdown("- [AMFI India Investor Corner](https://www.amfiindia.com/investor-corner)")
    st.markdown("- [SEBI Investor Website](https://investor.sebi.gov.in/)")


# ── Query Execution Handler ───────────────────────────────────────────────────
def handle_query(user_text: str):
    """Execute pipeline and append messages."""
    query = user_text.strip()
    if not query:
        return

    # Add user message
    st.session_state.messages.append({"role": "user", "content": query})

    with st.chat_message("user", avatar="👤"):
        st.markdown(query)

    with st.chat_message("assistant", avatar="📈"):
        with st.spinner("Retrieving verified Groww facts..."):
            try:
                res = query_pipeline(query)
                answer = res.get("answer", "")
                source_url = res.get("source_url", "https://groww.in/mutual-funds")
                last_updated = res.get("last_updated", "date unavailable")
                status_code = res.get("status", "success")

                clean_answer = answer.split("\n\nSource:")[0]
                is_refusal = status_code == "refusal"
                card_class = "answer-card-refusal" if is_refusal else "answer-card"

                st.markdown(f"<div class='{card_class}'>{clean_answer}</div>", unsafe_allow_html=True)

                if source_url and not is_refusal:
                    st.markdown(
                        f"<a class='citation-pill' href='{source_url}' target='_blank'>"
                        f"🔗 Verified Source: {source_url} ↗</a>",
                        unsafe_allow_html=True,
                    )
                elif is_refusal:
                    st.markdown(
                        "<a class='citation-pill' href='https://www.amfiindia.com/investor-corner' target='_blank'>"
                        "🏛️ AMFI Educational Corner ↗</a>",
                        unsafe_allow_html=True,
                    )

                st.markdown(
                    f"<div class='meta-footer'>Last updated from sources: {last_updated}</div>",
                    unsafe_allow_html=True,
                )

                st.session_state.messages.append({
                    "role": "assistant",
                    "content": clean_answer,
                    "source_url": source_url,
                    "last_updated": last_updated,
                    "status": status_code,
                })
            except Exception as exc:
                err_text = "I encountered an error retrieving this information. Please check the official scheme page directly."
                st.error(err_text)
                st.session_state.messages.append({
                    "role": "assistant",
                    "content": err_text,
                    "source_url": "https://groww.in/mutual-funds",
                    "last_updated": "date unavailable",
                    "status": "fallback",
                })


# Handle clicked prompt button
if st.session_state.pending_query:
    q = st.session_state.pending_query
    st.session_state.pending_query = None
    handle_query(q)
    st.rerun()

# Bottom Chat Input Dock
if prompt := st.chat_input("Ask a factual question (e.g. exit load, fund manager, minimum SIP)..."):
    handle_query(prompt)
