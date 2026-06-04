"""Tests for shared ClipMind runtime configuration."""

import json
from pathlib import Path

import pytest

from clipmind.config import ConfigError, load_runtime_config
from clipmind.secrets import SecretLookupError


FIXTURE = Path(__file__).parents[1] / "fixtures" / "runtime" / "config-v1.json"


class FakeSecrets:
    def __init__(self, values):
        self.values = values

    def get(self, reference):
        try:
            return self.values[reference]
        except KeyError as exc:
            raise SecretLookupError(reference) from exc


def write_config(tmp_path, mutate=None):
    data = json.loads(FIXTURE.read_text(encoding="utf-8"))
    if mutate:
        mutate(data)
    path = tmp_path / "config.json"
    path.write_text(json.dumps(data), encoding="utf-8")
    return path


def test_load_runtime_config_resolves_active_preset_and_secrets(tmp_path):
    runtime = load_runtime_config(
        write_config(tmp_path),
        FakeSecrets({"quality-api": "api-secret", "discord-hook": "discord-secret"}),
    )

    assert runtime.preset.model == "model-a"
    assert runtime.preset.api_key == "api-secret"
    assert runtime.discord_webhook == "discord-secret"
    assert runtime.slack_webhook is None
    assert runtime.default_destinations == ("discord",)
    assert runtime.secrets == ["api-secret", "discord-secret"]


@pytest.mark.parametrize(
    ("mutate", "message"),
    [
        (lambda data: data.update(schemaVersion=2), "schemaVersion"),
        (lambda data: data.update(activePresetId="missing"), "activePresetId"),
        (lambda data: data["presets"].append(data["presets"][0].copy()), "presets"),
        (
            lambda data: data["presets"][0].update(summarizeUserPrompt=""),
            "summarizeUserPrompt",
        ),
        (
            lambda data: data["shared"].update(enabledDestinations=["email"]),
            "enabledDestinations",
        ),
    ],
)
def test_invalid_configuration_is_actionable(tmp_path, mutate, message):
    with pytest.raises(ConfigError, match=message):
        load_runtime_config(write_config(tmp_path, mutate), FakeSecrets({}))


def test_missing_config_file_is_actionable(tmp_path):
    with pytest.raises(ConfigError, match="config"):
        load_runtime_config(tmp_path / "missing.json", FakeSecrets({}))


def test_invalid_json_is_actionable(tmp_path):
    path = tmp_path / "config.json"
    path.write_text("{", encoding="utf-8")

    with pytest.raises(ConfigError, match="JSON"):
        load_runtime_config(path, FakeSecrets({}))


def test_missing_referenced_secret_is_actionable(tmp_path):
    with pytest.raises(ConfigError, match="quality-api"):
        load_runtime_config(write_config(tmp_path), FakeSecrets({}))


def test_unconfigured_destination_secret_is_not_loaded(tmp_path):
    path = write_config(
        tmp_path,
        lambda data: data["shared"].update(
            enabledDestinations=[], discordWebhookRef=None
        ),
    )

    runtime = load_runtime_config(path, FakeSecrets({"quality-api": "api-secret"}))

    assert runtime.default_destinations == ()
    assert runtime.discord_webhook is None
