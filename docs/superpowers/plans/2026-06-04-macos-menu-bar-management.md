# ClipMind macOS Menu Bar Management Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add a native macOS menu bar management app that edits shared ClipMind presets and secrets, while the existing Python CLI, Chrome extension, and Alfred entry points continue to execute the YouTube pipeline and publish observable progress.

**Architecture:** The Python core owns the cross-entry-point runtime contract: shared JSON configuration, Keychain secret resolution, immutable per-job configuration snapshots, and atomic job-status files. A SwiftUI `MenuBarExtra` application edits the same JSON schema, stores secrets through the Security framework, discovers OpenAI-compatible models, and observes job-status files; it is never required for pipeline execution.

**Tech Stack:** Python 3.10+, pytest, macOS `/usr/bin/security`, Swift 6, SwiftUI, Foundation, Security framework, Swift Testing/XCTest, Swift Package Manager

---

## Implementation Boundaries

### Python files

- Create `clipmind/config.py`: JSON schema dataclasses, validation, active-preset resolution, immutable `RuntimeConfig`.
- Create `clipmind/secrets.py`: Keychain command adapter and secret redaction.
- Create `clipmind/jobs.py`: job state model, atomic status writer, state transitions, retention cleanup.
- Modify `clipmind/paths.py`: shared Application Support paths.
- Modify `clipmind/summarizer.py`: remove import-time `.env` globals and accept an immutable LLM configuration.
- Modify `clipmind/pipeline.py`: accept a runtime snapshot, report stages, and use configured defaults.
- Modify `clipmind/destinations/__init__.py`, `discord.py`, and `slack.py`: inject resolved webhook values instead of reading `.env`.
- Modify `native-host/clipmind_host.py` and `clipmind_runner.py`: use shared job IDs and shared configuration.
- Create `tests/fixtures/runtime/config-v1.json` and job fixtures: golden JSON
  contracts decoded by both Python and Swift tests.
- Modify existing tests and add focused unit/integration tests.

### Swift files

- Create `macos-app/Package.swift`: macOS 13+ executable and test targets.
- Create `macos-app/Sources/ClipMindMenuBar/Models/ClipMindConfig.swift`: schema matching Python JSON.
- Create `macos-app/Sources/ClipMindMenuBar/Models/JobStatus.swift`: status schema and presentation labels.
- Create `macos-app/Sources/ClipMindMenuBar/Services/ConfigStore.swift`: atomic configuration persistence and validation.
- Create `macos-app/Sources/ClipMindMenuBar/Services/KeychainStore.swift`: Security framework adapter.
- Create `macos-app/Sources/ClipMindMenuBar/Services/ModelDiscoveryClient.swift`: `{baseURL}/models` discovery.
- Create `macos-app/Sources/ClipMindMenuBar/Services/JobMonitor.swift`: status-directory polling and derived current/recent state.
- Create focused SwiftUI app and view files under `macos-app/Sources/ClipMindMenuBar/`.
- Create corresponding tests under `macos-app/Tests/ClipMindMenuBarTests/`.

## Shared Contracts

Use these values consistently in Python and Swift:

```text
Application Support root:
~/Library/Application Support/ClipMind

Configuration:
~/Library/Application Support/ClipMind/config.json

Jobs:
~/Library/Application Support/ClipMind/jobs/<jobId>.json

Keychain service:
com.kichinosukey.clipmind

Job stages:
queued
downloading_audio
transcribing_with_whisper
summarizing
translating
delivering
completed
failed
```

## Task 1: Define Shared Python Paths

**Files:**
- Modify: `clipmind/paths.py`
- Modify: `tests/unit/test_paths.py`

- [ ] **Step 1: Write failing shared-path tests**

Add tests that isolate the home directory:

```python
def test_application_support_paths(monkeypatch, tmp_path):
    monkeypatch.setattr(Path, "home", classmethod(lambda cls: tmp_path))
    import importlib
    import clipmind.paths

    paths = importlib.reload(clipmind.paths)

    assert paths.APPLICATION_SUPPORT_DIR == (
        tmp_path / "Library" / "Application Support" / "ClipMind"
    )
    assert paths.CONFIG_PATH == paths.APPLICATION_SUPPORT_DIR / "config.json"
    assert paths.JOBS_DIR == paths.APPLICATION_SUPPORT_DIR / "jobs"
```

- [ ] **Step 2: Run the focused test and verify failure**

Run:

```bash
.venv/bin/python -m pytest tests/unit/test_paths.py::test_application_support_paths -v
```

Expected: FAIL because `APPLICATION_SUPPORT_DIR`, `CONFIG_PATH`, and `JOBS_DIR` do not exist.

- [ ] **Step 3: Add shared runtime paths**

Add to `clipmind/paths.py`:

```python
APPLICATION_SUPPORT_DIR = (
    Path.home() / "Library" / "Application Support" / "ClipMind"
)
CONFIG_PATH = APPLICATION_SUPPORT_DIR / "config.json"
JOBS_DIR = APPLICATION_SUPPORT_DIR / "jobs"
KEYCHAIN_SERVICE = "com.kichinosukey.clipmind"
```

Change the existing temporary `STATUS_DIR` alias to:

```python
STATUS_DIR = JOBS_DIR
```

- [ ] **Step 4: Run path tests**

Run:

```bash
.venv/bin/python -m pytest tests/unit/test_paths.py -v
```

Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add clipmind/paths.py tests/unit/test_paths.py
git commit -m "feat: define shared ClipMind runtime paths"
```

## Task 2: Implement Keychain Secret Access and Redaction

**Files:**
- Create: `clipmind/secrets.py`
- Create: `tests/unit/test_secrets.py`

- [ ] **Step 1: Write failing Keychain and redaction tests**

Create `tests/unit/test_secrets.py`:

```python
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
    assert run.call_args.args[0] == [
        "/usr/bin/security", "find-generic-password",
        "-s", "com.kichinosukey.clipmind",
        "-a", "preset-main-api-key", "-w",
    ]


def test_missing_secret_raises_without_exposing_stderr(mocker):
    mocker.patch(
        "clipmind.secrets.subprocess.run",
        return_value=subprocess.CompletedProcess([], 44, stdout="", stderr="secret output"),
    )

    with pytest.raises(SecretLookupError, match="preset-main-api-key"):
        KeychainSecretStore().get("preset-main-api-key")


def test_redact_secrets_replaces_known_values():
    assert redact_secrets("failed token-123 webhook-456", ["token-123", "webhook-456"]) == (
        "failed [REDACTED] [REDACTED]"
    )
```

- [ ] **Step 2: Run tests and verify failure**

Run:

```bash
.venv/bin/python -m pytest tests/unit/test_secrets.py -v
```

Expected: collection FAIL because `clipmind.secrets` does not exist.

- [ ] **Step 3: Implement the secret-store boundary**

Create `clipmind/secrets.py` with:

```python
from __future__ import annotations

import subprocess
from dataclasses import dataclass
from typing import Protocol

from clipmind.paths import KEYCHAIN_SERVICE


class SecretLookupError(RuntimeError):
    pass


class SecretStore(Protocol):
    def get(self, reference: str) -> str: ...


@dataclass(frozen=True)
class KeychainSecretStore:
    service: str = KEYCHAIN_SERVICE

    def get(self, reference: str) -> str:
        result = subprocess.run(
            [
                "/usr/bin/security", "find-generic-password",
                "-s", self.service, "-a", reference, "-w",
            ],
            capture_output=True,
            text=True,
            check=False,
        )
        if result.returncode != 0:
            raise SecretLookupError(f"Keychain secret is unavailable: {reference}")
        return result.stdout.rstrip("\n")


def redact_secrets(message: str, secrets: list[str]) -> str:
    redacted = message
    for secret in sorted((s for s in secrets if s), key=len, reverse=True):
        redacted = redacted.replace(secret, "[REDACTED]")
    return redacted
```

- [ ] **Step 4: Run secret tests**

Run:

```bash
.venv/bin/python -m pytest tests/unit/test_secrets.py -v
```

Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add clipmind/secrets.py tests/unit/test_secrets.py
git commit -m "feat: add Keychain secret adapter"
```

## Task 3: Implement Shared Configuration Loading

**Files:**
- Create: `clipmind/config.py`
- Create: `tests/unit/test_config.py`
- Create: `tests/fixtures/runtime/config-v1.json`

- [ ] **Step 1: Write failing configuration tests**

Create `tests/unit/test_config.py` with fixtures that write a complete `config.json`:

```python
import json

import pytest

from clipmind.config import ConfigError, load_runtime_config


class FakeSecrets:
    def __init__(self, values):
        self.values = values

    def get(self, reference):
        return self.values[reference]


def write_config(path):
    path.write_text(json.dumps({
        "schemaVersion": 1,
        "activePresetId": "quality",
        "presets": [{
            "id": "quality",
            "name": "Quality",
            "baseURL": "http://localhost:1234/v1",
            "model": "model-a",
            "apiKeyRef": "quality-api",
            "summarizeSystemPrompt": "summarize system",
            "summarizeUserPrompt": "summary {text}",
            "translateSystemPrompt": "translate system",
            "translateUserPrompt": "translate {text}"
        }],
        "shared": {
            "whisperBinaryPath": "/opt/homebrew/bin/whisper-cli",
            "whisperModelPath": "/models/base.bin",
            "outputRoot": "/tmp/clipmind-output",
            "enabledDestinations": ["discord"],
            "discordWebhookRef": "discord-hook",
            "slackWebhookRef": None
        }
    }), encoding="utf-8")


def test_load_runtime_config_resolves_active_preset_and_secrets(tmp_path):
    path = tmp_path / "config.json"
    write_config(path)

    runtime = load_runtime_config(
        path,
        FakeSecrets({"quality-api": "api-secret", "discord-hook": "discord-secret"}),
    )

    assert runtime.preset.model == "model-a"
    assert runtime.preset.api_key == "api-secret"
    assert runtime.discord_webhook == "discord-secret"
    assert runtime.default_destinations == ("discord",)


def test_missing_active_preset_is_actionable(tmp_path):
    path = tmp_path / "config.json"
    write_config(path)
    data = json.loads(path.read_text())
    data["activePresetId"] = "missing"
    path.write_text(json.dumps(data))

    with pytest.raises(ConfigError, match="activePresetId"):
        load_runtime_config(path, FakeSecrets({}))
```

Move the representative JSON payload into
`tests/fixtures/runtime/config-v1.json`. Python tests must load this golden
fixture and override only fields relevant to each test. The same file is read
by Swift tests in Task 9 to detect cross-language schema drift.

- [ ] **Step 2: Run tests and verify failure**

Run:

```bash
.venv/bin/python -m pytest tests/unit/test_config.py -v
```

Expected: collection FAIL because `clipmind.config` does not exist.

- [ ] **Step 3: Implement immutable configuration types and loader**

Create `clipmind/config.py` defining frozen dataclasses:

```python
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
            value for value in (
                self.preset.api_key,
                self.discord_webhook,
                self.slack_webhook,
            ) if value
        ]
```

Implement `load_runtime_config(path=CONFIG_PATH, secret_store=KeychainSecretStore())`
using `json.loads`, explicit required-field validation, active preset resolution,
`Path.expanduser()` for filesystem paths, destination-name validation against
`{"discord", "slack"}`, and Keychain resolution only for configured references.
Raise `ConfigError` with the JSON field name for all validation failures.

- [ ] **Step 4: Add validation cases and run tests**

Add tests for missing config file, unsupported schema version, duplicate preset
IDs, missing required prompt, unsupported destination, and absent referenced
secret.

Run:

```bash
.venv/bin/python -m pytest tests/unit/test_config.py tests/unit/test_secrets.py -v
```

Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add clipmind/config.py tests/unit/test_config.py
git commit -m "feat: load shared ClipMind configuration"
```

## Task 4: Implement Atomic Job Progress and Retention

**Files:**
- Create: `clipmind/jobs.py`
- Create: `tests/unit/test_jobs.py`

- [ ] **Step 1: Write failing job-store tests**

Create `tests/unit/test_jobs.py`:

```python
import json

import pytest

from clipmind.jobs import JobStage, JobStatusStore, InvalidTransition


def test_job_store_writes_progress_atomically(tmp_path):
    store = JobStatusStore(tmp_path, job_id="job-1", source_url="https://youtu.be/a")
    store.transition(JobStage.DOWNLOADING_AUDIO)

    data = json.loads((tmp_path / "job-1.json").read_text())
    assert data["stage"] == "downloading_audio"
    assert not list(tmp_path.glob("*.tmp"))


def test_failure_records_failed_stage_and_redacts_secret(tmp_path):
    store = JobStatusStore(
        tmp_path, job_id="job-1", source_url="https://youtu.be/a",
        secrets=["token-123"],
    )
    store.transition(JobStage.SUMMARIZING)
    store.fail(RuntimeError("request failed token-123"))

    data = json.loads((tmp_path / "job-1.json").read_text())
    assert data["stage"] == "failed"
    assert data["failedStage"] == "summarizing"
    assert data["errorSummary"] == "request failed [REDACTED]"


def test_invalid_transition_is_rejected(tmp_path):
    store = JobStatusStore(tmp_path, job_id="job-1", source_url="https://youtu.be/a")
    with pytest.raises(InvalidTransition):
        store.transition(JobStage.TRANSLATING)
```

- [ ] **Step 2: Run tests and verify failure**

Run:

```bash
.venv/bin/python -m pytest tests/unit/test_jobs.py -v
```

Expected: collection FAIL because `clipmind.jobs` does not exist.

- [ ] **Step 3: Implement job state and atomic persistence**

Create `clipmind/jobs.py` with:

```python
class JobStage(str, Enum):
    QUEUED = "queued"
    DOWNLOADING_AUDIO = "downloading_audio"
    TRANSCRIBING_WITH_WHISPER = "transcribing_with_whisper"
    SUMMARIZING = "summarizing"
    TRANSLATING = "translating"
    DELIVERING = "delivering"
    COMPLETED = "completed"
    FAILED = "failed"
```

Implement `JobStatusStore` to:

- Write the initial queued file in `__init__`.
- Permit the approved forward state sequence and failure from any non-terminal state.
- Update title and delivery results.
- Persist camel-case JSON fields from the design.
- Write to `<jobId>.json.tmp`, flush, `os.fsync`, then `os.replace`.
- Redact all configured secret values from `errorSummary`.
- Preserve `failedStage` before transitioning to `failed`.

- [ ] **Step 4: Add retention test and implementation**

Add a test that creates 25 terminal jobs and one active job, invokes cleanup,
and asserts that only the latest 20 terminal files plus the active file remain.
Create paired `<jobId>.log` files and assert cleanup removes logs paired with
removed terminal jobs while preserving active and retained job logs. Implement
`cleanup_terminal_jobs(retain=20)` and call it from `complete()` and `fail()`.

- [ ] **Step 5: Run job tests**

Run:

```bash
.venv/bin/python -m pytest tests/unit/test_jobs.py -v
```

Expected: PASS.

- [ ] **Step 6: Commit**

```bash
git add clipmind/jobs.py tests/unit/test_jobs.py
git commit -m "feat: add observable pipeline job state"
```

## Task 5: Refactor Summarizer to Use a Runtime Snapshot

**Files:**
- Modify: `clipmind/summarizer.py`
- Modify: `tests/unit/test_summarizer.py`
- Modify: `tests/unit/test_summarizer_eli10.py`

- [ ] **Step 1: Rewrite one summarizer test around explicit configuration**

Add a fixture:

```python
@pytest.fixture
def llm_preset():
    return LLMPreset(
        id="test", name="Test", base_url="http://test/v1", model="test-model",
        api_key="test-key",
        summarize_system_prompt="summarize system",
        summarize_user_prompt="summarize {text}",
        translate_system_prompt="translate system",
        translate_user_prompt="translate {text}",
    )
```

Change the model assertion test to call:

```python
result = summarize_text("Some text", mode="summarize", preset=llm_preset)
assert result == "Mocked summary output"
assert mock_client.chat.completions.create.call_args.kwargs["model"] == "test-model"
```

- [ ] **Step 2: Run the focused test and verify failure**

Run:

```bash
.venv/bin/python -m pytest tests/unit/test_summarizer.py::TestSummarizeText::test_temperature_and_model -v
```

Expected: FAIL because `summarize_text` does not accept `preset`.

- [ ] **Step 3: Refactor summarizer dependency injection**

Remove `load_project_dotenv()`, `BASE_URL`, `API_KEY`, `MODEL`, `PROMPTS`, and
`USER_PROMPTS` from import-time runtime behavior. Change signatures to:

```python
def _call_llm(
    client: OpenAI,
    model: str,
    system_prompt: str,
    user_prompt: str,
) -> str:
    response = client.chat.completions.create(
        model=model,
        messages=[
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt},
        ],
        temperature=0.3,
    )
    return response.choices[0].message.content.strip()


def summarize_text(text: str, mode: str, preset: LLMPreset) -> str:
    if not text.strip():
        raise ValueError("Input text is empty.")
    prompts = {
        "summarize": (
            preset.summarize_system_prompt,
            preset.summarize_user_prompt,
        ),
        "translate": (
            preset.translate_system_prompt,
            preset.translate_user_prompt,
        ),
    }
    if mode not in prompts:
        raise ValueError(f"Unsupported mode: {mode}")
    client = OpenAI(base_url=preset.base_url, api_key=preset.api_key)
    system_prompt, user_template = prompts[mode]
    user_prompt = user_template.format(text=text)
    return _call_llm(client, preset.model, system_prompt, user_prompt)
```

Select prompt fields from `preset` by mode. Let library errors raise normally
instead of calling `handle_error`; only command-line boundaries may convert
errors to exit codes. Update `summarizer.main()` to call
`load_runtime_config()` and pass its active preset; direct summarizer CLI use
must not retain a hidden `.env` path.

- [ ] **Step 4: Update all summarizer tests**

Update existing tests to pass `llm_preset`, remove patches of old module globals,
and assert API errors raise their original exception.

Run:

```bash
.venv/bin/python -m pytest tests/unit/test_summarizer.py tests/unit/test_summarizer_eli10.py -v
```

Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add clipmind/summarizer.py tests/unit/test_summarizer.py tests/unit/test_summarizer_eli10.py
git commit -m "refactor: inject LLM preset into summarizer"
```

## Task 6: Inject Destination Secrets

**Files:**
- Modify: `clipmind/destinations/__init__.py`
- Modify: `clipmind/destinations/discord.py`
- Modify: `clipmind/destinations/slack.py`
- Modify: `clipmind/discord_client.py`
- Modify: `tests/unit/test_destinations.py`
- Modify: `tests/unit/test_discord_adapter.py`
- Modify: `tests/unit/test_slack_adapter.py`

- [ ] **Step 1: Write failing destination-factory tests**

Add:

```python
def test_resolve_discord_destination_injects_webhook():
    adapter = resolve_destination("discord", webhook_url="https://discord.test/hook")
    assert adapter.webhook_url == "https://discord.test/hook"


def test_resolve_slack_destination_injects_webhook():
    adapter = resolve_destination("slack", webhook_url="https://slack.test/hook")
    assert adapter.webhook_url == "https://slack.test/hook"
```

- [ ] **Step 2: Run tests and verify failure**

Run:

```bash
.venv/bin/python -m pytest tests/unit/test_destinations.py -v
```

Expected: FAIL because `resolve_destination` does not accept `webhook_url`.

- [ ] **Step 3: Implement destination injection**

Change the registry to store factory callables and resolve with:

```python
def resolve_destination(name: str, *, webhook_url: str | None) -> DestinationAdapter:
    if name not in _ADAPTERS:
        raise KeyError(f"Unknown destination: {name!r}. Available: {list(_ADAPTERS)}")
    if not webhook_url:
        raise ValueError(f"Webhook is not configured for destination: {name}")
    return _ADAPTERS[name](webhook_url=webhook_url)
```

Make `DiscordDestination` and `SlackDestination` frozen dataclasses with a
`webhook_url` field. Pass the Discord URL explicitly to
`post_clip_to_discord`. Remove `.env` loading and default webhook globals from
destination execution. Delete the existing log statements that print webhook
prefixes; no part of a webhook URL may be logged.

- [ ] **Step 4: Update and run destination tests**

Run:

```bash
.venv/bin/python -m pytest \
  tests/unit/test_destinations.py \
  tests/unit/test_discord_adapter.py \
  tests/unit/test_slack_adapter.py \
  tests/unit/test_discord_client.py -v
```

Expected: PASS and no test relies on `.env` webhook globals.

- [ ] **Step 5: Commit**

```bash
git add clipmind/destinations clipmind/discord_client.py tests/unit/test_destinations.py tests/unit/test_discord_adapter.py tests/unit/test_slack_adapter.py tests/unit/test_discord_client.py
git commit -m "refactor: inject delivery webhooks"
```

## Task 7: Integrate Runtime Configuration and Progress into the Pipeline

**Files:**
- Modify: `clipmind/pipeline.py`
- Modify: `tests/unit/test_pipeline.py`
- Modify: `tests/integration/test_pipeline_integration.py`

- [ ] **Step 1: Add a failing pipeline progress test**

Add a test using a complete `RuntimeConfig` fixture and mocked `JobStatusStore`:

```python
def test_pipeline_reports_whisper_and_llm_stages(
    mocker, runtime_config, tmp_path, ytdlp_metadata
):
    reporter = mocker.MagicMock()
    mocker.patch("clipmind.pipeline.warn_if_outdated")
    _patch_subprocess_runs(
        mocker,
        _make_subprocess_side_effect(tmp_path, ytdlp_metadata),
    )
    mocker.patch(
        "clipmind.pipeline.summarize_text",
        side_effect=["English summary", "日本語要約"],
    )
    mocker.patch("clipmind.pipeline.resolve_destination", return_value=mocker.MagicMock())
    run_pipeline(
        "https://youtu.be/test",
        config=runtime_config,
        reporter=reporter,
        outroot=str(tmp_path),
    )
    assert [call.args[0] for call in reporter.transition.call_args_list] == [
        JobStage.DOWNLOADING_AUDIO,
        JobStage.TRANSCRIBING_WITH_WHISPER,
        JobStage.SUMMARIZING,
        JobStage.TRANSLATING,
        JobStage.DELIVERING,
    ]
    reporter.complete.assert_called_once()
```

- [ ] **Step 2: Run the focused test and verify failure**

Run:

```bash
.venv/bin/python -m pytest tests/unit/test_pipeline.py::TestRunPipeline::test_pipeline_reports_whisper_and_llm_stages -v
```

Expected: FAIL because `run_pipeline` does not accept `config` or `reporter`.

- [ ] **Step 3: Change the pipeline contract**

Use:

```python
def run_pipeline(
    url: str,
    *,
    config: RuntimeConfig,
    reporter: JobStatusStore,
    destinations: list[str] | None = None,
    outroot: str | None = None,
    skip_wav_download: bool = False,
    skip_transcribe: bool = False,
) -> dict:
```

Apply these rules:

- Resolve destinations from the explicit per-job list when provided; otherwise
  use `config.default_destinations`.
- Resolve output and Whisper paths from `config`, while keeping explicit
  `outroot` only as a test/developer override.
- Pass `config.preset` to both summarizer calls.
- Inject the matching `config.discord_webhook` or `config.slack_webhook`.
- Transition immediately before each expensive stage.
- Call `reporter.set_title()` after metadata lookup.
- Call `reporter.complete(delivery_results)` after delivery.
- On any exception, call `reporter.fail(exc)` and re-raise.
- Remove all `.env` loads and `os.getenv` runtime reads from `pipeline.py`.

- [ ] **Step 4: Update pipeline and integration fixtures**

Create shared test fixtures for `LLMPreset` and `RuntimeConfig` in
`tests/conftest.py`. Update every pipeline test to pass a runtime snapshot and
reporter. Assert explicit destination selection overrides configured defaults.

Run:

```bash
.venv/bin/python -m pytest tests/unit/test_pipeline.py tests/integration/test_pipeline_integration.py -v
```

Expected: PASS.

- [ ] **Step 5: Run all Python tests before committing**

Run:

```bash
.venv/bin/python -m pytest -v
```

Expected: PASS.

- [ ] **Step 6: Commit**

```bash
git add clipmind/pipeline.py tests/conftest.py tests/unit/test_pipeline.py tests/integration/test_pipeline_integration.py
git commit -m "feat: run pipeline from shared runtime snapshot"
```

## Task 8: Cut CLI, Chrome Native Host, and Alfred over to Shared Configuration

**Files:**
- Modify: `clipmind/pipeline.py`
- Modify: `native-host/clipmind_host.py`
- Modify: `native-host/clipmind_runner.py`
- Delete: `native-host/clipmind_config.py`
- Modify: `chrome-extension/popup.js`
- Modify: `tests/unit/test_launcher.py`
- Modify: `tests/unit_native/test_clipmind_host.py`
- Modify: `tests/unit_native/test_clipmind_runner.py`
- Delete: `tests/unit_native/test_host_get_config.py`

- [ ] **Step 1: Write failing CLI-boundary and runner tests**

Add tests asserting:

```python
def test_main_loads_shared_config_and_creates_job(mocker, runtime_config):
    load = mocker.patch("clipmind.pipeline.load_runtime_config", return_value=runtime_config)
    reporter_cls = mocker.patch("clipmind.pipeline.JobStatusStore")
    run = mocker.patch("clipmind.pipeline.run_pipeline")
    mocker.patch("sys.argv", ["pipeline.py", "https://youtu.be/test"])
    assert main() == 0
    load.assert_called_once()
    reporter_cls.assert_called_once()
    run.assert_called_once()


def test_native_runner_uses_host_job_id(mocker, tmp_path, runtime_config):
    import clipmind_runner
    mocker.patch(
        "sys.argv",
        ["clipmind_runner.py", "https://youtu.be/test", "host-job-id", "discord"],
    )
    mocker.patch("clipmind_runner.load_runtime_config", return_value=runtime_config)
    reporter_cls = mocker.patch("clipmind_runner.JobStatusStore")
    reporter_cls.return_value.job_id = "host-job-id"
    mock_pipeline = mocker.patch("clipmind.pipeline.run_pipeline", return_value={"title": "Video"})
    mocker.patch("clipmind_runner.notify")
    clipmind_runner.main()
    mock_pipeline.assert_called_once()
    assert mock_pipeline.call_args.kwargs["reporter"].job_id == "host-job-id"
```

- [ ] **Step 2: Run focused tests and verify failure**

Run:

```bash
.venv/bin/python -m pytest tests/unit/test_launcher.py tests/unit_native/test_clipmind_runner.py -v
```

Expected: FAIL because entry points still load `.env` and use old status files.

- [ ] **Step 3: Implement the shared CLI boundary**

In `clipmind.pipeline.main()`:

```python
config = load_runtime_config()
job_id = uuid.uuid4().hex[:12]
reporter = JobStatusStore(
    JOBS_DIR,
    job_id=job_id,
    source_url=args.url,
    secrets=config.secrets,
)
run_pipeline(
    args.url,
    config=config,
    reporter=reporter,
    destinations=args.destinations,
)
```

Use `argparse` so `clipmind-run URL [discord,slack]` remains compatible. Catch
errors at this CLI boundary, log only redacted summaries, and return a nonzero
exit code.

- [ ] **Step 4: Simplify Native Messaging around the same contract**

- Have `clipmind_host.py` generate a job ID and invoke:
  `clipmind_runner.py <youtube_url> <job_id> [destinations]`.
- Have `clipmind_runner.py` load shared configuration, create the shared
  `JobStatusStore`, and call `run_pipeline`.
- Remove `load_project_dotenv` calls and temp status-file writing.
- Delete `clipmind_config.py` and the `get_config` Native Messaging action.
- Remove the popup's `get_config` call; leave destination checkboxes enabled and
  let missing webhook configuration fail with an actionable shared-config
  error.
- Preserve Chrome's explicit destination list.

- [ ] **Step 5: Run entry-point tests**

Run:

```bash
.venv/bin/python -m pytest \
  tests/unit/test_launcher.py \
  tests/unit_native/test_clipmind_host.py \
  tests/unit_native/test_clipmind_runner.py -v
```

Expected: PASS with no `.env` or temporary status-file assumptions.

- [ ] **Step 6: Verify no supported execution path reads `.env`**

Run:

```bash
rg -n 'load_project_dotenv|os\\.getenv\\(' \
  clipmind/pipeline.py clipmind/summarizer.py clipmind/discord_client.py \
  clipmind/destinations native-host
```

Expected: no matches.

- [ ] **Step 7: Commit**

```bash
git add clipmind/pipeline.py native-host chrome-extension/popup.js tests/unit/test_launcher.py tests/unit_native
git commit -m "feat: cut entry points over to shared configuration"
```

## Task 9: Create the Swift Package and Shared Models

**Files:**
- Create: `macos-app/Package.swift`
- Create: `macos-app/Sources/ClipMindMenuBar/Models/ClipMindConfig.swift`
- Create: `macos-app/Sources/ClipMindMenuBar/Models/JobStatus.swift`
- Create: `macos-app/Tests/ClipMindMenuBarTests/ModelDecodingTests.swift`
- Create: `tests/fixtures/runtime/job-active-v1.json`
- Create: `tests/fixtures/runtime/job-failed-v1.json`

- [ ] **Step 1: Create package manifest and failing model tests**

Create `macos-app/Package.swift`:

```swift
// swift-tools-version: 6.0
import PackageDescription

let package = Package(
    name: "ClipMindMenuBar",
    platforms: [.macOS(.v13)],
    products: [.executable(name: "ClipMindMenuBar", targets: ["ClipMindMenuBar"])],
    targets: [
        .executableTarget(name: "ClipMindMenuBar"),
        .testTarget(name: "ClipMindMenuBarTests", dependencies: ["ClipMindMenuBar"])
    ]
)
```

Create model tests that locate the repository's
`tests/fixtures/runtime/config-v1.json`, `job-active-v1.json`, and
`job-failed-v1.json` relative to `#filePath`. Decode those shared golden
fixtures and assert the active preset fields, `transcribing_with_whisper`,
failed stage, and delivery results. Python job tests must also decode the two
job fixtures so both implementations are checked against identical contracts.

- [ ] **Step 2: Run Swift tests and verify failure**

Run:

```bash
swift test --package-path macos-app
```

Expected: compile FAIL because model types do not exist.

- [ ] **Step 3: Implement Codable shared models**

Define:

```swift
struct ClipMindConfig: Codable, Equatable {
    var schemaVersion: Int
    var activePresetId: String
    var presets: [Preset]
    var shared: SharedSettings
}

struct Preset: Codable, Equatable, Identifiable {
    var id: String
    var name: String
    var baseURL: String
    var model: String
    var apiKeyRef: String
    var summarizeSystemPrompt: String
    var summarizeUserPrompt: String
    var translateSystemPrompt: String
    var translateUserPrompt: String
}

enum JobStage: String, Codable {
    case queued, downloadingAudio = "downloading_audio"
    case transcribingWithWhisper = "transcribing_with_whisper"
    case summarizing, translating, delivering, completed, failed
}
```

Add `SharedSettings`, `JobStatus`, and user-facing Japanese stage labels. Keep
property names aligned with Python camel-case JSON.

- [ ] **Step 4: Run Swift tests**

Run:

```bash
swift test --package-path macos-app
```

Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add macos-app
git commit -m "feat: define menu app shared models"
```

## Task 10: Implement Swift Configuration and Keychain Services

**Files:**
- Create: `macos-app/Sources/ClipMindMenuBar/Services/RuntimePaths.swift`
- Create: `macos-app/Sources/ClipMindMenuBar/Services/ConfigStore.swift`
- Create: `macos-app/Sources/ClipMindMenuBar/Services/KeychainStore.swift`
- Create: `macos-app/Tests/ClipMindMenuBarTests/ConfigStoreTests.swift`
- Create: `macos-app/Tests/ClipMindMenuBarTests/KeychainStoreTests.swift`

- [ ] **Step 1: Write failing ConfigStore tests**

Use a temporary root and assert:

```swift
func testSaveAndLoadRoundTrip() throws {
    let store = ConfigStore(configURL: temporaryURL.appendingPathComponent("config.json"))
    try store.save(sampleConfig)
    XCTAssertEqual(try store.load(), sampleConfig)
}

func testValidationRejectsMissingActivePreset() {
    var config = sampleConfig
    config.activePresetId = "missing"
    XCTAssertThrowsError(try ConfigStore.validate(config))
}
```

Also assert no `.tmp` file remains after save.

- [ ] **Step 2: Run tests and verify failure**

Run:

```bash
swift test --package-path macos-app --filter ConfigStoreTests
```

Expected: compile FAIL because services do not exist.

- [ ] **Step 3: Implement RuntimePaths and ConfigStore**

`RuntimePaths` must resolve:

```swift
static let applicationSupport =
    FileManager.default.homeDirectoryForCurrentUser
        .appendingPathComponent("Library/Application Support/ClipMind")
static let config = applicationSupport.appendingPathComponent("config.json")
static let jobs = applicationSupport.appendingPathComponent("jobs")
```

`ConfigStore` must validate schema version, unique preset IDs, active preset,
required fields, supported destinations, required destination references,
existence and executable permission of the Whisper binary, existence of the
Whisper model, and existence of the output directory. Save with
`Data.write(to:options:.atomic)`.

- [ ] **Step 4: Write and implement Keychain tests through an injectable backend**

Define:

```swift
protocol SecretStoring {
    func get(reference: String) throws -> String
    func set(reference: String, value: String) throws
    func delete(reference: String) throws
}
```

Implement `KeychainStore` with Security framework generic-password queries,
service `com.kichinosukey.clipmind`, and account equal to the reference.
Tests use an in-memory `SecretStoring` fake for editor/view-model behavior and
verify stable reference generation such as `preset-<id>-api-key`,
`destination-discord-webhook`, and `destination-slack-webhook`.

- [ ] **Step 5: Run service tests**

Run:

```bash
swift test --package-path macos-app --filter ConfigStoreTests
swift test --package-path macos-app --filter KeychainStoreTests
```

Expected: PASS.

- [ ] **Step 6: Commit**

```bash
git add macos-app/Sources/ClipMindMenuBar/Services macos-app/Tests/ClipMindMenuBarTests
git commit -m "feat: persist menu app settings and secrets"
```

## Task 11: Implement Model Discovery

**Files:**
- Create: `macos-app/Sources/ClipMindMenuBar/Services/ModelDiscoveryClient.swift`
- Create: `macos-app/Tests/ClipMindMenuBarTests/ModelDiscoveryClientTests.swift`

- [ ] **Step 1: Write failing URLProtocol-backed tests**

Test that:

```swift
let models = try await client.fetchModels(
    baseURL: "http://localhost:1234/v1",
    apiKey: "secret"
)
XCTAssertEqual(models, ["model-a", "model-b"])
```

The test protocol must assert a GET request to
`http://localhost:1234/v1/models` and `Authorization: Bearer secret`. Add cases
for base URLs with a trailing slash, malformed JSON, and non-2xx responses.

- [ ] **Step 2: Run tests and verify failure**

Run:

```bash
swift test --package-path macos-app --filter ModelDiscoveryClientTests
```

Expected: compile FAIL because `ModelDiscoveryClient` does not exist.

- [ ] **Step 3: Implement model discovery**

Implement an injectable `URLSession` client that decodes:

```swift
private struct ModelsResponse: Decodable {
    struct Model: Decodable { let id: String }
    let data: [Model]
}
```

Normalize the base URL, append `models`, apply bearer authentication when the
API key is non-empty, sort unique model IDs, and throw concise typed errors.
The UI must retain manual model entry when discovery fails.

- [ ] **Step 4: Run model discovery tests**

Run:

```bash
swift test --package-path macos-app --filter ModelDiscoveryClientTests
```

Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add macos-app/Sources/ClipMindMenuBar/Services/ModelDiscoveryClient.swift macos-app/Tests/ClipMindMenuBarTests/ModelDiscoveryClientTests.swift
git commit -m "feat: discover OpenAI-compatible models"
```

## Task 12: Implement Job Monitoring

**Files:**
- Create: `macos-app/Sources/ClipMindMenuBar/Services/JobMonitor.swift`
- Create: `macos-app/Tests/ClipMindMenuBarTests/JobMonitorTests.swift`

- [ ] **Step 1: Write failing derived-state tests**

Write JSON files in a temporary jobs directory and assert:

```swift
XCTAssertEqual(snapshot.activeCount, 2)
XCTAssertEqual(snapshot.currentJob?.jobId, "most-recent-active")
XCTAssertEqual(snapshot.latestTerminalJob?.jobId, "latest-failed")
```

Add malformed JSON and empty-directory cases.

- [ ] **Step 2: Run tests and verify failure**

Run:

```bash
swift test --package-path macos-app --filter JobMonitorTests
```

Expected: compile FAIL because `JobMonitor` does not exist.

- [ ] **Step 3: Implement polling monitor**

Implement `@MainActor final class JobMonitor: ObservableObject` with published
`activeCount`, `currentJob`, and `latestTerminalJob`. Use a cancellable
Foundation timer to reload `*.json` every second. Decode valid files, ignore
malformed or temporary files, select the most recently updated active job, and
select the most recently updated terminal job.

Use polling for the first version because the jobs directory is tiny and the
one-second latency is acceptable; do not add filesystem event dependencies.

- [ ] **Step 4: Run monitor tests**

Run:

```bash
swift test --package-path macos-app --filter JobMonitorTests
```

Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add macos-app/Sources/ClipMindMenuBar/Services/JobMonitor.swift macos-app/Tests/ClipMindMenuBarTests/JobMonitorTests.swift
git commit -m "feat: monitor ClipMind job progress"
```

## Task 13: Build the Menu Bar and Settings UI

**Files:**
- Create: `macos-app/Sources/ClipMindMenuBar/ClipMindMenuBarApp.swift`
- Create: `macos-app/Sources/ClipMindMenuBar/ViewModels/SettingsViewModel.swift`
- Create: `macos-app/Sources/ClipMindMenuBar/Views/MenuContentView.swift`
- Create: `macos-app/Sources/ClipMindMenuBar/Views/SettingsView.swift`
- Create: `macos-app/Sources/ClipMindMenuBar/Views/PresetEditorView.swift`
- Create: `macos-app/Sources/ClipMindMenuBar/Views/SharedSettingsView.swift`
- Create: `macos-app/Sources/ClipMindMenuBar/Views/StatusView.swift`
- Create: `macos-app/Tests/ClipMindMenuBarTests/SettingsViewModelTests.swift`

- [ ] **Step 1: Write failing view-model tests**

Test behaviors rather than SwiftUI rendering:

```swift
func testSelectingPresetPersistsActivePreset() throws {
    let viewModel = makeViewModel(config: sampleConfig)
    try viewModel.selectPreset(id: "fast")
    XCTAssertEqual(viewModel.config.activePresetId, "fast")
    XCTAssertEqual(try configStore.load().activePresetId, "fast")
}

func testDuplicatePresetCreatesUniqueIdAndSecretReference() throws {
    let duplicate = try viewModel.duplicatePreset(id: "quality")
    XCTAssertNotEqual(duplicate.id, "quality")
    XCTAssertEqual(duplicate.apiKeyRef, "preset-\(duplicate.id)-api-key")
}
```

Add tests for deleting the active preset, required-field validation, saving API
keys/webhooks, model discovery success, and model discovery failure preserving
manual model input. Deleting the only preset must be rejected; deleting the
active preset when others exist must select and persist the first remaining
preset.

- [ ] **Step 2: Run tests and verify failure**

Run:

```bash
swift test --package-path macos-app --filter SettingsViewModelTests
```

Expected: compile FAIL because `SettingsViewModel` does not exist.

- [ ] **Step 3: Implement SettingsViewModel**

The view model must:

- Load config or expose a first-run empty configuration.
- Add, duplicate, delete, edit, and select presets.
- Validate before saving.
- Save secrets through `SecretStoring`, never in published config values.
- Fetch models through `ModelDiscoveryClient`.
- Use successful model discovery as the endpoint connection test and expose a
  separate `Test Connection` action that does not change the selected model.
- Expose concise errors suitable for the settings UI.
- Provide file-picker URLs for Whisper binary, Whisper model, and output root.

- [ ] **Step 4: Implement the SwiftUI app and views**

Use:

```swift
@main
struct ClipMindMenuBarApp: App {
    @StateObject private var jobs = JobMonitor()

    var body: some Scene {
        MenuBarExtra("ClipMind", systemImage: "text.badge.checkmark") {
            MenuContentView()
                .environmentObject(jobs)
        }
        Settings {
            SettingsView()
                .environmentObject(jobs)
        }
    }
}
```

The menu content shows an active-preset picker, active count, current
stage/title, latest terminal result, Settings, and Quit. The settings window
uses tabs for Presets, Shared Settings, and Status. Keep detailed logs, retry,
cancellation, and history controls out of scope.

- [ ] **Step 5: Run all Swift tests and build**

Run:

```bash
swift test --package-path macos-app
swift build --package-path macos-app
```

Expected: all tests PASS and build succeeds.

- [ ] **Step 6: Launch and manually inspect**

Run:

```bash
swift run --package-path macos-app ClipMindMenuBar
```

Expected:

- ClipMind appears in the menu bar.
- Settings opens and persists a manually entered preset.
- API keys and webhooks do not appear in `config.json`.
- The app can quit without affecting later CLI execution.

- [ ] **Step 7: Commit**

```bash
git add macos-app
git commit -m "feat: add ClipMind menu bar management app"
```

## Task 14: Documentation, Cutover Verification, and Regression

**Files:**
- Modify: `README.md`
- Delete: `.env.example`
- Create: `macos-app/README.md`
- Modify: `tests/integration/test_multi_dest_pipeline.py`

- [ ] **Step 1: Update integration test for explicit destination override**

Ensure the configured default is one destination while the invocation explicitly
requests both, then assert both adapters are invoked. Run:

```bash
.venv/bin/python -m pytest tests/integration/test_multi_dest_pipeline.py -v
```

Expected: PASS.

- [ ] **Step 2: Document the explicit cutover**

Update `README.md` to state:

- New executions require shared configuration and Keychain.
- `.env` is no longer read by CLI, Chrome, Alfred, pipeline, summarizer, or
  destination adapters.
- First-time settings are entered manually in the menu app.
- How to launch the app with `swift run --package-path macos-app ClipMindMenuBar`.
- How to verify Whisper binary/model paths.
- How to diagnose concise job status versus detailed existing job logs.

Delete `.env.example` after the cutover because no supported or documented
execution path consumes it. Do not describe automatic migration.

- [ ] **Step 3: Run full verification**

Run:

```bash
.venv/bin/python -m pytest -v
swift test --package-path macos-app
swift build --package-path macos-app
rg -n 'load_project_dotenv|os\\.getenv\\(' \
  clipmind/pipeline.py clipmind/summarizer.py clipmind/discord_client.py \
  clipmind/destinations native-host
```

Expected:

- Python tests PASS.
- Swift tests PASS.
- Swift build succeeds.
- The `rg` command returns no matches.

- [ ] **Step 4: Perform manual cross-entry-point checks**

Verify:

```text
1. Create two presets in the menu app.
2. Select preset A and start a CLI job.
3. Switch to preset B while job A is running.
4. Confirm job A continues with preset A and the next job uses preset B.
5. Quit the menu app and run clipmind-run successfully.
6. Start a Chrome right-click job and confirm its explicit destination choices.
7. Start an Alfred job and confirm it uses the active preset.
8. Inspect config.json and jobs/*.json for absence of API keys and webhook URLs.
```

- [ ] **Step 5: Commit**

```bash
git add -A README.md .env.example macos-app/README.md tests/integration/test_multi_dest_pipeline.py
git commit -m "docs: document ClipMind shared configuration cutover"
```

## Final Review Gate

Before merging, use `superpowers:requesting-code-review` and review from these
four perspectives:

```text
Architecture:
- Menu app closure cannot prevent CLI/Chrome/Alfred execution.
- Runtime config is immutable for the duration of a job.

Security:
- Secrets exist only in Keychain and in-memory runtime snapshots.
- Logs and job JSON redact API keys and webhook URLs.

Operations:
- Failed stage is visible and terminal job files are bounded.
- Detailed per-job logs are removed when their terminal job JSON is pruned.
- Whisper binary/model errors are actionable before transcription.

Compatibility:
- Existing YouTube pipeline behavior remains.
- Chrome per-job destination selection overrides shared defaults.
```

Then run the full verification commands from Task 14 again before claiming
completion.
