"""
scheduler.py — Automated Daily Ingestion Scheduler (Phase 7)

Schedules and executes the mutual fund ingestion and vector index pipeline
daily at 10:00 AM IST (Asia/Kolkata).

Pipeline chain:
  1. fetch_all()   — Fetch Groww scheme factsheets
  2. parse_all()   — Extract clean facts, tables, and metadata
  3. chunk_all()   — Split documents into atomic chunks
  4. embed_all()   — Upsert embeddings into ChromaDB vector store

Usage:
  python -m src.scheduler --now       # Run ingestion immediately
  python -m src.scheduler --daemon    # Run blocking scheduler daemon (10:00 AM IST)
  python -m src.scheduler --status    # View last & next execution status
"""

from __future__ import annotations

import argparse
import json
import logging
import os
import sys
import time
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, Optional

from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.schedulers.blocking import BlockingScheduler
from apscheduler.triggers.cron import CronTrigger

try:
    from zoneinfo import ZoneInfo
except ImportError:
    from backports.zoneinfo import ZoneInfo  # type: ignore

# ── Paths & Constants ─────────────────────────────────────────────────────────
ROOT = Path(__file__).resolve().parents[1]
DATA_DIR = ROOT / "data"
STATUS_FILE = DATA_DIR / "scheduler_status.json"
METADATA_FILE = DATA_DIR / "metadata.json"

SCHEDULE_TIMEZONE = "Asia/Kolkata"
SCHEDULE_HOUR = 10
SCHEDULE_MINUTE = 0
CRON_EXPRESSION = "0 10 * * *"
JOB_ID = "groww_daily_ingestion"

logger = logging.getLogger("mutual_fund_faq.scheduler")
if not logger.handlers:
    logging.basicConfig(
        level=os.getenv("LOG_LEVEL", "INFO"),
        format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    )


# ── Timezone Helper ───────────────────────────────────────────────────────────
def get_ist_timezone():
    """Return ZoneInfo for Asia/Kolkata with fallback."""
    try:
        return ZoneInfo(SCHEDULE_TIMEZONE)
    except Exception:
        # Fallback if tzdata missing on bare Windows
        import pytz
        return pytz.timezone(SCHEDULE_TIMEZONE)


def now_ist() -> datetime:
    """Return current datetime in Asia/Kolkata timezone."""
    return datetime.now(get_ist_timezone())


def get_next_run_time() -> str:
    """Calculate next upcoming 10:00 AM IST execution timestamp."""
    try:
        tz = get_ist_timezone()
        trigger = CronTrigger(hour=SCHEDULE_HOUR, minute=SCHEDULE_MINUTE, timezone=tz)
        current = datetime.now(tz)
        next_fire = trigger.get_next_fire_time(None, current)
        if next_fire:
            return next_fire.strftime("%Y-%m-%d %H:%M:%S %Z")
    except Exception as exc:
        logger.debug("Could not calculate next run time: %s", exc)
    return "Daily at 10:00 AM IST"


# ── Status Persistence ────────────────────────────────────────────────────────
def read_scheduler_status() -> Dict[str, Any]:
    """Read latest execution status or return initialized default."""
    if STATUS_FILE.exists():
        try:
            with open(STATUS_FILE, "r", encoding="utf-8") as f:
                data = json.load(f)
                data["next_run_ist"] = get_next_run_time()
                return data
        except Exception as exc:
            logger.warning("Failed to read scheduler status file: %s", exc)

    return {
        "status": "idle",
        "schedule": f"Daily at {SCHEDULE_HOUR:02d}:{SCHEDULE_MINUTE:02d} IST",
        "timezone": SCHEDULE_TIMEZONE,
        "cron_expression": CRON_EXPRESSION,
        "last_run_ist": None,
        "last_status": "never_run",
        "next_run_ist": get_next_run_time(),
        "last_duration_seconds": 0.0,
        "chunks_indexed": 0,
        "schemes_processed": 0,
        "error": None,
    }


def write_scheduler_status(status_data: Dict[str, Any]) -> None:
    """Persist execution status to data/scheduler_status.json."""
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    try:
        with open(STATUS_FILE, "w", encoding="utf-8") as f:
            json.dump(status_data, f, indent=2, default=str)
    except Exception as exc:
        logger.error("Failed to write scheduler status: %s", exc)


# ── Pipeline Execution ────────────────────────────────────────────────────────
def run_daily_ingestion(force_fetch: bool = False) -> Dict[str, Any]:
    """
    Execute the end-to-end mutual fund ingestion and vector index update.

    Pipeline steps:
      1. fetch_all(force=force_fetch)
      2. parse_all()
      3. chunk_all()
      4. embed_all()

    Returns execution summary dict and saves status to disk.
    """
    from src.ingestion.fetch import fetch_all
    from src.ingestion.parse import parse_all
    from src.ingestion.chunker import chunk_all
    from src.ingestion.embedder import embed_all

    start_time = time.time()
    start_dt_str = now_ist().strftime("%Y-%m-%d %H:%M:%S %Z")
    logger.info("=== Starting Daily Mutual Fund Ingestion (10:00 AM IST trigger) ===")

    current_status = read_scheduler_status()
    current_status["status"] = "running"
    current_status["last_run_ist"] = start_dt_str
    current_status["error"] = None
    write_scheduler_status(current_status)

    try:
        # Step 1: Fetch factsheets
        logger.info("[1/4] Fetching latest scheme factsheets...")
        fetch_all(force=force_fetch)

        # Step 2: Parse raw documents
        logger.info("[2/4] Parsing scheme HTML and tables...")
        parse_all()

        # Step 3: Chunk cleaned content
        logger.info("[3/4] Generating semantic chunks...")
        chunks = chunk_all(dry_run=False)
        chunk_count = len(chunks) if isinstance(chunks, list) else 0

        # Step 4: Embed & upsert into ChromaDB
        logger.info("[4/4] Generating embeddings and upserting into ChromaDB...")
        embedded_count = embed_all()

        # Count schemes from metadata
        schemes_count = 0
        if METADATA_FILE.exists():
            try:
                with open(METADATA_FILE, "r", encoding="utf-8") as f:
                    meta = json.load(f)
                    sources = meta.get("sources", [])
                    schemes_count = len(sources)
            except Exception:
                pass

        duration = round(time.time() - start_time, 2)
        logger.info(
            "=== Ingestion complete in %.2fs: %d schemes, %d chunks upserted ===",
            duration,
            schemes_count,
            embedded_count or chunk_count,
        )

        final_status = {
            "status": "idle",
            "schedule": f"Daily at {SCHEDULE_HOUR:02d}:{SCHEDULE_MINUTE:02d} IST",
            "timezone": SCHEDULE_TIMEZONE,
            "cron_expression": CRON_EXPRESSION,
            "last_run_ist": start_dt_str,
            "last_status": "success",
            "next_run_ist": get_next_run_time(),
            "last_duration_seconds": duration,
            "chunks_indexed": embedded_count or chunk_count,
            "schemes_processed": schemes_count,
            "error": None,
        }
        write_scheduler_status(final_status)
        return final_status

    except Exception as exc:
        duration = round(time.time() - start_time, 2)
        error_msg = str(exc)
        logger.error("Daily ingestion failed after %.2fs: %s", duration, error_msg, exc_info=True)

        failed_status = {
            "status": "error",
            "schedule": f"Daily at {SCHEDULE_HOUR:02d}:{SCHEDULE_MINUTE:02d} IST",
            "timezone": SCHEDULE_TIMEZONE,
            "cron_expression": CRON_EXPRESSION,
            "last_run_ist": start_dt_str,
            "last_status": "failed",
            "next_run_ist": get_next_run_time(),
            "last_duration_seconds": duration,
            "chunks_indexed": current_status.get("chunks_indexed", 0),
            "schemes_processed": current_status.get("schemes_processed", 0),
            "error": error_msg,
        }
        write_scheduler_status(failed_status)
        return failed_status


# ── Scheduler Setup ───────────────────────────────────────────────────────────
def create_scheduler(background: bool = True):
    """
    Construct an APScheduler instance configured for 10:00 AM IST daily ingestion.

    Args:
        background: If True returns BackgroundScheduler, else BlockingScheduler.
    """
    tz = get_ist_timezone()
    scheduler_cls = BackgroundScheduler if background else BlockingScheduler
    scheduler = scheduler_cls(timezone=tz)

    trigger = CronTrigger(
        hour=SCHEDULE_HOUR,
        minute=SCHEDULE_MINUTE,
        timezone=tz,
    )

    scheduler.add_job(
        run_daily_ingestion,
        trigger=trigger,
        id=JOB_ID,
        name="Daily Mutual Fund Ingestion (10:00 AM IST)",
        replace_existing=True,
    )
    return scheduler


def start_daemon():
    """Start blocking daemon scheduler running until interrupted."""
    scheduler = create_scheduler(background=False)
    logger.info("=" * 60)
    logger.info("Groww MF Ingestion Daemon started.")
    logger.info("Schedule : Daily at %02d:%02d IST (%s)", SCHEDULE_HOUR, SCHEDULE_MINUTE, SCHEDULE_TIMEZONE)
    logger.info("Cron     : %s", CRON_EXPRESSION)
    logger.info("Next Run : %s", get_next_run_time())
    logger.info("Press Ctrl+C to terminate.")
    logger.info("=" * 60)

    try:
        scheduler.start()
    except (KeyboardInterrupt, SystemExit):
        logger.info("Daemon shutdown requested. Stopping scheduler...")
        scheduler.shutdown(wait=False)
        logger.info("Daemon stopped cleanly.")


# ── CLI Interface ─────────────────────────────────────────────────────────────
def main():
    parser = argparse.ArgumentParser(
        description="Groww Mutual Fund Daily Ingestion Scheduler (10:00 AM IST)"
    )
    parser.add_argument(
        "--now",
        action="store_true",
        help="Trigger ingestion pipeline immediately and display results",
    )
    parser.add_argument(
        "--daemon",
        action="store_true",
        help="Run scheduler in foreground blocking daemon mode",
    )
    parser.add_argument(
        "--status",
        action="store_true",
        help="Display last and next scheduled execution status",
    )
    parser.add_argument(
        "--force",
        action="store_true",
        help="With --now, force re-fetching of all scheme URLs",
    )

    args = parser.parse_args()

    if args.status:
        status_info = read_scheduler_status()
        print("\n=== Groww Mutual Fund Ingestion Scheduler Status ===")
        for key, val in status_info.items():
            print(f"  {key:22s}: {val}")
        print()
        return

    if args.now:
        print("\n[Scheduler] Triggering ingestion pipeline now...")
        res = run_daily_ingestion(force_fetch=args.force)
        print(f"[Scheduler] Ingestion finished with status: {res.get('last_status')}")
        print(f"[Scheduler] Duration: {res.get('last_duration_seconds')}s | Chunks: {res.get('chunks_indexed')}\n")
        return

    if args.daemon:
        start_daemon()
        return

    parser.print_help()


if __name__ == "__main__":
    main()
