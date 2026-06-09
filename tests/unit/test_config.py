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


def use_missing_global_active_preset(data):
    data.pop("appProfiles", None)
    data.update(activePresetId="missing")


def test_load_runtime_config_reads_clipmind_context_length(tmp_path):
    def mutate(data):
        data["appProfiles"]["clipmind"]["settings"]["contextLength"] = 32768

    runtime = load_runtime_config(
        write_config(tmp_path, mutate),
        FakeSecrets({"quality-api": "api-secret", "discord-hook": "discord-secret"}),
    )

    assert runtime.context_length == 32768


def test_load_runtime_config_rejects_invalid_clipmind_context_length(tmp_path):
    def mutate(data):
        data["appProfiles"]["clipmind"]["settings"]["contextLength"] = True

    with pytest.raises(ConfigError, match="contextLength"):
        load_runtime_config(
            write_config(tmp_path, mutate),
            FakeSecrets({"quality-api": "api-secret", "discord-hook": "discord-secret"}),
        )


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


def test_load_runtime_config_uses_clipmind_app_profile(tmp_path):
    def mutate(data):
        data["presets"].append(
            {
                **data["presets"][0],
                "id": "clipmind-fast",
                "name": "ClipMind Fast",
                "model": "fast-model",
                "apiKeyRef": "clipmind-fast-api",
            }
        )
        data["appProfiles"] = {
            "clipmind": {
                "activePresetId": "clipmind-fast",
                "settings": data["appProfiles"]["clipmind"]["settings"],
            },
            "meeting-summary-local-llm": {"activePresetId": data["activePresetId"]},
        }

    runtime = load_runtime_config(
        write_config(tmp_path, mutate),
        FakeSecrets(
            {"clipmind-fast-api": "clipmind-fast-key", "discord-hook": "discord-secret"}
        ),
    )

    assert runtime.preset.id == "clipmind-fast"
    assert runtime.preset.model == "fast-model"
    assert runtime.preset.api_key == "clipmind-fast-key"


def test_load_runtime_config_reads_clipmind_prompts_from_app_profile_settings(tmp_path):
    def mutate(data):
        for field in (
            "summarizeSystemPrompt",
            "summarizeUserPrompt",
            "translateSystemPrompt",
            "translateUserPrompt",
        ):
            data["presets"][0].pop(field, None)
        data["appProfiles"] = {
            "clipmind": {
                "activePresetId": "quality",
                "settings": {
                    "summarizeSystemPrompt": "profile summarize system",
                    "summarizeUserPrompt": "profile summary {text}",
                    "translateSystemPrompt": "profile translate system",
                    "translateUserPrompt": "profile translate {text}",
                },
            }
        }

    runtime = load_runtime_config(
        write_config(tmp_path, mutate),
        FakeSecrets({"quality-api": "api-secret", "discord-hook": "discord-secret"}),
    )

    assert runtime.preset.summarize_system_prompt == "profile summarize system"
    assert runtime.preset.summarize_user_prompt == "profile summary {text}"
    assert runtime.preset.translate_system_prompt == "profile translate system"
    assert runtime.preset.translate_user_prompt == "profile translate {text}"


def test_load_runtime_config_keeps_legacy_preset_prompt_fallback(tmp_path):
    def mutate(data):
        data.pop("appProfiles", None)
        data["presets"][0].update(
            summarizeSystemPrompt="legacy summarize system",
            summarizeUserPrompt="legacy summary {text}",
            translateSystemPrompt="legacy translate system",
            translateUserPrompt="legacy translate {text}",
        )

    runtime = load_runtime_config(
        write_config(tmp_path, mutate),
        FakeSecrets({"quality-api": "api-secret", "discord-hook": "discord-secret"}),
    )

    assert runtime.preset.summarize_system_prompt == "legacy summarize system"
    assert runtime.preset.summarize_user_prompt == "legacy summary {text}"
    assert runtime.preset.translate_system_prompt == "legacy translate system"
    assert runtime.preset.translate_user_prompt == "legacy translate {text}"


def test_load_runtime_config_rejects_incomplete_clipmind_settings_even_with_legacy_prompts(
    tmp_path,
):
    def mutate(data):
        data["presets"][0].update(
            summarizeSystemPrompt="legacy summarize system",
            summarizeUserPrompt="legacy summary {text}",
            translateSystemPrompt="legacy translate system",
            translateUserPrompt="legacy translate {text}",
        )
        data["appProfiles"]["clipmind"]["settings"].pop("translateUserPrompt")

    with pytest.raises(ConfigError, match="translateUserPrompt"):
        load_runtime_config(
            write_config(tmp_path, mutate),
            FakeSecrets({"quality-api": "api-secret", "discord-hook": "discord-secret"}),
        )


def test_load_runtime_config_rejects_non_object_clipmind_settings(tmp_path):
    path = write_config(
        tmp_path,
        lambda data: data["appProfiles"]["clipmind"].update(settings="invalid"),
    )

    with pytest.raises(ConfigError, match=r"appProfiles\.clipmind\.settings"):
        load_runtime_config(path, FakeSecrets({"quality-api": "api-secret"}))


def test_load_runtime_config_falls_back_to_global_when_clipmind_profile_empty(tmp_path):
    path = write_config(
        tmp_path,
        lambda data: data["appProfiles"]["clipmind"].update(activePresetId=""),
    )

    runtime = load_runtime_config(
        path,
        FakeSecrets({"quality-api": "api-secret", "discord-hook": "discord-secret"}),
    )

    assert runtime.preset.id == "quality"
    assert runtime.preset.model == "model-a"


def test_load_runtime_config_rejects_missing_clipmind_app_profile_preset(tmp_path):
    path = write_config(
        tmp_path,
        lambda data: data.update(appProfiles={"clipmind": {"activePresetId": "missing"}}),
    )

    with pytest.raises(ConfigError, match="activePresetId"):
        load_runtime_config(path, FakeSecrets({"quality-api": "api-secret"}))


@pytest.mark.parametrize(
    ("mutate", "message"),
    [
        (lambda data: data.update(schemaVersion=2), "schemaVersion"),
        (use_missing_global_active_preset, "activePresetId"),
        (lambda data: data["presets"].append(data["presets"][0].copy()), "presets"),
        (
            lambda data: data["appProfiles"]["clipmind"]["settings"].update(
                summarizeUserPrompt=""
            ),
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
        lambda data: data["shared"].update(enabledDestinations=[]),
    )

    runtime = load_runtime_config(path, FakeSecrets({"quality-api": "api-secret"}))

    assert runtime.default_destinations == ()
    assert runtime.discord_webhook is None


def test_disabled_destination_secret_is_available_for_explicit_override(tmp_path):
    path = write_config(
        tmp_path,
        lambda data: data["shared"].update(enabledDestinations=[]),
    )

    runtime = load_runtime_config(
        path,
        FakeSecrets({"quality-api": "api-secret", "discord-hook": "discord-secret"}),
    )

    assert runtime.default_destinations == ()
    assert runtime.discord_webhook == "discord-secret"
