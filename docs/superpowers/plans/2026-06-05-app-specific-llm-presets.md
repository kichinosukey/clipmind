# App-Specific LLM Presets Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Let ClipMind and Meeting Summary choose different active LLM presets through an `Apps` settings tab backed by `appProfiles`.

**Architecture:** Extend the existing ClipMind config schema additively with optional app profile mappings. ClipMind uses `appProfiles.clipmind.activePresetId` before global `activePresetId`; Meeting Summary uses `appProfiles.meeting-summary-local-llm.activePresetId` before global `activePresetId`, while preserving CLI/env precedence. Preset definitions, Keychain references, and app-specific non-LLM settings remain unchanged.

**Tech Stack:** SwiftUI, Swift Codable, XCTest, Python 3 standard library, pytest, Ruff.

---

## Implementation Review Before Coding

This is a cross-repo behavior change, so review the plan from these perspectives before implementation:

- Backward compatibility: existing configs without `appProfiles` must decode and behave unchanged.
- User mental model: `Apps` selects which existing LLM preset each app uses; it does not create separate per-app preset lists.
- Safety: deleting a preset must not leave an app profile pointing at a missing preset.
- Reader tolerance: Meeting Summary must fail softly on missing or invalid app profiles and still honor CLI/env overrides.
- Scope control: do not move Whisper, output paths, destinations, Slack, Notion, styles, or routing into `Apps`.

## File Structure

- Modify `/Users/kichinosukey-mba/projects/clipmind/macos-app/Sources/ClipMindMenuBar/Models/ClipMindConfig.swift`
  - Add `appProfiles` and app profile model types.
- Modify `/Users/kichinosukey-mba/projects/clipmind/macos-app/Sources/ClipMindMenuBar/Services/ConfigStore.swift`
  - Validate non-empty app profile preset IDs.
- Modify `/Users/kichinosukey-mba/projects/clipmind/macos-app/Sources/ClipMindMenuBar/ViewModels/SettingsViewModel.swift`
  - Add app-specific preset helpers and clear deleted references.
- Create `/Users/kichinosukey-mba/projects/clipmind/macos-app/Sources/ClipMindMenuBar/Views/AppProfilesView.swift`
  - Add the Apps tab UI.
- Modify `/Users/kichinosukey-mba/projects/clipmind/macos-app/Sources/ClipMindMenuBar/Views/SettingsView.swift`
  - Add `Apps` tab.
- Modify `/Users/kichinosukey-mba/projects/clipmind/clipmind/config.py`
  - Resolve ClipMind app-specific preset.
- Modify `/Users/kichinosukey-mba/projects/clipmind/tests/unit/test_config.py`
  - Cover ClipMind app profile fallback and override.
- Modify `/Users/kichinosukey-mba/projects/clipmind/macos-app/Tests/ClipMindMenuBarTests/ConfigStoreTests.swift`
  - Cover Swift validation and deletion behavior.
- Modify `/Users/kichinosukey-mba/projects/clipmind/macos-app/Tests/ClipMindMenuBarTests/SharedContractTests.swift`
  - Cover decoding config with and without `appProfiles`.
- Modify `/Users/kichinosukey-mba/mentalbase/projects/meeting-summary-local-llm/scripts/shared_llm_config.py`
  - Resolve Meeting Summary app-specific preset.
- Modify `/Users/kichinosukey-mba/mentalbase/projects/meeting-summary-local-llm/tests/test_shared_llm_config.py`
  - Cover app profile override/fallback/invalid cases.
- Modify `/Users/kichinosukey-mba/mentalbase/projects/meeting-summary-local-llm/tests/test_run_meeting_summary.py`
  - Ensure CLI/env tests still override app-specific preset.

## Task 1: Swift Config Schema, Validation, and Apps UI

**Files:**
- Modify: `/Users/kichinosukey-mba/projects/clipmind/macos-app/Sources/ClipMindMenuBar/Models/ClipMindConfig.swift`
- Modify: `/Users/kichinosukey-mba/projects/clipmind/macos-app/Sources/ClipMindMenuBar/Services/ConfigStore.swift`
- Modify: `/Users/kichinosukey-mba/projects/clipmind/macos-app/Sources/ClipMindMenuBar/ViewModels/SettingsViewModel.swift`
- Create: `/Users/kichinosukey-mba/projects/clipmind/macos-app/Sources/ClipMindMenuBar/Views/AppProfilesView.swift`
- Modify: `/Users/kichinosukey-mba/projects/clipmind/macos-app/Sources/ClipMindMenuBar/Views/SettingsView.swift`
- Modify: `/Users/kichinosukey-mba/projects/clipmind/macos-app/Tests/ClipMindMenuBarTests/ConfigStoreTests.swift`
- Modify: `/Users/kichinosukey-mba/projects/clipmind/macos-app/Tests/ClipMindMenuBarTests/SharedContractTests.swift`

- [ ] **Step 1: Write failing Swift tests for app profiles**

Append these tests to `ConfigStoreTests`:

```swift
    func testValidationAcceptsAppProfilePresetReferences() throws {
        var (config, root) = try validConfig()
        defer { try? FileManager.default.removeItem(at: root) }
        let secondary = Preset(
            id: "meeting", name: "Meeting", baseURL: "http://localhost:1234/v1",
            model: "model-b", apiKeyRef: "meeting-api",
            summarizeSystemPrompt: "system", summarizeUserPrompt: "{text}",
            translateSystemPrompt: "system", translateUserPrompt: "{text}"
        )
        config.presets.append(secondary)
        config.appProfiles = [
            "clipmind": AppProfile(activePresetId: config.activePresetId),
            "meeting-summary-local-llm": AppProfile(activePresetId: secondary.id),
        ]

        XCTAssertNoThrow(try ConfigStore.validate(config))
    }

    func testValidationRejectsMissingAppProfilePresetReference() throws {
        var (config, root) = try validConfig()
        defer { try? FileManager.default.removeItem(at: root) }
        config.appProfiles = [
            "meeting-summary-local-llm": AppProfile(activePresetId: "missing")
        ]

        XCTAssertThrowsError(try ConfigStore.validate(config))
    }

    func testDeletePresetClearsAppSpecificReference() throws {
        let viewModel = SettingsViewModel()
        let clipmind = Preset(
            id: "clipmind", name: "ClipMind", baseURL: "http://localhost:1234/v1",
            model: "model-a", apiKeyRef: "clipmind-api",
            summarizeSystemPrompt: "summary", summarizeUserPrompt: "{text}",
            translateSystemPrompt: "translate", translateUserPrompt: "{text}"
        )
        let meeting = Preset(
            id: "meeting", name: "Meeting", baseURL: "http://localhost:1234/v1",
            model: "model-b", apiKeyRef: "meeting-api",
            summarizeSystemPrompt: "summary", summarizeUserPrompt: "{text}",
            translateSystemPrompt: "translate", translateUserPrompt: "{text}"
        )
        viewModel.config.presets = [clipmind, meeting]
        viewModel.config.activePresetId = clipmind.id
        viewModel.config.appProfiles = [
            "meeting-summary-local-llm": AppProfile(activePresetId: meeting.id)
        ]

        viewModel.deletePreset(meeting.id)

        XCTAssertEqual(viewModel.config.appProfiles["meeting-summary-local-llm"]?.activePresetId, "")
    }
```

Append this test to `SharedContractTests`:

```swift
    func testDecodesConfigWithAppProfiles() throws {
        let json = """
        {
          "schemaVersion": 1,
          "activePresetId": "preset-1",
          "presets": [
            {
              "id": "preset-1",
              "name": "Default",
              "baseURL": "http://localhost:1234/v1",
              "model": "default-model",
              "apiKeyRef": "preset-1-api-key",
              "summarizeSystemPrompt": "",
              "summarizeUserPrompt": "",
              "translateSystemPrompt": "",
              "translateUserPrompt": ""
            },
            {
              "id": "meeting",
              "name": "Meeting",
              "baseURL": "http://localhost:1234/v1",
              "model": "meeting-model",
              "apiKeyRef": "meeting-api-key",
              "summarizeSystemPrompt": "",
              "summarizeUserPrompt": "",
              "translateSystemPrompt": "",
              "translateUserPrompt": ""
            }
          ],
          "appProfiles": {
            "meeting-summary-local-llm": { "activePresetId": "meeting" }
          },
          "shared": {
            "whisperBinaryPath": "/opt/homebrew/bin/whisper-cli",
            "whisperModelPath": "/tmp/ggml-base.en.bin",
            "outputRoot": "/tmp/out",
            "enabledDestinations": []
          }
        }
        """.data(using: .utf8)!

        let config = try JSONDecoder().decode(ClipMindConfig.self, from: json)

        XCTAssertEqual(config.appProfiles["meeting-summary-local-llm"]?.activePresetId, "meeting")
    }
```

- [ ] **Step 2: Run Swift tests and verify failure**

Run:

```bash
cd /Users/kichinosukey-mba/projects/clipmind
swift test --package-path macos-app
```

Expected: FAIL because `AppProfile` and `ClipMindConfig.appProfiles` do not exist.

- [ ] **Step 3: Add Swift schema types**

Update `ClipMindConfig.swift`:

```swift
struct ClipMindConfig: Codable, Equatable {
    var schemaVersion: Int
    var activePresetId: String
    var presets: [Preset]
    var appProfiles: [String: AppProfile]
    var shared: SharedSettings

    enum CodingKeys: String, CodingKey {
        case schemaVersion
        case activePresetId
        case presets
        case appProfiles
        case shared
    }

    init(
        schemaVersion: Int,
        activePresetId: String,
        presets: [Preset],
        appProfiles: [String: AppProfile] = [:],
        shared: SharedSettings
    ) {
        self.schemaVersion = schemaVersion
        self.activePresetId = activePresetId
        self.presets = presets
        self.appProfiles = appProfiles
        self.shared = shared
    }

    init(from decoder: Decoder) throws {
        let container = try decoder.container(keyedBy: CodingKeys.self)
        schemaVersion = try container.decode(Int.self, forKey: .schemaVersion)
        activePresetId = try container.decode(String.self, forKey: .activePresetId)
        presets = try container.decode([Preset].self, forKey: .presets)
        appProfiles = try container.decodeIfPresent([String: AppProfile].self, forKey: .appProfiles) ?? [:]
        shared = try container.decode(SharedSettings.self, forKey: .shared)
    }

    static let empty = ClipMindConfig(
        schemaVersion: 1, activePresetId: "", presets: [], appProfiles: [:],
        shared: SharedSettings(
            whisperBinaryPath: "", whisperModelPath: "", outputRoot: "",
            enabledDestinations: [], discordWebhookRef: nil, slackWebhookRef: nil
        )
    )
}

struct AppProfile: Codable, Equatable {
    var activePresetId: String
}
```

- [ ] **Step 4: Validate app profile references**

In `ConfigStore.validate(_:)`, after the global active preset check, add:

```swift
        let presetIdSet = Set(config.presets.map(\.id))
        for (appId, profile) in config.appProfiles {
            let trimmed = profile.activePresetId.trimmingCharacters(in: .whitespacesAndNewlines)
            guard trimmed.isEmpty || presetIdSet.contains(trimmed) else {
                throw ConfigStoreError.invalid("App profile active preset is missing: \(appId)")
            }
        }
```

- [ ] **Step 5: Add SettingsViewModel app helpers and deletion cleanup**

In `SettingsViewModel.swift`, add:

```swift
    let supportedAppProfiles: [(id: String, name: String)] = [
        ("clipmind", "ClipMind"),
        ("meeting-summary-local-llm", "Meeting Summary"),
    ]

    func appPresetId(for appId: String) -> String {
        config.appProfiles[appId]?.activePresetId ?? ""
    }

    func setAppPresetId(_ presetId: String, for appId: String) {
        config.appProfiles[appId] = AppProfile(activePresetId: presetId)
        save()
    }
```

Update `deletePreset(_:)` so that after removing the preset and fixing global `activePresetId`, it clears app references to the deleted ID:

```swift
        for appId in config.appProfiles.keys {
            if config.appProfiles[appId]?.activePresetId == id {
                config.appProfiles[appId] = AppProfile(activePresetId: "")
            }
        }
```

- [ ] **Step 6: Add Apps UI**

Create `AppProfilesView.swift`:

```swift
import SwiftUI

struct AppProfilesView: View {
    @EnvironmentObject var settings: SettingsViewModel

    var body: some View {
        Form {
            Section {
                Text("Choose which LLM preset each app uses. Default falls back to the global active preset.")
                    .font(.caption)
                    .foregroundStyle(.secondary)
            }
            ForEach(settings.supportedAppProfiles, id: \.id) { app in
                Section(app.name) {
                    Picker(
                        "LLM preset",
                        selection: Binding(
                            get: { settings.appPresetId(for: app.id) },
                            set: { settings.setAppPresetId($0, for: app.id) }
                        )
                    ) {
                        Text("Default").tag("")
                        ForEach(settings.config.presets) { preset in
                            Text(preset.name).tag(preset.id)
                        }
                    }
                }
            }
            if let error = settings.errorMessage {
                Text(error).foregroundStyle(.red)
            }
        }
        .padding()
    }
}
```

Update `SettingsView.swift`:

```swift
            AppProfilesView().tabItem { Label("Apps", systemImage: "app.connected.to.app.below.fill") }
```

Insert the Apps tab between `LLM Presets` and `Shared`.

- [ ] **Step 7: Run Swift tests**

Run:

```bash
cd /Users/kichinosukey-mba/projects/clipmind
swift test --package-path macos-app
```

Expected: PASS.

- [ ] **Step 8: Run Swift build**

Run:

```bash
cd /Users/kichinosukey-mba/projects/clipmind
swift build --package-path macos-app
```

Expected: build succeeds.

- [ ] **Step 9: Commit**

Run:

```bash
cd /Users/kichinosukey-mba/projects/clipmind
git add macos-app/Sources/ClipMindMenuBar/Models/ClipMindConfig.swift macos-app/Sources/ClipMindMenuBar/Services/ConfigStore.swift macos-app/Sources/ClipMindMenuBar/ViewModels/SettingsViewModel.swift macos-app/Sources/ClipMindMenuBar/Views/AppProfilesView.swift macos-app/Sources/ClipMindMenuBar/Views/SettingsView.swift macos-app/Tests/ClipMindMenuBarTests/ConfigStoreTests.swift macos-app/Tests/ClipMindMenuBarTests/SharedContractTests.swift
git commit -m "feat: add app-specific llm preset settings"
```

## Task 2: ClipMind Runtime Uses ClipMind App Profile

**Files:**
- Modify: `/Users/kichinosukey-mba/projects/clipmind/clipmind/config.py`
- Modify: `/Users/kichinosukey-mba/projects/clipmind/tests/unit/test_config.py`

- [ ] **Step 1: Write failing Python tests for ClipMind app profile resolution**

In `tests/unit/test_config.py`, add tests following the existing fixture style. Add this helper if none exists:

```python
def with_app_profiles(config: dict, profiles: dict) -> dict:
    updated = dict(config)
    updated["appProfiles"] = profiles
    return updated
```

Add tests:

```python
def test_load_runtime_config_uses_clipmind_app_profile(tmp_path, fake_secret_store):
    config = valid_config(tmp_path)
    config["presets"].append({
        **config["presets"][0],
        "id": "clipmind-fast",
        "name": "ClipMind Fast",
        "model": "fast-model",
        "apiKeyRef": "clipmind-fast-api",
    })
    config["appProfiles"] = {
        "clipmind": {"activePresetId": "clipmind-fast"},
        "meeting-summary-local-llm": {"activePresetId": config["activePresetId"]},
    }
    fake_secret_store.values["clipmind-fast-api"] = "clipmind-fast-key"
    path = write_config(tmp_path, config)

    runtime = load_runtime_config(path, secret_store=fake_secret_store)

    assert runtime.preset.id == "clipmind-fast"
    assert runtime.preset.model == "fast-model"
    assert runtime.preset.api_key == "clipmind-fast-key"


def test_load_runtime_config_falls_back_to_global_when_clipmind_profile_empty(tmp_path, fake_secret_store):
    config = valid_config(tmp_path)
    config["appProfiles"] = {"clipmind": {"activePresetId": ""}}
    path = write_config(tmp_path, config)

    runtime = load_runtime_config(path, secret_store=fake_secret_store)

    assert runtime.preset.id == config["activePresetId"]
```

Use the exact helper names already present in `test_config.py`; if names differ, adapt the test code to the local file while preserving assertions.

- [ ] **Step 2: Run tests and verify failure**

Run:

```bash
cd /Users/kichinosukey-mba/projects/clipmind
.venv/bin/python -m pytest tests/unit/test_config.py -q
```

Expected: FAIL because `load_runtime_config` ignores `appProfiles.clipmind`.

- [ ] **Step 3: Implement app-specific preset selection**

In `clipmind/config.py`, add:

```python
CLIPMIND_APP_ID = "clipmind"


def _active_preset_id(raw: dict[str, Any], app_id: str) -> str:
    app_profiles = raw.get("appProfiles")
    if isinstance(app_profiles, dict):
        profile = app_profiles.get(app_id)
        if isinstance(profile, dict):
            app_active = profile.get("activePresetId")
            if isinstance(app_active, str) and app_active.strip():
                return app_active
    return _required_text(raw, "activePresetId")
```

Replace:

```python
    active_id = _required_text(raw, "activePresetId")
```

with:

```python
    active_id = _active_preset_id(raw, CLIPMIND_APP_ID)
```

Do not change missing preset behavior: if the app-specific ID is non-empty but missing from `presets`, raise `ConfigError`.

- [ ] **Step 4: Run focused tests**

Run:

```bash
cd /Users/kichinosukey-mba/projects/clipmind
.venv/bin/python -m pytest tests/unit/test_config.py -q
```

Expected: PASS.

- [ ] **Step 5: Run broader ClipMind Python tests**

Run:

```bash
cd /Users/kichinosukey-mba/projects/clipmind
.venv/bin/python -m pytest -q
```

Expected: PASS.

- [ ] **Step 6: Commit**

Run:

```bash
cd /Users/kichinosukey-mba/projects/clipmind
git add clipmind/config.py tests/unit/test_config.py
git commit -m "feat: resolve clipmind app preset"
```

## Task 3: Meeting Summary Uses Meeting App Profile

**Files:**
- Modify: `/Users/kichinosukey-mba/mentalbase/projects/meeting-summary-local-llm/scripts/shared_llm_config.py`
- Modify: `/Users/kichinosukey-mba/mentalbase/projects/meeting-summary-local-llm/tests/test_shared_llm_config.py`
- Modify: `/Users/kichinosukey-mba/mentalbase/projects/meeting-summary-local-llm/tests/test_run_meeting_summary.py`

- [ ] **Step 1: Write failing tests for Meeting Summary app profile resolution**

In `tests/test_shared_llm_config.py`, add a second preset helper inside `valid_config()` tests by appending where needed. Add tests:

```python
def test_meeting_summary_app_profile_overrides_global_active_preset(tmp_path: Path) -> None:
    config = valid_config()
    config["presets"].append(
        {
            **config["presets"][0],
            "id": "meeting",
            "name": "Meeting",
            "model": "meeting-model",
            "apiKeyRef": "meeting-api-key",
        }
    )
    config["appProfiles"] = {
        "meeting-summary-local-llm": {"activePresetId": "meeting"},
        "clipmind": {"activePresetId": "preset-1"},
    }
    config_path = tmp_path / "config.json"
    write_config(config_path, config)

    preset = load_shared_llm_preset(config_path, secret_lookup=lambda ref: f"secret:{ref}")

    assert preset is not None
    assert preset.model == "meeting-model"
    assert preset.api_token == "secret:meeting-api-key"


@pytest.mark.parametrize(
    "profile",
    [
        {},
        {"meeting-summary-local-llm": {"activePresetId": ""}},
        {"meeting-summary-local-llm": {"activePresetId": "missing"}},
    ],
)
def test_meeting_summary_app_profile_falls_back_to_global(tmp_path: Path, profile: dict) -> None:
    config = valid_config()
    config["appProfiles"] = profile
    config_path = tmp_path / "config.json"
    write_config(config_path, config)

    preset = load_shared_llm_preset(config_path, secret_lookup=lambda _ref: None)

    assert preset is not None
    assert preset.model == "qwen3-8b-mlx"
```

In `tests/test_run_meeting_summary.py`, keep existing CLI/env override tests unchanged unless they fail. They should continue to prove outer precedence because `fake_shared_preset` stands in for the resolved app-specific preset.

- [ ] **Step 2: Run tests and verify failure**

Run:

```bash
cd /Users/kichinosukey-mba/mentalbase/projects/meeting-summary-local-llm
.venv/bin/pytest tests/test_shared_llm_config.py -v -k "app_profile"
```

Expected: FAIL because `load_shared_llm_preset` still uses global `activePresetId`.

- [ ] **Step 3: Implement app-specific selection with soft fallback**

In `scripts/shared_llm_config.py`, add:

```python
MEETING_SUMMARY_APP_ID = "meeting-summary-local-llm"


def _active_preset_id(payload: dict[str, Any], app_id: str) -> str | None:
    global_active = payload.get("activePresetId")
    if not isinstance(global_active, str) or global_active == "":
        return None
    app_profiles = payload.get("appProfiles")
    if isinstance(app_profiles, dict):
        profile = app_profiles.get(app_id)
        if isinstance(profile, dict):
            app_active = profile.get("activePresetId")
            if isinstance(app_active, str) and app_active != "":
                return app_active
    return global_active
```

Replace the direct `activePresetId` read with `_active_preset_id(payload, MEETING_SUMMARY_APP_ID)`.

After `_find_active_preset(...)`, if the app-specific ID was missing, fallback to global active preset. One clear implementation is:

```python
    active_preset_id = _active_preset_id(payload, MEETING_SUMMARY_APP_ID)
    if active_preset_id is None:
        return None

    active_preset = _find_active_preset(presets, active_preset_id)
    if active_preset is None and active_preset_id != payload.get("activePresetId"):
        active_preset_id = payload.get("activePresetId")
        active_preset = (
            _find_active_preset(presets, active_preset_id)
            if isinstance(active_preset_id, str)
            else None
        )
    if active_preset is None:
        return None
```

This keeps invalid app-specific references soft for Meeting Summary.

- [ ] **Step 4: Run focused tests**

Run:

```bash
cd /Users/kichinosukey-mba/mentalbase/projects/meeting-summary-local-llm
.venv/bin/pytest tests/test_shared_llm_config.py -v
```

Expected: PASS.

- [ ] **Step 5: Run Meeting Summary focused integration tests and lint**

Run:

```bash
cd /Users/kichinosukey-mba/mentalbase/projects/meeting-summary-local-llm
.venv/bin/pytest tests/test_shared_llm_config.py tests/test_run_meeting_summary.py -q
.venv/bin/python -m ruff format scripts/shared_llm_config.py tests/test_shared_llm_config.py tests/test_run_meeting_summary.py
.venv/bin/python -m ruff check scripts/shared_llm_config.py tests/test_shared_llm_config.py tests/test_run_meeting_summary.py
.venv/bin/python -m ruff format --check scripts/shared_llm_config.py tests/test_shared_llm_config.py tests/test_run_meeting_summary.py
```

Expected: tests pass and Ruff passes.

- [ ] **Step 6: Commit**

Run:

```bash
cd /Users/kichinosukey-mba/mentalbase/projects/meeting-summary-local-llm
git add scripts/shared_llm_config.py tests/test_shared_llm_config.py tests/test_run_meeting_summary.py
git commit -m "feat: resolve meeting summary app preset"
```

## Task 4: Manual Smoke And Final Verification

**Files:**
- No source changes expected.

- [ ] **Step 1: Run ClipMind verification**

Run:

```bash
cd /Users/kichinosukey-mba/projects/clipmind
swift test --package-path macos-app
swift build --package-path macos-app
.venv/bin/python -m pytest -q
```

Expected: Swift tests pass, Swift build succeeds, Python tests pass.

- [ ] **Step 2: Run Meeting Summary verification**

Run:

```bash
cd /Users/kichinosukey-mba/mentalbase/projects/meeting-summary-local-llm
.venv/bin/pytest tests/test_shared_llm_config.py tests/test_run_meeting_summary.py -q
.venv/bin/python -m ruff check scripts/shared_llm_config.py tests/test_shared_llm_config.py tests/test_run_meeting_summary.py
.venv/bin/python -m ruff format --check scripts/shared_llm_config.py tests/test_shared_llm_config.py tests/test_run_meeting_summary.py
```

Expected: all pass.

- [ ] **Step 3: Launch rebuilt ClipMind app**

Run:

```bash
cd /Users/kichinosukey-mba/projects/clipmind
open macos-app/.build/debug/ClipMindMenuBar
```

Expected: menu bar app launches. Settings includes an `Apps` tab with `ClipMind` and `Meeting Summary` preset pickers.

- [ ] **Step 4: Manual UI check**

In the app:

```text
Settings -> Apps
  ClipMind: choose one preset
  Meeting Summary: choose another preset
  close/reopen Settings
  confirm selections persist
```

Expected: `~/Library/Application Support/ClipMind/config.json` includes `appProfiles` with the selected IDs.

- [ ] **Step 5: Meeting Summary mock smoke**

Run:

```bash
printf 'A: app profile smoke.\\nB: ok.\\n' > /tmp/app-profile-meeting-smoke.txt
cd /Users/kichinosukey-mba/mentalbase/projects/meeting-summary-local-llm
env -u LM_API_TOKEN -u LM_BASE_URL -u LM_MODEL -u LM_TIMEOUT -u LM_CONTEXT_LENGTH \
  .venv/bin/python scripts/run_meeting_summary.py \
  --input /tmp/app-profile-meeting-smoke.txt \
  --mock \
  --output-dir /tmp/meeting-summary-app-profile-smoke
```

Expected: exits 0 and prints `[RESULT] status=success ...`.

- [ ] **Step 6: Final status check**

Run:

```bash
git -C /Users/kichinosukey-mba/projects/clipmind status --short --branch
git -C /Users/kichinosukey-mba/mentalbase/projects/meeting-summary-local-llm status --short --branch
```

Expected: only known unrelated files remain dirty; no uncommitted files from this task.

## Self-Review

- Spec coverage: The plan adds optional `appProfiles`, Apps UI, ClipMind app profile resolution, Meeting Summary app profile resolution, deletion cleanup, validation, fallback behavior, and smoke verification.
- Placeholder scan: No unresolved placeholders remain.
- Type consistency: Swift uses `AppProfile(activePresetId:)`; JSON uses `appProfiles`; Python readers use app IDs `clipmind` and `meeting-summary-local-llm`.
