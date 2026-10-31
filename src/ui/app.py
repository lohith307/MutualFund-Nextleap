"""
app.py — Streamlit Chat Interface (Phase 4)

User interface for the Mutual Fund FAQ Assistant:
  - Sticky Disclaimer Banner: "Facts-only. No investment advice."
  - Welcome card explaining scope and boundaries
  - 3 clickable quick-example buttons
  - Chat interface using st.chat_message and st.chat_input
  - Grounded source links and 'Last updated from sources' timestamps
  - Sidebar with scheme browser across all 15 covered funds

Run with:
  streamlit run src/ui/app.py
"""

from __future__ import annotations

import json
import logging
import os
from pathlib import Path
from typing import Any, Dict, List

import streamlit as st
from dotenv import load_dotenv

from src.pipeline import query_pipeline

load_dotenv()

# ── Streamlit Page Configuration ──────────────────────────────────────────────
st.set_page_config(
    page_title="Groww Mutual Fund FAQ Assistant",
    page_icon="📈",
    layout="wide",
    initial_sidebar_state="expanded",
)

# ── Custom CSS for Sticky Banner and Elegant Chat UI ──────────────────────────
st.markdown(
    """
    <style>
    /* Fixed top sticky disclaimer banner */
    .sticky-banner {
        position: sticky;
        top: 0;
        z-index: 9999;
        background-color: #fff3cd;
        border: 1px solid #ffeeba;
        color: #856404;
        padding: 10px 16px;
        border-radius: 6px;
        margin-bottom: 20px;
        font-size: 0.92rem;
        display: flex;
        align-items: center;
        box-shadow: 0 2px 4px rgba(0,0,0,0.05);
    }
    .sticky-banner strong {
        color: #664d03;
        margin-right: 6px;
    }
    /* Source pill styling */
    .source-pill {
        display: inline-block;
        background-color: #f1f3f5;
        border: 1px solid #dee2e6;
        border-radius: 12px;
        padding: 2px 10px;
        font-size: 0.8rem;
        color: #495057;
        margin-top: 6px;
    }
    /* Timestamp footer */
    .timestamp-footer {
        font-size: 0.78rem;
        color: #6c757d;
        margin-top: 4px;
        font-style: italic;
    }
    </style>
    <div class="sticky-banner">
        <span>⚠️ <strong>Disclaimer:</strong> Facts-only assistant. We do <u>not</u> provide investment advice, personal recommendations, performance projections, or buy/sell guidance.</span>
    </div>
    """,
    unsafe_allow_html=True,
)


# ── Load Scheme Metadata for Sidebar Explorer ─────────────────────────────────
@st.cache_data
def load_schemes_metadata() -> List[Dict[str, str]]:
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
                "scheme_name": item.get("scheme", "Unknown"),
                "category": item.get("category", "Equity"),
                "last_updated": item.get("last_fetched", "date unavailable"),
            }
            for item in sources
        ]
    except Exception:
        return []


schemes = load_schemes_metadata()

# ── Sidebar ───────────────────────────────────────────────────────────────────
with st.sidebar:
    st.title("📈 Scope & Settings")
    st.info(
        "**Facts-Only Assistant**\n\n"
        "Answers factual queries (expense ratio, exit load, lock-in, fund manager, "
        "min SIP, riskometer) for **15 popular Groww mutual fund schemes**."
    )

    st.markdown("### 📚 Covered Schemes (15)")
    if schemes:
        for s in sorted(schemes, key=lambda x: x["scheme_name"]):
            with st.expander(s["scheme_name"]):
                st.caption(f"**Category:** {s['category']}")
                st.caption(f"**Last Scraped:** {s['last_updated']}")
                st.markdown(f"[View on Groww]({s['url']})")
    else:
        st.write("No scheme metadata loaded.")

    st.divider()

    st.markdown("### ⚖️ Official Resources")
    st.markdown("- [AMFI Investor Corner](https://www.amfiindia.com/investor-corner)")
    st.markdown("- [SEBI Mutual Funds Guide](https://www.sebi.gov.in/)")
    st.markdown("- [Groww Mutual Funds](https://groww.in/mutual-funds)")

    st.divider()

    if st.button("🗑️ Clear Conversation", use_container_width=True):
        st.session_state.messages = []
        st.rerun()


# ── Session State Initialization ──────────────────────────────────────────────
if "messages" not in st.session_state:
    st.session_state.messages = []

if "pending_query" not in st.session_state:
    st.session_state.pending_query = None


# ── Title & Intro ─────────────────────────────────────────────────────────────
st.header("Groww Mutual Fund FAQ Assistant")
st.caption(
    "Ask factual questions about expense ratios, exit loads, minimum SIPs, "
    "fund managers, and risk ratings for 15 top mutual fund schemes."
)

# ── Quick Example Buttons ─────────────────────────────────────────────────────
st.markdown("**Quick Examples (click to ask):**")
col1, col2, col3 = st.columns(3)

example_1 = "What is the expense ratio of Nippon India Small Cap Fund?"
example_2 = "What is the exit load for Parag Parikh Flexi Cap Fund?"
example_3 = "Who is the fund manager of Quant Small Cap Fund?"

with col1:
    if st.button("📊 " + example_1, key="btn_ex1", use_container_width=True):
        st.session_state.pending_query = example_1

with col2:
    if st.button("🚪 " + example_2, key="btn_ex2", use_container_width=True):
        st.session_state.pending_query = example_2

with col3:
    if st.button("👤 " + example_3, key="btn_ex3", use_container_width=True):
        st.session_state.pending_query = example_3

st.divider()


# ── Render Chat History ───────────────────────────────────────────────────────
if not st.session_state.messages:
    with st.chat_message("assistant"):
        st.markdown(
            "Hello! I can help you with verified factual details about the 15 mutual funds "
            "indexed in our database.\n\n"
            "Try asking questions like:\n"
            "- *What is the expense ratio of Motilal Oswal Midcap Fund?*\n"
            "- *What is the minimum SIP amount for Tata Small Cap Fund?*\n"
            "- *Who manages SBI Contra Fund and since when?*\n\n"
            "*(Note: I strictly do not provide investment advice, stock tips, or return forecasts.)*"
        )

for msg in st.session_state.messages:
    with st.chat_message(msg["role"]):
        st.markdown(msg["content"])
        if msg.get("source_url") and msg["role"] == "assistant":
            st.markdown(f"🔗 **Source:** [{msg['source_url']}]({msg['source_url']})")
        if msg.get("last_updated") and msg["role"] == "assistant":
            st.markdown(
                f"<div class='timestamp-footer'>Last updated from sources: {msg['last_updated']}</div>",
                unsafe_allow_html=True,
            )


# ── Query Handler ─────────────────────────────────────────────────────────────
def process_user_query(query_text: str):
    """Execute pipeline and display response."""
    # Append user question
    st.session_state.messages.append({"role": "user", "content": query_text})
    with st.chat_message("user"):
        st.markdown(query_text)

    # Generate assistant answer
    with st.chat_message("assistant"):
        with st.spinner("Retrieving verified facts..."):
            try:
                res = query_pipeline(query_text)
                answer = res.get("answer", "")
                source_url = res.get("source_url", "")
                last_updated = res.get("last_updated", "")

                st.markdown(answer)

                st.session_state.messages.append({
                    "role": "assistant",
                    "content": answer,
                    "source_url": source_url,
                    "last_updated": last_updated,
                })
            except Exception as exc:
                err_msg = (
                    "I encountered an error while retrieving this information. "
                    "Please try again or refer to the official factsheet directly."
                )
                st.error(err_msg)
                st.session_state.messages.append({
                    "role": "assistant",
                    "content": err_msg,
                    "source_url": "https://groww.in/mutual-funds",
                    "last_updated": "date unavailable",
                })


# Handle clicked example button if present
if st.session_state.pending_query:
    q = st.session_state.pending_query
    st.session_state.pending_query = None
    process_user_query(q)
    st.rerun()

# Handle chat input widget
if user_input := st.chat_input("Ask a factual question about mutual funds..."):
    process_user_query(user_input)
