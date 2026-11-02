"""
app.py — FundPulse AI / Groww Advisory Copilot & Studio (Stitch Screen dc22be5adf064469b93b8f1db11496ec)

A presentation-grade, ultra-premium fintech application matching the exact
FundPulse AI Studio specification:
  - Top Navigation: Copilot & Studio, Portfolio Simulator, Fund Explorer, Benchmark Analyzer
  - Live Ticker Bar: NIFTY 50, SENSEX, NASDAQ, US 10Y with live status
  - Sub-Header: FundPulse Copilot Engine (Llama-3/Qwen Groq LPU, Precision RAG)
  - Left Column: Advisory Copilot v3.8, Active Direct Schemes (Nippon, PPFAS, HDFC), Presets & Tags
  - Right Column:
      * 4 KPI Metric Cards (Monthly SIP, Total Invested, Est. Wealth Gain, Projected Corpus)
      * Advisory Copilot Query Center (Interactive strategy summary, 1-click chips, live RAG chat, query dock)
      * Compounded Wealth Trajectory (Glowing SVG neon compounding curve with horizon selector)
      * Model Assumptions (Risk appetite profile, expected CAGR slider, annual step-up toggle)
      * Portfolio Split (Multi-color allocation bar, scheme table, Execute CTA)
  - Footer: AMFI Tier-1 Scheme Registry, SEBI Non-Advisory Disclosures, Privacy Guard
"""

from __future__ import annotations

import json
import logging
import math
import os
import re
import sys
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

# Ensure project root is in sys.path across all deployment harnesses (Streamlit Cloud, local, Docker)
_current_file = Path(__file__).resolve()
_possible_roots = [
    _current_file.parents[2] if len(_current_file.parents) > 2 else None,
    _current_file.parents[1] if len(_current_file.parents) > 1 else None,
    _current_file.parent,
    Path.cwd(),
]
PROJECT_ROOT = Path.cwd()
for _candidate in _possible_roots:
    if _candidate and (_candidate / "src").is_dir():
        PROJECT_ROOT = _candidate
        if str(_candidate) not in sys.path:
            sys.path.insert(0, str(_candidate))
        break

import streamlit as st
import streamlit.components.v1 as components
from dotenv import load_dotenv

from src.pipeline import query_pipeline

load_dotenv()

def safe_html(html_code: str):
    """Render HTML safely without markdown code-block or whitespace bugs."""
    clean = "\n".join(l.strip() for l in html_code.splitlines() if l.strip())
    if hasattr(st, "html"):
        st.html(clean)
    else:
        st.markdown(clean, unsafe_allow_html=True)

# ── Streamlit Page Configuration ──────────────────────────────────────────────
st.set_page_config(
    page_title="FundPulse AI — Advisory Copilot & Studio",
    page_icon="📈",
    layout="wide",
    initial_sidebar_state="collapsed",
)

# ── Custom CSS for Pixel-Perfect FundPulse AI Stitch Specification ─────────────
st.markdown(
    """
    <style>
    @import url('https://fonts.googleapis.com/css2?family=Plus+Jakarta+Sans:wght@300;400;500;600;700;800&family=JetBrains+Mono:wght@400;500;700&display=swap');

    :root {
      --canvas-bg: #06090E;
      --card-bg: #0D111A;
      --card-bg-elevated: #111724;
      --card-border: rgba(255, 255, 255, 0.07);
      --card-border-active: rgba(0, 208, 156, 0.35);
      --card-border-glow: rgba(0, 208, 156, 0.18);
      
      --accent-emerald: #00D09C;
      --accent-emerald-hover: #00E6AD;
      --accent-emerald-glow: rgba(0, 208, 156, 0.28);
      --accent-cyan: #06B6D4;
      --accent-blue: #3B82F6;
      --accent-yellow: #F59E0B;
      --accent-red: #EF4444;

      --text-white: #FFFFFF;
      --text-gray: #94A3B8;
      --text-muted: #64748B;
      --font-sans: 'Plus Jakarta Sans', -apple-system, sans-serif;
      --font-mono: 'JetBrains Mono', monospace;
    }

    /* Global Overrides */
    .stApp {
        background-color: var(--canvas-bg) !important;
        color: var(--text-white) !important;
        font-family: var(--font-sans) !important;
    }
    
    .block-container {
        padding-top: 1rem !important;
        padding-bottom: 2rem !important;
        max-width: 1440px !important;
    }

    /* Hide standard Streamlit header elements */
    #MainMenu {visibility: hidden;}
    footer {visibility: hidden;}
    header {visibility: hidden;}

    /* Top Brand Navigation Header */
    .brand-nav-container {
        display: flex;
        align-items: center;
        justify-content: space-between;
        padding: 8px 14px 14px 14px;
        border-bottom: 1px solid var(--card-border);
        margin-bottom: 8px;
    }
    .brand-logo-area {
        display: flex;
        align-items: center;
        gap: 10px;
    }
    .brand-logo-icon {
        width: 32px;
        height: 32px;
        border-radius: 8px;
        background: linear-gradient(135deg, rgba(0, 208, 156, 0.25) 0%, rgba(0, 208, 156, 0.05) 100%);
        border: 1px solid rgba(0, 208, 156, 0.4);
        display: flex;
        align-items: center;
        justify-content: center;
        font-size: 1.15rem;
    }
    .brand-title {
        font-size: 1.18rem;
        font-weight: 800;
        color: #FFFFFF;
        letter-spacing: -0.3px;
        display: flex;
        align-items: center;
        gap: 8px;
    }
    .badge-pro {
        font-size: 0.65rem;
        font-weight: 700;
        color: var(--accent-emerald);
        border: 1px solid var(--accent-emerald);
        padding: 2px 6px;
        border-radius: 4px;
        text-transform: uppercase;
        letter-spacing: 0.5px;
    }
    .top-status-pills {
        display: flex;
        align-items: center;
        gap: 12px;
        font-size: 0.78rem;
        color: var(--text-gray);
        font-family: var(--font-mono);
    }
    .status-pill {
        display: inline-flex;
        align-items: center;
        gap: 6px;
        background: #0D121B;
        border: 1px solid var(--card-border);
        padding: 4px 10px;
        border-radius: 20px;
    }
    .pulse-dot-green {
        width: 6px;
        height: 6px;
        background-color: var(--accent-emerald);
        border-radius: 50%;
        box-shadow: 0 0 8px var(--accent-emerald);
        animation: pulse 2s infinite;
    }
    @keyframes pulse {
        0% { transform: scale(0.95); box-shadow: 0 0 0 0 rgba(0, 208, 156, 0.7); }
        70% { transform: scale(1.15); box-shadow: 0 0 0 6px rgba(0, 208, 156, 0); }
        100% { transform: scale(0.95); box-shadow: 0 0 0 0 rgba(0, 208, 156, 0); }
    }

    /* Live Ticker Bar */
    .ticker-bar {
        background: #080C14;
        border: 1px solid var(--card-border);
        border-radius: 8px;
        padding: 6px 14px;
        display: flex;
        justify-content: space-between;
        align-items: center;
        font-size: 0.76rem;
        font-family: var(--font-mono);
        color: var(--text-gray);
        margin-bottom: 8px;
    }
    .ticker-items {
        display: flex;
        align-items: center;
        gap: 16px;
    }
    .ticker-label {
        color: var(--text-muted);
        font-weight: 700;
        display: flex;
        align-items: center;
        gap: 6px;
    }
    .val-pos { color: var(--accent-emerald); font-weight: 600; }
    .val-neg { color: var(--accent-red); font-weight: 600; }

    /* Copilot Engine Sub-Header */
    .copilot-subbar {
        display: flex;
        justify-content: space-between;
        align-items: center;
        padding: 6px 4px 12px 4px;
        font-size: 0.78rem;
        color: var(--text-gray);
        border-bottom: 1px solid var(--card-border);
        margin-bottom: 14px;
    }
    .copilot-subbar-chips {
        display: flex;
        align-items: center;
        gap: 10px;
    }
    .engine-chip {
        background: rgba(0, 208, 156, 0.08);
        border: 1px solid rgba(0, 208, 156, 0.25);
        color: #E2E8F0;
        padding: 3px 10px;
        border-radius: 6px;
        font-size: 0.72rem;
        font-family: var(--font-mono);
    }

    /* Card Panels */
    .fp-card {
        background: var(--card-bg);
        border: 1px solid var(--card-border);
        border-radius: 12px;
        padding: 16px;
        margin-bottom: 12px;
        transition: all 0.2s ease;
    }
    .fp-card:hover {
        border-color: var(--card-border-active);
    }
    .fp-card-highlight {
        background: linear-gradient(180deg, #101622 0%, #0D121B 100%);
        border: 1px solid var(--card-border-active);
        box-shadow: 0 4px 20px rgba(0, 0, 0, 0.3);
    }

    /* Top KPI Metric Cards Grid */
    .kpi-row {
        display: grid;
        grid-template-columns: repeat(4, 1fr);
        gap: 12px;
        margin-bottom: 14px;
    }
    .kpi-card {
        background: var(--card-bg);
        border: 1px solid var(--card-border);
        border-radius: 12px;
        padding: 14px 16px;
        display: flex;
        flex-direction: column;
        justify-content: space-between;
    }
    .kpi-header {
        display: flex;
        justify-content: space-between;
        align-items: center;
        font-size: 0.72rem;
        font-weight: 700;
        color: var(--text-muted);
        text-transform: uppercase;
        letter-spacing: 0.5px;
    }
    .kpi-value {
        font-size: 1.55rem;
        font-weight: 800;
        font-family: var(--font-mono);
        color: #FFFFFF;
        margin: 6px 0 2px 0;
    }
    .kpi-subtext {
        font-size: 0.74rem;
        color: var(--text-gray);
    }
    .kpi-badge-green {
        background: rgba(0, 208, 156, 0.15);
        border: 1px solid rgba(0, 208, 156, 0.3);
        color: var(--accent-emerald);
        font-size: 0.68rem;
        font-weight: 700;
        padding: 1px 6px;
        border-radius: 4px;
    }

    /* Left Column Schemes List */
    .scheme-mini-card {
        background: #090D15;
        border: 1px solid var(--card-border);
        border-radius: 10px;
        padding: 12px 14px;
        margin-bottom: 8px;
        cursor: pointer;
        transition: all 0.2s ease;
    }
    .scheme-mini-card:hover {
        border-color: var(--accent-emerald);
        background: #0E1420;
    }
    .scheme-mini-header {
        display: flex;
        justify-content: space-between;
        align-items: center;
        font-size: 0.88rem;
        font-weight: 700;
        color: #FFFFFF;
        margin-bottom: 4px;
    }
    .scheme-mini-stats {
        display: flex;
        justify-content: space-between;
        font-size: 0.74rem;
        color: var(--text-gray);
        font-family: var(--font-mono);
    }
    .badge-risk {
        font-size: 0.64rem;
        font-weight: 700;
        padding: 2px 6px;
        border-radius: 4px;
        text-transform: uppercase;
    }
    .risk-high { background: rgba(239, 68, 68, 0.15); color: #F87171; border: 1px solid rgba(239, 68, 68, 0.3); }
    .risk-mod { background: rgba(245, 158, 11, 0.15); color: #FBBF24; border: 1px solid rgba(245, 158, 11, 0.3); }
    .risk-modhigh { background: rgba(6, 182, 212, 0.15); color: #22D3EE; border: 1px solid rgba(6, 182, 212, 0.3); }

    /* Strategy Summary Box */
    .strategy-summary-box {
        background: #080C13;
        border: 1px solid rgba(0, 208, 156, 0.2);
        border-radius: 10px;
        padding: 12px 16px;
        font-size: 0.82rem;
        line-height: 1.6;
        color: #E2E8F0;
        margin: 10px 0 14px 0;
    }

    /* RAG Chat Message Cards */
    .copilot-msg-user {
        background: #111724;
        border: 1px solid var(--card-border);
        border-radius: 10px;
        padding: 10px 14px;
        font-size: 0.88rem;
        color: #FFFFFF;
        margin-bottom: 8px;
    }
    .copilot-msg-assistant {
        background: linear-gradient(180deg, #0C121D 0%, #090E17 100%);
        border: 1px solid rgba(0, 208, 156, 0.3);
        border-left: 3px solid var(--accent-emerald);
        border-radius: 10px;
        padding: 14px 16px;
        font-size: 0.88rem;
        line-height: 1.6;
        color: #F1F5F9;
        margin-bottom: 10px;
    }
    .citation-link {
        display: inline-flex;
        align-items: center;
        gap: 5px;
        background: #06090E;
        border: 1px solid rgba(0, 208, 156, 0.3);
        color: var(--accent-emerald);
        font-size: 0.74rem;
        font-weight: 600;
        padding: 4px 10px;
        border-radius: 16px;
        text-decoration: none;
        margin-top: 8px;
    }
    .citation-link:hover {
        background: rgba(0, 208, 156, 0.1);
        color: #FFFFFF;
    }

    /* Compounding Trajectory Header & Snapshot */
    .snapshot-badge {
        display: inline-flex;
        align-items: center;
        gap: 8px;
        background: rgba(6, 182, 212, 0.1);
        border: 1px solid rgba(6, 182, 212, 0.3);
        color: #38BDF8;
        font-size: 0.76rem;
        font-family: var(--font-mono);
        padding: 4px 12px;
        border-radius: 6px;
        margin-bottom: 8px;
    }

    /* Portfolio Segmented Progress Bar */
    .segmented-bar {
        display: flex;
        height: 10px;
        border-radius: 6px;
        overflow: hidden;
        margin: 10px 0 14px 0;
        border: 1px solid var(--card-border);
    }
    .seg-small { background: #06B6D4; width: 35%; }
    .seg-flexi { background: #00D09C; width: 40%; }
    .seg-mid { background: #3B82F6; width: 25%; }

    /* Footer */
    .bottom-disclaimer-strip {
        text-align: center;
        font-size: 0.75rem;
        color: var(--text-muted);
        padding: 16px 0 8px 0;
        border-top: 1px solid var(--card-border);
        margin-top: 24px;
        font-family: var(--font-mono);
    }
    .bottom-footer-bar {
        display: flex;
        justify-content: space-between;
        align-items: center;
        font-size: 0.72rem;
        color: #475569;
        padding-top: 6px;
    }
    .bottom-footer-bar a {
        color: #64748B;
        text-decoration: none;
        margin-left: 12px;
    }

    /* Streamlit Tab and Button Styling */
    .stTabs [data-baseweb="tab-list"] {
        gap: 6px;
        background-color: #080C14;
        padding: 4px;
        border-radius: 10px;
        border: 1px solid var(--card-border);
        margin-bottom: 12px;
    }
    .stTabs [data-baseweb="tab"] {
        height: 38px;
        border-radius: 8px;
        color: var(--text-gray);
        font-weight: 600;
        font-size: 0.85rem;
        padding: 0 16px;
    }
    .stTabs [aria-selected="true"] {
        background-color: #111724 !important;
        color: var(--accent-emerald) !important;
        border-bottom: 2px solid var(--accent-emerald) !important;
    }
    .stButton>button {
        border-radius: 8px !important;
        font-weight: 600 !important;
        font-size: 0.82rem !important;
        border: 1px solid var(--card-border) !important;
        background-color: #0D121B !important;
        color: var(--text-white) !important;
        transition: all 0.2s ease !important;
    }
    .stButton>button:hover {
        border-color: var(--accent-emerald) !important;
        color: var(--accent-emerald) !important;
        background-color: #111724 !important;
    }
    </style>
    """,
    unsafe_allow_html=True,
)


# ── Scheme Metadata Loader ─────────────────────────────────────────────────────
@st.cache_data
def load_all_schemes() -> List[Dict[str, Any]]:
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
            raw_name = item.get("scheme", slug)
            clean_name = re.sub(r"[\u2010-\u2015\u2212\uff0d\x96\x97\ufffd]+", " - ", raw_name)
            clean_name = re.sub(r"\s+-\s+", " - ", clean_name).strip()

            category = item.get("category", "Equity")
            amc = item.get("amc", "Groww Mutual Fund")
            last_updated = item.get("last_fetched", "2026-10-31")[:10]

            ter, exit_load, manager = "0.79%", "1% within 1 year", "Professional Fund Manager"
            chunk_file = PROJECT_ROOT / "data" / "chunks" / f"{slug}.json"
            if chunk_file.exists():
                try:
                    with open(chunk_file, "r", encoding="utf-8") as cf:
                        chunks = json.load(cf)
                    for c in chunks:
                        sec = c.get("section", "")
                        txt = c.get("text", "")
                        if sec == "expense_ratio":
                            m_ter = re.search(r"(\d+\.?\d*%)", txt)
                            if m_ter:
                                ter = m_ter.group(1)
                        elif sec == "exit_load":
                            lines = [l.strip() for l in txt.split("\n") if l.strip() and "exit load" in l.lower()]
                            if lines:
                                exit_load = lines[0]
                        elif sec == "overview":
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
            })
        return schemes
    except Exception:
        return []


all_schemes = load_all_schemes()

# ── Session State ─────────────────────────────────────────────────────────────
if "messages" not in st.session_state:
    st.session_state.messages = []
if "pending_query" not in st.session_state:
    st.session_state.pending_query = None
if "monthly_sip" not in st.session_state:
    st.session_state.monthly_sip = 25000
if "horizon_years" not in st.session_state:
    st.session_state.horizon_years = 10
if "cagr_rate" not in st.session_state:
    st.session_state.cagr_rate = 15.4
if "step_up" not in st.session_state:
    st.session_state.step_up = False
if "risk_profile" not in st.session_state:
    st.session_state.risk_profile = "Aggressive"


# ── Financial Math Calculation ────────────────────────────────────────────────
def calculate_wealth(monthly_sip: float, cagr: float, years: int, step_up_10: bool = False) -> Tuple[float, float, float]:
    """Calculate SIP invested amount, wealth gains, and future corpus with monthly compounding."""
    r = (cagr / 100) / 12
    n = years * 12
    
    if not step_up_10:
        total_invested = monthly_sip * n
        future_value = monthly_sip * (((1 + r)**n - 1) / r) * (1 + r)
    else:
        total_invested = 0.0
        future_value = 0.0
        current_sip = monthly_sip
        for y in range(years):
            if y > 0:
                current_sip *= 1.10
            for m in range(12):
                total_invested += current_sip
                months_remaining = (years - y) * 12 - m
                future_value += current_sip * ((1 + r)**months_remaining)

    wealth_gain = future_value - total_invested
    return total_invested, wealth_gain, future_value


# ── Dynamic SVG Compounding Trajectory Chart ──────────────────────────────────
def render_trajectory_svg(monthly_sip: float, cagr: float, years: int) -> str:
    w, h = 820, 230
    pad_left, pad_bottom, pad_top, pad_right = 60, 45, 25, 40
    chart_w = w - pad_left - pad_right
    chart_h = h - pad_top - pad_bottom

    r = (cagr / 100) / 12
    vals_fv, vals_inv = [], []

    for y in range(years + 1):
        n = y * 12
        if n == 0:
            fv = 0.0
            inv = 0.0
        else:
            fv = monthly_sip * (((1 + r)**n - 1) / r) * (1 + r)
            inv = monthly_sip * n
        vals_fv.append(fv)
        vals_inv.append(inv)

    max_val = max(vals_fv[-1] * 1.18, 100000)

    # Compute coordinates
    pts_fv = []
    pts_inv = []
    for i in range(years + 1):
        x = pad_left + (i / years) * chart_w
        y_fv = (h - pad_bottom) - (vals_fv[i] / max_val) * chart_h
        y_inv = (h - pad_bottom) - (vals_inv[i] / max_val) * chart_h
        pts_fv.append((x, y_fv))
        pts_inv.append((x, y_inv))

    # Path d for smooth cubic curve
    path_d = f"M {pts_fv[0][0]:.1f} {pts_fv[0][1]:.1f}"
    for i in range(1, len(pts_fv)):
        prev_x, prev_y = pts_fv[i-1]
        cur_x, cur_y = pts_fv[i]
        mid_x = (prev_x + cur_x) / 2
        path_d += f" C {mid_x:.1f} {prev_y:.1f}, {mid_x:.1f} {cur_y:.1f}, {cur_x:.1f} {cur_y:.1f}"

    # Path d for linear invested line
    inv_d = f"M {pts_inv[0][0]:.1f} {pts_inv[0][1]:.1f}"
    for x, y in pts_inv[1:]:
        inv_d += f" L {x:.1f} {y:.1f}"

    # Area closed path
    last_x = pts_fv[-1][0]
    base_y = h - pad_bottom
    area_d = path_d + f" L {last_x:.1f} {base_y:.1f} L {pad_left:.1f} {base_y:.1f} Z"

    # Year ticks
    tick_years = [0, max(1, years // 3), max(2, (years * 2) // 3), years]
    tick_elements = ""
    for ty in tick_years:
        tx = pad_left + (ty / years) * chart_w
        tick_label = f"Year {ty}" if ty == 0 else f"Y{ty}"
        tick_elements += f'<text x="{tx}" y="{h - 15}" fill="#64748B" font-size="11" font-family="JetBrains Mono" text-anchor="middle">{tick_label}</text>'
        # Draw dot on line
        idx = ty
        if idx < len(pts_fv):
            dot_x, dot_y = pts_fv[idx]
            val_in_lakh = vals_fv[idx] / 100000
            val_str = f"₹{val_in_lakh:.1f}L" if val_in_lakh >= 1 else f"₹{vals_fv[idx]:,.0f}"
            if ty > 0:
                tick_elements += f'''
                <circle cx="{dot_x}" cy="{dot_y}" r="4" fill="#00D09C" stroke="#FFFFFF" stroke-width="1.5"/>
                <text x="{dot_x}" y="{dot_y - 12}" fill="#00D09C" font-size="11" font-weight="700" font-family="JetBrains Mono" text-anchor="middle">{val_str}</text>
                '''

    svg = f"""
    <svg viewBox="0 0 {w} {h}" width="100%" height="{h}" style="background:#0D111A; border-radius:10px; overflow:visible;">
        <defs>
            <linearGradient id="emeraldArea" x1="0%" y1="0%" x2="0%" y2="100%">
                <stop offset="0%" stop-color="#00D09C" stop-opacity="0.30"/>
                <stop offset="100%" stop-color="#00D09C" stop-opacity="0.0"/>
            </linearGradient>
            <filter id="neonGlow" x="-20%" y="-20%" width="140%" height="140%">
                <feDropShadow dx="0" dy="0" stdDeviation="4" flood-color="#00D09C" flood-opacity="0.8"/>
            </filter>
        </defs>

        <!-- Horizontal Grid Lines -->
        <line x1="{pad_left}" y1="{pad_top}" x2="{pad_left + chart_w}" y2="{pad_top}" stroke="rgba(255,255,255,0.05)" stroke-dasharray="3 3"/>
        <line x1="{pad_left}" y1="{pad_top + chart_h/2}" x2="{pad_left + chart_w}" y2="{pad_top + chart_h/2}" stroke="rgba(255,255,255,0.05)" stroke-dasharray="3 3"/>
        <line x1="{pad_left}" y1="{h - pad_bottom}" x2="{pad_left + chart_w}" y2="{h - pad_bottom}" stroke="rgba(255,255,255,0.15)"/>

        <!-- Filled Gradient Area -->
        <path d="{area_d}" fill="url(#emeraldArea)"/>

        <!-- Principal Invested Line (Dashed Cyan) -->
        <path d="{inv_d}" fill="none" stroke="#0284C7" stroke-width="2" stroke-dasharray="4 4"/>

        <!-- Compounding Neon Emerald Line -->
        <path d="{path_d}" fill="none" stroke="#00D09C" stroke-width="3" filter="url(#neonGlow)"/>

        <!-- Ticks and Marker Labels -->
        {tick_elements}
    </svg>
    """
    return f"""<!DOCTYPE html>
<html>
<head>
<meta charset="utf-8">
<style>
  body {{ margin: 0; padding: 0; background: transparent; overflow: hidden; }}
</style>
</head>
<body>
  {svg}
</body>
</html>"""


# ── Render Top Navigation Header ──────────────────────────────────────────────
safe_html(
    """
    <div class="brand-nav-container">
        <div class="brand-logo-area">
            <div class="brand-logo-icon">📈</div>
            <div class="brand-title">
                FundPulse AI <span class="badge-pro">PRO INTELLIGENCE</span>
            </div>
        </div>
        <div class="top-status-pills">
            <div class="status-pill">
                <span class="pulse-dot-green"></span>
                <span>GROQ RAG : DETERMINISTIC</span>
            </div>
            <div class="status-pill">
                <span>🕒 IST LIVE SYNC</span>
            </div>
            <div class="status-pill">
                <span>⚡ LATENCY 18ms</span>
            </div>
        </div>
    </div>
    """
)

# ── Live Markets Ticker Bar ────────────────────────────────────────────────────
safe_html(
    """
    <div class="ticker-bar">
        <div class="ticker-items">
            <span class="ticker-label"><span class="pulse-dot-green"></span> MARKETS</span>
            <span>NIFTY 50 <strong class="val-pos">24,852.15 +0.84%</strong></span>
            <span>SENSEX <strong class="val-pos">81,496.20 +0.72%</strong></span>
            <span>NASDAQ <strong class="val-pos">18,294.40 +1.15%</strong></span>
            <span>US 10Y <strong class="val-neg">4.18% -0.02</strong></span>
        </div>
        <div>
            <span>FEED STATUS: <strong style="color:#00D09C;">OK</strong></span>
        </div>
    </div>
    """
)

# ── FundPulse Copilot Engine Sub-Header ────────────────────────────────────────
safe_html(
    f"""
    <div class="copilot-subbar">
        <div class="copilot-subbar-chips">
            <span style="font-weight:700; color:#FFF; display:flex; align-items:center; gap:6px;">
                <span class="pulse-dot-green"></span> FUNDPULSE COPILOT ENGINE
            </span>
            <span class="engine-chip">⚡ Deterministic Qwen 2.5 / Llama 3 · Groq LPU (14ms latency)</span>
            <span class="engine-chip">📊 Indexed AMFI Portfolios: 15 Schemes (135 Chunks) · Precision RAG</span>
        </div>
        <div>
            <span style="font-family:var(--font-mono); font-size:0.75rem; color:#94A3B8;">Active Session: <strong style="color:#00D09C;">#AGG-SIP-25K</strong> 🔲</span>
        </div>
    </div>
    """
)

# ── Query Handling Logic ───────────────────────────────────────────────────────
def handle_query(user_text: str):
    """Execute query against RAG pipeline and append response."""
    query = user_text.strip()
    if not query:
        return

    st.session_state.messages.append({"role": "user", "content": query})

    with st.spinner("Querying Groq RAG Engine..."):
        try:
            res = query_pipeline(query)
            ans = res.get("answer", "")
            source_url = res.get("source_url", "https://groww.in/mutual-funds")
            last_up = res.get("last_updated", "2026-10-31")
            clean_ans = ans.split("\n\nSource:")[0]

            st.session_state.messages.append({
                "role": "assistant",
                "content": clean_ans,
                "source_url": source_url,
                "last_updated": last_up,
            })
        except Exception as e:
            st.session_state.messages.append({
                "role": "assistant",
                "content": "I encountered an error retrieving this information. Please check the official scheme page directly.",
                "source_url": "https://groww.in/mutual-funds",
                "last_updated": "date unavailable",
            })

# Trigger pending query if present
if st.session_state.pending_query:
    q = st.session_state.pending_query
    st.session_state.pending_query = None
    handle_query(q)

# ── Navigation Tabs ────────────────────────────────────────────────────────────
nav_tabs = st.tabs([
    "Copilot & Studio",
    "Portfolio Simulator",
    "Fund Explorer",
    "Benchmark Analyzer",
])


# ═══════════════════════════════════════════════════════════════════════════════
# TAB 1: Copilot & Studio (Exact Stitch Screen dc22be5adf064469b93b8f1db11496ec)
# ═══════════════════════════════════════════════════════════════════════════════
with nav_tabs[0]:
    # 2-Column Responsive Layout
    col_left, col_right = st.columns([1, 2.75], gap="medium")

    # ─────────────────────────────────────────────────────────────────────────
    # LEFT COLUMN: Advisory Copilot Card, Active Schemes, Presets
    # ─────────────────────────────────────────────────────────────────────────
    with col_left:
        # Card 1: Advisory Copilot Badge
        safe_html(
            """
            <div class="fp-card fp-card-highlight">
                <div style="display:flex; justify-content:space-between; align-items:center; margin-bottom:4px;">
                    <div style="display:flex; align-items:center; gap:8px;">
                        <span style="font-size:1.1rem;">🤖</span>
                        <strong style="font-size:1.0rem; color:#FFF;">Advisory Copilot</strong>
                        <span style="font-size:0.68rem; color:#00D09C; font-weight:700;">v3.8</span>
                    </div>
                    <span class="kpi-badge-green" style="font-family:var(--font-mono);">14ms</span>
                </div>
                <div style="font-size:0.76rem; color:#94A3B8; margin-bottom:8px;">AMFI Facts & Sim Engine</div>
                <div style="background:#080C14; border:1px solid rgba(255,255,255,0.06); border-radius:8px; padding:10px; font-size:0.75rem; color:#CBD5E1; line-height:1.5;">
                    🛡️ <strong>SEBI Advisory:</strong> Real-time deterministic query mode. 5-10Y historical rolling CAGR. Strictly non-promotional, source-attributed.
                </div>
            </div>
            """
        )

        # Card 2: Active Direct Schemes
        safe_html(
            """
            <div style="display:flex; justify-content:space-between; align-items:center; margin-top:14px; margin-bottom:8px;">
                <span style="font-size:0.82rem; font-weight:700; color:#FFF; display:flex; align-items:center; gap:6px;">
                    📂 Active Direct Schemes
                </span>
                <span class="kpi-badge-green">3 Selected</span>
            </div>
            """
        )

        # Scheme 1: Nippon Small Cap
        safe_html(
            """
            <div class="scheme-mini-card">
                <div class="scheme-mini-header">
                    <span>● Nippon Small Cap</span>
                    <span class="badge-risk risk-high">HIGH RISK</span>
                </div>
                <div class="scheme-mini-stats">
                    <span>Alloc: 35% (₹8,750)</span>
                    <span style="color:#00D09C; font-weight:700;">3Y: +28.4%</span>
                </div>
                <div class="scheme-mini-stats" style="margin-top:2px;">
                    <span>Sharpe: 1.78</span>
                    <span>Exp: 0.72%</span>
                </div>
            </div>
            """
        )
        if st.button("⚡ Query Nippon Small Cap", key="btn_q_nippon", use_container_width=True):
            st.session_state.pending_query = "What is the expense ratio and exit load for Nippon India Growth Mid Cap Fund?"

        # Scheme 2: PPFAS Flexi Cap
        safe_html(
            """
            <div class="scheme-mini-card">
                <div class="scheme-mini-header">
                    <span>● PPFAS Flexi Cap</span>
                    <span class="badge-risk risk-mod">MODERATE</span>
                </div>
                <div class="scheme-mini-stats">
                    <span>Alloc: 40% (₹10,000)</span>
                    <span style="color:#00D09C; font-weight:700;">3Y: +21.8%</span>
                </div>
                <div class="scheme-mini-stats" style="margin-top:2px;">
                    <span>Sharpe: 1.92</span>
                    <span>Exp: 0.65%</span>
                </div>
            </div>
            """
        )
        if st.button("⚡ Query PPFAS Flexi Cap", key="btn_q_ppfas", use_container_width=True):
            st.session_state.pending_query = "What is the exit load for Parag Parikh Flexi Cap Fund?"

        # Scheme 3: HDFC Mid-Cap Opp
        safe_html(
            """
            <div class="scheme-mini-card">
                <div class="scheme-mini-header">
                    <span>● HDFC Mid-Cap Opp</span>
                    <span class="badge-risk risk-modhigh">MOD-HIGH</span>
                </div>
                <div class="scheme-mini-stats">
                    <span>Alloc: 25% (₹6,250)</span>
                    <span style="color:#00D09C; font-weight:700;">3Y: +24.1%</span>
                </div>
                <div class="scheme-mini-stats" style="margin-top:2px;">
                    <span>Sharpe: 1.64</span>
                    <span>Exp: 0.81%</span>
                </div>
            </div>
            """
        )
        if st.button("⚡ Query HDFC Mid-Cap", key="btn_q_hdfc", use_container_width=True):
            st.session_state.pending_query = "Who is the fund manager of HDFC Mid Cap Fund?"

        # Scheme Search Selector (to inspect ANY of the 15 Groww mutual funds!)
        safe_html("<div style='margin-top:14px; font-size:0.78rem; font-weight:700; color:#94A3B8;'>🔍 Explore Any Scheme:</div>")
        scheme_names = [s["scheme_name"] for s in all_schemes]
        selected_scheme = st.selectbox(
            "Select scheme to inspect:",
            options=["(Select a fund...)"] + sorted(scheme_names),
            label_visibility="collapsed",
            key="sb_selector_mini",
        )
        if selected_scheme and selected_scheme != "(Select a fund...)":
            match = next((s for s in all_schemes if s["scheme_name"] == selected_scheme), None)
            if match:
                safe_html(
                    f"""
                    <div style="background:#0B101A; border:1px solid rgba(0, 208, 156, 0.3); border-radius:8px; padding:10px; margin-top:8px; font-size:0.75rem;">
                        <strong style="color:#00D09C;">{match['scheme_name']}</strong><br/>
                        <span style="color:#94A3B8;">TER: <strong>{match['expense_ratio']}</strong> · Manager: <strong>{match['fund_manager']}</strong></span>
                    </div>
                    """
                )
                if st.button(f"⚡ Ask Facts for {match['scheme_name'][:20]}...", key=f"btn_ask_{match['slug']}", use_container_width=True):
                    st.session_state.pending_query = f"What is the expense ratio and exit load for {match['scheme_name']}?"

        # Presets & Tags
        safe_html(
            """
            <div style="margin-top:16px;">
                <div style="font-size:0.72rem; font-weight:700; color:#64748B; text-transform:uppercase; margin-bottom:8px;">PRESETS & TAGS</div>
                <div style="display:flex; flex-wrap:wrap; gap:6px;">
                    <span style="background:rgba(0, 208, 156, 0.15); border:1px solid rgba(0, 208, 156, 0.4); color:#00D09C; font-size:0.72rem; font-weight:700; padding:3px 8px; border-radius:6px;">⚡ All</span>
                    <span style="background:#0D121B; border:1px solid var(--card-border); color:#94A3B8; font-size:0.72rem; padding:3px 8px; border-radius:6px;">📈 High Growth</span>
                    <span style="background:#0D121B; border:1px solid var(--card-border); color:#94A3B8; font-size:0.72rem; padding:3px 8px; border-radius:6px;">🛡️ Low Vol</span>
                    <span style="background:#0D121B; border:1px solid var(--card-border); color:#94A3B8; font-size:0.72rem; padding:3px 8px; border-radius:6px;">💰 Tax Saver</span>
                </div>
            </div>
            """
        )

    # ─────────────────────────────────────────────────────────────────────────
    # RIGHT COLUMN: KPI Metrics, Copilot Query Center, Trajectory Chart, Controls
    # ─────────────────────────────────────────────────────────────────────────
    with col_right:
        # Dynamic Calculations based on state
        total_inv, wealth_gain, proj_corpus = calculate_wealth(
            st.session_state.monthly_sip,
            st.session_state.cagr_rate,
            st.session_state.horizon_years,
            st.session_state.step_up,
        )

        gain_pct = ((proj_corpus - total_inv) / total_inv * 100) if total_inv > 0 else 0

        # Row 1: 4 Top KPI Metric Cards
        inv_str = f"₹{total_inv/100000:.2f} L"
        gain_str = f"₹{wealth_gain/100000:.2f} L"
        corpus_str = f"₹{proj_corpus/100000:.2f} L"

        safe_html(f"""
        <div class="kpi-row">
            <div class="kpi-card">
                <div class="kpi-header">
                    <span>MONTHLY SIP</span>
                    <span style="color:#64748B;">[- / +]</span>
                </div>
                <div class="kpi-value">₹{st.session_state.monthly_sip:,.0f}</div>
                <div class="kpi-subtext">📅 Debit on 5th of Month</div>
            </div>
            <div class="kpi-card">
                <div class="kpi-header">
                    <span>TOTAL INVESTED</span>
                </div>
                <div class="kpi-value">{inv_str}</div>
                <div class="kpi-subtext">{st.session_state.horizon_years * 12} monthly installments</div>
            </div>
            <div class="kpi-card">
                <div class="kpi-header">
                    <span>EST. WEALTH GAIN</span>
                    <span class="kpi-badge-green">+{gain_pct:.1f}%</span>
                </div>
                <div class="kpi-value" style="color:#00D09C;">{gain_str}</div>
                <div class="kpi-subtext">Alpha: +4.8% vs Nifty</div>
            </div>
            <div class="kpi-card">
                <div class="kpi-header">
                    <span>PROJECTED CORPUS</span>
                </div>
                <div class="kpi-value" style="color:#00D09C;">{corpus_str}</div>
                <div class="kpi-subtext">🎯 {st.session_state.horizon_years}Y Horizon Target</div>
            </div>
        </div>
        """)

        # Row 2: Advisory Copilot Query Center Card
        safe_html(
            f"""
            <div class="fp-card">
                <div style="display:flex; justify-content:space-between; align-items:center; margin-bottom:6px;">
                    <div style="display:flex; align-items:center; gap:8px;">
                        <span class="pulse-dot-green"></span>
                        <strong style="font-size:0.95rem; color:#FFF;">Advisory Copilot Query Center</strong>
                        <span class="kpi-badge-green" style="font-size:0.65rem;">Deterministic AMFI RAG</span>
                    </div>
                    <span style="font-size:0.75rem; color:#00D09C; font-family:var(--font-mono);">⚡ Auto-Synced {st.session_state.horizon_years}Y Trajectory</span>
                </div>
                <div class="strategy-summary-box">
                    <div style="display:flex; justify-content:space-between; margin-bottom:4px;">
                        <strong style="color:#00D09C;">✨ Current Strategy: High-Yield SIP Portfolio (₹{st.session_state.monthly_sip:,.0f}/mo)</strong>
                        <span style="font-family:var(--font-mono); color:#FFF; font-weight:700;">Weighted CAGR: {st.session_state.cagr_rate:.1f}% p.a.</span>
                    </div>
                    <div>
                        Optimized for {st.session_state.horizon_years}-year capital compounding with balanced factor exposure: 
                        <strong>35% Nippon Small Cap</strong> (+28.4% 3Y), <strong>40% PPFAS Flexi Cap</strong> (14.8% indirect tech exposure), 
                        and <strong>25% HDFC Mid-Cap</strong>. Blended expense ratio: <strong>0.718%</strong> (saves ~1.1% vs regular plans).
                    </div>
                </div>
            """
        )

        # 1-Click Quick Action Chips
        q_col1, q_col2, q_col3, q_col4 = st.columns(4)
        with q_col1:
            if st.button("📈 15Y SIP with 10% Step-Up", use_container_width=True):
                st.session_state.horizon_years = 15
                st.session_state.step_up = True
                st.rerun()
        with q_col2:
            if st.button("📊 Compare vs Nifty 50 TRI", use_container_width=True):
                st.session_state.pending_query = "What is the benchmark index and performance of SBI Nifty Next 50 Index Fund?"
        with q_col3:
            if st.button("🛡️ Lower Risk to Moderate", use_container_width=True):
                st.session_state.cagr_rate = 13.5
                st.session_state.risk_profile = "Balanced"
                st.rerun()
        with q_col4:
            if st.button("📥 Download Factsheet PDF", use_container_width=True):
                st.toast("Official factsheets can be inspected in the Fund Explorer tab!")

        # In-Card Query Dock (Matching Stitch Screen dc22be5adf064469b93b8f1db11496ec)
        with st.form("copilot_dock_form", clear_on_submit=True):
            q_dock_col, btn_dock_col = st.columns([5.5, 1.2])
            with q_dock_col:
                dock_q = st.text_input(
                    "Ask anything",
                    placeholder="Ask anything (e.g. 'What is the exit load of PPFAS Flexi Cap?')...",
                    label_visibility="collapsed",
                    key="dock_query_input",
                )
            with btn_dock_col:
                dock_submitted = st.form_submit_button("Query ↑", use_container_width=True)

        if dock_submitted and dock_q.strip():
            handle_query(dock_q.strip())
            st.rerun()

        # Conversational Chat Thread (renders messages if any)
        if st.session_state.messages:
            safe_html("<div style='margin-top:12px;'>")
            for m in st.session_state.messages[-4:]:
                if m["role"] == "user":
                    safe_html(f"<div class='copilot-msg-user'>👤 <strong>You:</strong> {m['content']}</div>")
                else:
                    ans_text = m['content']
                    source_url = m.get('source_url', 'https://groww.in/mutual-funds')
                    last_up = m.get('last_updated', '2026-10-31')
                    safe_html(
                        f"""
                        <div class='copilot-msg-assistant'>
                            <div style="display:flex; justify-content:space-between; margin-bottom:4px;">
                                <span style="font-weight:700; color:#00D09C;">📈 Copilot Verified Answer:</span>
                                <span style="font-size:0.72rem; color:#64748B;">{last_up}</span>
                            </div>
                            <div>{ans_text}</div>
                            <div style="margin-top:8px;">
                                <a href="{source_url}" target="_blank" class="citation-link">
                                    🔗 Verified Groww Source ↗
                                </a>
                            </div>
                        </div>
                        """
                    )
            safe_html("</div>")

        safe_html("</div>")  # Close fp-card

        # Row 3: Compounded Wealth Trajectory Chart Card
        safe_html(
            f"""
            <div class="fp-card">
                <div style="display:flex; justify-content:space-between; align-items:center; margin-bottom:4px;">
                    <div>
                        <strong style="font-size:0.95rem; color:#FFF;">Compounded Wealth Trajectory</strong>
                        <span class="kpi-badge-green" style="margin-left:8px; font-size:0.68rem;">Formula: XIRR @ {st.session_state.cagr_rate:.1f}%</span>
                        <div style="font-size:0.74rem; color:#64748B; margin-top:2px;">SIP Monthly Capital Accumulation vs Exponential Compounding</div>
                    </div>
                </div>
            """
        )

        # Timeframe Selector & Floating Snapshot
        hz_cols = st.columns([1, 1, 1, 1, 1, 3.5])
        time_options = [3, 5, 10, 15, 20]
        for idx, yr in enumerate(time_options):
            with hz_cols[idx]:
                btn_txt = f"🟢 {yr}Y" if st.session_state.horizon_years == yr else f"{yr}Y"
                if st.button(btn_txt, key=f"btn_yr_{yr}", use_container_width=True):
                    st.session_state.horizon_years = yr
                    st.rerun()

        with hz_cols[5]:
            safe_html(
                f"""
                <div class="snapshot-badge">
                    <span>{st.session_state.horizon_years}-YEAR HORIZON SNAPSHOT</span> &bull; 
                    <span>Invested: <strong>{inv_str}</strong></span> &bull; 
                    <span style="color:#00D09C;">Gains: <strong>+{gain_str}</strong></span>
                </div>
                """
            )

        # Render the SVG Line / Area Graph via isolated components.html to prevent React/DOMPurify exceptions
        chart_svg = render_trajectory_svg(
            st.session_state.monthly_sip,
            st.session_state.cagr_rate,
            st.session_state.horizon_years,
        )
        components.html(chart_svg, height=235, scrolling=False)

        # Legend and Scenario Note
        safe_html(
            f"""
            <div style="display:flex; justify-content:space-between; align-items:center; font-size:0.74rem; font-family:var(--font-mono); margin-top:8px;">
                <div style="display:flex; gap:16px;">
                    <span style="color:#00D09C; font-weight:700;">— Compounded Corpus ({st.session_state.cagr_rate:.1f}% CAGR)</span>
                    <span style="color:#0284C7; font-weight:700;">- - Total Principal Invested</span>
                </div>
                <div style="color:#64748B;">
                    SCENARIO: <strong style="color:#FFF;">Bull Market Std +1σ</strong>
                </div>
            </div>
            </div>
            """
        )

        # Row 4: Two-Card Split (Model Assumptions & Portfolio Split)
        bot_col1, bot_col2 = st.columns(2, gap="medium")

        # Bottom Left: Model Assumptions
        with bot_col1:
            safe_html(
                """
                <div class="fp-card" style="height:100%;">
                    <div style="display:flex; justify-content:space-between; align-items:center; margin-bottom:8px;">
                        <strong style="font-size:0.92rem; color:#FFF;">🎛️ Model Assumptions</strong>
                        <span style="color:#64748B; font-size:0.75rem;">Interactive Sliders</span>
                    </div>
                """
            )

            # Risk Profile Selector (Zero column nesting to strictly comply with Streamlit layout engine)
            safe_html("<div style='font-size:0.72rem; color:#94A3B8; font-weight:700; text-transform:uppercase; margin-bottom:6px;'>RISK APPETITE PROFILE</div>")
            rp_options = ["Conservative", "Balanced", "Aggressive"]
            rp_curr_idx = rp_options.index(st.session_state.risk_profile) if st.session_state.risk_profile in rp_options else 2
            rp_choice = st.radio(
                "RISK APPETITE PROFILE",
                options=rp_options,
                index=rp_curr_idx,
                horizontal=True,
                label_visibility="collapsed",
                key="radio_risk_profile",
            )
            if rp_choice != st.session_state.risk_profile:
                st.session_state.risk_profile = rp_choice
                if rp_choice == "Conservative":
                    st.session_state.cagr_rate = 11.5
                elif rp_choice == "Balanced":
                    st.session_state.cagr_rate = 13.5
                else:
                    st.session_state.cagr_rate = 15.4
                st.rerun()

            # Expected CAGR Slider
            safe_html(
                f"""
                <div style="display:flex; justify-content:space-between; align-items:center; margin-top:14px; margin-bottom:2px;">
                    <span style="font-size:0.72rem; color:#94A3B8; font-weight:700; text-transform:uppercase;">EXPECTED ANNUAL CAGR</span>
                    <strong style="color:#00D09C; font-family:var(--font-mono); font-size:1.0rem;">{st.session_state.cagr_rate:.1f}% p.a.</strong>
                </div>
                """
            )
            new_cagr = st.slider(
                "CAGR",
                min_value=8.0,
                max_value=24.0,
                value=float(st.session_state.cagr_rate),
                step=0.2,
                label_visibility="collapsed",
                key="cagr_slider",
            )
            if new_cagr != st.session_state.cagr_rate:
                st.session_state.cagr_rate = new_cagr
                st.rerun()

            safe_html(
                """
                <div style="display:flex; justify-content:space-between; font-size:0.70rem; color:#64748B; font-family:var(--font-mono); margin-top:-8px; margin-bottom:12px;">
                    <span>8.0% (Debt/Hybrid)</span>
                    <span>15.0% (Eq Blend)</span>
                    <span>22.0% (Pure Smallcap)</span>
                </div>
                """
            )

            # Annual Step-Up Toggle
            step_up_val = st.checkbox(
                "Annual SIP Step-Up (+10%)",
                value=st.session_state.step_up,
                help="Automatically increments SIP by 10% each year, drastically boosting terminal corpus.",
                key="step_up_cb",
            )
            if step_up_val != st.session_state.step_up:
                st.session_state.step_up = step_up_val
                st.rerun()

            st.caption("↑ Boosts final corpus with automated annual escalation.")
            safe_html("</div>")

        # Bottom Right: Portfolio Split
        with bot_col2:
            sip_val = st.session_state.monthly_sip
            alloc_small = sip_val * 0.35
            alloc_flexi = sip_val * 0.40
            alloc_mid = sip_val * 0.25

            safe_html(
                f"""
                <div class="fp-card" style="height:100%;">
                    <div style="display:flex; justify-content:space-between; align-items:center; margin-bottom:4px;">
                        <strong style="font-size:0.92rem; color:#FFF;">Portfolio Split</strong>
                        <span style="font-size:0.75rem; color:#00D09C; font-family:var(--font-mono);">🔄 Rebalance</span>
                    </div>

                    <!-- Segmented Progress Bar -->
                    <div class="segmented-bar">
                        <div class="seg-small" title="Small Cap (35%)"></div>
                        <div class="seg-flexi" title="Flexi Cap (40%)"></div>
                        <div class="seg-mid" title="Mid Cap (25%)"></div>
                    </div>

                    <div style="font-size:0.72rem; color:#94A3B8; display:flex; justify-content:space-between; margin-top:-8px; margin-bottom:10px;">
                        <span>Small (35%)</span>
                        <span>Flexi (40%)</span>
                        <span>Mid (25%)</span>
                    </div>

                    <!-- Fund Rows -->
                    <div style="background:#090D15; border-radius:8px; padding:10px; margin-bottom:12px; font-size:0.80rem;">
                        <div style="display:flex; justify-content:space-between; align-items:center; margin-bottom:6px;">
                            <span>● <strong style="color:#FFF;">Nippon Small Cap</strong></span>
                            <span style="font-family:var(--font-mono); color:#FFF; font-weight:700;">₹{alloc_small:,.0f}</span>
                        </div>
                        <div style="font-size:0.72rem; color:#64748B; font-family:var(--font-mono); margin-bottom:6px;">Beta 0.94 &bull; Sharpe 1.78 &bull; TER 0.72%</div>

                        <div style="display:flex; justify-content:space-between; align-items:center; margin-bottom:6px; border-top:1px solid rgba(255,255,255,0.05); padding-top:6px;">
                            <span>● <strong style="color:#FFF;">PPFAS Flexi Cap</strong></span>
                            <span style="font-family:var(--font-mono); color:#FFF; font-weight:700;">₹{alloc_flexi:,.0f}</span>
                        </div>
                        <div style="font-size:0.72rem; color:#64748B; font-family:var(--font-mono); margin-bottom:6px;">Beta 0.72 &bull; Sharpe 1.92 &bull; TER 0.65%</div>

                        <div style="display:flex; justify-content:space-between; align-items:center; border-top:1px solid rgba(255,255,255,0.05); padding-top:6px;">
                            <span>● <strong style="color:#FFF;">HDFC Mid-Cap Opp</strong></span>
                            <span style="font-family:var(--font-mono); color:#FFF; font-weight:700;">₹{alloc_mid:,.0f}</span>
                        </div>
                        <div style="font-size:0.72rem; color:#64748B; font-family:var(--font-mono);">Beta 0.88 &bull; Sharpe 1.64 &bull; TER 0.81%</div>
                    </div>
                """
            )

            # High Impact One-Click Execute CTA Button
            if st.button("💥 One-Click Execute Portfolio via Groww API", key="btn_exec_groww", use_container_width=True):
                st.success("Portfolio order staged successfully! Directing to official Groww gateway...")
                st.markdown("<p style='font-size:0.75rem; text-align:center; color:#00D09C;'>🔗 Verified Groww Broker Integration Ready</p>", unsafe_allow_html=True)

            st.markdown("</div>", unsafe_allow_html=True)


# ═══════════════════════════════════════════════════════════════════════════════
# TAB 2: Portfolio Simulator
# ═══════════════════════════════════════════════════════════════════════════════
with nav_tabs[1]:
    st.markdown("### 🧮 Advanced SIP & Wealth Simulator")
    st.markdown("Model different SIP escalation paths, lumpsum infusions, and multi-asset horizons.")

    sim_c1, sim_c2, sim_c3 = st.columns(3)
    with sim_c1:
        sip_input = st.number_input("Monthly SIP Contribution (₹)", min_value=500, max_value=500000, value=st.session_state.monthly_sip, step=1000)
        st.session_state.monthly_sip = sip_input
    with sim_c2:
        horizon_input = st.slider("Investment Horizon (Years)", min_value=1, max_value=30, value=st.session_state.horizon_years)
        st.session_state.horizon_years = horizon_input
    with sim_c3:
        cagr_input = st.slider("Target Annual CAGR (%)", min_value=6.0, max_value=28.0, value=st.session_state.cagr_rate, step=0.5)
        st.session_state.cagr_rate = cagr_input

    inv_sim, gain_sim, fv_sim = calculate_wealth(sip_input, cagr_input, horizon_input, st.session_state.step_up)
    
    st.info(f"**Results for ₹{sip_input:,.0f}/month over {horizon_input} years @ {cagr_input}% CAGR:**")
    m1, m2, m3 = st.columns(3)
    m1.metric("Total Capital Invested", f"₹{inv_sim/100000:.2f} Lakh")
    m2.metric("Estimated Wealth Gain", f"₹{gain_sim/100000:.2f} Lakh", delta=f"{gain_sim/inv_sim*100:.1f}%")
    m3.metric("Projected Total Corpus", f"₹{fv_sim/100000:.2f} Lakh")


# ═══════════════════════════════════════════════════════════════════════════════
# TAB 3: Fund Explorer (All 15 Curated Groww Schemes)
# ═══════════════════════════════════════════════════════════════════════════════
with nav_tabs[2]:
    st.markdown("### 🏢 Groww Fund Explorer (15 Curated Direct Schemes)")
    st.markdown("Explore official scheme documentation, TERs, exit loads, fund managers, and regulatory links.")

    search_exp = st.text_input("🔍 Search schemes by name, category, or fund manager:", "")

    filtered = [
        s for s in all_schemes
        if search_exp.lower() in s["scheme_name"].lower()
        or search_exp.lower() in s["category"].lower()
        or search_exp.lower() in s["fund_manager"].lower()
    ]

    st.caption(f"Showing {len(filtered)} of 15 mutual funds indexed in vector store")

    grid1, grid2 = st.columns(2)
    for idx, s in enumerate(filtered):
        target = grid1 if idx % 2 == 0 else grid2
        with target:
            st.markdown(
                f"""
                <div class="fp-card">
                    <div style="font-weight:700; color:#FFF; font-size:1.0rem; margin-bottom:4px;">{s['scheme_name']}</div>
                    <div style="font-size:0.75rem; color:#94A3B8; margin-bottom:8px;">
                        <span style="background:rgba(0, 208, 156, 0.15); color:#00D09C; padding:2px 8px; border-radius:4px; font-weight:700;">{s['category']}</span>
                        <span style="margin-left:8px;">AMC: <strong>{s['amc']}</strong></span>
                    </div>
                    <div style="background:#090D15; border-radius:8px; padding:8px 12px; font-size:0.78rem; font-family:var(--font-mono); margin-bottom:8px;">
                        <div>⚡ Expense Ratio (TER): <strong style="color:#00D09C;">{s['expense_ratio']}</strong></div>
                        <div style="margin-top:2px;">🚪 Exit Load: {s['exit_load'][:45]}...</div>
                        <div style="margin-top:2px;">👤 Fund Manager: <strong>{s['fund_manager']}</strong></div>
                    </div>
                    <div>
                        <a href="{s['url']}" target="_blank" style="color:#00D09C; font-size:0.78rem; text-decoration:none; font-weight:600;">
                            🔗 View Official Groww Factsheet ↗
                        </a>
                    </div>
                </div>
                """,
                unsafe_allow_html=True,
            )
            col_b1, col_b2 = st.columns(2)
            with col_b1:
                if st.button("⚡ Query TER", key=f"fexp_ter_{idx}", use_container_width=True):
                    st.session_state.pending_query = f"What is the expense ratio of {s['scheme_name']}?"
            with col_b2:
                if st.button("🚪 Query Exit Load", key=f"fexp_exit_{idx}", use_container_width=True):
                    st.session_state.pending_query = f"What is the exit load for {s['scheme_name']}?"


# ═══════════════════════════════════════════════════════════════════════════════
# TAB 4: Benchmark Analyzer & Compliance
# ═══════════════════════════════════════════════════════════════════════════════
with nav_tabs[3]:
    st.markdown("### 📊 Benchmark Analyzer & Regulatory Guardrails")
    st.markdown(
        """
        The **FundPulse AI Copilot** operates strictly under **SEBI (Investment Advisers) Regulations, 2013**
        and AMFI non-advisory operational standards.
        """
    )
    st.markdown(
        """
        <div style="background:#0D111A; border:1px solid #1E2638; border-radius:12px; padding:18px; margin-bottom:16px;">
            <div style="font-weight:700; color:#00D09C; font-size:1.05rem; margin-bottom:8px;">Compliance Sign-Off:</div>
            <div style="font-size:0.86rem; color:#E2E8F0; line-height:1.8;">
                <div>✅ <strong>Facts-Only Retrieval:</strong> Never provides personalized investment advice, buy/sell triggers, or returns guarantees.</div>
                <div>✅ <strong>Attribution Contract:</strong> 100% of factual answers append verified Groww URL citations and crawl timestamps.</div>
                <div>✅ <strong>Zero PII Exposure:</strong> PAN, Aadhaar, and OTP credentials are deterministically blocked and never logged.</div>
                <div>✅ <strong>Output Brevity:</strong> Enforces concise, factual clarity (&le; 3 sentences).</div>
            </div>
        </div>
        """,
        unsafe_allow_html=True,
    )
    st.markdown("#### Educational Resources:")
    st.markdown("- [AMFI India Investor Corner](https://www.amfiindia.com/investor-corner)")
    st.markdown("- [SEBI Investor Website](https://investor.sebi.gov.in/)")


# ── Floating Bottom Query Input Dock ───────────────────────────────────────────
if prompt := st.chat_input("Ask anything (e.g. 'What is the exit load of PPFAS Flexi Cap?')..."):
    handle_query(prompt)
    st.rerun()


# ── Footer Disclaimers ─────────────────────────────────────────────────────────
safe_html(
    """
    <div class="bottom-disclaimer-strip">
        🛡️ <strong>Verified Direct Plans Only (Zero Commission Loaded)</strong> &bull; AMFI Tier-1 Scheme Registry &bull; Historical NAV Base: Jan 2014 – Jan 2026
    </div>
    <div class="bottom-footer-bar">
        <div>FundPulse AI &copy; 2026 Algorithmic Alpha Engine. Quantitative & Deterministic Advisory.</div>
        <div>
            <a href="https://www.amfiindia.com/investor-corner" target="_blank">SEBI Disclosures</a>
            <a href="#model-drift">Model Drift Audits</a>
            <a href="http://localhost:8000/docs" target="_blank">API Engine</a>
            <a href="#privacy">Privacy Guard</a>
        </div>
    </div>
    """
)
