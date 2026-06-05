# Shared Local LLM Config Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Let `meeting-summary-local-llm` consume ClipMind's active LLM preset while keeping existing CLI and environment-variable overrides intact.

**Architecture:** Add a small local shared-preset reader to `meeting-summary-local-llm` instead of extracting a package yet. The reader loads `~/Library/Application Support/ClipMind/config.json`, resolves the active preset, optionally reads the API key from macOS Keychain, and returns values only when explicit CLI/env values are absent. ClipMind keeps the current storage path and gains UI/docs wording that identifies LLM presets as shared local AI settings.

**Tech Stack:** Python 3 standard library, pytest, SwiftUI, Swift Package Manager, macOS Keychain via `/usr/bin/security`.

---

## File Structure

- Create `mentalbase/projects/meeting-summary-local-llm/scripts/shared_llm_config.py`
  - Responsibility: load ClipMind's active LLM preset and resolve its Keychain secret without importing ClipMind.
- Modify `mentalbase/projects/meeting-summary-local-llm/scripts/run_meeting_summary.py`
  - Responsibility: merge CLI args, env vars, shared preset, and defaults in the approved precedence order.
- Create `mentalbase/projects/meeting-summary-local-llm/tests/test_shared_llm_config.py`
  - Responsibility: focused unit tests for config parsing, missing files, malformed data, and Keychain behavior.
- Modify `mentalbase/projects/meeting-summary-local-llm/tests/test_run_meeting_summary.py`
  - Responsibility: integration-level precedence tests for `run_meeting_summary.main()`.
- Modify `projects/clipmind/macos-app/Sources/ClipMindMenuBar/Views/SettingsView.swift`
  - Responsibility: rename the preset tab from generic "Presets" to "LLM Presets".
- Modify `projects/clipmind/macos-app/Sources/ClipMindMenuBar/Views/PresetEditorView.swift`
  - Responsibility: add short UI copy that explains presets are shared across local AI tools.
- Modify `projects/clipmind/macos-app/Tests/ClipMindMenuBarTests/SharedContractTests.swift`
  - Responsibility: assert the Swift contract still exposes the fields needed by external consumers.
- Modify `projects/clipmind/macos-app/README.md`
  - Responsibility: document the shared-preset interpretation without renaming the app.

## Task 1: Add Meeting Summary Shared Preset Reader

**Files:**
- Create: `/Users/kichinosukey-mba/mentalbase/projects/meeting-summary-local-llm/scripts/shared_llm_config.py`
- Create: `/Users/kichinosukey-mba/mentalbase/projects/meeting-summary-local-llm/tests/test_shared_llm_config.py`

- [ ] **Step 1: Write failing tests for missing, valid, invalid, and Keychain behavior**

Create `/Users/kichinosukey-mba/mentalbase/projects/meeting-summary-local-llm/tests/test_shared_llm_config.py` with:

```python
from __future__ import annotations

import json
from pathlib import Path

import pytest

from scripts.shared_llm_config import (
    SharedLLMPreset,
    keychain_lookup,
    load_shared_llm_preset,
)


def write_config(path: Path, payload: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload), encoding="utf-8")


def valid_config() -> dict:
    return {
        "schemaVersion": 1,
        "activePresetId": "preset-1",
        "presets": [
            {
                "id": "preset-1",
                "name": "Local Qwen",
                "baseURL": "http://localhost:1234/v1",
                "model": "qwen3-8b-mlx",
                "apiKeyRef": "preset-1-api-key",
                "summarizeSystemPrompt": "",
                "summarizeUserPrompt": "",
                "translateSystemPrompt": "",
                "translateUserPrompt": "",
            }
        ],
        "shared": {
            "whisperBinaryPath": "/opt/homebrew/bin/whisper-cli",
            "whisperModelPath": "/tmp/ggml-base.en.bin",
            "outputRoot": "/tmp/out",
            "enabledDestinations": [],
            "discordWebhookRef": None,
            "slackWebhookRef": None,
        },
    }


def test_missing_config_returns_none(tmp_path: Path) -> None:
    assert load_shared_llm_preset(tmp_path / "missing.json") is None


def test_valid_config_returns_active_preset_without_keychain(tmp_path: Path) -> None:
    config_path = tmp_path / "Application Support" / "ClipMind" / "config.json"
    write_config(config_path, valid_config())

    preset = load_shared_llm_preset(config_path, secret_lookup=lambda _ref: None)

    assert preset == SharedLLMPreset(
        base_url="http://localhost:1234/v1",
        model="qwen3-8b-mlx",
        api_token=None,
        timeout=None,
        context_length=None,
    )


def test_valid_config_resolves_keychain_secret(tmp_path: Path) -> None:
    config_path = tmp_path / "config.json"
    write_config(config_path, valid_config())

    preset = load_shared_llm_preset(config_path, secret_lookup=lambda ref: f"secret:{ref}")

    assert preset is not None
    assert preset.api_token == "secret:preset-1-api-key"


def test_optional_timeout_and_context_length_are_read_when_present(tmp_path: Path) -> None:
    config = valid_config()
    config["presets"][0]["timeout"] = 900
    config["presets"][0]["contextLength"] = 32768
    config_path = tmp_path / "config.json"
    write_config(config_path, config)

    preset = load_shared_llm_preset(config_path, secret_lookup=lambda _ref: None)

    assert preset is not None
    assert preset.timeout == 900
    assert preset.context_length == 32768


@pytest.mark.parametrize(
    "payload",
    [
        {},
        {"schemaVersion": 2, "activePresetId": "preset-1", "presets": []},
        {"schemaVersion": 1, "activePresetId": "missing", "presets": []},
        {"schemaVersion": 1, "activePresetId": "preset-1", "presets": [{"id": "preset-1"}]},
    ],
)
def test_invalid_or_unsupported_config_returns_none(tmp_path: Path, payload: dict) -> None:
    config_path = tmp_path / "config.json"
    write_config(config_path, payload)

    assert load_shared_llm_preset(config_path) is None


def test_malformed_json_returns_none(tmp_path: Path) -> None:
    config_path = tmp_path / "config.json"
    config_path.write_text("{", encoding="utf-8")

    assert load_shared_llm_preset(config_path) is None


def test_keychain_lookup_returns_none_when_security_fails(monkeypatch: pytest.MonkeyPatch) -> None:
    class Result:
        returncode = 44
        stdout = ""

    def fake_run(*_args, **_kwargs):
        return Result()

    monkeypatch.setattr("scripts.shared_llm_config.subprocess.run", fake_run)

    assert keychain_lookup("missing-ref") is None
```

- [ ] **Step 2: Run tests to verify they fail**

Run:

```bash
cd /Users/kichinosukey-mba/mentalbase/projects/meeting-summary-local-llm
.venv/bin/pytest tests/test_shared_llm_config.py -v
```

Expected: FAIL with `ModuleNotFoundError: No module named 'scripts.shared_llm_config'`.

- [ ] **Step 3: Implement the reader**

Create `/Users/kichinosukey-mba/mentalbase/projects/meeting-summary-local-llm/scripts/shared_llm_config.py`:

```python
from __future__ import annotations

import json
import subprocess
from dataclasses import dataclass
from pathlib import Path
from typing import Callable, Any


KEYCHAIN_SERVICE = "com.kichinosukey.clipmind"
DEFAULT_CONFIG_PATH = (
    Path.home() / "Library" / "Application Support" / "ClipMind" / "config.json"
)


@dataclass(frozen=True)
class SharedLLMPreset:
    base_url: str | None
    model: str | None
    api_token: str | None
    timeout: int | None
    context_length: int | None


SecretLookup = Callable[[str], str | None]


def keychain_lookup(reference: str) -> str | None:
    result = subprocess.run(
        [
            "/usr/bin/security",
            "find-generic-password",
            "-s",
            KEYCHAIN_SERVICE,
            "-a",
            reference,
            "-w",
        ],
        check=False,
        capture_output=True,
        text=True,
    )
    if result.returncode != 0:
        return None
    value = result.stdout.rstrip("\r\n")
    return value or None


def _optional_int(value: Any) -> int | None:
    if value is None:
        return None
    if isinstance(value, bool):
        return None
    if isinstance(value, int):
        return value
    return None


def _optional_text(value: Any) -> str | None:
    if not isinstance(value, str):
        return None
    stripped = value.strip()
    return stripped or None


def load_shared_llm_preset(
    config_path: Path = DEFAULT_CONFIG_PATH,
    *,
    secret_lookup: SecretLookup = keychain_lookup,
) -> SharedLLMPreset | None:
    try:
        raw = json.loads(config_path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return None

    if not isinstance(raw, dict) or raw.get("schemaVersion") != 1:
        return None

    active_id = raw.get("activePresetId")
    presets = raw.get("presets")
    if not isinstance(active_id, str) or not isinstance(presets, list):
        return None

    active = next(
        (preset for preset in presets if isinstance(preset, dict) and preset.get("id") == active_id),
        None,
    )
    if active is None:
        return None

    base_url = _optional_text(active.get("baseURL"))
    model = _optional_text(active.get("model"))
    api_key_ref = _optional_text(active.get("apiKeyRef"))
    if base_url is None or model is None or api_key_ref is None:
        return None

    return SharedLLMPreset(
        base_url=base_url,
        model=model,
        api_token=secret_lookup(api_key_ref),
        timeout=_optional_int(active.get("timeout")),
        context_length=_optional_int(active.get("contextLength")),
    )
```

- [ ] **Step 4: Run tests to verify they pass**

Run:

```bash
cd /Users/kichinosukey-mba/mentalbase/projects/meeting-summary-local-llm
.venv/bin/pytest tests/test_shared_llm_config.py -v
```

Expected: PASS, all tests in `tests/test_shared_llm_config.py`.

- [ ] **Step 5: Commit**

Run:

```bash
cd /Users/kichinosukey-mba/mentalbase/projects/meeting-summary-local-llm
git add scripts/shared_llm_config.py tests/test_shared_llm_config.py
git commit -m "feat: read shared local llm preset"
```

## Task 2: Apply Shared Preset In Meeting Summary Precedence

**Files:**
- Modify: `/Users/kichinosukey-mba/mentalbase/projects/meeting-summary-local-llm/scripts/run_meeting_summary.py`
- Modify: `/Users/kichinosukey-mba/mentalbase/projects/meeting-summary-local-llm/tests/test_run_meeting_summary.py`

- [ ] **Step 1: Write failing precedence tests**

Add this fixture after `clean_lm_env` in `/Users/kichinosukey-mba/mentalbase/projects/meeting-summary-local-llm/tests/test_run_meeting_summary.py`:

```python
@pytest.fixture
def fake_shared_preset(monkeypatch: pytest.MonkeyPatch) -> SimpleNamespace:
    preset = SimpleNamespace(
        base_url="http://shared.example/v1",
        model="shared-model",
        api_token="shared-token",
        timeout=777,
        context_length=12345,
    )
    monkeypatch.setattr(uut, "load_shared_llm_preset", lambda: preset)
    return preset
```

Add these tests near existing `main()` tests:

```python
def test_main_uses_shared_preset_when_args_and_env_missing(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
    clean_lm_env: None,
    fake_shared_preset: SimpleNamespace,
) -> None:
    transcript = make_transcript(tmp_path)
    args = make_args(transcript)
    patch_main_common(monkeypatch, args)
    calls: list[dict[str, object]] = []

    def fake_chat(base_url, token, model, input_text, system_prompt, temperature,
                  max_output_tokens, context_length, timeout, reasoning=None):
        calls.append(
            {
                "base_url": base_url,
                "token": token,
                "model": model,
                "context_length": context_length,
                "timeout": timeout,
                "reasoning": reasoning,
            }
        )
        return VALID_RESPONSE

    monkeypatch.setattr(uut, "chat", fake_chat)

    assert uut.main() == 0

    assert calls == [
        {
            "base_url": "http://shared.example/v1",
            "token": "shared-token",
            "model": "shared-model",
            "context_length": 12345,
            "timeout": 777,
            "reasoning": None,
        }
    ]
    assert extract_result_fields(capsys.readouterr().out)["status"] == "success"


def test_main_cli_args_override_shared_preset(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    clean_lm_env: None,
    fake_shared_preset: SimpleNamespace,
) -> None:
    transcript = make_transcript(tmp_path)
    args = make_args(
        transcript,
        base_url="http://cli.example/v1",
        model="cli-model",
        timeout=111,
        context_length=222,
    )
    patch_main_common(monkeypatch, args)
    calls: list[dict[str, object]] = []

    def fake_chat(base_url, token, model, input_text, system_prompt, temperature,
                  max_output_tokens, context_length, timeout, reasoning=None):
        calls.append(
            {
                "base_url": base_url,
                "token": token,
                "model": model,
                "context_length": context_length,
                "timeout": timeout,
            }
        )
        return VALID_RESPONSE

    monkeypatch.setattr(uut, "chat", fake_chat)

    assert uut.main() == 0

    assert calls[0] == {
        "base_url": "http://cli.example/v1",
        "token": "shared-token",
        "model": "cli-model",
        "context_length": 222,
        "timeout": 111,
    }


def test_main_env_vars_override_shared_preset(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    clean_lm_env: None,
    fake_shared_preset: SimpleNamespace,
) -> None:
    transcript = make_transcript(tmp_path)
    args = make_args(transcript)
    patch_main_common(monkeypatch, args)
    monkeypatch.setenv("LM_API_TOKEN", "env-token")
    monkeypatch.setenv("LM_BASE_URL", "http://env.example/v1")
    monkeypatch.setenv("LM_MODEL", "env-model")
    monkeypatch.setenv("LM_TIMEOUT", "333")
    monkeypatch.setenv("LM_CONTEXT_LENGTH", "444")
    calls: list[dict[str, object]] = []

    def fake_chat(base_url, token, model, input_text, system_prompt, temperature,
                  max_output_tokens, context_length, timeout, reasoning=None):
        calls.append(
            {
                "base_url": base_url,
                "token": token,
                "model": model,
                "context_length": context_length,
                "timeout": timeout,
            }
        )
        return VALID_RESPONSE

    monkeypatch.setattr(uut, "chat", fake_chat)

    assert uut.main() == 0

    assert calls[0] == {
        "base_url": "http://env.example/v1",
        "token": "env-token",
        "model": "env-model",
        "context_length": 444,
        "timeout": 333,
    }


def test_main_missing_shared_preset_keeps_existing_defaults(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    clean_lm_env: None,
) -> None:
    transcript = make_transcript(tmp_path)
    args = make_args(transcript)
    patch_main_common(monkeypatch, args)
    monkeypatch.setattr(uut, "load_shared_llm_preset", lambda: None)
    monkeypatch.setattr(uut, "select_model", lambda base_url, token, timeout: "auto-model")
    calls: list[dict[str, object]] = []

    def fake_chat(base_url, token, model, input_text, system_prompt, temperature,
                  max_output_tokens, context_length, timeout, reasoning=None):
        calls.append(
            {
                "base_url": base_url,
                "token": token,
                "model": model,
                "context_length": context_length,
                "timeout": timeout,
            }
        )
        return VALID_RESPONSE

    monkeypatch.setattr(uut, "chat", fake_chat)

    assert uut.main() == 0

    assert calls[0] == {
        "base_url": "http://localhost:1234",
        "token": None,
        "model": "auto-model",
        "context_length": None,
        "timeout": 600,
    }
```

- [ ] **Step 2: Run tests to verify they fail**

Run:

```bash
cd /Users/kichinosukey-mba/mentalbase/projects/meeting-summary-local-llm
.venv/bin/pytest tests/test_run_meeting_summary.py -v -k "shared_preset or missing_shared"
```

Expected: FAIL because `run_meeting_summary` does not import `load_shared_llm_preset` yet and still ignores shared presets.

- [ ] **Step 3: Import and apply shared preset**

In `/Users/kichinosukey-mba/mentalbase/projects/meeting-summary-local-llm/scripts/run_meeting_summary.py`, add this import after the existing `urllib` imports:

```python
from shared_llm_config import load_shared_llm_preset
```

Replace the LLM resolution block in `main()` from:

```python
    token = os.getenv("LM_API_TOKEN")
    env_base_url = os.getenv("LM_BASE_URL")
    base_url = (args.base_url or env_base_url or "http://localhost:1234").rstrip("/")
    env_timeout = os.getenv("LM_TIMEOUT")
    try:
        timeout = args.timeout or (int(env_timeout) if env_timeout else 600)
    except ValueError:
        print("[ERROR] LM_TIMEOUT must be an integer (seconds)", file=sys.stderr)
        print_result_line("failure", 1, None, None)
        return 1

    model = args.model or os.getenv("LM_MODEL")
    reasoning = args.reasoning or os.getenv("LM_REASONING") or None
    if args.context_length is None:
        env_ctx = os.getenv("LM_CONTEXT_LENGTH")
        if env_ctx:
            try:
                args.context_length = int(env_ctx)
            except ValueError:
                print("[ERROR] LM_CONTEXT_LENGTH must be an integer", file=sys.stderr)
                print_result_line("failure", 1, None, None)
                return 1
```

with:

```python
    shared_preset = load_shared_llm_preset()

    token = os.getenv("LM_API_TOKEN") or (
        shared_preset.api_token if shared_preset else None
    )
    env_base_url = os.getenv("LM_BASE_URL")
    shared_base_url = shared_preset.base_url if shared_preset else None
    base_url = (args.base_url or env_base_url or shared_base_url or "http://localhost:1234").rstrip("/")

    env_timeout = os.getenv("LM_TIMEOUT")
    try:
        timeout = args.timeout or (
            int(env_timeout)
            if env_timeout
            else shared_preset.timeout if shared_preset and shared_preset.timeout else 600
        )
    except ValueError:
        print("[ERROR] LM_TIMEOUT must be an integer (seconds)", file=sys.stderr)
        print_result_line("failure", 1, None, None)
        return 1

    model = args.model or os.getenv("LM_MODEL") or (
        shared_preset.model if shared_preset else None
    )
    reasoning = args.reasoning or os.getenv("LM_REASONING") or None
    if args.context_length is None:
        env_ctx = os.getenv("LM_CONTEXT_LENGTH")
        if env_ctx:
            try:
                args.context_length = int(env_ctx)
            except ValueError:
                print("[ERROR] LM_CONTEXT_LENGTH must be an integer", file=sys.stderr)
                print_result_line("failure", 1, None, None)
                return 1
        elif shared_preset and shared_preset.context_length:
            args.context_length = shared_preset.context_length
```

- [ ] **Step 4: Run focused tests**

Run:

```bash
cd /Users/kichinosukey-mba/mentalbase/projects/meeting-summary-local-llm
.venv/bin/pytest tests/test_shared_llm_config.py tests/test_run_meeting_summary.py -v -k "shared_preset or missing_shared"
```

Expected: PASS for the shared-preset tests.

- [ ] **Step 5: Run full meeting-summary tests**

Run:

```bash
cd /Users/kichinosukey-mba/mentalbase/projects/meeting-summary-local-llm
.venv/bin/pytest tests -q
```

Expected: PASS for the full test suite. If unrelated tests fail, capture the failing test names and output before deciding whether they are in scope.

- [ ] **Step 6: Commit**

Run:

```bash
cd /Users/kichinosukey-mba/mentalbase/projects/meeting-summary-local-llm
git add scripts/run_meeting_summary.py tests/test_run_meeting_summary.py
git commit -m "feat: use shared llm preset for meeting summaries"
```

## Task 3: Clarify ClipMind UI As Shared LLM Preset Owner

**Files:**
- Modify: `/Users/kichinosukey-mba/projects/clipmind/macos-app/Sources/ClipMindMenuBar/Views/SettingsView.swift`
- Modify: `/Users/kichinosukey-mba/projects/clipmind/macos-app/Sources/ClipMindMenuBar/Views/PresetEditorView.swift`
- Modify: `/Users/kichinosukey-mba/projects/clipmind/macos-app/Tests/ClipMindMenuBarTests/SharedContractTests.swift`
- Modify: `/Users/kichinosukey-mba/projects/clipmind/macos-app/README.md`

- [ ] **Step 1: Write a Swift contract test for external LLM fields**

Append this test method to `SharedContractTests` in `/Users/kichinosukey-mba/projects/clipmind/macos-app/Tests/ClipMindMenuBarTests/SharedContractTests.swift`:

```swift
    func testPresetContractContainsExternalLLMFields() throws {
        let json = """
        {
          "schemaVersion": 1,
          "activePresetId": "preset-1",
          "presets": [
            {
              "id": "preset-1",
              "name": "Shared Local",
              "baseURL": "http://localhost:1234/v1",
              "model": "qwen3-8b-mlx",
              "apiKeyRef": "preset-1-api-key",
              "summarizeSystemPrompt": "",
              "summarizeUserPrompt": "",
              "translateSystemPrompt": "",
              "translateUserPrompt": ""
            }
          ],
          "shared": {
            "whisperBinaryPath": "/opt/homebrew/bin/whisper-cli",
            "whisperModelPath": "/tmp/ggml-base.en.bin",
            "outputRoot": "/tmp/out",
            "enabledDestinations": []
          }
        }
        """.data(using: .utf8)!

        let config = try JSONDecoder().decode(ClipMindConfig.self, from: json)
        let preset = try XCTUnwrap(config.presets.first)

        XCTAssertEqual(config.activePresetId, "preset-1")
        XCTAssertEqual(preset.baseURL, "http://localhost:1234/v1")
        XCTAssertEqual(preset.model, "qwen3-8b-mlx")
        XCTAssertEqual(preset.apiKeyRef, "preset-1-api-key")
    }
```

- [ ] **Step 2: Run Swift tests**

Run:

```bash
cd /Users/kichinosukey-mba/projects/clipmind
swift test --package-path macos-app
```

Expected: PASS. This test should pass before UI edits because it captures the existing schema contract.

- [ ] **Step 3: Update Settings tab label**

In `/Users/kichinosukey-mba/projects/clipmind/macos-app/Sources/ClipMindMenuBar/Views/SettingsView.swift`, replace:

```swift
            PresetEditorView().tabItem { Label("Presets", systemImage: "slider.horizontal.3") }
```

with:

```swift
            PresetEditorView().tabItem { Label("LLM Presets", systemImage: "slider.horizontal.3") }
```

- [ ] **Step 4: Add explanatory copy to the preset editor**

In `/Users/kichinosukey-mba/projects/clipmind/macos-app/Sources/ClipMindMenuBar/Views/PresetEditorView.swift`, inside `VStack(alignment: .leading) {` and before the `if let index = ...` block, insert:

```swift
                Text("LLM presets are shared by ClipMind and other personal local AI tools.")
                    .font(.caption)
                    .foregroundStyle(.secondary)
```

- [ ] **Step 5: Document shared preset interpretation**

In `/Users/kichinosukey-mba/projects/clipmind/macos-app/README.md`, add this paragraph after the sentence that mentions `~/Library/Application Support/ClipMind/config.json` and Keychain:

```markdown
The LLM preset section is intentionally treated as a shared local AI preset contract. Other personal tools may read the active preset for `baseURL`, `model`, and `apiKeyRef` while ClipMind-specific settings such as Whisper paths, output root, and destinations remain ClipMind-owned.
```

- [ ] **Step 6: Run ClipMind verification**

Run:

```bash
cd /Users/kichinosukey-mba/projects/clipmind
swift test --package-path macos-app
swift build --package-path macos-app
.venv/bin/python -m pytest -q
```

Expected: Swift tests pass, Swift build succeeds, Python tests pass.

- [ ] **Step 7: Commit**

Run:

```bash
cd /Users/kichinosukey-mba/projects/clipmind
git add macos-app/Sources/ClipMindMenuBar/Views/SettingsView.swift macos-app/Sources/ClipMindMenuBar/Views/PresetEditorView.swift macos-app/Tests/ClipMindMenuBarTests/SharedContractTests.swift macos-app/README.md
git commit -m "docs: clarify shared llm presets"
```

## Task 4: Manual Smoke Test Shared Preset Flow

**Files:**
- No source changes expected.

- [ ] **Step 1: Confirm ClipMind config exists**

Run:

```bash
ls "$HOME/Library/Application Support/ClipMind/config.json"
```

Expected: prints the config path.

- [ ] **Step 2: Run meeting summary with no LLM env overrides in mock mode**

Run:

```bash
cd /Users/kichinosukey-mba/mentalbase/projects/meeting-summary-local-llm
env -u LM_API_TOKEN -u LM_BASE_URL -u LM_MODEL -u LM_TIMEOUT -u LM_CONTEXT_LENGTH .venv/bin/python scripts/run_meeting_summary.py --input tests/fixtures/sample_transcript.txt --mock --output-dir /tmp/meeting-summary-shared-preset-smoke
```

Expected: command exits 0 and prints `[RESULT] status=success ...`.

- [ ] **Step 3: Run focused non-mock check with a short timeout only if LM Studio is running**

Run:

```bash
curl -sS http://localhost:1234/v1/models
```

Expected if LM Studio is running: JSON containing a model list. If this fails, skip Step 4 and record that live LLM verification was not available.

- [ ] **Step 4: Run meeting summary using the shared preset against the local server**

Run:

```bash
cd /Users/kichinosukey-mba/mentalbase/projects/meeting-summary-local-llm
env -u LM_API_TOKEN -u LM_BASE_URL -u LM_MODEL -u LM_TIMEOUT -u LM_CONTEXT_LENGTH .venv/bin/python scripts/run_meeting_summary.py --input tests/fixtures/sample_transcript.txt --timeout 30 --output-dir /tmp/meeting-summary-shared-preset-live
```

Expected: command exits 0 and prints `[RESULT] status=success ...`. If it fails because the selected model is not loaded or the local server is unavailable, capture the error and do not change code unless the failure contradicts the precedence tests.

- [ ] **Step 5: Final status check**

Run:

```bash
git -C /Users/kichinosukey-mba/projects/clipmind status --short --branch
git -C /Users/kichinosukey-mba/mentalbase/projects/meeting-summary-local-llm status --short --branch
```

Expected: only intended commits are ahead of their remotes; no unexpected modified files remain.

## Self-Review

- Spec coverage: The plan implements shared LLM connection settings only, preserves existing CLI/env precedence, keeps ClipMind storage in place, avoids `.env` migration, uses Keychain refs, and defers package extraction.
- Placeholder scan: No task uses `TBD`, `TODO`, "implement later", or unspecified test instructions.
- Type consistency: Python uses `base_url`, `api_token`, `context_length`; Swift keeps `baseURL`, `apiKeyRef`; JSON keeps the existing ClipMind camelCase contract.
