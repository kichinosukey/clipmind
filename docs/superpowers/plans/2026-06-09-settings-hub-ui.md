# Settings Hub UI Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Redesign the ClipMind menu bar app UI to match the shared LLM hub information architecture, auto-save interaction model, and native macOS visual quality bar defined in `docs/superpowers/specs/2026-06-09-settings-hub-ui-design.md`.

**Architecture:** Introduce a small navigation/auto-save layer in `SettingsViewModel`, rebuild the menu bar popover as a per-app preset shortcut surface, and restructure Settings into three tabs (`LLM Presets`, `Apps`, `Activity`). Relocate existing `Shared` and `Status` content without changing `config.json` schema keys. Use grouped native SwiftUI controls (`Form`, `GroupBox`, `LabeledContent`) and commit-on-blur persistence for text fields.

**Tech Stack:** Swift 6, SwiftUI, AppKit (`NSApplication`, menu bar extra dismiss), XCTest, existing `ConfigStore` / `KeychainStore` / `JobMonitor`.

**Spec:** `docs/superpowers/specs/2026-06-09-settings-hub-ui-design.md`

---

## File Structure

- Create: `macos-app/Sources/ClipMindMenuBar/Models/SettingsTab.swift`
  - Enum for Settings tab selection and deep-link entry points.

- Create: `macos-app/Sources/ClipMindMenuBar/Views/Components/AutoSaveTextField.swift`
  - Reusable text field that calls a commit closure on submit and focus loss.

- Create: `macos-app/Sources/ClipMindMenuBar/Views/ActivityView.swift`
  - Replaces top-level `Status` tab content under the `Activity` label.

- Create: `macos-app/Sources/ClipMindMenuBar/Views/ClipMindRuntimeSection.swift`
  - ClipMind runtime/output/destination fields moved from `SharedSettingsView`.

- Modify: `macos-app/Sources/ClipMindMenuBar/ViewModels/SettingsViewModel.swift`
  - Tab routing, `persistConfig()`, secret commit helpers, preset display names.

- Modify: `macos-app/Sources/ClipMindMenuBar/Views/MenuContentView.swift`
  - Per-app preset rows, compact activity summary, dismiss-before-settings.

- Modify: `macos-app/Sources/ClipMindMenuBar/Views/SettingsView.swift`
  - Three tabs only; bind selected tab from view model.

- Modify: `macos-app/Sources/ClipMindMenuBar/Views/PresetEditorView.swift`
  - Auto-save, `+` creation, context menu duplicate/delete, demoted test connection.

- Modify: `macos-app/Sources/ClipMindMenuBar/Views/AppProfilesView.swift`
  - Distinct app cards; embed `ClipMindRuntimeSection`; remove `Save`.

- Modify: `macos-app/Sources/ClipMindMenuBar/ClipMindMenuBarApp.swift`
  - Inject shared navigation state into menu content and settings scenes.

- Delete: `macos-app/Sources/ClipMindMenuBar/Views/SharedSettingsView.swift`
- Delete: `macos-app/Sources/ClipMindMenuBar/Views/StatusView.swift`

- Create: `macos-app/Tests/ClipMindMenuBarTests/SettingsHubUITests.swift`
  - View-model tests for tab routing, auto-save, and preset display helpers.

- Modify: `macos-app/README.md`
  - Document three-tab Settings IA and popover behavior.

---

### Task 1: Settings Tab Model and View-Model Navigation

**Files:**
- Create: `macos-app/Sources/ClipMindMenuBar/Models/SettingsTab.swift`
- Modify: `macos-app/Sources/ClipMindMenuBar/ViewModels/SettingsViewModel.swift`
- Create: `macos-app/Tests/ClipMindMenuBarTests/SettingsHubUITests.swift`

- [ ] **Step 1: Write the failing navigation test**

```swift
import XCTest
@testable import ClipMindMenuBar

@MainActor
final class SettingsHubUITests: XCTestCase {
    func testOpenSettingsTabUpdatesSelection() {
        let viewModel = SettingsViewModel()
        XCTAssertEqual(viewModel.selectedSettingsTab, .llmPresets)

        viewModel.openSettings(tab: .activity)

        XCTAssertEqual(viewModel.selectedSettingsTab, .activity)
    }

    func testPresetDisplayNameUsesDefaultForEmptyAppProfileSelection() {
        let viewModel = SettingsViewModel()
        let preset = Preset(
            id: "p1", name: "Local Gemma", baseURL: "http://localhost:1234/v1",
            model: "google/gemma-4-12b", apiKeyRef: "p1-key"
        )
        viewModel.config.presets = [preset]
        viewModel.config.appProfiles = [
            "clipmind": AppProfile(activePresetId: "", settings: .defaultClipMind)
        ]

        XCTAssertEqual(viewModel.presetDisplayName(for: "clipmind"), "Default")
        XCTAssertEqual(viewModel.presetDisplayName(for: "meeting-summary-local-llm"), "Default")
    }
}
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd /Users/kichinosukey-mba/projects/clipmind && swift test --package-path macos-app --filter SettingsHubUITests -v`

Expected: FAIL — `SettingsTab`, `selectedSettingsTab`, `openSettings(tab:)`, or `presetDisplayName(for:)` not found.

- [ ] **Step 3: Add `SettingsTab` enum**

Create `macos-app/Sources/ClipMindMenuBar/Models/SettingsTab.swift`:

```swift
import Foundation

enum SettingsTab: String, CaseIterable, Identifiable, Equatable {
    case llmPresets
    case apps
    case activity

    var id: String { rawValue }

    var title: String {
        switch self {
        case .llmPresets: "LLM Presets"
        case .apps: "Apps"
        case .activity: "Activity"
        }
    }

    var systemImage: String {
        switch self {
        case .llmPresets: "slider.horizontal.3"
        case .apps: "app.badge"
        case .activity: "waveform.path.ecg"
        }
    }
}
```

- [ ] **Step 4: Extend `SettingsViewModel`**

Add to `SettingsViewModel.swift`:

```swift
@Published var selectedSettingsTab: SettingsTab = .llmPresets

func openSettings(tab: SettingsTab) {
    selectedSettingsTab = tab
}

func persistConfig() {
    save()
}

func presetDisplayName(for appId: String) -> String {
    let presetId = appPresetId(for: appId)
    guard !presetId.isEmpty,
          let preset = config.presets.first(where: { $0.id == presetId }) else {
        if let global = config.presets.first(where: { $0.id == config.activePresetId }) {
            return global.name
        }
        return "Default"
    }
    return preset.name
}
```

- [ ] **Step 5: Run test to verify it passes**

Run: `cd /Users/kichinosukey-mba/projects/clipmind && swift test --package-path macos-app --filter SettingsHubUITests -v`

Expected: PASS

- [ ] **Step 6: Commit**

```bash
cd /Users/kichinosukey-mba/projects/clipmind
git add macos-app/Sources/ClipMindMenuBar/Models/SettingsTab.swift \
  macos-app/Sources/ClipMindMenuBar/ViewModels/SettingsViewModel.swift \
  macos-app/Tests/ClipMindMenuBarTests/SettingsHubUITests.swift
git commit -m "feat: add settings tab navigation helpers"
```

---

### Task 2: Auto-Save Field Component and Persist Hooks

**Files:**
- Create: `macos-app/Sources/ClipMindMenuBar/Views/Components/AutoSaveTextField.swift`
- Modify: `macos-app/Sources/ClipMindMenuBar/ViewModels/SettingsViewModel.swift`
- Modify: `macos-app/Tests/ClipMindMenuBarTests/SettingsHubUITests.swift`

- [ ] **Step 1: Write failing persist hook test**

Append to `SettingsHubUITests.swift`:

```swift
func testPersistConfigInvokesStoreSave() throws {
    let root = FileManager.default.temporaryDirectory.appendingPathComponent(UUID().uuidString)
    try FileManager.default.createDirectory(at: root, withIntermediateDirectories: true)
    defer { try? FileManager.default.removeItem(at: root) }

    let binary = root.appendingPathComponent("whisper")
    FileManager.default.createFile(atPath: binary.path, contents: Data())
    try FileManager.default.setAttributes([.posixPermissions: 0o755], ofItemAtPath: binary.path)
    let model = root.appendingPathComponent("model.bin")
    FileManager.default.createFile(atPath: model.path, contents: Data())

    let store = ConfigStore(configURL: root.appendingPathComponent("config.json"))
    let viewModel = SettingsViewModel(store: store)
    viewModel.config = ClipMindConfig(
        schemaVersion: 1,
        activePresetId: "p1",
        presets: [Preset(
            id: "p1", name: "Quality", baseURL: "http://localhost:1234/v1",
            model: "model-a", apiKeyRef: "p1-key"
        )],
        appProfiles: ["clipmind": AppProfile(activePresetId: "p1", settings: .defaultClipMind)],
        shared: SharedSettings(
            whisperBinaryPath: binary.path, whisperModelPath: model.path,
            outputRoot: root.path, enabledDestinations: [],
            discordWebhookRef: nil, slackWebhookRef: nil
        )
    )

    viewModel.persistConfig()

    let loaded = try store.load()
    XCTAssertEqual(loaded.presets.first?.name, "Quality")
}
```

- [ ] **Step 2: Run test to verify it fails or passes baseline**

Run: `swift test --package-path macos-app --filter testPersistConfigInvokesStoreSave -v`

Expected: PASS once `persistConfig()` from Task 1 exists; if failing, implement minimal `persistConfig() { save() }`.

- [ ] **Step 3: Add secret commit helpers to `SettingsViewModel`**

```swift
func commitPresetAPIKey(for preset: Preset, value: String) {
    guard !value.isEmpty else { return }
    saveSecret(reference: preset.apiKeyRef, value: value)
    persistConfig()
}

func commitDestinationSecret(reference: String, value: String, assignTo keyPath: WritableKeyPath<SharedSettings, String?>) {
    guard !value.isEmpty else { return }
    config.shared[keyPath: keyPath] = reference
    saveSecret(reference: reference, value: value)
    persistConfig()
}
```

- [ ] **Step 4: Create `AutoSaveTextField`**

Create `macos-app/Sources/ClipMindMenuBar/Views/Components/AutoSaveTextField.swift`:

```swift
import SwiftUI

struct AutoSaveTextField: View {
    let title: String
    @Binding var text: String
    let onCommit: () -> Void

    @FocusState private var isFocused: Bool
    @State private var lastCommittedValue: String

    init(_ title: String, text: Binding<String>, onCommit: @escaping () -> Void) {
        self.title = title
        self._text = text
        self.onCommit = onCommit
        self._lastCommittedValue = State(initialValue: text.wrappedValue)
    }

    var body: some View {
        TextField(title, text: $text)
            .focused($isFocused)
            .onSubmit(commitIfNeeded)
            .onChange(of: isFocused) { focused in
                if !focused { commitIfNeeded() }
            }
    }

    private func commitIfNeeded() {
        guard text != lastCommittedValue else { return }
        lastCommittedValue = text
        onCommit()
    }
}

struct AutoSaveSecureField: View {
    let title: String
    @Binding var text: String
    let onCommit: () -> Void

    @FocusState private var isFocused: Bool

    var body: some View {
        SecureField(title, text: $text)
            .focused($isFocused)
            .onSubmit(onCommit)
            .onChange(of: isFocused) { focused in
                if !focused && !text.isEmpty { onCommit() }
            }
    }
}
```

- [ ] **Step 5: Run full Swift test suite**

Run: `cd /Users/kichinosukey-mba/projects/clipmind && swift test --package-path macos-app`

Expected: all tests PASS

- [ ] **Step 6: Commit**

```bash
git add macos-app/Sources/ClipMindMenuBar/Views/Components/AutoSaveTextField.swift \
  macos-app/Sources/ClipMindMenuBar/ViewModels/SettingsViewModel.swift \
  macos-app/Tests/ClipMindMenuBarTests/SettingsHubUITests.swift
git commit -m "feat: add auto-save field components and persist hooks"
```

---

### Task 3: Menu Bar Popover Redesign

**Files:**
- Modify: `macos-app/Sources/ClipMindMenuBar/Views/MenuContentView.swift`
- Modify: `macos-app/Sources/ClipMindMenuBar/ClipMindMenuBarApp.swift`

- [ ] **Step 1: Replace `MenuContentView` body**

Rewrite `MenuContentView.swift` to:

```swift
import AppKit
import SwiftUI

struct MenuContentView: View {
    @EnvironmentObject var jobs: JobMonitor
    @EnvironmentObject var settings: SettingsViewModel
    @Environment(\.openSettings) private var openSettings
    @Environment(\.dismiss) private var dismiss

    var body: some View {
        VStack(alignment: .leading, spacing: 0) {
            ForEach(settings.supportedApps) { app in
                LabeledContent(app.name) {
                    Picker("LLM preset", selection: appPresetBinding(for: app.id)) {
                        Text("Default").tag("")
                        ForEach(settings.config.presets) { preset in
                            Text(preset.name).tag(preset.id)
                        }
                    }
                    .labelsHidden()
                    .frame(maxWidth: 180)
                }
                .padding(.horizontal, 12)
                .padding(.vertical, 8)
            }

            Divider()

            Button(action: openActivityTab) {
                HStack(spacing: 6) {
                    Image(systemName: jobs.activeCount > 0 ? "circle.fill" : "circle")
                        .font(.caption)
                        .foregroundStyle(jobs.activeCount > 0 ? .green : .secondary)
                    Text(activitySummary)
                        .font(.callout)
                        .lineLimit(1)
                        .truncationMode(.tail)
                }
                .frame(maxWidth: .infinity, alignment: .leading)
                .contentShape(Rectangle())
            }
            .buttonStyle(.plain)
            .padding(.horizontal, 12)
            .padding(.vertical, 10)

            Divider()

            VStack(spacing: 4) {
                Button("設定を開く…", action: openSettingsTab)
                Button("終了") { NSApplication.shared.terminate(nil) }
            }
            .padding(12)
        }
        .frame(width: 300)
    }

    private var activitySummary: String {
        let running = "実行中: \(jobs.activeCount)"
        if let recent = jobs.latestTerminalJob {
            let title = recent.title ?? recent.sourceURL
            return "\(running)  ·  直近: \(recent.stage.label) \(title)"
        }
        return running
    }

    private func appPresetBinding(for appId: String) -> Binding<String> {
        Binding(
            get: { settings.appPresetId(for: appId) },
            set: { settings.setAppPresetId($0, for: appId) }
        )
    }

    private func openSettingsTab() {
        settings.openSettings(tab: .llmPresets)
        presentSettings()
    }

    private func openActivityTab() {
        settings.openSettings(tab: .activity)
        presentSettings()
    }

    private func presentSettings() {
        dismiss()
        NSApplication.shared.setActivationPolicy(.regular)
        NSApplication.shared.activate(ignoringOtherApps: true)
        openSettings()
        DispatchQueue.main.async {
            NSApplication.shared.activate(ignoringOtherApps: true)
        }
    }
}
```

Remove the old `OpenSettingsMenuItem` struct and the global `プリセット` picker.

- [ ] **Step 2: Build and smoke-run**

Run:

```bash
cd /Users/kichinosukey-mba/projects/clipmind
swift build --package-path macos-app
./macos-app/.build/debug/ClipMindMenuBar
```

Manual check:
- Popover shows `ClipMind` and `Meeting Summary` rows with preset pickers.
- Clicking `設定を開く…` closes popover before Settings appears.
- Clicking activity summary opens Settings on `Activity` tab.

- [ ] **Step 3: Commit**

```bash
git add macos-app/Sources/ClipMindMenuBar/Views/MenuContentView.swift
git commit -m "feat: redesign menu bar popover for per-app presets"
```

---

### Task 4: Settings Shell — Three Tabs and Activity View

**Files:**
- Modify: `macos-app/Sources/ClipMindMenuBar/Views/SettingsView.swift`
- Create: `macos-app/Sources/ClipMindMenuBar/Views/ActivityView.swift`
- Delete: `macos-app/Sources/ClipMindMenuBar/Views/StatusView.swift`

- [ ] **Step 1: Create `ActivityView`**

Create `macos-app/Sources/ClipMindMenuBar/Views/ActivityView.swift` using the current `StatusView` content:

```swift
import SwiftUI

struct ActivityView: View {
    @EnvironmentObject var jobs: JobMonitor

    var body: some View {
        Form {
            Section("Runtime") {
                LabeledContent("実行中", value: "\(jobs.activeCount)")
                if let job = jobs.currentJob {
                    LabeledContent("現在工程", value: job.stage.label)
                    Text(job.title ?? job.sourceURL)
                        .foregroundStyle(.secondary)
                }
                if let job = jobs.latestTerminalJob {
                    LabeledContent("直近結果", value: job.stage.label)
                    if let error = job.errorSummary {
                        Text(error).foregroundStyle(.red)
                    }
                }
            }
        }
        .formStyle(.grouped)
        .padding()
    }
}
```

- [ ] **Step 2: Update `SettingsView`**

Replace `SettingsView.swift` body with:

```swift
import SwiftUI

struct SettingsView: View {
    @EnvironmentObject var jobs: JobMonitor
    @EnvironmentObject var settings: SettingsViewModel

    var body: some View {
        TabView(selection: $settings.selectedSettingsTab) {
            PresetEditorView()
                .tabItem { Label(SettingsTab.llmPresets.title, systemImage: SettingsTab.llmPresets.systemImage) }
                .tag(SettingsTab.llmPresets)

            AppProfilesView()
                .tabItem { Label(SettingsTab.apps.title, systemImage: SettingsTab.apps.systemImage) }
                .tag(SettingsTab.apps)

            ActivityView()
                .tabItem { Label(SettingsTab.activity.title, systemImage: SettingsTab.activity.systemImage) }
                .tag(SettingsTab.activity)
        }
        .frame(minWidth: 680, minHeight: 520)
    }
}
```

- [ ] **Step 3: Delete obsolete `StatusView.swift`**

```bash
rm macos-app/Sources/ClipMindMenuBar/Views/StatusView.swift
```

- [ ] **Step 4: Build and verify tabs**

Run: `swift build --package-path macos-app`

Manual check: only three tabs visible; `Shared` and `Status` are gone.

- [ ] **Step 5: Commit**

```bash
git add macos-app/Sources/ClipMindMenuBar/Views/SettingsView.swift \
  macos-app/Sources/ClipMindMenuBar/Views/ActivityView.swift
git rm macos-app/Sources/ClipMindMenuBar/Views/StatusView.swift
git commit -m "feat: restructure settings into presets apps activity tabs"
```

---

### Task 5: LLM Presets Editor — Auto-Save and Simplified Actions

**Files:**
- Modify: `macos-app/Sources/ClipMindMenuBar/Views/PresetEditorView.swift`
- Modify: `macos-app/Sources/ClipMindMenuBar/ViewModels/SettingsViewModel.swift`

- [ ] **Step 1: Write failing test for add-preset-only-through-view-model API**

Append to `SettingsHubUITests.swift`:

```swift
func testAddPresetSelectsNewPresetWithoutRequiringSaveButton() {
    let viewModel = SettingsViewModel()
    let source = Preset(
        id: "source", name: "Quality", baseURL: "http://localhost:1234/v1",
        model: "model-a", apiKeyRef: "source-api"
    )
    viewModel.config.presets = [source]
    viewModel.config.activePresetId = source.id

    viewModel.addPreset()
    viewModel.persistConfig()

    XCTAssertEqual(viewModel.config.presets.count, 2)
    XCTAssertEqual(viewModel.config.activePresetId, viewModel.config.presets.last?.id)
}
```

Run: `swift test --package-path macos-app --filter testAddPresetSelectsNewPresetWithoutRequiringSaveButton -v`

Expected: PASS with existing `addPreset()`; this is a guard test for the UI refactor.

- [ ] **Step 2: Rewrite `PresetEditorView`**

Replace `PresetEditorView.swift` with a split sidebar/detail layout:

```swift
import SwiftUI

struct PresetEditorView: View {
    @EnvironmentObject var settings: SettingsViewModel
    @State private var apiKey = ""

    var body: some View {
        HStack(spacing: 0) {
            List(selection: $settings.config.activePresetId) {
                ForEach(settings.config.presets) { preset in
                    Text(preset.name)
                        .tag(preset.id)
                        .contextMenu {
                            Button("Duplicate") { settings.duplicatePreset(preset) }
                            Button("Delete…", role: .destructive) {
                                settings.deletePreset(preset.id)
                            }
                        }
                }
            }
            .frame(width: 180)
            .toolbar {
                ToolbarItem(placement: .primaryAction) {
                    Button(action: settings.addPreset) {
                        Label("Add Preset", systemImage: "plus")
                    }
                }
            }

            if let index = selectedPresetIndex {
                Form {
                    Section {
                        Text("LLM presets are shared connection settings. App-specific prompts and limits live under Apps.")
                            .font(.callout)
                            .foregroundStyle(.secondary)
                    }

                    Section("Connection") {
                        AutoSaveTextField("Name", text: $settings.config.presets[index].name) {
                            settings.persistConfig()
                        }
                        AutoSaveTextField("Base URL", text: $settings.config.presets[index].baseURL) {
                            settings.persistConfig()
                        }
                        AutoSaveTextField("Model", text: $settings.config.presets[index].model) {
                            settings.persistConfig()
                        }
                        if !settings.discoveredModels.isEmpty {
                            Picker("Discovered model", selection: $settings.config.presets[index].model) {
                                ForEach(settings.discoveredModels, id: \.self) { Text($0).tag($0) }
                            }
                            .onChange(of: settings.config.presets[index].model) { _, _ in
                                settings.persistConfig()
                            }
                        }
                        AutoSaveSecureField("API key", text: $apiKey) {
                            settings.commitPresetAPIKey(for: settings.config.presets[index], value: apiKey)
                            apiKey = ""
                        }
                    }

                    Section {
                        Button("接続を確認") {
                            Task { await settings.discoverModels() }
                        }
                        .buttonStyle(.link)
                    }
                }
                .formStyle(.grouped)
                .padding()
            } else {
                ContentUnavailableView(
                    "No Preset Selected",
                    systemImage: "slider.horizontal.3",
                    description: Text("Create a preset with the plus button in the sidebar.")
                )
            }
        }
        if let error = settings.errorMessage {
            Text(error).foregroundStyle(.red).padding()
        }
    }

    private var selectedPresetIndex: Int? {
        settings.config.presets.firstIndex { $0.id == settings.config.activePresetId }
    }
}
```

Remove `Save`, `Save API Key`, bottom `Add Preset`, and inline `Duplicate`/`Delete` buttons.

- [ ] **Step 3: Build and manual check**

Run: `swift build --package-path macos-app`

Manual check on `LLM Presets`:
- `+` adds a preset.
- Context menu duplicates/deletes.
- Editing name/base URL/model persists without a Save button.
- API key writes on field commit.
- `接続を確認` is a link, not a primary button row.

- [ ] **Step 4: Commit**

```bash
git add macos-app/Sources/ClipMindMenuBar/Views/PresetEditorView.swift \
  macos-app/Tests/ClipMindMenuBarTests/SettingsHubUITests.swift
git commit -m "feat: simplify llm presets editor with auto-save"
```

---

### Task 6: Apps Tab — App Cards and ClipMind Runtime Relocation

**Files:**
- Create: `macos-app/Sources/ClipMindMenuBar/Views/ClipMindRuntimeSection.swift`
- Modify: `macos-app/Sources/ClipMindMenuBar/Views/AppProfilesView.swift`
- Delete: `macos-app/Sources/ClipMindMenuBar/Views/SharedSettingsView.swift`

- [ ] **Step 1: Extract runtime section from old shared view**

Create `ClipMindRuntimeSection.swift`:

```swift
import SwiftUI

struct ClipMindRuntimeSection: View {
    @EnvironmentObject var settings: SettingsViewModel
    @State private var discordWebhook = ""
    @State private var slackWebhook = ""

    var body: some View {
        Group {
            AutoSaveTextField("Whisper binary", text: $settings.config.shared.whisperBinaryPath) {
                settings.persistConfig()
            }
            AutoSaveTextField("Whisper model", text: $settings.config.shared.whisperModelPath) {
                settings.persistConfig()
            }
            AutoSaveTextField("Output root", text: $settings.config.shared.outputRoot) {
                settings.persistConfig()
            }
            Toggle("Discord", isOn: destination("discord"))
                .onChange(of: settings.config.shared.enabledDestinations) { _, _ in
                    settings.persistConfig()
                }
            AutoSaveSecureField("Discord webhook", text: $discordWebhook) {
                settings.commitDestinationSecret(
                    reference: "destination-discord-webhook",
                    value: discordWebhook,
                    assignTo: \.discordWebhookRef
                )
                discordWebhook = ""
            }
            Toggle("Slack", isOn: destination("slack"))
                .onChange(of: settings.config.shared.enabledDestinations) { _, _ in
                    settings.persistConfig()
                }
            AutoSaveSecureField("Slack webhook", text: $slackWebhook) {
                settings.commitDestinationSecret(
                    reference: "destination-slack-webhook",
                    value: slackWebhook,
                    assignTo: \.slackWebhookRef
                )
                slackWebhook = ""
            }
        }
    }

    private func destination(_ name: String) -> Binding<Bool> {
        Binding(
            get: { settings.config.shared.enabledDestinations.contains(name) },
            set: { enabled in
                settings.config.shared.enabledDestinations.removeAll { $0 == name }
                if enabled { settings.config.shared.enabledDestinations.append(name) }
            }
        )
    }
}
```

- [ ] **Step 2: Rewrite `AppProfilesView` with grouped cards**

Replace `AppProfilesView.swift` body with grouped `GroupBox` sections and no `Save` button:

```swift
import SwiftUI

struct AppProfilesView: View {
    @EnvironmentObject var settings: SettingsViewModel

    var body: some View {
        ScrollView {
            VStack(alignment: .leading, spacing: 20) {
                Text("Choose the LLM preset each app uses. App-specific settings stay with the app.")
                    .font(.callout)
                    .foregroundStyle(.secondary)

                GroupBox("ClipMind") {
                    Form {
                        Section("LLM") {
                            Picker("LLM preset", selection: appPresetBinding(for: "clipmind")) {
                                Text("Default").tag("")
                                ForEach(settings.config.presets) { preset in
                                    Text(preset.name).tag(preset.id)
                                }
                            }
                        }
                        Section("Prompts") {
                            AutoSaveTextField("Summary system prompt", text: clipMindSettingsBinding(\.summarizeSystemPrompt)) {
                                settings.persistConfig()
                            }
                            AutoSaveTextField("Summary user prompt", text: clipMindSettingsBinding(\.summarizeUserPrompt)) {
                                settings.persistConfig()
                            }
                            AutoSaveTextField("Translation system prompt", text: clipMindSettingsBinding(\.translateSystemPrompt)) {
                                settings.persistConfig()
                            }
                            AutoSaveTextField("Translation user prompt", text: clipMindSettingsBinding(\.translateUserPrompt)) {
                                settings.persistConfig()
                            }
                        }
                        Section("Runtime") {
                            ClipMindRuntimeSection()
                        }
                    }
                    .formStyle(.grouped)
                }

                GroupBox("Meeting Summary") {
                    Form {
                        Section("LLM") {
                            Picker("LLM preset", selection: appPresetBinding(for: "meeting-summary-local-llm")) {
                                Text("Default").tag("")
                                ForEach(settings.config.presets) { preset in
                                    Text(preset.name).tag(preset.id)
                                }
                            }
                        }
                        Section("Limits") {
                            AutoSaveTextField("Timeout", text: meetingSummaryIntBinding(\.timeout)) {
                                settings.persistConfig()
                            }
                            AutoSaveTextField("Context length", text: meetingSummaryIntBinding(\.contextLength)) {
                                settings.persistConfig()
                            }
                        }
                    }
                    .formStyle(.grouped)
                }
            }
            .padding()
        }
        if let error = settings.errorMessage {
            Text(error).foregroundStyle(.red).padding()
        }
    }

    // keep existing appPresetBinding, clipMindSettingsBinding, meetingSummaryIntBinding helpers
}
```

- [ ] **Step 3: Delete `SharedSettingsView.swift`**

```bash
rm macos-app/Sources/ClipMindMenuBar/Views/SharedSettingsView.swift
```

- [ ] **Step 4: Build, test, manual check**

Run:

```bash
swift test --package-path macos-app
swift build --package-path macos-app
```

Manual check on `Apps`:
- ClipMind and Meeting Summary are visually separate cards.
- ClipMind runtime fields live under `Runtime`.
- No `Save` button on the tab.

- [ ] **Step 5: Commit**

```bash
git add macos-app/Sources/ClipMindMenuBar/Views/AppProfilesView.swift \
  macos-app/Sources/ClipMindMenuBar/Views/ClipMindRuntimeSection.swift
git rm macos-app/Sources/ClipMindMenuBar/Views/SharedSettingsView.swift
git commit -m "feat: split apps settings into cards and move clipmind runtime"
```

---

### Task 7: Delete-Preset Confirmation and Final Polish Pass

**Files:**
- Modify: `macos-app/Sources/ClipMindMenuBar/ViewModels/SettingsViewModel.swift`
- Modify: `macos-app/Sources/ClipMindMenuBar/Views/PresetEditorView.swift`

- [ ] **Step 1: Add explicit delete confirmation in the view**

Update the delete branch in `PresetEditorView` context menu to use a local alert state:

```swift
@State private var presetPendingDeletion: Preset?

.alert(
    "Delete preset?",
    isPresented: Binding(
        get: { presetPendingDeletion != nil },
        set: { if !$0 { presetPendingDeletion = nil } }
    ),
    presenting: presetPendingDeletion
) { preset in
    Button("Delete", role: .destructive) {
        settings.deletePreset(preset.id)
        presetPendingDeletion = nil
    }
    Button("Cancel", role: .cancel) { presetPendingDeletion = nil }
} message: { preset in
    Text("“\(preset.name)” will be removed. App preset selections referencing it will reset to Default.")
}
```

Set `presetPendingDeletion = preset` from the context menu instead of calling `deletePreset` directly.

- [ ] **Step 2: Ensure picker changes persist immediately**

Verify `setAppPresetId` in `SettingsViewModel` still ends with `save()` and is used by both popover and Apps pickers.

- [ ] **Step 3: Run full suite**

Run: `cd /Users/kichinosukey-mba/projects/clipmind && swift test --package-path macos-app`

Expected: all tests PASS

- [ ] **Step 4: Commit**

```bash
git add macos-app/Sources/ClipMindMenuBar/Views/PresetEditorView.swift \
  macos-app/Sources/ClipMindMenuBar/ViewModels/SettingsViewModel.swift
git commit -m "fix: confirm preset deletion and polish settings interactions"
```

---

### Task 8: Documentation and Manual Acceptance

**Files:**
- Modify: `macos-app/README.md`

- [ ] **Step 1: Update README tab descriptions**

Replace the generic settings note in `macos-app/README.md` with:

```markdown
Settings tabs:

- `LLM Presets` — shared LLM connection templates (`baseURL`, `model`, `apiKeyRef`)
- `Apps` — per-app preset selection and owned settings
  - `ClipMind` prompts and runtime/output/destination settings
  - `Meeting Summary` timeout and context length
- `Activity` — current and recent ClipMind job status

The menu bar popover provides per-app preset quick switching and a one-line activity summary. Changes persist automatically; routine Save buttons are not used.
```

- [ ] **Step 2: Manual acceptance checklist**

Run the app:

```bash
cd /Users/kichinosukey-mba/projects/clipmind
swift run --package-path macos-app ClipMindMenuBar
```

Verify:

- Popover layout is compact and native; no full-width gray button stack.
- `設定を開く…` does not leave the popover overlapping Settings.
- `LLM Presets` has no `Save` / `Save API Key` / bottom `Add Preset` row.
- `Apps` shows separate ClipMind and Meeting Summary cards.
- ClipMind runtime settings are under `Apps > ClipMind > Runtime`.
- `Activity` shows job status previously on `Status`.
- Editing a field and tabbing out persists to `~/Library/Application Support/ClipMind/config.json`.

- [ ] **Step 3: Commit docs**

```bash
git add macos-app/README.md
git commit -m "docs: describe settings hub ui tabs and popover behavior"
```

---

## Spec Coverage Check

| Spec requirement | Task |
|---|---|
| Shared LLM hub identity | Tasks 3–6 |
| Popover per-app preset switching | Task 3 |
| Popover dismiss before Settings | Task 3 |
| Auto-save, no routine Save buttons | Tasks 2, 5, 6 |
| Settings tabs: LLM Presets / Apps / Activity | Task 4 |
| Retire Shared tab, move runtime under ClipMind | Task 6 |
| Retire Status tab, move to Activity | Task 4 |
| LLM Presets simplified actions | Task 5 |
| Apps visual separation | Task 6 |
| Native macOS visual quality bar | Tasks 3–6 (grouped forms, labeled content, link-style secondary actions) |
| Delete confirmation | Task 7 |
| README update | Task 8 |
| App name stays ClipMind | No rename tasks (spec non-goal) |
| No schema change | No config model tasks |

## Plan Self-Review Notes

- `ContentUnavailableView` requires macOS 14+; package already targets macOS 13 in `Package.swift`. If build fails on 13, replace with a simple `Text` empty state in Task 5.
- `List` toolbar `+` placement may need a `NavigationSplitView` wrapper if toolbar does not appear; fallback is a trailing overlay button in the sidebar column.
- `MenuBarExtra` dismiss uses `@Environment(\.dismiss)`; if it fails in manual QA, add an AppKit fallback in `presentSettings()` to close the key window before `openSettings()`.
