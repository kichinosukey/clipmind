# LLM Preset App Profile Boundary Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Move app-specific LLM settings out of shared presets and into `appProfiles.<appId>.settings` while preserving existing config compatibility.

**Architecture:** Shared preset objects become app-independent connection records. Each app resolves a runtime snapshot by combining its selected shared preset with its own `settings` object, using legacy preset-level fields only as fallback during migration. ClipMind owns writing the JSON; Meeting Summary remains a tolerant reader of the same file.

**Tech Stack:** Swift / SwiftUI / XCTest for the macOS menu bar app, Python / pytest for ClipMind runtime, Python / pytest / Ruff for Meeting Summary runtime.

---

## File Structure

- Modify `macos-app/Sources/ClipMindMenuBar/Models/ClipMindConfig.swift`
  - Keep `Preset` focused on shared LLM connection fields.
  - Expand `AppProfile` to include `settings`.
  - Add a small app profile settings model that can encode/decode ClipMind prompts and Meeting Summary numeric fields.
  - Decode legacy preset-level prompt fields for migration without keeping them as active `Preset` fields.

- Modify `macos-app/Sources/ClipMindMenuBar/Services/ConfigStore.swift`
  - Validate shared preset fields separately from app profile settings.
  - Validate app profile preset references.
  - Validate ClipMind prompt settings after fallback.
  - Validate Meeting Summary numeric settings when present.

- Modify `macos-app/Sources/ClipMindMenuBar/ViewModels/SettingsViewModel.swift`
  - Add helpers for ClipMind prompt settings and Meeting Summary settings.
  - Keep add/duplicate/delete preset behavior focused on shared connection fields.
  - Preserve migration data when loading legacy configs.

- Modify `macos-app/Sources/ClipMindMenuBar/Views/PresetEditorView.swift`
  - Remove ClipMind prompt editors from the shared preset editor.

- Modify `macos-app/Sources/ClipMindMenuBar/Views/AppProfilesView.swift`
  - Add app-specific editors under ClipMind and Meeting Summary.

- Modify `clipmind/config.py`
  - Split the runtime data model into shared preset fields plus ClipMind prompt fields.
  - Resolve prompts from `appProfiles.clipmind.settings`, falling back to selected preset legacy prompt fields.

- Modify `tests/unit/test_config.py`
  - Cover new ClipMind runtime resolution and fallback behavior.

- Modify `/Users/kichinosukey-mba/mentalbase/projects/meeting-summary-local-llm/scripts/shared_llm_config.py`
  - Resolve `timeout` and `contextLength` from `appProfiles.meeting-summary-local-llm.settings` first.
  - Keep legacy preset-level fallback.

- Modify `/Users/kichinosukey-mba/mentalbase/projects/meeting-summary-local-llm/tests/test_shared_llm_config.py`
  - Cover app profile settings precedence and legacy fallback.

- Modify `README.md` and `macos-app/README.md`
  - Document the new ownership boundary and UI location.

---

### Task 1: Swift Config Model Boundary

**Files:**
- Modify: `macos-app/Sources/ClipMindMenuBar/Models/ClipMindConfig.swift`
- Modify: `macos-app/Tests/ClipMindMenuBarTests/SharedContractTests.swift`
- Modify: `macos-app/Tests/ClipMindMenuBarTests/ConfigStoreTests.swift`

- [ ] **Step 1: Update failing Swift contract tests**

Replace the old preset-contract test data in `SharedContractTests.swift` so shared presets no longer require prompt fields, and add an explicit legacy decode test.

```swift
func testPresetContractContainsOnlySharedLLMFields() throws {
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
          "apiKeyRef": "preset-1-api-key"
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

func testDecodesLegacyPresetPromptsIntoClipMindAppSettings() throws {
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
          "summarizeSystemPrompt": "legacy summary system",
          "summarizeUserPrompt": "legacy summary {text}",
          "translateSystemPrompt": "legacy translate system",
          "translateUserPrompt": "legacy translate {text}"
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
    let settings = try XCTUnwrap(config.appProfiles["clipmind"]?.settings)

    XCTAssertEqual(settings.summarizeSystemPrompt, "legacy summary system")
    XCTAssertEqual(settings.summarizeUserPrompt, "legacy summary {text}")
    XCTAssertEqual(settings.translateSystemPrompt, "legacy translate system")
    XCTAssertEqual(settings.translateUserPrompt, "legacy translate {text}")
}
```

Update `testDecodesConfigWithAppProfiles` to include settings:

```swift
XCTAssertEqual(config.appProfiles["clipmind"]?.activePresetId, "preset-1")
XCTAssertEqual(config.appProfiles["clipmind"]?.settings?.summarizeUserPrompt, "{text}")
XCTAssertEqual(config.appProfiles["meeting-summary-local-llm"]?.activePresetId, "")
XCTAssertEqual(config.appProfiles["meeting-summary-local-llm"]?.settings?.timeout, 900)
XCTAssertEqual(config.appProfiles["meeting-summary-local-llm"]?.settings?.contextLength, 32768)
```

- [ ] **Step 2: Run Swift tests and verify failure**

Run:

```bash
cd /Users/kichinosukey-mba/projects/clipmind
swift test --package-path macos-app --filter SharedContractTests
```

Expected: FAIL because `Preset` still requires prompt fields and `AppProfile` has no `settings`.

- [ ] **Step 3: Implement Swift models**

In `ClipMindConfig.swift`, replace `Preset` and `AppProfile` with:

```swift
struct Preset: Codable, Equatable, Identifiable {
    var id: String
    var name: String
    var baseURL: String
    var model: String
    var apiKeyRef: String

    enum CodingKeys: String, CodingKey {
        case id, name, baseURL, model, apiKeyRef
        case legacySummarizeSystemPrompt = "summarizeSystemPrompt"
        case legacySummarizeUserPrompt = "summarizeUserPrompt"
        case legacyTranslateSystemPrompt = "translateSystemPrompt"
        case legacyTranslateUserPrompt = "translateUserPrompt"
    }

    var legacyClipMindSettings: AppProfileSettings?

    init(
        id: String,
        name: String,
        baseURL: String,
        model: String,
        apiKeyRef: String,
        legacyClipMindSettings: AppProfileSettings? = nil
    ) {
        self.id = id
        self.name = name
        self.baseURL = baseURL
        self.model = model
        self.apiKeyRef = apiKeyRef
        self.legacyClipMindSettings = legacyClipMindSettings
    }

    init(from decoder: Decoder) throws {
        let container = try decoder.container(keyedBy: CodingKeys.self)
        id = try container.decode(String.self, forKey: .id)
        name = try container.decode(String.self, forKey: .name)
        baseURL = try container.decode(String.self, forKey: .baseURL)
        model = try container.decode(String.self, forKey: .model)
        apiKeyRef = try container.decode(String.self, forKey: .apiKeyRef)
        let legacy = AppProfileSettings(
            summarizeSystemPrompt: try container.decodeIfPresent(String.self, forKey: .legacySummarizeSystemPrompt),
            summarizeUserPrompt: try container.decodeIfPresent(String.self, forKey: .legacySummarizeUserPrompt),
            translateSystemPrompt: try container.decodeIfPresent(String.self, forKey: .legacyTranslateSystemPrompt),
            translateUserPrompt: try container.decodeIfPresent(String.self, forKey: .legacyTranslateUserPrompt),
            timeout: nil,
            contextLength: nil
        )
        legacyClipMindSettings = legacy.hasClipMindPrompts ? legacy : nil
    }

    func encode(to encoder: Encoder) throws {
        var container = encoder.container(keyedBy: CodingKeys.self)
        try container.encode(id, forKey: .id)
        try container.encode(name, forKey: .name)
        try container.encode(baseURL, forKey: .baseURL)
        try container.encode(model, forKey: .model)
        try container.encode(apiKeyRef, forKey: .apiKeyRef)
    }
}

struct AppProfile: Codable, Equatable {
    var activePresetId: String
    var settings: AppProfileSettings?

    init(activePresetId: String, settings: AppProfileSettings? = nil) {
        self.activePresetId = activePresetId
        self.settings = settings
    }
}

struct AppProfileSettings: Codable, Equatable {
    var summarizeSystemPrompt: String?
    var summarizeUserPrompt: String?
    var translateSystemPrompt: String?
    var translateUserPrompt: String?
    var timeout: Int?
    var contextLength: Int?

    var hasClipMindPrompts: Bool {
        summarizeSystemPrompt != nil || summarizeUserPrompt != nil ||
            translateSystemPrompt != nil || translateUserPrompt != nil
    }

    static let defaultClipMind = AppProfileSettings(
        summarizeSystemPrompt: "Summarize the transcript.",
        summarizeUserPrompt: "{text}",
        translateSystemPrompt: "Translate the summary into Japanese.",
        translateUserPrompt: "{text}",
        timeout: nil,
        contextLength: nil
    )
}
```

In `ClipMindConfig.init(from:)`, after decoding `presets` and `appProfiles`, copy legacy prompt settings into `appProfiles["clipmind"].settings` when missing:

```swift
if appProfiles["clipmind"]?.settings == nil,
   let selected = presets.first(where: { $0.id == activePresetId }),
   let legacy = selected.legacyClipMindSettings {
    var profile = appProfiles["clipmind"] ?? AppProfile(activePresetId: "")
    profile.settings = legacy
    appProfiles["clipmind"] = profile
}
```

- [ ] **Step 4: Update Swift test factories**

Update every `Preset(...)` construction in `ConfigStoreTests.swift` and other Swift tests to remove prompt arguments:

```swift
Preset(
    id: id,
    name: "Quality",
    baseURL: "http://localhost:1234/v1",
    model: "model-a",
    apiKeyRef: "quality-api"
)
```

When tests need ClipMind prompt settings, set:

```swift
config.appProfiles["clipmind"] = AppProfile(
    activePresetId: config.activePresetId,
    settings: .defaultClipMind
)
```

- [ ] **Step 5: Run Swift model tests**

Run:

```bash
cd /Users/kichinosukey-mba/projects/clipmind
swift test --package-path macos-app --filter SharedContractTests
```

Expected: PASS.

- [ ] **Step 6: Commit**

```bash
cd /Users/kichinosukey-mba/projects/clipmind
git add macos-app/Sources/ClipMindMenuBar/Models/ClipMindConfig.swift macos-app/Tests/ClipMindMenuBarTests/SharedContractTests.swift macos-app/Tests/ClipMindMenuBarTests/ConfigStoreTests.swift
git commit -m "refactor: separate shared presets from app settings"
```

---

### Task 2: Swift Validation and ViewModel Helpers

**Files:**
- Modify: `macos-app/Sources/ClipMindMenuBar/Services/ConfigStore.swift`
- Modify: `macos-app/Sources/ClipMindMenuBar/ViewModels/SettingsViewModel.swift`
- Modify: `macos-app/Tests/ClipMindMenuBarTests/ConfigStoreTests.swift`

- [ ] **Step 1: Add failing validation and helper tests**

Add tests to `ConfigStoreTests.swift`:

```swift
func testValidationRejectsEmptyClipMindPromptSettings() throws {
    var (config, root) = try validConfig()
    defer { try? FileManager.default.removeItem(at: root) }
    config.appProfiles["clipmind"] = AppProfile(
        activePresetId: config.activePresetId,
        settings: AppProfileSettings(
            summarizeSystemPrompt: "",
            summarizeUserPrompt: "{text}",
            translateSystemPrompt: "translate",
            translateUserPrompt: "{text}",
            timeout: nil,
            contextLength: nil
        )
    )

    XCTAssertThrowsError(try ConfigStore.validate(config))
}

func testValidationAcceptsMeetingSummarySettings() throws {
    var (config, root) = try validConfig()
    defer { try? FileManager.default.removeItem(at: root) }
    config.appProfiles["meeting-summary-local-llm"] = AppProfile(
        activePresetId: "",
        settings: AppProfileSettings(
            summarizeSystemPrompt: nil,
            summarizeUserPrompt: nil,
            translateSystemPrompt: nil,
            translateUserPrompt: nil,
            timeout: 900,
            contextLength: 32768
        )
    )

    XCTAssertNoThrow(try ConfigStore.validate(config))
}

@MainActor
func testClipMindSettingsHelperCreatesDefaults() {
    let viewModel = SettingsViewModel()
    viewModel.config.presets = [
        Preset(
            id: "quality",
            name: "Quality",
            baseURL: "http://localhost:1234/v1",
            model: "model-a",
            apiKeyRef: "quality-api"
        )
    ]
    viewModel.config.activePresetId = "quality"

    XCTAssertEqual(viewModel.clipMindSettings.summarizeUserPrompt, "{text}")
}
```

- [ ] **Step 2: Run tests and verify failure**

Run:

```bash
cd /Users/kichinosukey-mba/projects/clipmind
swift test --package-path macos-app --filter ConfigStoreTests
```

Expected: FAIL because validation still checks prompt fields on `Preset`, and `clipMindSettings` does not exist.

- [ ] **Step 3: Update validation**

In `ConfigStore.validate`, set `requiredPresetFields` to shared fields only:

```swift
let requiredPresetFields: [(Preset) -> String] = [
    \.id, \.name, \.baseURL, \.model, \.apiKeyRef,
]
```

Add helper validation:

```swift
if let clipmind = config.appProfiles["clipmind"]?.settings {
    let promptFields = [
        clipmind.summarizeSystemPrompt,
        clipmind.summarizeUserPrompt,
        clipmind.translateSystemPrompt,
        clipmind.translateUserPrompt,
    ]
    if promptFields.contains(where: { ($0 ?? "").trimmingCharacters(in: .whitespacesAndNewlines).isEmpty }) {
        throw ConfigStoreError.invalid("ClipMind prompts must not be empty")
    }
}
```

No explicit Swift validation is needed for bool numeric values because `Int?` decoding rejects booleans before validation.

- [ ] **Step 4: Add ViewModel helpers**

In `SettingsViewModel.swift`, add:

```swift
var clipMindSettings: AppProfileSettings {
    get {
        config.appProfiles["clipmind"]?.settings ?? .defaultClipMind
    }
    set {
        var profile = config.appProfiles["clipmind"] ?? AppProfile(activePresetId: "")
        profile.settings = newValue
        config.appProfiles["clipmind"] = profile
    }
}

var meetingSummarySettings: AppProfileSettings {
    get {
        config.appProfiles["meeting-summary-local-llm"]?.settings ?? AppProfileSettings(
            summarizeSystemPrompt: nil,
            summarizeUserPrompt: nil,
            translateSystemPrompt: nil,
            translateUserPrompt: nil,
            timeout: nil,
            contextLength: nil
        )
    }
    set {
        var profile = config.appProfiles["meeting-summary-local-llm"] ?? AppProfile(activePresetId: "")
        profile.settings = newValue
        config.appProfiles["meeting-summary-local-llm"] = profile
    }
}
```

Update `addPreset()` to create only shared preset fields:

```swift
config.presets.append(Preset(
    id: id,
    name: "New Preset",
    baseURL: "http://localhost:1234/v1",
    model: "",
    apiKeyRef: "preset-\(id)-api-key"
))
```

- [ ] **Step 5: Run Swift validation tests**

Run:

```bash
cd /Users/kichinosukey-mba/projects/clipmind
swift test --package-path macos-app --filter ConfigStoreTests
```

Expected: PASS.

- [ ] **Step 6: Commit**

```bash
cd /Users/kichinosukey-mba/projects/clipmind
git add macos-app/Sources/ClipMindMenuBar/Services/ConfigStore.swift macos-app/Sources/ClipMindMenuBar/ViewModels/SettingsViewModel.swift macos-app/Tests/ClipMindMenuBarTests/ConfigStoreTests.swift
git commit -m "feat: validate app profile settings"
```

---

### Task 3: SwiftUI Settings Ownership

**Files:**
- Modify: `macos-app/Sources/ClipMindMenuBar/Views/PresetEditorView.swift`
- Modify: `macos-app/Sources/ClipMindMenuBar/Views/AppProfilesView.swift`

- [ ] **Step 1: Move prompt editors out of PresetEditorView**

In `PresetEditorView.swift`, remove these fields from the active preset editor:

```swift
Text("Summary system prompt")
TextEditor(text: $settings.config.presets[index].summarizeSystemPrompt)
Text("Summary user prompt")
TextEditor(text: $settings.config.presets[index].summarizeUserPrompt)
Text("Translation system prompt")
TextEditor(text: $settings.config.presets[index].translateSystemPrompt)
Text("Translation user prompt")
TextEditor(text: $settings.config.presets[index].translateUserPrompt)
```

Replace the caption with:

```swift
Text("LLM presets are shared connection settings. App-specific prompts and limits live under Apps.")
    .font(.caption)
    .foregroundStyle(.secondary)
```

- [ ] **Step 2: Add app-specific editors**

In `AppProfilesView.swift`, replace the body with a scrollable form:

```swift
var body: some View {
    Form {
        Text("Choose the LLM preset each app uses. App-specific settings stay with the app.")
            .font(.caption)
            .foregroundStyle(.secondary)

        Section("ClipMind") {
            Picker("LLM preset", selection: appPresetBinding(for: "clipmind")) {
                Text("Default").tag("")
                ForEach(settings.config.presets) { preset in
                    Text(preset.name).tag(preset.id)
                }
            }
            TextField("Summary system prompt", text: clipMindStringBinding(\.summarizeSystemPrompt))
            TextField("Summary user prompt", text: clipMindStringBinding(\.summarizeUserPrompt))
            TextField("Translation system prompt", text: clipMindStringBinding(\.translateSystemPrompt))
            TextField("Translation user prompt", text: clipMindStringBinding(\.translateUserPrompt))
        }

        Section("Meeting Summary") {
            Picker("LLM preset", selection: appPresetBinding(for: "meeting-summary-local-llm")) {
                Text("Default").tag("")
                ForEach(settings.config.presets) { preset in
                    Text(preset.name).tag(preset.id)
                }
            }
            TextField("Timeout", text: meetingSummaryIntTextBinding(\.timeout))
            TextField("Context length", text: meetingSummaryIntTextBinding(\.contextLength))
        }

        Button("Save") { settings.save() }
    }
    .padding()
}
```

Add helper bindings:

```swift
private func clipMindStringBinding(
    _ keyPath: WritableKeyPath<AppProfileSettings, String?>
) -> Binding<String> {
    Binding(
        get: { settings.clipMindSettings[keyPath: keyPath] ?? "" },
        set: { value in
            var appSettings = settings.clipMindSettings
            appSettings[keyPath: keyPath] = value
            settings.clipMindSettings = appSettings
        }
    )
}

private func meetingSummaryIntTextBinding(
    _ keyPath: WritableKeyPath<AppProfileSettings, Int?>
) -> Binding<String> {
    Binding(
        get: {
            guard let value = settings.meetingSummarySettings[keyPath: keyPath] else {
                return ""
            }
            return String(value)
        },
        set: { value in
            var appSettings = settings.meetingSummarySettings
            appSettings[keyPath: keyPath] = Int(value.trimmingCharacters(in: .whitespacesAndNewlines))
            settings.meetingSummarySettings = appSettings
        }
    )
}
```

- [ ] **Step 3: Build the macOS app**

Run:

```bash
cd /Users/kichinosukey-mba/projects/clipmind
swift build --package-path macos-app
```

Expected: success.

- [ ] **Step 4: Run Swift tests**

Run:

```bash
cd /Users/kichinosukey-mba/projects/clipmind
swift test --package-path macos-app
```

Expected: all tests pass.

- [ ] **Step 5: Commit**

```bash
cd /Users/kichinosukey-mba/projects/clipmind
git add macos-app/Sources/ClipMindMenuBar/Views/PresetEditorView.swift macos-app/Sources/ClipMindMenuBar/Views/AppProfilesView.swift
git commit -m "feat: move app settings into apps tab"
```

---

### Task 4: ClipMind Python Runtime Boundary

**Files:**
- Modify: `clipmind/config.py`
- Modify: `tests/unit/test_config.py`
- Modify: `tests/fixtures/runtime/config-v1.json`

- [ ] **Step 1: Add failing Python runtime tests**

Add to `tests/unit/test_config.py`:

```python
def test_load_runtime_config_reads_clipmind_prompts_from_app_profile_settings(tmp_path):
    def mutate(data):
        data["presets"][0].pop("summarizeSystemPrompt", None)
        data["presets"][0].pop("summarizeUserPrompt", None)
        data["presets"][0].pop("translateSystemPrompt", None)
        data["presets"][0].pop("translateUserPrompt", None)
        data["appProfiles"] = {
            "clipmind": {
                "activePresetId": data["activePresetId"],
                "settings": {
                    "summarizeSystemPrompt": "profile summary system",
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

    assert runtime.preset.summarize_system_prompt == "profile summary system"
    assert runtime.preset.summarize_user_prompt == "profile summary {text}"
    assert runtime.preset.translate_system_prompt == "profile translate system"
    assert runtime.preset.translate_user_prompt == "profile translate {text}"


def test_load_runtime_config_keeps_legacy_preset_prompt_fallback(tmp_path):
    runtime = load_runtime_config(
        write_config(tmp_path),
        FakeSecrets({"quality-api": "api-secret", "discord-hook": "discord-secret"}),
    )

    assert runtime.preset.summarize_system_prompt == "summarize system"
    assert runtime.preset.summarize_user_prompt == "summary {text}"
```

Update the invalid config parametrization so empty prompts are tested through `appProfiles.clipmind.settings`, not preset fields:

```python
(
    lambda data: data.update(
        appProfiles={
            "clipmind": {
                "activePresetId": data["activePresetId"],
                "settings": {
                    "summarizeSystemPrompt": "system",
                    "summarizeUserPrompt": "",
                    "translateSystemPrompt": "translate",
                    "translateUserPrompt": "{text}",
                },
            }
        }
    ),
    "summarizeUserPrompt",
),
```

- [ ] **Step 2: Run Python test and verify failure**

Run:

```bash
cd /Users/kichinosukey-mba/projects/clipmind
.venv/bin/python -m pytest tests/unit/test_config.py -q
```

Expected: FAIL because runtime still reads prompts only from selected preset.

- [ ] **Step 3: Implement ClipMind profile prompt resolution**

In `clipmind/config.py`, add:

```python
def _app_profile(raw: dict[str, Any], app_id: str) -> dict[str, Any]:
    app_profiles = raw.get("appProfiles")
    if not isinstance(app_profiles, dict):
        return {}
    profile = app_profiles.get(app_id)
    if not isinstance(profile, dict):
        return {}
    return profile


def _app_settings(raw: dict[str, Any], app_id: str) -> dict[str, Any]:
    settings = _app_profile(raw, app_id).get("settings")
    if not isinstance(settings, dict):
        return {}
    return settings


def _prompt_text(
    settings: dict[str, Any],
    legacy_preset: dict[str, Any],
    field: str,
    context: str,
) -> str:
    if field in settings:
        return _required_text(settings, field, context)
    return _required_text(legacy_preset, field, f"presets.{legacy_preset['id']}")
```

Update `_active_preset_id` to call `_app_profile`:

```python
def _active_preset_id(raw: dict[str, Any], app_id: str) -> str:
    profile = _app_profile(raw, app_id)
    app_active = profile.get("activePresetId")
    if isinstance(app_active, str) and app_active.strip():
        return app_active
    return _required_text(raw, "activePresetId")
```

Replace prompt extraction with:

```python
clipmind_settings = _app_settings(raw, CLIPMIND_APP_ID)
preset_values = {
    "name": _required_text(active, "name", f"presets.{active_id}"),
    "base_url": _required_text(active, "baseURL", f"presets.{active_id}"),
    "model": _required_text(active, "model", f"presets.{active_id}"),
    "summarize_system_prompt": _prompt_text(
        clipmind_settings, active, "summarizeSystemPrompt", "appProfiles.clipmind.settings"
    ),
    "summarize_user_prompt": _prompt_text(
        clipmind_settings, active, "summarizeUserPrompt", "appProfiles.clipmind.settings"
    ),
    "translate_system_prompt": _prompt_text(
        clipmind_settings, active, "translateSystemPrompt", "appProfiles.clipmind.settings"
    ),
    "translate_user_prompt": _prompt_text(
        clipmind_settings, active, "translateUserPrompt", "appProfiles.clipmind.settings"
    ),
}
```

- [ ] **Step 4: Update fixture to canonical shape**

In `tests/fixtures/runtime/config-v1.json`, move prompt fields from `presets[0]` to:

```json
"appProfiles": {
  "clipmind": {
    "activePresetId": "quality",
    "settings": {
      "summarizeSystemPrompt": "summarize system",
      "summarizeUserPrompt": "summary {text}",
      "translateSystemPrompt": "translate system",
      "translateUserPrompt": "translate {text}"
    }
  }
}
```

Keep the test `test_load_runtime_config_keeps_legacy_preset_prompt_fallback` using inline mutation data that still has legacy prompt fields.

- [ ] **Step 5: Run ClipMind Python config tests**

Run:

```bash
cd /Users/kichinosukey-mba/projects/clipmind
.venv/bin/python -m pytest tests/unit/test_config.py -q
```

Expected: PASS.

- [ ] **Step 6: Commit**

```bash
cd /Users/kichinosukey-mba/projects/clipmind
git add clipmind/config.py tests/unit/test_config.py tests/fixtures/runtime/config-v1.json
git commit -m "feat: resolve clipmind app profile settings"
```

---

### Task 5: Meeting Summary Reader Boundary

**Files:**
- Modify: `/Users/kichinosukey-mba/mentalbase/projects/meeting-summary-local-llm/scripts/shared_llm_config.py`
- Modify: `/Users/kichinosukey-mba/mentalbase/projects/meeting-summary-local-llm/tests/test_shared_llm_config.py`

- [ ] **Step 1: Add failing Meeting Summary tests**

In `tests/test_shared_llm_config.py`, replace `test_optional_timeout_and_context_length_are_read_when_present` with:

```python
def test_timeout_and_context_length_are_read_from_app_profile_settings(tmp_path: Path) -> None:
    config = valid_config()
    config["appProfiles"] = {
        "meeting-summary-local-llm": {
            "activePresetId": "preset-1",
            "settings": {
                "timeout": 900,
                "contextLength": 32768,
            },
        }
    }
    config_path = tmp_path / "config.json"
    write_config(config_path, config)

    preset = load_shared_llm_preset(config_path, secret_lookup=lambda _ref: None)

    assert preset is not None
    assert preset.timeout == 900
    assert preset.context_length == 32768
```

Add legacy fallback test:

```python
def test_legacy_preset_timeout_and_context_length_remain_fallback(tmp_path: Path) -> None:
    config = valid_config()
    config["presets"][0]["timeout"] = 901
    config["presets"][0]["contextLength"] = 32769
    config_path = tmp_path / "config.json"
    write_config(config_path, config)

    preset = load_shared_llm_preset(config_path, secret_lookup=lambda _ref: None)

    assert preset is not None
    assert preset.timeout == 901
    assert preset.context_length == 32769
```

Update bool rejection to place invalid values under app settings:

```python
config["appProfiles"] = {
    "meeting-summary-local-llm": {
        "activePresetId": "preset-1",
        "settings": {field: value},
    }
}
```

- [ ] **Step 2: Run Meeting Summary tests and verify failure**

Run:

```bash
cd /Users/kichinosukey-mba/mentalbase/projects/meeting-summary-local-llm
.venv/bin/pytest tests/test_shared_llm_config.py -q
```

Expected: FAIL because `timeout` and `contextLength` are still read only from selected preset.

- [ ] **Step 3: Implement app settings precedence**

In `scripts/shared_llm_config.py`, add:

```python
def _app_profile(payload: dict[str, Any]) -> dict[str, Any]:
    app_profiles = payload.get("appProfiles")
    if not isinstance(app_profiles, dict):
        return {}
    app_profile = app_profiles.get(MEETING_SUMMARY_APP_ID)
    if not isinstance(app_profile, dict):
        return {}
    return app_profile


def _app_settings(payload: dict[str, Any]) -> dict[str, Any]:
    settings = _app_profile(payload).get("settings")
    if not isinstance(settings, dict):
        return {}
    return settings
```

Update `_app_active_preset_id`:

```python
def _app_active_preset_id(payload: dict[str, Any]) -> str | None:
    active_preset_id = _app_profile(payload).get("activePresetId")
    if not _is_present_string(active_preset_id):
        return None
    return active_preset_id
```

Replace timeout/context resolution:

```python
settings = _app_settings(payload)
timeout = _optional_int(settings.get("timeout", active_preset.get("timeout")))
context_length = _optional_int(
    settings.get("contextLength", active_preset.get("contextLength"))
)
```

- [ ] **Step 4: Run focused Meeting Summary tests**

Run:

```bash
cd /Users/kichinosukey-mba/mentalbase/projects/meeting-summary-local-llm
.venv/bin/pytest tests/test_shared_llm_config.py -q
```

Expected: PASS.

- [ ] **Step 5: Run scoped Ruff checks**

Run:

```bash
cd /Users/kichinosukey-mba/mentalbase/projects/meeting-summary-local-llm
.venv/bin/python -m ruff check scripts/shared_llm_config.py tests/test_shared_llm_config.py
.venv/bin/python -m ruff format --check scripts/shared_llm_config.py tests/test_shared_llm_config.py
```

Expected: both pass.

- [ ] **Step 6: Commit in Meeting Summary repo**

```bash
cd /Users/kichinosukey-mba/mentalbase/projects/meeting-summary-local-llm
git add scripts/shared_llm_config.py tests/test_shared_llm_config.py
git commit -m "feat: read meeting summary app settings"
```

---

### Task 6: Docs and Full Verification

**Files:**
- Modify: `README.md`
- Modify: `macos-app/README.md`

- [ ] **Step 1: Update ClipMind README config example**

In `README.md`, update the config example so `presets` only contains shared LLM fields and app-specific settings are under `appProfiles`:

```json
{
  "schemaVersion": 1,
  "activePresetId": "quality",
  "presets": [
    {
      "id": "quality",
      "name": "Quality",
      "baseURL": "http://localhost:1234/v1",
      "model": "google/gemma-4-12b",
      "apiKeyRef": "preset-quality-api-key"
    }
  ],
  "appProfiles": {
    "clipmind": {
      "activePresetId": "quality",
      "settings": {
        "summarizeSystemPrompt": "Summarize the transcript.",
        "summarizeUserPrompt": "{text}",
        "translateSystemPrompt": "Translate the summary into Japanese.",
        "translateUserPrompt": "{text}"
      }
    },
    "meeting-summary-local-llm": {
      "activePresetId": "",
      "settings": {
        "timeout": 900,
        "contextLength": 32768
      }
    }
  }
}
```

- [ ] **Step 2: Update macOS app README**

In `macos-app/README.md`, replace the paragraph beginning `The LLM preset section is intentionally` with:

```markdown
The LLM preset section is a shared local AI connection contract. Other personal
tools may read `baseURL`, `model`, and `apiKeyRef` from the selected preset.
App-specific settings, including ClipMind prompts and Meeting Summary limits,
live under `appProfiles.<appId>.settings`.
```

- [ ] **Step 3: Run full ClipMind verification**

Run:

```bash
cd /Users/kichinosukey-mba/projects/clipmind
swift test --package-path macos-app
swift build --package-path macos-app
.venv/bin/python -m pytest -q
```

Expected: all pass.

- [ ] **Step 4: Run focused Meeting Summary verification**

Run:

```bash
cd /Users/kichinosukey-mba/mentalbase/projects/meeting-summary-local-llm
.venv/bin/pytest tests/test_shared_llm_config.py tests/test_run_meeting_summary.py -q
.venv/bin/python -m ruff check scripts/shared_llm_config.py tests/test_shared_llm_config.py tests/test_run_meeting_summary.py
.venv/bin/python -m ruff format --check scripts/shared_llm_config.py tests/test_shared_llm_config.py tests/test_run_meeting_summary.py
```

Expected: all pass.

- [ ] **Step 5: Verify production config was not modified by tests**

Run:

```bash
sed -n '1,220p' "$HOME/Library/Application Support/ClipMind/config.json"
```

Expected: user config still has model `google/gemma-4-12b`; no test preset named `first` exists.

- [ ] **Step 6: Commit docs**

```bash
cd /Users/kichinosukey-mba/projects/clipmind
git add README.md macos-app/README.md tests/fixtures/runtime/config-v1.json
git commit -m "docs: document app profile settings boundary"
```

- [ ] **Step 7: GUI smoke check**

Run:

```bash
cd /Users/kichinosukey-mba/projects/clipmind
open macos-app/.build/debug/ClipMindMenuBar
```

Expected visual result:

- `LLM Presets` shows only shared connection fields.
- `Apps > ClipMind` shows prompt fields.
- `Apps > Meeting Summary` shows timeout and context length.
- `Shared` and `Status` are not presented as shared LLM preset settings.
