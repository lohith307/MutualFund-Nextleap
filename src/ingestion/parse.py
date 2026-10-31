"""
parse.py — HTML Parser & Section Extractor

Reads raw HTML from data/raw/<slug>.html, strips navigation/footer/boilerplate,
and extracts scheme-specific content tagged into named sections.

Sections extracted:
    - overview            : Fund name, AMC, category, NAV, AUM
    - fund_house          : AMC name, website, established
    - investment_objective: Fund's stated investment objective
    - fund_management     : Fund manager(s), experience, managing since
    - expense_ratio       : Total expense ratio (TER)
    - exit_load           : Exit load terms and percentage
    - minimum_investment  : Minimum SIP and lump-sum amounts
    - benchmark           : Benchmark index name
    - tax                 : Tax treatment (STCG, LTCG, ELSS lock-in)

Output per fund:
    data/cleaned/<slug>.json  — structured dict with all extracted sections

Usage:
    python -m src.ingestion.parse            # parse all fetched HTML files
    python -m src.ingestion.parse --slug hdfc-mid-cap-fund-direct-growth

Edge cases handled:
    I-13: Malformed HTML — lenient BeautifulSoup parser
    I-14: Empty document after cleaning — logged and skipped
    I-09: Generic/non-scheme-specific content — tagged with low specificity flag
"""

from __future__ import annotations

import argparse
import json
import logging
import re
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional

from bs4 import BeautifulSoup, Tag

# ── Paths ─────────────────────────────────────────────────────────────────────
ROOT = Path(__file__).resolve().parents[2]
METADATA_PATH = ROOT / "data" / "metadata.json"
RAW_DIR = ROOT / "data" / "raw"
CLEANED_DIR = ROOT / "data" / "cleaned"

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)
logger = logging.getLogger(__name__)


# ── Section keyword maps ──────────────────────────────────────────────────────
# Each section maps to a list of keywords/patterns that identify relevant text.
SECTION_KEYWORDS: dict[str, list[str]] = {
    "overview": [
        "nav", "net asset value", "aum", "assets under management",
        "category", "fund type", "fund size", "launch date", "inception",
        "riskometer", "risk", "rating",
    ],
    "fund_house": [
        "fund house", "amc", "asset management", "established",
        "registered office", "trustee",
    ],
    "investment_objective": [
        "investment objective", "scheme objective", "objective of the scheme",
        "the fund seeks", "the scheme seeks", "aims to",
    ],
    "fund_management": [
        "fund manager", "managed by", "managing since", "managing the fund",
        "co-fund manager", "co-manager", "years of experience",
        "experience", "portfolio manager",
    ],
    "expense_ratio": [
        "expense ratio", "total expense ratio", "ter", "annual charges",
        "management fee", "ongoing charges",
    ],
    "exit_load": [
        "exit load", "redemption load", "exit charge",
        "if redeemed", "within 1 year", "within 12 months",
        "no exit load", "nil exit load",
    ],
    "minimum_investment": [
        "minimum investment", "minimum sip", "minimum lump", "minimum purchase",
        "min sip", "min investment", "minimum additional", "minimum redemption",
        "₹", "rs.", "inr",
    ],
    "benchmark": [
        "benchmark", "benchmark index", "index", "nifty", "sensex",
        "bse", "nse", "crisil", "s&p",
    ],
    "tax": [
        "tax", "taxation", "stcg", "ltcg", "short term capital gain",
        "long term capital gain", "elss", "lock-in", "lock in",
        "tax benefit", "80c", "section 80",
    ],
}

# Tags to strip entirely before text extraction
STRIP_TAGS = [
    "script", "style", "noscript", "iframe", "svg",
    "meta", "link", "head",
]

# CSS class/id patterns that indicate boilerplate (nav, footer, ads)
BOILERPLATE_PATTERNS = [
    re.compile(p, re.IGNORECASE)
    for p in [
        r"nav(bar|igation)?", r"header", r"footer", r"menu",
        r"sidebar", r"breadcrumb", r"cookie", r"banner",
        r"advertisement", r"promo", r"social", r"share",
        r"related", r"recommend", r"trending", r"popular",
        r"disclaimer.*footer", r"app.?download",
    ]
]


# ── HTML Cleaning ─────────────────────────────────────────────────────────────

def _is_boilerplate(tag: Tag) -> bool:
    """Return True if the tag looks like navigation, footer, or boilerplate."""
    if not hasattr(tag, "attrs") or tag.attrs is None:
        return False
    for attr in ("class", "id", "role", "aria-label"):
        values = tag.attrs.get(attr, [])
        if values is None:
            continue
        if isinstance(values, str):
            values = [values]
        combined = " ".join(values).lower()
        for pattern in BOILERPLATE_PATTERNS:
            if pattern.search(combined):
                return True
    return False


def clean_html(html: str) -> str:
    """
    Remove scripts, styles, navigation, footers, and other boilerplate.
    Returns cleaned plain text.

    Edge case I-13: Uses lenient 'html.parser' to handle malformed HTML.
    """
    soup = BeautifulSoup(html, "html.parser")

    # Remove non-content tags entirely
    for tag_name in STRIP_TAGS:
        for tag in soup.find_all(tag_name):
            tag.decompose()

    # Remove boilerplate structural elements
    for tag in soup.find_all(True):
        if _is_boilerplate(tag):
            tag.decompose()

    # Extract visible text
    text = soup.get_text(separator="\n")

    # Normalize whitespace
    lines = [re.sub(r"[ \t]+", " ", line).strip() for line in text.splitlines()]
    lines = [line for line in lines if line]           # drop empty lines
    text = "\n".join(lines)

    return text


# ── Section Extraction ────────────────────────────────────────────────────────

def _score_line(line: str, keywords: list[str]) -> float:
    """
    Return a relevance score [0.0–1.0] for a text line against a keyword list.
    Higher score = more keyword matches.
    """
    line_lower = line.lower()
    hits = sum(1 for kw in keywords if kw in line_lower)
    return hits / len(keywords) if keywords else 0.0


def extract_sections(text: str) -> dict[str, list[str]]:
    """
    Tag each line of clean text into one or more named sections based on
    keyword relevance scoring.

    Returns a dict mapping section names to lists of relevant text lines.
    Unmatched lines go into a special "_unclassified" bucket.
    """
    sections: dict[str, list[str]] = {name: [] for name in SECTION_KEYWORDS}
    sections["_unclassified"] = []

    lines = text.splitlines()

    for line in lines:
        if not line.strip():
            continue

        scores = {
            section: _score_line(line, keywords)
            for section, keywords in SECTION_KEYWORDS.items()
        }

        best_section = max(scores, key=scores.get)
        best_score = scores[best_section]

        if best_score > 0:
            sections[best_section].append(line)
        else:
            sections["_unclassified"].append(line)

    return sections


def _assess_specificity(sections: dict[str, list[str]]) -> bool:
    """
    Return True if the page has enough scheme-specific content.
    Pages that are mostly unclassified are likely generic (edge case I-09).
    """
    total_lines = sum(len(v) for v in sections.values())
    unclassified = len(sections.get("_unclassified", []))
    if total_lines == 0:
        return False
    specificity_ratio = 1 - (unclassified / total_lines)
    return specificity_ratio >= 0.15   # at least 15% of lines are section-tagged


# ── Main parse function ───────────────────────────────────────────────────────

def parse_file(slug: str, metadata_entry: Optional[dict] = None) -> Optional[dict]:
    """
    Parse a single raw HTML file and extract structured sections.

    Args:
        slug:           File slug (e.g. 'hdfc-mid-cap-fund-direct-growth').
        metadata_entry: Corresponding metadata.json entry for this slug.

    Returns:
        Parsed document dict, or None if the file is missing/empty.
    """
    raw_path = RAW_DIR / f"{slug}.html"

    if not raw_path.exists():
        logger.warning("Raw file not found, skipping: %s", raw_path)
        return None

    html = raw_path.read_text(encoding="utf-8", errors="replace")

    if not html.strip():
        logger.warning("Empty raw file, skipping: %s", raw_path)   # edge case I-14
        return None

    # Step 1: Clean HTML → plain text
    clean_text = clean_html(html)

    if len(clean_text) < 100:
        logger.warning(
            "Document too short after cleaning (%d chars), skipping: %s",
            len(clean_text),
            slug,
        )
        return None                                                   # edge case I-14

    # Step 2: Tag lines into sections
    sections = extract_sections(clean_text)

    # Step 3: Assess specificity
    is_specific = _assess_specificity(sections)
    if not is_specific:
        logger.warning(
            "Low specificity — mostly generic content (edge case I-09): %s", slug
        )

    parsed_doc = {
        "slug": slug,
        "url": metadata_entry.get("url", "") if metadata_entry else "",
        "scheme": metadata_entry.get("scheme", "") if metadata_entry else "",
        "amc": metadata_entry.get("amc", "") if metadata_entry else "",
        "category": metadata_entry.get("category", "") if metadata_entry else "",
        "parsed_at": datetime.now(timezone.utc).isoformat(),
        "is_scheme_specific": is_specific,
        "sections": {
            section: lines
            for section, lines in sections.items()
            if lines  # omit empty sections from output
        },
        "full_clean_text": clean_text,
    }

    return parsed_doc


def save_parsed(parsed_doc: dict) -> Path:
    """Save parsed document as JSON to data/cleaned/<slug>.json."""
    CLEANED_DIR.mkdir(parents=True, exist_ok=True)
    out_path = CLEANED_DIR / f"{parsed_doc['slug']}.json"
    with open(out_path, "w", encoding="utf-8") as f:
        json.dump(parsed_doc, f, indent=2, ensure_ascii=False)
    logger.info("Saved parsed doc → %s", out_path.relative_to(ROOT))
    return out_path


def parse_all() -> None:
    """Parse all successfully fetched HTML files listed in metadata.json."""
    with open(METADATA_PATH, encoding="utf-8") as f:
        metadata = json.load(f)

    sources = metadata.get("sources", [])
    parsed = 0
    skipped = 0
    failed = 0

    for entry in sources:
        if entry.get("status") != "fetched":
            logger.info(
                "Skipping (status=%s): %s",
                entry.get("status"),
                entry.get("url"),
            )
            skipped += 1
            continue

        raw_file = entry.get("raw_file", "")
        slug = Path(raw_file).stem if raw_file else None

        if not slug:
            logger.warning("No raw_file recorded for: %s", entry.get("url"))
            failed += 1
            continue

        result = parse_file(slug, metadata_entry=entry)
        if result:
            save_parsed(result)
            parsed += 1
        else:
            failed += 1

    logger.info(
        "Parse complete — parsed: %d | skipped: %d | failed: %d",
        parsed,
        skipped,
        failed,
    )


# ── CLI entry point ───────────────────────────────────────────────────────────

if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description="Parse raw HTML files and extract scheme sections to data/cleaned/"
    )
    parser.add_argument(
        "--slug",
        type=str,
        default=None,
        help="Parse a single slug (e.g. hdfc-mid-cap-fund-direct-growth). "
             "Omit to parse all fetched files.",
    )
    args = parser.parse_args()

    if args.slug:
        with open(METADATA_PATH, encoding="utf-8") as f:
            metadata = json.load(f)
        entry = next(
            (s for s in metadata["sources"] if s["url"].endswith(args.slug)),
            None,
        )
        result = parse_file(args.slug, metadata_entry=entry)
        if result:
            save_parsed(result)
    else:
        parse_all()

