"""Tests for clipmind.ytdlp_health."""

import subprocess
from unittest.mock import patch

import pytest

from clipmind import ytdlp_health


class TestVersionComparison:
    def test_is_version_outdated_true(self):
        assert ytdlp_health.is_version_outdated("2026.01.31") is True

    def test_is_version_outdated_false(self):
        assert ytdlp_health.is_version_outdated("2026.02.04") is False
        assert ytdlp_health.is_version_outdated("2026.03.01") is False

    def test_is_version_outdated_none(self):
        assert ytdlp_health.is_version_outdated(None) is True


class TestParseVersion:
    def test_parse_version_from_stdout(self):
        assert ytdlp_health.parse_version_string("2026.01.31") == "2026.01.31"

    def test_parse_version_rejects_garbage(self):
        assert ytdlp_health.parse_version_string("stable") is None


class TestRecoverableError:
    def _cp_error(self, stderr: str) -> subprocess.CalledProcessError:
        return subprocess.CalledProcessError(
            1,
            ["yt-dlp", "-J", "https://example.com"],
            stderr=stderr,
        )

    def test_n_challenge_is_recoverable(self):
        err = self._cp_error("WARNING: n challenge solving failed\n")
        assert ytdlp_health.is_recoverable_ytdlp_error(err) is True

    def test_format_not_available_is_recoverable(self):
        err = self._cp_error("ERROR: Requested format is not available\n")
        assert ytdlp_health.is_recoverable_ytdlp_error(err) is True

    def test_unrelated_error_not_recoverable(self):
        err = subprocess.CalledProcessError(1, ["ffmpeg"], stderr="No such file")
        assert ytdlp_health.is_recoverable_ytdlp_error(err) is False

    def test_empty_stderr_not_recoverable(self):
        err = self._cp_error("")
        assert ytdlp_health.is_recoverable_ytdlp_error(err) is False


class TestGetYtdlpVersion:
    @patch("clipmind.ytdlp_health.subprocess.run")
    def test_get_version_success(self, mock_run):
        mock_run.return_value = subprocess.CompletedProcess(
            ["yt-dlp", "--version"], 0, stdout="2026.01.31\n", stderr=""
        )
        with patch(
            "clipmind.ytdlp_health.resolve_ytdlp_bin",
            return_value="/opt/homebrew/bin/yt-dlp",
        ):
            assert ytdlp_health.get_ytdlp_version() == "2026.01.31"

    @patch("clipmind.ytdlp_health.resolve_ytdlp_bin", return_value=None)
    def test_get_version_missing_binary(self, _mock_bin):
        assert ytdlp_health.get_ytdlp_version() is None


class TestReport:
    @patch("clipmind.ytdlp_health.get_ytdlp_version", return_value="2026.01.31")
    @patch(
        "clipmind.ytdlp_health.resolve_ytdlp_bin",
        return_value="/opt/homebrew/bin/yt-dlp",
    )
    def test_report_outdated(self, *_mocks):
        text = ytdlp_health.report()
        assert "yt-dlp health:" in text
        assert "OUTDATED" in text
        assert "brew upgrade yt-dlp" in text

    @patch("clipmind.ytdlp_health.get_ytdlp_version", return_value="2026.03.01")
    @patch(
        "clipmind.ytdlp_health.resolve_ytdlp_bin",
        return_value="/opt/homebrew/bin/yt-dlp",
    )
    def test_report_ok(self, *_mocks):
        assert "status: OK" in ytdlp_health.report()


class TestWarnIfOutdated:
    @patch("clipmind.ytdlp_health.log")
    @patch("clipmind.ytdlp_health.get_ytdlp_version", return_value="2026.01.31")
    @patch(
        "clipmind.ytdlp_health.resolve_ytdlp_bin",
        return_value="/opt/homebrew/bin/yt-dlp",
    )
    def test_warn_logs_for_outdated(self, _mock_bin, _mock_ver, mock_log):
        ytdlp_health.warn_if_outdated()
        mock_log.assert_called_once()
        assert mock_log.call_args[0][1] == "WARN"


class TestTryBrewUpgrade:
    @patch("clipmind.ytdlp_health.get_ytdlp_version", return_value="2026.03.01")
    @patch("clipmind.ytdlp_health.subprocess.run")
    @patch("clipmind.ytdlp_health.shutil.which")
    def test_upgrade_success(self, mock_which, mock_run, _mock_version):
        mock_which.side_effect = lambda name: (
            "/opt/homebrew/bin/brew" if name == "brew" else None
        )
        mock_run.return_value = subprocess.CompletedProcess(["brew"], 0)
        assert ytdlp_health.try_brew_upgrade_ytdlp() is True
        mock_run.assert_called_once()
        assert mock_run.call_args[0][0] == [
            "/opt/homebrew/bin/brew",
            "upgrade",
            "yt-dlp",
        ]

    @patch("clipmind.ytdlp_health.shutil.which", return_value=None)
    def test_upgrade_no_brew(self, _mock_which):
        assert ytdlp_health.try_brew_upgrade_ytdlp() is False


class TestRunYtdlpWithFallback:
    def setup_method(self):
        ytdlp_health.reset_upgrade_state()

    def teardown_method(self):
        ytdlp_health.reset_upgrade_state()

    @patch("clipmind.ytdlp_health.subprocess.run")
    def test_success_no_upgrade(self, mock_run):
        mock_run.return_value = subprocess.CompletedProcess(
            ["yt-dlp"], 0, stdout="{}", stderr=""
        )
        result = ytdlp_health.run_ytdlp_with_fallback(
            ["-J", "https://example.com"], capture_output=True, text=True
        )
        assert result.returncode == 0
        assert mock_run.call_count == 1

    @patch("clipmind.ytdlp_health.try_brew_upgrade_ytdlp", return_value=True)
    @patch("clipmind.ytdlp_health.subprocess.run")
    def test_recovers_after_upgrade(self, mock_run, mock_upgrade):
        stderr = "ERROR: Requested format is not available\n"
        mock_run.side_effect = [
            subprocess.CalledProcessError(1, ["yt-dlp"], stderr=stderr),
            subprocess.CompletedProcess(["yt-dlp"], 0, stdout="{}", stderr=""),
        ]
        result = ytdlp_health.run_ytdlp_with_fallback(
            ["-J", "https://example.com"], capture_output=True, text=True
        )
        assert result.returncode == 0
        mock_upgrade.assert_called_once()
        assert mock_run.call_count == 2

    @patch("clipmind.ytdlp_health.try_brew_upgrade_ytdlp")
    @patch("clipmind.ytdlp_health.subprocess.run")
    def test_non_recoverable_skips_upgrade(self, mock_run, mock_upgrade):
        mock_run.side_effect = subprocess.CalledProcessError(
            1, ["yt-dlp"], stderr="permission denied"
        )
        with pytest.raises(subprocess.CalledProcessError):
            ytdlp_health.run_ytdlp_with_fallback(
                ["-J", "https://example.com"], check=True
            )
        mock_upgrade.assert_not_called()
