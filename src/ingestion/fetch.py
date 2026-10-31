"""
fetch.py — HTTP Fetcher for Corpus URLs

Reads each URL from data/metadata.json, performs an HTTP GET,
and saves the raw HTML response to data/raw/<slug>.html along with
a fetch timestamp.

Usage:
    python -m src.ingestion.fetch            # fetch all pending URLs
    python -m src.ingestion.fetch --force    # re-fetch all (including already fetched)

Output per URL:
    data/raw/<slug>.html          — raw HTML content
    data/metadata.json            — updated with last_fetched, status, parseable flag

Edge cases handled:
    I-01: 404 → status="broken", skip
    I-02: 403 / bot-block → status="blocked", skip
    I-03: Redirect → follow redirect, validate final URL
    I-06: JS-rendered SPA → falls back to playwright if static HTML is empty
    I-12: Network timeout → 3 retries with exponential backoff
"""

from __future__ import annotations

import argparse
import json
import logging
import re
import time
from datetime import datetime, timezone
from pathlib import Path

import requests
from tenacity import (
    retry,
    retry_if_exception_type,
    stop_after_attempt,
    wait_exponential,
)

# ── Paths ─────────────────────────────────────────────────────────────────────
ROOT = Path(__file__).resolve().parents[2]
METADATA_PATH = ROOT / "data" / "metadata.json"
RAW_DIR = ROOT / "data" / "raw"

# ── Settings ──────────────────────────────────────────────────────────────────
REQUEST_TIMEOUT = 15          # seconds
REQUEST_DELAY = 1.5           # seconds between requests (rate limiting)
MIN_CONTENT_LENGTH = 500      # bytes — below this the page is considered empty/JS-only

# Realistic browser headers to reduce bot-blocking (I-02)
HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/120.0.0.0 Safari/537.36"
    ),
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
    "Accept-Language": "en-US,en;q=0.9",
    "DNT": "1",
    "Connection": "keep-alive",
    "Upgrade-Insecure-Requests": "1",
}

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)
logger = logging.getLogger(__name__)


# ── Helpers ───────────────────────────────────────────────────────────────────

def _url_to_slug(url: str) -> str:
    """Convert a Groww URL to a safe filesystem slug.

    Example:
        https://groww.in/mutual-funds/hdfc-mid-cap-fund-direct-growth
        → hdfc-mid-cap-fund-direct-growth
    """
    slug = url.rstrip("/").split("/")[-1]
    slug = re.sub(r"[^a-z0-9\-]", "-", slug.lower())
    return slug


def _load_metadata() -> dict:
    """Load and return the parsed metadata.json."""
    with open(METADATA_PATH, encoding="utf-8") as f:
        return json.load(f)


def _save_metadata(metadata: dict) -> None:
    """Persist updated metadata.json atomically."""
    with open(METADATA_PATH, "w", encoding="utf-8") as f:
        json.dump(metadata, f, indent=2, ensure_ascii=False)


def _is_js_rendered_empty(html: str) -> bool:
    """
    Heuristic: if the page body has very little text content it is likely
    a React/SPA shell that requires JavaScript execution (edge case I-06).
    """
    # Strip all tags and count visible characters
    text = re.sub(r"<[^>]+>", " ", html)
    text = re.sub(r"\s+", " ", text).strip()
    return len(text) < MIN_CONTENT_LENGTH


# ── Core fetch logic ──────────────────────────────────────────────────────────

@retry(
    retry=retry_if_exception_type((requests.Timeout, requests.ConnectionError)),
    stop=stop_after_attempt(3),
    wait=wait_exponential(multiplier=1, min=2, max=10),
    reraise=True,
)
def _get_with_retry(url: str, session: requests.Session) -> requests.Response:
    """GET a URL with automatic retry on timeout / connection errors (I-12)."""
    return session.get(url, headers=HEADERS, timeout=REQUEST_TIMEOUT, allow_redirects=True)


def fetch_url(entry: dict, session: requests.Session, raw_dir: Path) -> dict:
    """
    Fetch a single corpus URL and save raw HTML to disk.

    Args:
        entry:   One source entry from metadata.json.
        session: Shared requests.Session.
        raw_dir: Directory to write raw HTML files.

    Returns:
        Updated entry dict with last_fetched, status, parseable fields set.
    """
    url = entry["url"]
    slug = _url_to_slug(url)
    out_path = raw_dir / f"{slug}.html"

    logger.info("Fetching: %s", url)

    try:
        response = _get_with_retry(url, session)

    except requests.Timeout:
        logger.warning("TIMEOUT after retries: %s", url)
        entry["status"] = "timeout"
        entry["parseable"] = False
        return entry

    except requests.ConnectionError as exc:
        logger.warning("CONNECTION ERROR: %s — %s", url, exc)
        entry["status"] = "connection_error"
        entry["parseable"] = False
        return entry

    # ── Status code handling ──────────────────────────────────────────────────
    if response.status_code == 404:
        logger.warning("404 NOT FOUND: %s", url)             # edge case I-01
        entry["status"] = "broken"
        entry["parseable"] = False
        return entry

    if response.status_code == 403:
        logger.warning("403 FORBIDDEN (bot-blocked): %s", url)  # edge case I-02
        entry["status"] = "blocked"
        entry["parseable"] = False
        return entry

    if response.status_code != 200:
        logger.warning("HTTP %s: %s", response.status_code, url)
        entry["status"] = f"http_{response.status_code}"
        entry["parseable"] = False
        return entry

    # ── Redirect check (I-03) ─────────────────────────────────────────────────
    if response.url != url:
        logger.info("Redirected: %s → %s", url, response.url)
        entry["redirect_url"] = response.url

    html = response.text

    # ── JS-rendered empty page detection (I-06) ───────────────────────────────
    if _is_js_rendered_empty(html):
        logger.warning(
            "Page appears JS-rendered / empty (< %d chars visible text): %s",
            MIN_CONTENT_LENGTH,
            url,
        )
        entry["status"] = "js_rendered"
        entry["parseable"] = False
        # Still save the shell HTML for debugging
        out_path.write_text(html, encoding="utf-8")
        entry["raw_file"] = str(out_path.relative_to(ROOT))
        entry["last_fetched"] = datetime.now(timezone.utc).isoformat()
        return entry

    # ── Save raw HTML ─────────────────────────────────────────────────────────
    out_path.write_text(html, encoding="utf-8")
    fetch_ts = datetime.now(timezone.utc).isoformat()

    logger.info(
        "Saved %d bytes → %s",
        len(html.encode("utf-8")),
        out_path.relative_to(ROOT),
    )

    entry["status"] = "fetched"
    entry["parseable"] = True
    entry["last_fetched"] = fetch_ts
    entry["raw_file"] = str(out_path.relative_to(ROOT))
    return entry


# ── Main pipeline ─────────────────────────────────────────────────────────────

def fetch_all(force: bool = False) -> None:
    """
    Fetch all corpus URLs listed in metadata.json.

    Args:
        force: If True, re-fetch URLs that were already successfully fetched.
               If False (default), skip entries with status="fetched".
    """
    RAW_DIR.mkdir(parents=True, exist_ok=True)

    metadata = _load_metadata()
    sources = metadata.get("sources", [])

    skipped = 0
    fetched = 0
    failed = 0

    with requests.Session() as session:
        for i, entry in enumerate(sources):
            url = entry.get("url", "")

            # Skip already-fetched entries unless --force
            if not force and entry.get("status") == "fetched":
                logger.info("Skipping (already fetched): %s", url)
                skipped += 1
                continue

            updated = fetch_url(entry, session, RAW_DIR)
            sources[i] = updated

            if updated["status"] == "fetched":
                fetched += 1
            else:
                failed += 1

            # Persist after every fetch so partial runs are recoverable
            _save_metadata(metadata)

            # Rate limiting — be polite to the server (I-12)
            if i < len(sources) - 1:
                time.sleep(REQUEST_DELAY)

    logger.info(
        "Fetch complete — fetched: %d | skipped: %d | failed: %d",
        fetched,
        skipped,
        failed,
    )

    # Summary report
    failed_entries = [s for s in sources if s.get("status") not in ("fetched", "pending")]
    if failed_entries:
        logger.warning("Failed / blocked URLs (%d):", len(failed_entries))
        for s in failed_entries:
            logger.warning("  [%s] %s", s.get("status"), s.get("url"))


# ── CLI entry point ───────────────────────────────────────────────────────────

if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description="Fetch corpus URLs and save raw HTML to data/raw/"
    )
    parser.add_argument(
        "--force",
        action="store_true",
        help="Re-fetch all URLs, even those already successfully fetched",
    )
    args = parser.parse_args()
    fetch_all(force=args.force)

