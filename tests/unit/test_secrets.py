"""Tests for macOS Keychain secret access and redaction."""

import subprocess

import pytest

from clipmind.secrets import KeychainSecretStore, SecretLookupError, redact_secrets


def test_get_secret_uses_clipmind_service(mocker):
    run = mocker.patch(
        "clipmind.secrets.subprocess.run",
        return_value=subprocess.CompletedProcess([], 0, stdout="token\n", stderr=""),
    )

    store = KeychainSecretStore(service="com.kichinosukey.clipmind")

    assert store.get("preset-main-api-key") == "token"
    run.assert_called_once_with(
        [
            "/usr/bin/security",
            "find-generic-password",
            "-s",
            "com.kichinosukey.clipmind",
            "-a",
            "preset-main-api-key",
            "-w",
        ],
        capture_output=True,
        text=True,
        check=False,
    )


def test_get_secret_strips_only_trailing_newlines(mocker):
    mocker.patch(
        "clipmind.secrets.subprocess.run",
        return_value=subprocess.CompletedProcess(
            [], 0, stdout="  token value  \r\n", stderr=""
        ),
    )

    assert KeychainSecretStore().get("api-key") == "  token value  "


def test_missing_secret_does_not_expose_command_output(mocker):
    mocker.patch(
        "clipmind.secrets.subprocess.run",
        return_value=subprocess.CompletedProcess(
            [], 44, stdout="stdout-secret", stderr="stderr-secret"
        ),
    )

    with pytest.raises(SecretLookupError) as caught:
        KeychainSecretStore().get("preset-main-api-key")

    message = str(caught.value)
    assert "preset-main-api-key" in message
    assert "stdout-secret" not in message
    assert "stderr-secret" not in message


def test_empty_secret_is_unavailable(mocker):
    mocker.patch(
        "clipmind.secrets.subprocess.run",
        return_value=subprocess.CompletedProcess([], 0, stdout="\n", stderr=""),
    )

    with pytest.raises(SecretLookupError, match="api-key"):
        KeychainSecretStore().get("api-key")


def test_redact_secrets_replaces_longest_values_first():
    assert redact_secrets(
        "failed token token-123 webhook-456",
        ["token", "token-123", "webhook-456"],
    ) == "failed [REDACTED] [REDACTED] [REDACTED]"


def test_redact_secrets_ignores_empty_values_and_unrelated_text():
    assert redact_secrets("nothing sensitive", ["", None]) == "nothing sensitive"
