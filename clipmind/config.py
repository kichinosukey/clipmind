"""Shared runtime configuration for every ClipMind entry point."""

from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from clipmind.paths import CONFIG_PATH
from clipmind.secrets import KeychainSecretStore, SecretLookupError, SecretStore

SUPPORTED_DESTINATIONS = {"discord", "slack"}
CLIPMIND_APP_ID = "clipmind"


class ConfigError(RuntimeError):
    """Raised when shared configuration cannot produce a runtime snapshot."""


@dataclass(frozen=True)
class LLMPreset:
    id: str
    name: str
    base_url: str
    model: str
    api_key: str
    summarize_system_prompt: str
    summarize_user_prompt: str
    translate_system_prompt: str
    translate_user_prompt: str


@dataclass(frozen=True)
class RuntimeConfig:
    preset: LLMPreset
    whisper_binary_path: str
    whisper_model_path: str
    output_root: str
    default_destinations: tuple[str, ...]
    discord_webhook: str | None
    slack_webhook: str | None

    @property
    def secrets(self) -> list[str]:
        return [
            value
            for value in (
                self.preset.api_key,
                self.discord_webhook,
                self.slack_webhook,
            )
            if value
        ]


def _required_text(data: dict[str, Any], field: str, context: str = "") -> str:
    value = data.get(field)
    if not isinstance(value, str) or not value.strip():
        prefix = f"{context}." if context else ""
        raise ConfigError(f"Required configuration field is missing: {prefix}{field}")
    return value


def _optional_reference(data: dict[str, Any], field: str) -> str | None:
    value = data.get(field)
    if value is None:
        return None
    if not isinstance(value, str) or not value.strip():
        raise ConfigError(f"Invalid configuration field: shared.{field}")
    return value


def _app_profile(raw: dict[str, Any], app_id: str) -> dict[str, Any]:
    app_profiles = raw.get("appProfiles")
    if not isinstance(app_profiles, dict):
        return {}
    profile = app_profiles.get(app_id)
    if not isinstance(profile, dict):
        return {}
    return profile


def _app_settings(raw: dict[str, Any], app_id: str) -> dict[str, Any] | None:
    profile = _app_profile(raw, app_id)
    if "settings" not in profile:
        return None
    settings = profile["settings"]
    if not isinstance(settings, dict):
        raise ConfigError(
            f"Configuration field appProfiles.{app_id}.settings must be an object"
        )
    return settings


def _active_preset_id(raw: dict[str, Any], app_id: str) -> str:
    profile = _app_profile(raw, app_id)
    app_active = profile.get("activePresetId")
    if isinstance(app_active, str) and app_active.strip():
        return app_active
    return _required_text(raw, "activePresetId")


def _prompt_source(
    settings: dict[str, Any] | None,
    legacy_preset: dict[str, Any],
    context: str,
) -> tuple[dict[str, Any], str]:
    if settings is not None:
        return settings, context
    return legacy_preset, f"presets.{legacy_preset['id']}"


def _load_secret(store: SecretStore, reference: str) -> str:
    try:
        return store.get(reference)
    except SecretLookupError as exc:
        raise ConfigError(f"Configured secret is unavailable: {reference}") from exc


def _load_optional_secret(store: SecretStore, reference: str | None) -> str | None:
    if not reference:
        return None
    try:
        return _load_secret(store, reference)
    except ConfigError:
        return None


def load_runtime_config(
    path: Path = CONFIG_PATH,
    secret_store: SecretStore | None = None,
) -> RuntimeConfig:
    """Validate shared JSON and resolve an immutable per-job runtime snapshot."""

    config_path = Path(path)
    store = secret_store or KeychainSecretStore()
    try:
        raw = json.loads(config_path.read_text(encoding="utf-8"))
    except FileNotFoundError as exc:
        raise ConfigError(f"Shared config file is missing: {config_path}") from exc
    except (OSError, json.JSONDecodeError) as exc:
        raise ConfigError(f"Shared config JSON is invalid: {config_path}") from exc

    if not isinstance(raw, dict):
        raise ConfigError("Shared config JSON root must be an object")
    if raw.get("schemaVersion") != 1:
        raise ConfigError("Unsupported schemaVersion; expected 1")

    presets = raw.get("presets")
    if not isinstance(presets, list) or not presets:
        raise ConfigError("Configuration field presets must be a non-empty list")
    if not all(isinstance(preset, dict) for preset in presets):
        raise ConfigError("Every presets item must be an object")

    preset_ids = [_required_text(preset, "id", "presets") for preset in presets]
    if len(preset_ids) != len(set(preset_ids)):
        raise ConfigError("Configuration field presets contains duplicate IDs")

    active_id = _active_preset_id(raw, CLIPMIND_APP_ID)
    active = next((preset for preset in presets if preset["id"] == active_id), None)
    if active is None:
        raise ConfigError(f"activePresetId does not match a preset: {active_id}")

    api_key_ref = _required_text(active, "apiKeyRef", f"presets.{active_id}")
    clipmind_settings = _app_settings(raw, CLIPMIND_APP_ID)
    prompt_source, prompt_context = _prompt_source(
        clipmind_settings,
        active,
        f"appProfiles.{CLIPMIND_APP_ID}.settings",
    )
    preset_values = {
        "name": _required_text(active, "name", f"presets.{active_id}"),
        "base_url": _required_text(active, "baseURL", f"presets.{active_id}"),
        "model": _required_text(active, "model", f"presets.{active_id}"),
        "summarize_system_prompt": _required_text(
            prompt_source,
            "summarizeSystemPrompt",
            prompt_context,
        ),
        "summarize_user_prompt": _required_text(
            prompt_source,
            "summarizeUserPrompt",
            prompt_context,
        ),
        "translate_system_prompt": _required_text(
            prompt_source,
            "translateSystemPrompt",
            prompt_context,
        ),
        "translate_user_prompt": _required_text(
            prompt_source,
            "translateUserPrompt",
            prompt_context,
        ),
    }

    shared = raw.get("shared")
    if not isinstance(shared, dict):
        raise ConfigError("Configuration field shared must be an object")
    destinations = shared.get("enabledDestinations")
    if not isinstance(destinations, list) or not all(
        isinstance(name, str) for name in destinations
    ):
        raise ConfigError("shared.enabledDestinations must be a list of strings")
    if len(destinations) != len(set(destinations)):
        raise ConfigError("shared.enabledDestinations contains duplicates")
    unsupported = set(destinations) - SUPPORTED_DESTINATIONS
    if unsupported:
        raise ConfigError(
            f"shared.enabledDestinations contains unsupported values: {sorted(unsupported)}"
        )

    discord_ref = _optional_reference(shared, "discordWebhookRef")
    slack_ref = _optional_reference(shared, "slackWebhookRef")
    if "discord" in destinations and not discord_ref:
        raise ConfigError("shared.discordWebhookRef is required when discord is enabled")
    if "slack" in destinations and not slack_ref:
        raise ConfigError("shared.slackWebhookRef is required when slack is enabled")

    llm_preset = LLMPreset(
        id=active_id,
        api_key=_load_secret(store, api_key_ref),
        **preset_values,
    )

    return RuntimeConfig(
        preset=llm_preset,
        whisper_binary_path=str(
            Path(_required_text(shared, "whisperBinaryPath", "shared")).expanduser()
        ),
        whisper_model_path=str(
            Path(_required_text(shared, "whisperModelPath", "shared")).expanduser()
        ),
        output_root=str(Path(_required_text(shared, "outputRoot", "shared")).expanduser()),
        default_destinations=tuple(destinations),
        discord_webhook=(
            _load_secret(store, discord_ref)
            if "discord" in destinations and discord_ref
            else _load_optional_secret(store, discord_ref)
        ),
        slack_webhook=(
            _load_secret(store, slack_ref)
            if "slack" in destinations and slack_ref
            else _load_optional_secret(store, slack_ref)
        ),
    )
