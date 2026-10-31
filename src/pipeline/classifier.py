"""
classifier.py — Query Classifier & Refusal Handler (Phase 3)

Classifies user input queries into categories:
  - PII          → Block immediately (PAN, Aadhaar, OTP, bank account)
  - ADVISORY     → Refusal Handler (investment advice, speculative returns, opinion)
  - COMPARATIVE  → Refusal Handler (fund comparison, 'which is better')
  - OUT_OF_SCOPE → Refusal Handler (FDs, crypto, non-mutual fund, general chit-chat)
  - UNRECOGNIZED → Clarification prompt (empty, gibberish, script tag)
  - FACTUAL      → Route to RAG Pipeline

Also provides:
  - detect_scheme(query): Resolves query text to one of the 15 corpus scheme names
  - detect_section(query): Identifies target section (expense_ratio, exit_load, etc.)
  - refusal_response(intent): Polite, compliant refusal message with AMFI link
"""

from __future__ import annotations

import re
from enum import Enum
from typing import Dict, List, Optional, Tuple


class QueryIntent(str, Enum):
    FACTUAL = "factual"
    ADVISORY = "advisory"
    COMPARATIVE = "comparative"
    PII = "pii"
    OUT_OF_SCOPE = "out_of_scope"
    UNRECOGNIZED = "unrecognized"
    PERFORMANCE_RETURNS = "performance_returns"


# ── Known 15 Corpus Schemes & Aliases ─────────────────────────────────────────

KNOWN_SCHEMES: Dict[str, List[str]] = {
    "Bandhan Small Cap Fund – Direct Growth": [
        "bandhan small cap", "bandhan smallcap", "bandhan",
    ],
    "Axis Silver FOF – Direct Growth": [
        "axis silver fof", "axis silver",
    ],
    "Parag Parikh Long Term Value Fund – Direct Growth": [
        "parag parikh long term value", "parag parikh flexi cap", "parag parikh", "ppfas",
    ],
    "Motilal Oswal Most Focused Midcap 30 Fund – Direct Growth": [
        "motilal oswal most focused midcap 30", "motilal oswal midcap", "motilal oswal", "motilal",
    ],
    "Kotak Silver ETF FOF – Direct Growth": [
        "kotak silver etf fof", "kotak silver",
    ],
    "HDFC Mid Cap Fund – Direct Growth": [
        "hdfc mid cap", "hdfc midcap", "hdfc mid",
    ],
    "JioBlackRock Flexi Cap Fund – Direct Growth": [
        "jioblackrock flexi cap", "jio blackrock flexi cap", "jioblackrock", "jio blackrock",
    ],
    "HDFC Silver ETF FOF – Direct Growth": [
        "hdfc silver etf fof", "hdfc silver",
    ],
    "SBI Nifty Next 50 Index Fund – Direct Growth": [
        "sbi nifty next 50", "sbi nifty next", "nifty next 50",
    ],
    "SBI PSU Fund – Direct Growth": [
        "sbi psu", "sbi psu fund",
    ],
    "Nippon India Growth Mid Cap Fund – Direct Growth": [
        "nippon india growth mid cap", "nippon india mid cap", "nippon growth mid cap", "nippon",
    ],
    "Bank of India Small Cap Fund – Direct Growth": [
        "bank of india small cap", "boi small cap", "bank of india smallcap",
    ],
    "ICICI Prudential Large Cap Fund – Direct Growth": [
        "icici prudential large cap", "icici large cap", "icici prudential", "icici",
    ],
    "Bank of India Flexi Cap Fund – Direct Growth": [
        "bank of india flexi cap", "boi flexi cap", "bank of india flexicap",
    ],
    "Axis Liquid Direct Fund – Growth": [
        "axis liquid", "axis liquid fund", "axis liquid direct",
    ],
}

# ── PII Patterns (S-03 to S-06) ───────────────────────────────────────────────

PII_PATTERNS = [
    # Permanent Account Number (PAN): 5 letters + 4 digits + 1 letter
    (re.compile(r"\b[A-Za-z]{5}\d{4}[A-Za-z]\b"), "PAN"),
    # Aadhaar Number: 12 digits, optional spaces/hyphens
    (re.compile(r"\b\d{4}[ -]?\d{4}[ -]?\d{4}\b"), "Aadhaar"),
    # One-Time Password (OTP): 6-digit standalone code preceded by 'otp' or isolated 6 digits
    (re.compile(r"\b(?:otp\s*(?:is|:)?\s*)?\d{6}\b", re.IGNORECASE), "OTP"),
    # Bank / Demat Account Numbers (9 to 18 digits)
    (re.compile(r"\b\d{9,18}\b"), "Account Number"),
]

# ── Advisory & Comparative Keywords (C-01 to C-11) ───────────────────────────

ADVISORY_PATTERNS = [
    r"\bshould i invest\b",
    r"\bshould i buy\b",
    r"\bis it safe to invest\b",
    r"\bis it good to invest\b",
    r"\bis this a good fund\b",
    r"\bis (?:the )?fund manager .*good\b",
    r"\bis (?:the )?fund manager good\b",
    r"\bworth investing\b",
    r"\bworth buying\b",
    r"\bcan i get rich\b",
    r"\bhow much return will i get\b",
    r"\bwill this fund give good returns\b",
    r"\brecommend (?:a|some|me)?\b",
    r"\bwhat should i pick\b",
    r"\bwhich one should i choose\b",
    r"\bif i invest .* how much\b",
]

COMPARATIVE_PATTERNS = [
    r"\bwhich fund is better\b",
    r"\bwhich is better\b",
    r"\bwhich one is better\b",
    r"\bbetter than\b",
    r"\bcompare\b",
    r"\bvs\b",
    r"\bversus\b",
    r"\bdifference between .* and\b",
]

PERFORMANCE_RETURN_PATTERNS = [
    r"\bwhat returns did\b",
    r"\bpast returns of\b",
    r"\bhow much returns did\b",
    r"\bhistorical returns\b",
    r"\b1 year return\b",
    r"\b3 year return\b",
    r"\b5 year return\b",
]

OUT_OF_SCOPE_PATTERNS = [
    r"\bfixed deposit\b",
    r"\bfd\b",
    r"\bppf\b",
    r"\bcrypto\b",
    r"\bbitcoin\b",
    r"\bweather\b",
    r"\bjoke\b",
    r"\bwho created you\b",
    r"\bwho built you\b",
    r"\bwhat can you do\b",
]

# ── Section Keyword Detection ─────────────────────────────────────────────────

SECTION_MAP = {
    "expense_ratio": ["expense ratio", "ter", "charges", "annual fees"],
    "exit_load": ["exit load", "redemption load", "exit penalty", "lock in fee"],
    "minimum_investment": ["minimum sip", "min sip", "minimum investment", "min investment", "lumpsum minimum"],
    "fund_management": ["fund manager", "who manages", "manager tenure", "manager experience", "co-manager"],
    "benchmark": ["benchmark", "benchmark index", "index"],
    "tax": ["tax", "taxation", "stcg", "ltcg", "capital gains", "80c"],
    "overview": ["aum", "fund size", "nav", "net asset value", "launch date", "riskometer", "risk rating"],
    "investment_objective": ["investment objective", "objective", "fund aim"],
}


# ── Classifier Functions ──────────────────────────────────────────────────────

def check_pii(query: str) -> Optional[str]:
    """Check if query contains PII (PAN, Aadhaar, OTP, Account No)."""
    for pattern, pii_type in PII_PATTERNS:
        match = pattern.search(query)
        if match:
            matched_str = match.group(0)
            # Avoid false positives for 6-digit years or short amounts like ₹10,000
            if pii_type == "OTP" and not any(k in query.lower() for k in ("otp", "code", "password", "pin")):
                continue
            if pii_type == "Account Number" and len(matched_str) < 9:
                continue
            return pii_type
    return None


def detect_scheme(query: str) -> Optional[str]:
    """
    Identify if one of the 15 known schemes is explicitly mentioned in the query.
    Returns the exact official scheme name from KNOWN_SCHEMES or None.
    """
    q_clean = query.lower()
    best_match = None
    longest_alias_len = 0

    for official_name, aliases in KNOWN_SCHEMES.items():
        for alias in aliases:
            if alias in q_clean:
                if len(alias) > longest_alias_len:
                    longest_alias_len = len(alias)
                    best_match = official_name

    return best_match


def detect_section(query: str) -> Optional[str]:
    """Identify which section topic the query is asking about."""
    q_clean = query.lower()
    for section, keywords in SECTION_MAP.items():
        if any(kw in q_clean for kw in keywords):
            return section
    return None


def classify(query: str) -> QueryIntent:
    """
    Classify incoming user query into QueryIntent enum.

    Precedence:
      1. Empty / Unrecognized / Non-string
      2. PII Detection (immediate block)
      3. Advisory Intent
      4. Comparative Intent
      5. Historical Returns Intent (direct to factsheet only)
      6. Out of Scope Intent
      7. Factual (default for scheme queries)
    """
    if not query or not isinstance(query, str) or not query.strip():
        return QueryIntent.UNRECOGNIZED

    q_strip = query.strip()
    q_lower = q_strip.lower()

    # Gibberish / Script tags / Special characters check
    if re.search(r"<script|javascript:|alert\(", q_lower):
        return QueryIntent.UNRECOGNIZED

    # Check PII first
    if check_pii(q_strip):
        return QueryIntent.PII

    # Check Advisory (exception: "What are the risks of this fund?" -> factual riskometer)
    is_risk_factual = "what are the risks" in q_lower or "risk rating" in q_lower or "riskometer" in q_lower
    if not is_risk_factual:
        for p in ADVISORY_PATTERNS:
            if re.search(p, q_lower):
                return QueryIntent.ADVISORY

    # Check Comparative
    for p in COMPARATIVE_PATTERNS:
        if re.search(p, q_lower):
            return QueryIntent.COMPARATIVE

    # Check Performance / Return requests (C-10: Must provide link to official factsheet only)
    for p in PERFORMANCE_RETURN_PATTERNS:
        if re.search(p, q_lower):
            return QueryIntent.PERFORMANCE_RETURNS

    # Check Out of Scope
    for p in OUT_OF_SCOPE_PATTERNS:
        if re.search(p, q_lower):
            return QueryIntent.OUT_OF_SCOPE

    # Check for pure numbers or nonsense strings without letters
    if not re.search(r"[a-zA-Z]", q_strip):
        return QueryIntent.UNRECOGNIZED

    return QueryIntent.FACTUAL


# ── Refusal Response Templates ────────────────────────────────────────────────

def refusal_response(intent: QueryIntent, query: str = "") -> str:
    """
    Generate polite, compliant, and standardized refusal responses based on intent.
    Every refusal includes the facts-only limitation and an educational link.
    """
    if intent == QueryIntent.PII:
        return (
            "For your security and privacy, please do not share personal details such as PAN, "
            "Aadhaar, OTP, or account numbers.\n\n"
            "This assistant only answers general, objective questions regarding mutual fund schemes.\n\n"
            "Facts-only. No investment advice."
        )

    elif intent == QueryIntent.ADVISORY:
        return (
            "I am only able to provide objective, factual information about mutual fund schemes "
            "(such as expense ratios, exit loads, minimum SIPs, or fund managers).\n\n"
            "I cannot offer investment advice, recommendations, or evaluate fund suitability. "
            "For investor education and guidance, please visit: https://www.amfiindia.com/investor-corner\n\n"
            "Facts-only. No investment advice."
        )

    elif intent == QueryIntent.COMPARATIVE:
        return (
            "I cannot compare the performance or suitability of different mutual fund schemes.\n\n"
            "You can review objective facts for individual schemes, or visit AMFI India for educational guidance: "
            "https://www.amfiindia.com/investor-corner\n\n"
            "Facts-only. No investment advice."
        )

    elif intent == QueryIntent.PERFORMANCE_RETURNS:
        scheme = detect_scheme(query)
        if scheme:
            # Find the Groww URL for the scheme
            for official, aliases in KNOWN_SCHEMES.items():
                if official == scheme:
                    pass
        return (
            "I do not calculate or compare historical fund returns.\n\n"
            "For verified past performance and monthly return tables, please refer directly to the scheme's "
            "official factsheet on the AMC website or Groww scheme page.\n\n"
            "Facts-only. No investment advice."
        )

    elif intent == QueryIntent.OUT_OF_SCOPE:
        return (
            "This assistant is designed exclusively to answer factual queries about mutual fund schemes.\n\n"
            "I am unable to assist with other financial products (such as FDs or PPF) or general queries. "
            "For mutual fund basics, visit: https://www.amfiindia.com\n\n"
            "Facts-only. No investment advice."
        )

    else:
        return (
            "Please enter a specific factual question about a mutual fund scheme "
            "(for example: 'What is the exit load for HDFC Mid Cap Fund?').\n\n"
            "Facts-only. No investment advice."
        )
