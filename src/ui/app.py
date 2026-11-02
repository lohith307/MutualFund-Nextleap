"""
app.py — Groww Mutual Fund FAQ Assistant (Phase 6 Stitch UI)

Ultra-premium, Stitch-grade Streamlit application styled with Groww's official
design system:
  - Brand Palette: Groww Emerald (#00D09C), Obsidian Dark (#0B0E14), Elevated Slate (#151B26)
  - Typography: Plus Jakarta Sans with crisp visual hierarchy
  - Sticky Navigation Bar: Live telemetry pulse + regulatory disclaimer banner
  - Interactive Scheme Category Filter Chips (All, Small Cap, Mid Cap, Large Cap, Flexi Cap, Index/Debt)
  - 1-Click Quick Example Prompt Cards
  - Conversational message thread with verified citation cards and timestamp badges
  - Real-time searchable scheme directory in the sidebar

Run with:
  streamlit run src/ui/app.py
"""

from __future__ import annotations

import json
import logging
import os
import sys
from pathlib import Path
from typing import Any, Dict, List, Optional

# Ensure project root is in sys.path when running on Streamlit Cloud or subdirectories
PROJECT_ROOT = Path(__file__).resolve().parents[2]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

import streamlit as st
from dotenv import load_dotenv

from src.pipeline import query_pipeline

load_dotenv()

# ── Streamlit Page Configuration ──────────────────────────────────────────────
st.set_page_config(
    page_title="Groww MF Assistant — Facts-Only RAG",
    page_icon="📈",
    layout="wide",
    initial_sidebar_state="expanded",
)

# ── Custom CSS for Stitch-Grade Groww Design System ───────────────────────────
st.markdown(
    """
    <style>
    @import url('https://fonts.googleapis.com/css2?family=Plus+Jakarta+Sans:wght@400;500;600;700;800&display=swap');

    :root {
      --groww-emerald: #00D09C;
      --groww-emerald-glow: rgba(0, 208, 156, 0.25);
      --groww-emerald-subtle: rgba(0, 208, 156, 0.10);
      --canvas-bg: #0B0E14;
      --surface-card: #151B26;
      --surface-card-hover: #1C2331;
      --surface-input: #121721;
      --border-subtle: rgba(255, 255, 255, 0.08);
      --border-strong: rgba(255, 255, 255, 0.16);
      --text-primary: #FFFFFF;
      --text-secondary: #94A3B8;
      --text-muted: #64748B;
      --font-family: 'Plus Jakarta Sans', -apple-system, BlinkMacSystemFont, sans-serif;
    }

    /* Global canvas */
    .stApp {
        background-color: var(--canvas-bg) !important;
        color: var(--text-primary) !important;
        font-family: var(--font-family) !important;
    }

    /* Fixed Sticky Regulatory Disclaimer Banner */
    .sticky-header-container {
        position: sticky;
        top: 0;
        z-index: 999;
        background-color: rgba(11, 14, 20, 0.95);
        backdrop-filter: blur(12px);
        padding: 6px 0 14px 0;
        border-bottom: 1px solid var(--border-subtle);
        margin-bottom: 20px;
    }

    .telemetry-bar {
        display: flex;
        justify-content: space-between;
        align-items: center;
        padding: 4px 12px;
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
        box-shadow: 0 0 8px var(--groww-emerald);
        animation: pulse 2s infinite;
    }

    @keyframes pulse {
        0% { transform: scale(0.95); box-shadow: 0 0 0 0 rgba(0, 208, 156, 0.7); }
        70% { transform: scale(1.1); box-shadow: 0 0 0 6px rgba(0, 208, 156, 0); }
        100% { transform: scale(0.95); box-shadow: 0 0 0 0 rgba(0, 208, 156, 0); }
    }

    .disclaimer-banner {
        background: linear-gradient(90deg, rgba(245, 158, 11, 0.12) 0%, rgba(245, 158, 11, 0.05) 100%);
        border: 1px solid rgba(245, 158, 11, 0.35);
        border-left: 4px solid #F59E0B;
        border-radius: 8px;
        padding: 10px 16px;
        color: #FCD34D;
        font-size: 0.88rem;
        line-height: 1.4;
    }

    /* Hero Branding */
    .hero-container {
        text-align: left;
        padding: 10px 0 20px 0;
    }
    .hero-title {
        font-size: 2.2rem;
        font-weight: 800;
        letter-spacing: -0.5px;
        color: #FFFFFF;
        display: flex;
        align-items: center;
        gap: 12px;
    }
    .hero-badge {
        font-size: 0.75rem;
        font-weight: 700;
        text-transform: uppercase;
        background-color: var(--groww-emerald-subtle);
        color: var(--groww-emerald);
        border: 1px solid var(--groww-emerald);
        border-radius: 20px;
        padding: 3px 10px;
        letter-spacing: 0.8px;
    }
    .hero-subtitle {
        color: var(--text-secondary);
        font-size: 1.0rem;
        margin-top: 4px;
        font-weight: 400;
    }

    /* Card styling for Assistant Answers */
    .answer-card {
        background-color: var(--surface-card);
        border: 1px solid var(--border-subtle);
        border-radius: 12px;
        padding: 18px 20px;
        margin-top: 6px;
        box-shadow: 0 4px 12px rgba(0, 0, 0, 0.2);
    }
    .answer-card-refusal {
        background-color: rgba(239, 68, 68, 0.06);
        border: 1px solid rgba(239, 68, 68, 0.3);
        border-left: 4px solid #EF4444;
        border-radius: 12px;
        padding: 18px 20px;
        margin-top: 6px;
    }

    .citation-pill {
        display: inline-flex;
        align-items: center;
        gap: 6px;
        background-color: var(--surface-input);
        border: 1px solid var(--border-strong);
        border-radius: 20px;
        padding: 4px 12px;
        font-size: 0.82rem;
        color: var(--groww-emerald);
        text-decoration: none;
        margin-top: 10px;
        font-weight: 600;
    }
    .citation-pill:hover {
        background-color: var(--surface-card-hover);
        border-color: var(--groww-emerald);
    }

    .meta-footer {
        font-size: 0.78rem;
        color: var(--text-muted);
        margin-top: 8px;
        font-style: italic;
    }

    /* Sidebar aesthetics */
    [data-testid="stSidebar"] {
        background-color: #0F131C !important;
        border-right: 1px solid var(--border-subtle) !important;
    }

    /* Buttons */
    .stButton>button {
        background-color: var(--surface-card) !important;
        color: var(--text-primary) !important;
        border: 1px solid var(--border-subtle) !important;
        border-radius: 10px !important;
        font-weight: 500 !important;
        font-size: 0.88rem !important;
        transition: all 0.2s ease !important;
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


# ── Scheme Metadata Loading ───────────────────────────────────────────────────
@st.cache_data
def load_all_schemes() -> List[Dict[str, str]]:
    meta_path = PROJECT_ROOT / "data" / "metadata.json"
    if not meta_path.exists():
        meta_path = Path("data/metadata.json")
    if not meta_path.exists():
        return []
    try:
        with open(meta_path, "r", encoding="utf-8") as f:
            data = json.load(f)
        sources = data.get("sources", []) if isinstance(data, dict) else []
        return [
            {
                "url": item.get("url", "https://groww.in/mutual-funds"),
                "scheme_name": item.get("scheme", "Unknown Scheme"),
                "category": item.get("category", "Equity"),
                "last_updated": item.get("last_fetched", "date unavailable"),
                "amc": item.get("amc", "Groww Mutual Fund"),
            }
            for item in sources
        ]
    except Exception:
        return []


all_schemes = load_all_schemes()

# ── Session State Initialization ──────────────────────────────────────────────
if "messages" not in st.session_state:
    st.session_state.messages = []

if "pending_query" not in st.session_state:
    st.session_state.pending_query = None

if "selected_category" not in st.session_state:
    st.session_state.selected_category = "All"


# ── Sticky Top Header with Telemetry & Regulatory Banner ───────────────────────
st.markdown(
    """
    <div class="sticky-header-container">
        <div class="telemetry-bar">
            <div>
                <span class="pulse-dot"></span>
                <strong>Groq Llama-3.3-70B</strong> (Ultra-Fast Deterministic) &bull; 
                <span style="color: #00D09C;">BGE-small ONNX</span> Semantic Search
            </div>
            <div>
                <span>Indexed Schemes: <strong>15</strong></span> &bull; 
                <span>Atomic Chunks: <strong>135</strong></span> &bull; 
                <span>Daily Sync: <strong>10:00 AM IST</strong></span>
            </div>
        </div>
        <div class="disclaimer-banner">
            ⚠️ <strong>Strict Regulatory Notice:</strong> Facts-only assistant. We do <u>not</u> provide investment advice, personal recommendations, performance projections, or buy/sell guidance. Sourced exclusively from official Groww scheme documentation.
        </div>
    </div>
    """,
    unsafe_allow_html=True,
)

# ── Hero Branding ─────────────────────────────────────────────────────────────
st.markdown(
    """
    <div class="hero-container">
        <div class="hero-title">
            <span>📈 Groww MF Assistant</span>
            <span class="hero-badge">Facts-Only RAG</span>
        </div>
        <div class="hero-subtitle">
            Get instant, verifiable answers on Expense Ratios (TER), Exit Loads, Minimum SIPs, Fund Managers, and Riskometers across 15 popular mutual fund schemes.
        </div>
    </div>
    """,
    unsafe_allow_html=True,
)


# ── Category Filter Chips ─────────────────────────────────────────────────────
categories = ["All", "Small Cap", "Mid Cap", "Flexi Cap / Value", "Large Cap", "Index & Debt"]
st.write("**Filter by Category:**")
chip_cols = st.columns(len(categories))

for i, cat in enumerate(categories):
    with chip_cols[i]:
        btn_label = f"🟢 {cat}" if st.session_state.selected_category == cat else cat
        if st.button(btn_label, key=f"chip_{cat}", use_container_width=True):
            st.session_state.selected_category = cat
            st.rerun()

# ── Dynamic Quick Prompt Cards based on Category ──────────────────────────────
category_prompts = {
    "All": [
        "What is the exit load for Parag Parikh Flexi Cap Fund?",
        "What is the exit load for HDFC Mid Cap Fund?",
        "Who is the fund manager of Nippon India Growth Mid Cap Fund?",
    ],
    "Small Cap": [
        "What is the minimum SIP for Bandhan Small Cap Fund?",
        "What is the exit load for Bank of India Small Cap Fund?",
        "Who manages Bandhan Small Cap Fund and since when?",
    ],
    "Mid Cap": [
        "What is the expense ratio of HDFC Mid Cap Fund?",
        "What is the benchmark index for Motilal Oswal Most Focused Midcap 30?",
        "What is the riskometer rating of Nippon India Growth Mid Cap Fund?",
    ],
    "Flexi Cap / Value": [
        "What is the exit load for Parag Parikh Flexi Cap Fund?",
        "What is the minimum investment for Bank of India Flexi Cap Fund?",
        "What is the benchmark of JioBlackRock Flexi Cap Fund?",
    ],
    "Large Cap": [
        "What is the expense ratio of ICICI Prudential Large Cap Fund?",
        "Who is the fund manager of ICICI Prudential Large Cap Fund?",
        "What is the exit load for ICICI Prudential Large Cap Fund?",
    ],
    "Index & Debt": [
        "What is the benchmark index for Axis Liquid Direct Fund?",
        "What is the exit load for Kotak Silver ETF FOF?",
        "What is the minimum SIP amount for SBI Nifty Next 50 Index Fund?",
    ],
}

active_prompts = category_prompts.get(st.session_state.selected_category, category_prompts["All"])

st.markdown("<p style='font-size:0.85rem; color:#94A3B8; margin-top:12px; margin-bottom:4px;'>Quick Factual Questions (1-Click Ask):</p>", unsafe_allow_html=True)
p_cols = st.columns(len(active_prompts))
for idx, prompt_text in enumerate(active_prompts):
    with p_cols[idx]:
        if st.button(f"⚡ {prompt_text}", key=f"quick_prompt_{idx}", use_container_width=True):
            st.session_state.pending_query = prompt_text

st.divider()


# ── Sidebar Scheme Explorer ───────────────────────────────────────────────────
with st.sidebar:
    st.markdown("### 🏢 Groww Scheme Directory")
    st.caption("15 Curated Mutual Fund Schemes Indexed in Vector Store")

    search_term = st.text_input("🔍 Search schemes...", "").lower()

    filtered_schemes = [
        s for s in all_schemes
        if search_term in s["scheme_name"].lower() or search_term in s["category"].lower() or search_term in s["amc"].lower()
    ]

    st.caption(f"Showing {len(filtered_schemes)} of 15 schemes")

    for s in sorted(filtered_schemes, key=lambda x: x["scheme_name"]):
        with st.expander(f"📌 {s['scheme_name']}"):
            st.markdown(f"**AMC:** `{s['amc']}`")
            st.markdown(f"**Category:** `{s['category']}`")
            st.markdown(f"**Source Scraped:** `{s['last_updated'][:10]}`")
            st.markdown(f"[🔗 View Scheme on Groww]({s['url']})")

    st.divider()

    st.markdown("### ⚖️ Educational Resources")
    st.markdown("- [AMFI India Investor Corner](https://www.amfiindia.com/investor-corner)")
    st.markdown("- [SEBI Investor Education](https://investor.sebi.gov.in/)")
    st.markdown("- [Groww Mutual Funds Hub](https://groww.in/mutual-funds)")

    st.divider()

    if st.button("🗑️ Clear Chat History", use_container_width=True):
        st.session_state.messages = []
        st.rerun()


# ── Chat Feed ─────────────────────────────────────────────────────────────────
if not st.session_state.messages:
    with st.chat_message("assistant", avatar="📈"):
        st.markdown(
            "**Welcome to the Groww Mutual Fund FAQ Assistant!**\n\n"
            "I provide verified factual metrics about the 15 mutual funds in our knowledge base.\n\n"
            "**You can ask about:**\n"
            "- Expense Ratios (TER)\n"
            "- Exit Load percentages and holding thresholds\n"
            "- Minimum SIP and Lumpsum amounts\n"
            "- Fund Manager names and experience\n"
            "- Riskometer ratings & Benchmark indices\n\n"
            "*(Strictly facts-only. No investment advice, comparison, or predictions.)*"
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
                    f"🔗 Verified Source: {msg['source_url']}</a>",
                    unsafe_allow_html=True,
                )
            elif is_refusal:
                st.markdown(
                    "<a class='citation-pill' href='https://www.amfiindia.com/investor-corner' target='_blank'>"
                    "🏛️ AMFI Educational Corner</a>",
                    unsafe_allow_html=True,
                )

            if msg.get("last_updated"):
                st.markdown(
                    f"<div class='meta-footer'>Last updated from sources: {msg['last_updated']}</div>",
                    unsafe_allow_html=True,
                )


# ── Query Processing Logic ────────────────────────────────────────────────────
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

                # Separate answer text from standard footer if already formatted
                clean_answer = answer.split("\n\nSource:")[0]

                is_refusal = status_code == "refusal"
                card_class = "answer-card-refusal" if is_refusal else "answer-card"

                st.markdown(f"<div class='{card_class}'>{clean_answer}</div>", unsafe_allow_html=True)

                if source_url and not is_refusal:
                    st.markdown(
                        f"<a class='citation-pill' href='{source_url}' target='_blank'>"
                        f"🔗 Verified Source: {source_url}</a>",
                        unsafe_allow_html=True,
                    )
                elif is_refusal:
                    st.markdown(
                        "<a class='citation-pill' href='https://www.amfiindia.com/investor-corner' target='_blank'>"
                        "🏛️ AMFI Educational Corner</a>",
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
                err_text = (
                    "I encountered an error retrieving this information. "
                    "Please check the official scheme page directly."
                )
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

# Handle chat input
if prompt := st.chat_input("Ask a factual question (e.g. expense ratio, exit load, fund manager)..."):
    handle_query(prompt)
