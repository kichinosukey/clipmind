"""yt-dlp version health checks and brew-based recovery for ClipMind."""

from __future__ import annotations

import re
import shutil
import subprocess
from typing import Any

from clipmind.utils.log import log

MIN_SUPPORTED_YT_DLP = "2026.02.04"

_VERSION_RE = re.compile(r"^(\d{4}\.\d{2}\.\d{2})")

_RECOVERABLE_STDERR_MARKERS = (
    "n challenge solving failed",
    "Requested format is not available",
    "found 0 n function possibilities",
    "found 0 sig function possibilities",
    "Confirm you are on the latest version",
)

_upgrade_attempted = False


def parse_version_string(raw: str) -> str | None:
    """Return YYYY.MM.DD prefix from yt-dlp --version output."""
    match = _VERSION_RE.match(raw.strip())
    return match.group(1) if match else None


def is_version_outdated(version: str | None) -> bool:
    if version is None:
        return True
    return version < MIN_SUPPORTED_YT_DLP


def resolve_ytdlp_bin() -> str | None:
    return shutil.which("yt-dlp")


def get_ytdlp_version() -> str | None:
    binary = resolve_ytdlp_bin()
    if not binary:
        return None
    try:
        result = subprocess.run(
            [binary, "--version"],
            capture_output=True,
            text=True,
            timeout=15,
            check=False,
        )
    except (OSError, subprocess.TimeoutExpired):
        return None
    stdout = (result.stdout or "").strip().split()
    if not stdout:
        return None
    return parse_version_string(stdout[0])


def _health_status(version: str | None, binary: str | None) -> str:
    if not binary:
        return "NOT_FOUND"
    if version is None:
        return "UNKNOWN"
    if is_version_outdated(version):
        return "OUTDATED"
    return "OK"


def report() -> str:
    binary = resolve_ytdlp_bin()
    version = get_ytdlp_version() if binary else None
    status = _health_status(version, binary)
    lines = [
        "yt-dlp health:",
        f"  binary: {binary or '(not found)'}",
        f"  version: {version or 'UNKNOWN'}",
        f"  minimum supported: {MIN_SUPPORTED_YT_DLP}",
        f"  status: {status}",
    ]
    if status == "NOT_FOUND":
        lines.append("  action: brew install yt-dlp")
    elif status in ("OUTDATED", "UNKNOWN"):
        lines.append("  action: brew upgrade yt-dlp")
    else:
        lines.append("  action: (none)")
    return "\n".join(lines)


def warn_if_outdated() -> None:
    binary = resolve_ytdlp_bin()
    if not binary:
        log("yt-dlp not found in PATH. Install: brew install yt-dlp", "WARN")
        return
    version = get_ytdlp_version()
    if version is None:
        log(
            "yt-dlp version could not be determined. Run: brew upgrade yt-dlp",
            "WARN",
        )
        return
    if is_version_outdated(version):
        log(
            f"yt-dlp {version} is below minimum {MIN_SUPPORTED_YT_DLP}. "
            "Run: brew upgrade yt-dlp",
            "WARN",
        )


def is_recoverable_ytdlp_error(exc: BaseException) -> bool:
    if not isinstance(exc, subprocess.CalledProcessError):
        return False
    cmd = exc.cmd if isinstance(exc.cmd, (list, tuple)) else [str(exc.cmd)]
    if not cmd or "yt-dlp" not in str(cmd[0]):
        return False
    stderr = exc.stderr or ""
    if isinstance(stderr, bytes):
        stderr = stderr.decode("utf-8", errors="replace")
    return any(marker in stderr for marker in _RECOVERABLE_STDERR_MARKERS)


def reset_upgrade_state() -> None:
    global _upgrade_attempted
    _upgrade_attempted = False


def try_brew_upgrade_ytdlp(*, timeout: int = 120) -> bool:
    brew = shutil.which("brew")
    if not brew:
        log("brew not found; cannot upgrade yt-dlp automatically", "WARN")
        return False
    log(
        "Attempting brew upgrade yt-dlp due to YouTube extraction failure...",
        "INFO",
    )
    try:
        result = subprocess.run(
            [brew, "upgrade", "yt-dlp"],
            capture_output=True,
            text=True,
            timeout=timeout,
            check=False,
        )
    except (OSError, subprocess.TimeoutExpired) as exc:
        log(f"brew upgrade yt-dlp failed: {exc}", "WARN")
        return False
    if result.returncode != 0:
        err = (result.stderr or result.stdout or "").strip()
        log(f"brew upgrade yt-dlp exited {result.returncode}: {err}", "WARN")
        return False
    new_version = get_ytdlp_version()
    log(
        f"brew upgrade yt-dlp succeeded (version: {new_version or 'unknown'})",
        "INFO",
    )
    return True


def run_ytdlp_with_fallback(args: list[str], **kwargs: Any) -> subprocess.CompletedProcess[Any]:
    global _upgrade_attempted

    binary = resolve_ytdlp_bin() or "yt-dlp"
    cmd = [binary, *args]

    def _run_once() -> subprocess.CompletedProcess[Any]:
        return subprocess.run(cmd, **kwargs)

    try:
        return _run_once()
    except subprocess.CalledProcessError as exc:
        if _upgrade_attempted or not is_recoverable_ytdlp_error(exc):
            raise
        _upgrade_attempted = True
        if not try_brew_upgrade_ytdlp():
            raise
        return _run_once()
