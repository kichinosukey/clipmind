"""Tests for clipmind.utils.error.handle_error()."""

import pytest

from clipmind.utils.error import handle_error


class TestHandleError:
    def test_exits_with_code_1(self):
        """Default call exits with code 1."""
        with pytest.raises(SystemExit) as exc_info:
            handle_error("something failed")
        assert exc_info.value.code == 1

    def test_custom_exit_code(self):
        """Custom exit_code is respected."""
        with pytest.raises(SystemExit) as exc_info:
            handle_error("custom error", exit_code=2)
        assert exc_info.value.code == 2

    def test_with_exception_prints_traceback(self, capsys):
        """When exc is provided, traceback is printed to stderr."""
        try:
            raise RuntimeError("original error")
        except RuntimeError as e:
            with pytest.raises(SystemExit):
                handle_error("wrapped error", exc=e)

        captured = capsys.readouterr()
        assert "original error" in captured.err

    def test_without_exception_no_traceback(self, capsys):
        """When exc is None, no traceback details are printed."""
        with pytest.raises(SystemExit):
            handle_error("simple error")

        captured = capsys.readouterr()
        assert "simple error" in captured.err
        assert "Traceback" not in captured.err
