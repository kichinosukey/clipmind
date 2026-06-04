"""Atomic, observable job status for ClipMind pipeline invocations."""

from __future__ import annotations

import json
import os
from datetime import datetime, timezone
from enum import Enum
from pathlib import Path

from clipmind.secrets import redact_secrets


class JobStage(str, Enum):
    QUEUED = "queued"
    DOWNLOADING_AUDIO = "downloading_audio"
    TRANSCRIBING_WITH_WHISPER = "transcribing_with_whisper"
    SUMMARIZING = "summarizing"
    TRANSLATING = "translating"
    DELIVERING = "delivering"
    COMPLETED = "completed"
    FAILED = "failed"


class InvalidTransition(RuntimeError):
    pass


_NEXT_STAGE = {
    JobStage.QUEUED: JobStage.DOWNLOADING_AUDIO,
    JobStage.DOWNLOADING_AUDIO: JobStage.TRANSCRIBING_WITH_WHISPER,
    JobStage.TRANSCRIBING_WITH_WHISPER: JobStage.SUMMARIZING,
    JobStage.SUMMARIZING: JobStage.TRANSLATING,
    JobStage.TRANSLATING: JobStage.DELIVERING,
}
_TERMINAL = {JobStage.COMPLETED.value, JobStage.FAILED.value}


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


class JobStatusStore:
    def __init__(
        self,
        directory: Path,
        *,
        job_id: str,
        source_url: str,
        secrets: list[str | None] | None = None,
    ):
        self.directory = Path(directory)
        self.job_id = job_id
        self.path = self.directory / f"{job_id}.json"
        self.secrets = list(secrets or [])
        timestamp = _now()
        self._data = {
            "schemaVersion": 1,
            "jobId": job_id,
            "sourceURL": source_url,
            "stage": JobStage.QUEUED.value,
            "startedAt": timestamp,
            "updatedAt": timestamp,
        }
        self._write()

    @property
    def stage(self) -> JobStage:
        return JobStage(self._data["stage"])

    def transition(self, stage: JobStage) -> None:
        expected = _NEXT_STAGE.get(self.stage)
        if stage != expected:
            raise InvalidTransition(f"Cannot transition from {self.stage.value} to {stage.value}")
        self._data["stage"] = stage.value
        self._touch()

    def set_title(self, title: str) -> None:
        self._data["title"] = title
        self._touch()

    def complete(self, delivery_results: dict[str, str]) -> None:
        if self.stage != JobStage.DELIVERING:
            raise InvalidTransition(f"Cannot complete from {self.stage.value}")
        self._data.update(
            stage=JobStage.COMPLETED.value,
            deliveryResults=delivery_results,
            completedAt=_now(),
        )
        self._touch()
        self.cleanup_terminal_jobs()

    def fail(self, error: Exception) -> None:
        if self.stage.value in _TERMINAL:
            raise InvalidTransition(f"Cannot fail from {self.stage.value}")
        self._data.update(
            stage=JobStage.FAILED.value,
            failedStage=self.stage.value,
            errorSummary=redact_secrets(str(error), self.secrets),
            completedAt=_now(),
        )
        self._touch()
        self.cleanup_terminal_jobs()

    def _touch(self) -> None:
        self._data["updatedAt"] = _now()
        self._write()

    def _write(self) -> None:
        self.directory.mkdir(parents=True, exist_ok=True)
        temporary = self.path.with_suffix(".json.tmp")
        with temporary.open("w", encoding="utf-8") as handle:
            json.dump(self._data, handle, ensure_ascii=False, indent=2)
            handle.write("\n")
            handle.flush()
            os.fsync(handle.fileno())
        os.replace(temporary, self.path)

    def cleanup_terminal_jobs(self, retain: int = 20) -> None:
        terminal: list[tuple[str, Path]] = []
        for path in self.directory.glob("*.json"):
            try:
                data = json.loads(path.read_text(encoding="utf-8"))
            except (OSError, json.JSONDecodeError):
                continue
            if data.get("stage") in _TERMINAL:
                terminal.append((str(data.get("updatedAt", "")), path))

        for _, path in sorted(terminal, reverse=True)[retain:]:
            path.unlink(missing_ok=True)
            path.with_suffix(".log").unlink(missing_ok=True)
