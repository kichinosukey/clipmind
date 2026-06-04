"""Tests for observable pipeline job state."""

import json
from datetime import datetime, timezone
from pathlib import Path

import pytest

from clipmind.jobs import InvalidTransition, JobStage, JobStatusStore

FIXTURES = Path(__file__).parents[1] / "fixtures" / "runtime"


def read_job(path):
    return json.loads(path.read_text(encoding="utf-8"))


def test_shared_job_fixtures_follow_python_contract():
    active = read_job(FIXTURES / "job-active-v1.json")
    failed = read_job(FIXTURES / "job-failed-v1.json")
    assert JobStage(active["stage"]) is JobStage.TRANSCRIBING_WITH_WHISPER
    assert JobStage(failed["stage"]) is JobStage.FAILED
    assert failed["failedStage"] == JobStage.SUMMARIZING.value


def test_job_store_writes_progress_atomically(tmp_path):
    store = JobStatusStore(tmp_path, job_id="job-1", source_url="https://youtu.be/a")
    store.transition(JobStage.DOWNLOADING_AUDIO)

    data = read_job(tmp_path / "job-1.json")
    assert data["stage"] == "downloading_audio"
    assert data["schemaVersion"] == 1
    assert not list(tmp_path.glob("*.tmp"))


def test_failure_records_failed_stage_and_redacts_secret(tmp_path):
    store = JobStatusStore(
        tmp_path,
        job_id="job-1",
        source_url="https://youtu.be/a",
        secrets=["token-123"],
    )
    store.transition(JobStage.DOWNLOADING_AUDIO)
    store.transition(JobStage.TRANSCRIBING_WITH_WHISPER)
    store.transition(JobStage.SUMMARIZING)
    store.fail(RuntimeError("request failed token-123"))

    data = read_job(tmp_path / "job-1.json")
    assert data["stage"] == "failed"
    assert data["failedStage"] == "summarizing"
    assert data["errorSummary"] == "request failed [REDACTED]"
    assert data["completedAt"]


def test_invalid_transition_is_rejected(tmp_path):
    store = JobStatusStore(tmp_path, job_id="job-1", source_url="https://youtu.be/a")
    with pytest.raises(InvalidTransition):
        store.transition(JobStage.TRANSLATING)


def test_title_delivery_and_completion_are_persisted(tmp_path):
    store = JobStatusStore(tmp_path, job_id="job-1", source_url="https://youtu.be/a")
    store.set_title("Video")
    for stage in (
        JobStage.DOWNLOADING_AUDIO,
        JobStage.TRANSCRIBING_WITH_WHISPER,
        JobStage.SUMMARIZING,
        JobStage.TRANSLATING,
        JobStage.DELIVERING,
    ):
        store.transition(stage)
    store.complete({"discord": "ok"})

    data = read_job(tmp_path / "job-1.json")
    assert data["title"] == "Video"
    assert data["stage"] == "completed"
    assert data["deliveryResults"] == {"discord": "ok"}


def test_cleanup_keeps_latest_terminal_jobs_and_all_active_jobs(tmp_path):
    active = JobStatusStore(tmp_path, job_id="active", source_url="active")
    active.transition(JobStage.DOWNLOADING_AUDIO)
    (tmp_path / "active.log").write_text("active")

    for index in range(25):
        store = JobStatusStore(tmp_path, job_id=f"done-{index:02}", source_url="url")
        store._data["stage"] = JobStage.COMPLETED.value
        store._data["updatedAt"] = datetime(
            2026, 1, 1, 0, 0, index, tzinfo=timezone.utc
        ).isoformat()
        store._write()
        (tmp_path / f"done-{index:02}.log").write_text("log")

    active.cleanup_terminal_jobs(retain=20)

    assert (tmp_path / "active.json").exists()
    assert (tmp_path / "active.log").exists()
    assert len(list(tmp_path.glob("done-*.json"))) == 20
    assert len(list(tmp_path.glob("done-*.log"))) == 20
    assert not (tmp_path / "done-00.json").exists()
    assert not (tmp_path / "done-00.log").exists()
