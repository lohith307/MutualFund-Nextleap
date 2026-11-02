"""
test_scheduler.py — Unit & Integration Tests for Daily Scheduler (Phase 7)

Covers:
  - Timezone and cron trigger validation (Asia/Kolkata, 10:00 AM IST)
  - Next execution calculation
  - Status read/write persistence
  - Pipeline execution with mocked ingestion components
  - Pipeline failure handling and error logging
  - FastAPI /scheduler/status and /scheduler/trigger endpoints
"""

import json
from unittest.mock import MagicMock, patch

import pytest
from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.schedulers.blocking import BlockingScheduler
from apscheduler.triggers.cron import CronTrigger
from fastapi.testclient import TestClient

from src.api.main import app
from src.scheduler import (
    CRON_EXPRESSION,
    SCHEDULE_HOUR,
    SCHEDULE_MINUTE,
    SCHEDULE_TIMEZONE,
    create_scheduler,
    get_ist_timezone,
    get_next_run_time,
    now_ist,
    read_scheduler_status,
    run_daily_ingestion,
    write_scheduler_status,
)

client = TestClient(app)


class TestSchedulerConfiguration:
    """Verifies timezone, cron schedule, and triggers."""

    def test_timezone_is_asia_kolkata(self):
        tz = get_ist_timezone()
        assert "Kolkata" in str(tz) or "Calcutta" in str(tz)

    def test_cron_expression_constants(self):
        assert SCHEDULE_HOUR == 10
        assert SCHEDULE_MINUTE == 0
        assert SCHEDULE_TIMEZONE == "Asia/Kolkata"
        assert CRON_EXPRESSION == "0 10 * * *"

    def test_now_ist_has_correct_tzinfo(self):
        current_ist = now_ist()
        assert current_ist.tzinfo is not None

    def test_next_run_time_calculation(self):
        next_run = get_next_run_time()
        assert isinstance(next_run, str)
        assert len(next_run) > 0
        assert "10:00:00" in next_run or "10:00 AM" in next_run

    def test_create_background_scheduler(self):
        scheduler = create_scheduler(background=True)
        assert isinstance(scheduler, BackgroundScheduler)
        jobs = scheduler.get_jobs()
        assert len(jobs) == 1
        job = jobs[0]
        assert job.id == "groww_daily_ingestion"
        assert isinstance(job.trigger, CronTrigger)

    def test_create_blocking_scheduler(self):
        scheduler = create_scheduler(background=False)
        assert isinstance(scheduler, BlockingScheduler)
        jobs = scheduler.get_jobs()
        assert len(jobs) == 1


class TestSchedulerPersistence:
    """Verifies reading and writing of scheduler status."""

    def test_read_default_status_when_no_file(self, tmp_path):
        dummy_file = tmp_path / "dummy_status.json"
        with patch("src.scheduler.STATUS_FILE", dummy_file):
            status = read_scheduler_status()
            assert status["status"] == "idle"
            assert status["timezone"] == "Asia/Kolkata"
            assert status["schedule"] == "Daily at 10:00 IST"
            assert status["last_status"] == "never_run"

    def test_write_and_read_status(self, tmp_path):
        dummy_file = tmp_path / "dummy_status.json"
        with patch("src.scheduler.STATUS_FILE", dummy_file):
            test_data = {
                "status": "idle",
                "schedule": "Daily at 10:00 IST",
                "timezone": "Asia/Kolkata",
                "cron_expression": "0 10 * * *",
                "last_run_ist": "2026-11-02 10:00:00 IST",
                "last_status": "success",
                "next_run_ist": "2026-11-03 10:00:00 IST",
                "last_duration_seconds": 4.52,
                "chunks_indexed": 135,
                "schemes_processed": 15,
                "error": None,
            }
            write_scheduler_status(test_data)
            read_back = read_scheduler_status()
            assert read_back["last_status"] == "success"
            assert read_back["chunks_indexed"] == 135
            assert read_back["schemes_processed"] == 15


class TestSchedulerPipelineExecution:
    """Verifies run_daily_ingestion execution and error handling."""

    @patch("src.ingestion.fetch.fetch_all")
    @patch("src.ingestion.parse.parse_all")
    @patch("src.ingestion.chunker.chunk_all")
    @patch("src.ingestion.embedder.embed_all")
    def test_run_daily_ingestion_success(self, mock_embed, mock_chunk, mock_parse, mock_fetch, tmp_path):
        mock_fetch.return_value = None
        mock_parse.return_value = None
        mock_chunk.return_value = [{"chunk_id": "c1"}, {"chunk_id": "c2"}]
        mock_embed.return_value = 135

        dummy_status = tmp_path / "scheduler_status.json"
        with patch("src.scheduler.STATUS_FILE", dummy_status):
            result = run_daily_ingestion(force_fetch=False)

            assert result["status"] == "idle"
            assert result["last_status"] == "success"
            assert result["chunks_indexed"] == 135
            assert result["error"] is None
            assert mock_fetch.called
            assert mock_parse.called
            assert mock_chunk.called
            assert mock_embed.called

    @patch("src.ingestion.fetch.fetch_all")
    def test_run_daily_ingestion_handles_failure(self, mock_fetch, tmp_path):
        mock_fetch.side_effect = ConnectionError("Network unreachable")

        dummy_status = tmp_path / "scheduler_status.json"
        with patch("src.scheduler.STATUS_FILE", dummy_status):
            result = run_daily_ingestion(force_fetch=False)

            assert result["status"] == "error"
            assert result["last_status"] == "failed"
            assert "Network unreachable" in result["error"]


class TestSchedulerApiEndpoints:
    """Verifies FastAPI /scheduler/status and /scheduler/trigger endpoints."""

    def test_get_scheduler_status_endpoint(self):
        response = client.get("/scheduler/status")
        assert response.status_code == 200
        data = response.json()
        assert data["timezone"] == "Asia/Kolkata"
        assert data["cron_expression"] == "0 10 * * *"
        assert "10:00" in data["schedule"]
        assert "next_run_ist" in data
        assert "last_status" in data

    def test_post_scheduler_trigger_endpoint(self):
        with patch("src.scheduler.run_daily_ingestion"):
            response = client.post("/scheduler/trigger")
            assert response.status_code == 200
            data = response.json()
            assert data["status"] == "triggered"
            assert "background" in data["message"].lower()
