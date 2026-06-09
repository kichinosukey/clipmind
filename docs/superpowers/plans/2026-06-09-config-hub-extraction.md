# Config Hub Extraction Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Extract the menu bar shared LLM hub from `clipmind/macos-app/` into a new `config-hub` repository as **Config Hub.app**, migrate runtime paths to `ConfigHub/`, and update all consumers.

**Architecture:** Copy the Swift package to a new repo, rename the module to `ConfigHub`, split config paths (`ConfigHub/config.json`) from ClipMind job logs (`ClipMind/jobs/`), run a one-time legacy migration on first launch, bundle a local unsigned `.app` with optional Login Item, then update Python consumers and remove `macos-app/` from clipmind.

**Tech Stack:** Swift 6, SwiftUI, SMAppService (Login Items), XCTest, Python 3.11+, pytest, bash bundle script.

**Spec:** `docs/superpowers/specs/2026-06-09-config-hub-extraction-design.md`

**Repos touched:**
- Create: `/Users/kichinosukey-mba/projects/config-hub`
- Modify: `/Users/kichinosukey-mba/projects/clipmind`
- Modify: `/Users/kichinosukey-mba/mentalbase/projects/meeting-summary-local-llm`

---

## File Structure

### config-hub (new repo)

- Create: `Package.swift` — Swift package `ConfigHub` executable
- Move: `Sources/ConfigHub/**` — from `clipmind/macos-app/Sources/ClipMindMenuBar/**`
- Move: `Tests/ConfigHubTests/**` — from `clipmind/macos-app/Tests/ClipMindMenuBarTests/**`
- Create: `Tests/Fixtures/runtime/*.json` — copied from `clipmind/tests/fixtures/runtime/`
- Modify: `Sources/ConfigHub/Services/RuntimePaths.swift` — split config vs jobs paths
- Modify: `Sources/ConfigHub/Services/KeychainStore.swift` — new service name
- Rename: `Sources/ConfigHub/Models/ClipMindConfig.swift` → `HubConfig.swift` (type `HubConfig`)
- Rename: `Sources/ConfigHub/ConfigHubApp.swift` — from `ClipMindMenuBarApp.swift`
- Create: `Sources/ConfigHub/Services/LegacyConfigMigrator.swift` — one-time migration
- Create: `Sources/ConfigHub/Views/GeneralSettingsView.swift` — Login Item toggle
- Create: `scripts/build-app.sh` — assembles `Config Hub.app`
- Create: `ConfigHub/Info.plist` — bundle metadata template used by script
- Create: `README.md` — launch, build, migration notes
- Create: `.gitignore` — ignore `.build/`, `Config Hub.app`

### clipmind (existing repo)

- Modify: `clipmind/paths.py` — split `CONFIG_PATH` / `JOBS_DIR`, new Keychain service
- Modify: `tests/unit/test_paths.py` — assert new paths
- Modify: `tests/unit/test_secrets.py` — default service string
- Modify: `README.md` — Config Hub as external settings app
- Delete: `macos-app/` — after config-hub verified

### meeting-summary-local-llm (existing repo)

- Modify: `scripts/shared_llm_config.py` — default path + Keychain service
- Modify: `tests/test_shared_llm_config.py` — add default-path assertion

---

### Task 1: Bootstrap config-hub Repository

**Files:**
- Create: `/Users/kichinosukey-mba/projects/config-hub/` (entire repo tree)
- Copy from: `clipmind/macos-app/**` (include uncommitted `ModelDiscoveryClient` changes)

- [ ] **Step 1: Create repo directory and copy sources**

```bash
mkdir -p /Users/kichinosukey-mba/projects/config-hub
rsync -a \
  /Users/kichinosukey-mba/projects/clipmind/macos-app/ \
  /Users/kichinosukey-mba/projects/config-hub/ \
  --exclude .build
mkdir -p /Users/kichinosukey-mba/projects/config-hub/Tests/Fixtures/runtime
cp /Users/kichinosukey-mba/projects/clipmind/tests/fixtures/runtime/*.json \
   /Users/kichinosukey-mba/projects/config-hub/Tests/Fixtures/runtime/
cd /Users/kichinosukey-mba/projects/config-hub
git init
```

- [ ] **Step 2: Rename source and test directories**

```bash
cd /Users/kichinosukey-mba/projects/config-hub
mv Sources/ClipMindMenuBar Sources/ConfigHub
mv Tests/ClipMindMenuBarTests Tests/ConfigHubTests
```

- [ ] **Step 3: Write `.gitignore`**

Create `/Users/kichinosukey-mba/projects/config-hub/.gitignore`:

```gitignore
.DS_Store
.build/
Config Hub.app
*.xcworkspace
```

- [ ] **Step 4: Update `Package.swift`**

Replace `/Users/kichinosukey-mba/projects/config-hub/Package.swift` with:

```swift
// swift-tools-version: 6.0
import PackageDescription

let package = Package(
    name: "ConfigHub",
    platforms: [.macOS(.v13)],
    products: [.executable(name: "ConfigHub", targets: ["ConfigHub"])],
    targets: [
        .executableTarget(name: "ConfigHub"),
        .testTarget(name: "ConfigHubTests", dependencies: ["ConfigHub"])
    ]
)
```

- [ ] **Step 5: Commit bootstrap**

```bash
cd /Users/kichinosukey-mba/projects/config-hub
git add .
git commit -m "$(cat <<'EOF'
chore: bootstrap Config Hub package from clipmind macos-app

Copy Swift menu bar sources, tests, and shared runtime fixtures into a new
standalone repository ahead of path migration and app bundling.
EOF
)"
```

---

### Task 2: Split Runtime Paths (config vs jobs)

**Files:**
- Modify: `Sources/ConfigHub/Services/RuntimePaths.swift`
- Modify: `Sources/ConfigHub/Services/JobMonitor.swift` (default jobs URL only if needed)
- Create: `Tests/ConfigHubTests/RuntimePathsTests.swift`

- [ ] **Step 1: Write the failing path test**

Create `Tests/ConfigHubTests/RuntimePathsTests.swift`:

```swift
import XCTest
@testable import ConfigHub

final class RuntimePathsTests: XCTestCase {
    func testConfigAndJobsUseSeparateApplicationSupportDirectories() {
        XCTAssertTrue(RuntimePaths.config.path.contains("/ConfigHub/config.json"))
        XCTAssertTrue(RuntimePaths.jobs.path.contains("/ClipMind/jobs"))
        XCTAssertFalse(RuntimePaths.config.path.contains("/ClipMind/config.json"))
    }

    func testLegacyConfigPathPointsAtOldClipMindLocation() {
        XCTAssertTrue(RuntimePaths.legacyConfig.path.contains("/ClipMind/config.json"))
    }
}
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd /Users/kichinosukey-mba/projects/config-hub && swift test --filter RuntimePathsTests -v`

Expected: FAIL — `legacyConfig` missing and/or paths still under `ClipMind/config.json`.

- [ ] **Step 3: Implement split paths**

Replace `Sources/ConfigHub/Services/RuntimePaths.swift`:

```swift
import Foundation

enum RuntimePaths {
    static let configSupport = FileManager.default.homeDirectoryForCurrentUser
        .appendingPathComponent("Library/Application Support/ConfigHub")
    static let clipMindSupport = FileManager.default.homeDirectoryForCurrentUser
        .appendingPathComponent("Library/Application Support/ClipMind")

    static let config = configSupport.appendingPathComponent("config.json")
    static let jobs = clipMindSupport.appendingPathComponent("jobs")
    static let legacyConfig = clipMindSupport.appendingPathComponent("config.json")
}
```

- [ ] **Step 4: Run test to verify it passes**

Run: `cd /Users/kichinosukey-mba/projects/config-hub && swift test --filter RuntimePathsTests -v`

Expected: PASS (module rename from Task 3 may still be pending — if import fails, complete Task 3 Step 1 first, then re-run).

- [ ] **Step 5: Commit**

```bash
cd /Users/kichinosukey-mba/projects/config-hub
git add Sources/ConfigHub/Services/RuntimePaths.swift Tests/ConfigHubTests/RuntimePathsTests.swift
git commit -m "feat: split ConfigHub config path from ClipMind jobs path"
```

---

### Task 3: Rename Swift Module and Hub Types

**Files:**
- Rename: `Sources/ConfigHub/ClipMindMenuBarApp.swift` → `ConfigHubApp.swift`
- Rename: `Sources/ConfigHub/Models/ClipMindConfig.swift` → `HubConfig.swift`
- Modify: all `Sources/ConfigHub/**/*.swift`, `Tests/ConfigHubTests/**/*.swift`

- [ ] **Step 1: Mechanical rename in sources and tests**

```bash
cd /Users/kichinosukey-mba/projects/config-hub
mv Sources/ConfigHub/ClipMindMenuBarApp.swift Sources/ConfigHub/ConfigHubApp.swift
mv Sources/ConfigHub/Models/ClipMindConfig.swift Sources/ConfigHub/Models/HubConfig.swift

rg -l 'ClipMindMenuBar|ClipMindConfig|ClipMindMenuBarApp' Sources Tests | while read -r f; do
  sed -i '' \
    -e 's/ClipMindMenuBarApp/ConfigHubApp/g' \
    -e 's/ClipMindConfig/HubConfig/g' \
    -e 's/@testable import ClipMindMenuBar/@testable import ConfigHub/g' \
    "$f"
done
```

- [ ] **Step 2: Update app entry branding**

In `Sources/ConfigHub/ConfigHubApp.swift`, ensure:

```swift
@main
struct ConfigHubApp: App {
    // ...
    var body: some Scene {
        MenuBarExtra("Config Hub", systemImage: "text.badge.checkmark") {
            // ...
        }
        Settings {
            SettingsView()
                .environmentObject(jobs)
                .environmentObject(settings)
        }
    }
}
```

- [ ] **Step 3: Fix SharedContractTests fixture path**

In `Tests/ConfigHubTests/SharedContractTests.swift`, replace `fixture(_:)` with:

```swift
private func fixture(_ name: String) -> URL {
    URL(fileURLWithPath: #filePath)
        .deletingLastPathComponent()
        .deletingLastPathComponent()
        .appendingPathComponent("Fixtures/runtime/\(name)")
}
```

Update decoded type references from `ClipMindConfig` to `HubConfig`.

- [ ] **Step 4: Run full Swift test suite**

Run: `cd /Users/kichinosukey-mba/projects/config-hub && swift test -v`

Expected: all tests PASS.

- [ ] **Step 5: Commit**

```bash
cd /Users/kichinosukey-mba/projects/config-hub
git add Sources Tests
git commit -m "refactor: rename ClipMindMenuBar module to ConfigHub"
```

---

### Task 4: Update Keychain Service

**Files:**
- Modify: `Sources/ConfigHub/Services/KeychainStore.swift`
- Create: `Tests/ConfigHubTests/KeychainStoreTests.swift`

- [ ] **Step 1: Write failing service-name test**

Create `Tests/ConfigHubTests/KeychainStoreTests.swift`:

```swift
import XCTest
@testable import ConfigHub

final class KeychainStoreTests: XCTestCase {
    func testDefaultServiceUsesConfigHubIdentifier() {
        XCTAssertEqual(KeychainStore().service, "com.kichinosukey.confighub")
        XCTAssertEqual(LegacyConfigMigrator.legacyKeychainService, "com.kichinosukey.clipmind")
    }
}
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd /Users/kichinosukey-mba/projects/config-hub && swift test --filter KeychainStoreTests -v`

Expected: FAIL — service still `com.kichinosukey.clipmind` and/or `LegacyConfigMigrator` missing.

- [ ] **Step 3: Update KeychainStore**

In `Sources/ConfigHub/Services/KeychainStore.swift`, change:

```swift
let service = "com.kichinosukey.confighub"
```

- [ ] **Step 4: Run test (still fails on migrator constant)**

Expected: partial FAIL until Task 5 adds `LegacyConfigMigrator.legacyKeychainService`.

- [ ] **Step 5: Commit Keychain service change**

```bash
cd /Users/kichinosukey-mba/projects/config-hub
git add Sources/ConfigHub/Services/KeychainStore.swift Tests/ConfigHubTests/KeychainStoreTests.swift
git commit -m "feat: use confighub Keychain service identifier"
```

---

### Task 5: Legacy Config and Keychain Migration

**Files:**
- Create: `Sources/ConfigHub/Services/LegacyConfigMigrator.swift`
- Modify: `Sources/ConfigHub/ViewModels/SettingsViewModel.swift`
- Create: `Tests/ConfigHubTests/LegacyConfigMigratorTests.swift`

- [ ] **Step 1: Write failing migration tests**

Create `Tests/ConfigHubTests/LegacyConfigMigratorTests.swift`:

```swift
import XCTest
@testable import ConfigHub

final class LegacyConfigMigratorTests: XCTestCase {
    private var directory: URL!

    override func setUp() {
        super.setUp()
        directory = FileManager.default.temporaryDirectory
            .appendingPathComponent(UUID().uuidString, isDirectory: true)
        try! FileManager.default.createDirectory(at: directory, withIntermediateDirectories: true)
    }

    override func tearDown() {
        try? FileManager.default.removeItem(at: directory)
        super.tearDown()
    }

    func testMigratesLegacyConfigWhenNewConfigMissing() throws {
        let legacyDir = directory.appendingPathComponent("ClipMind", isDirectory: true)
        let newDir = directory.appendingPathComponent("ConfigHub", isDirectory: true)
        try FileManager.default.createDirectory(at: legacyDir, withIntermediateDirectories: true)
        let legacyConfig = legacyDir.appendingPathComponent("config.json")
        try Data("{}".utf8).write(to: legacyConfig)

        let migrator = LegacyConfigMigrator(
            fileManager: .default,
            legacyConfigURL: legacyConfig,
            configURL: newDir.appendingPathComponent("config.json"),
            secrets: MigratingSecretStore()
        )

        XCTAssertTrue(try migrator.migrateIfNeeded())
        XCTAssertTrue(FileManager.default.fileExists(atPath: newDir.appendingPathComponent("config.json").path))
        XCTAssertTrue(FileManager.default.fileExists(atPath: legacyDir.appendingPathComponent("config.json.migrated").path))
    }

    func testSkipsMigrationWhenNewConfigAlreadyExists() throws {
        let newConfig = directory.appendingPathComponent("ConfigHub/config.json")
        try FileManager.default.createDirectory(at: newConfig.deletingLastPathComponent(), withIntermediateDirectories: true)
        try Data("{}".utf8).write(to: newConfig)

        let migrator = LegacyConfigMigrator(
            fileManager: .default,
            legacyConfigURL: directory.appendingPathComponent("ClipMind/config.json"),
            configURL: newConfig,
            secrets: MigratingSecretStore()
        )

        XCTAssertFalse(try migrator.migrateIfNeeded())
    }
}

private struct MigratingSecretStore: SecretMigrating {
    func copySecretIfNeeded(reference: String) throws {}
}
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd /Users/kichinosukey-mba/projects/config-hub && swift test --filter LegacyConfigMigratorTests -v`

Expected: FAIL — types not found.

- [ ] **Step 3: Implement migrator**

Create `Sources/ConfigHub/Services/LegacyConfigMigrator.swift`:

```swift
import Foundation

protocol SecretMigrating {
    func copySecretIfNeeded(reference: String) throws
}

struct LegacyConfigMigrator {
    static let legacyKeychainService = "com.kichinosukey.clipmind"

    var fileManager: FileManager
    var legacyConfigURL: URL
    var configURL: URL
    var secrets: SecretMigrating

    init(
        fileManager: FileManager = .default,
        legacyConfigURL: URL = RuntimePaths.legacyConfig,
        configURL: URL = RuntimePaths.config,
        secrets: SecretMigrating = KeychainSecretMigrator()
    ) {
        self.fileManager = fileManager
        self.legacyConfigURL = legacyConfigURL
        self.configURL = configURL
        self.secrets = secrets
    }

    func migrateIfNeeded() throws -> Bool {
        if fileManager.fileExists(atPath: configURL.path) {
            return false
        }
        guard fileManager.fileExists(atPath: legacyConfigURL.path) else {
            return false
        }

        try fileManager.createDirectory(
            at: configURL.deletingLastPathComponent(),
            withIntermediateDirectories: true
        )
        try fileManager.copyItem(at: legacyConfigURL, to: configURL)

        let config = try JSONDecoder().decode(HubConfig.self, from: Data(contentsOf: configURL))
        let references = secretReferences(in: config)
        for reference in references {
            try secrets.copySecretIfNeeded(reference: reference)
        }

        let migratedURL = legacyConfigURL.deletingLastPathComponent()
            .appendingPathComponent("config.json.migrated")
        try fileManager.moveItem(at: legacyConfigURL, to: migratedURL)
        return true
    }

    private func secretReferences(in config: HubConfig) -> [String] {
        var references = Set(config.presets.map(\.apiKeyRef))
        if let discord = config.shared.discordWebhookRef { references.insert(discord) }
        if let slack = config.shared.slackWebhookRef { references.insert(slack) }
        return references.filter { !$0.trimmingCharacters(in: .whitespacesAndNewlines).isEmpty }
    }
}

struct KeychainSecretMigrator: SecretMigrating {
    private let legacy = KeychainStore(service: LegacyConfigMigrator.legacyKeychainService)
    private let current = KeychainStore()

    init() {}

    func copySecretIfNeeded(reference: String) throws {
        if (try? current.get(reference: reference)) != nil { return }
        let value = try legacy.get(reference: reference)
        try current.set(reference: reference, value: value)
    }
}
```

Update `KeychainStore` to accept injectable service:

```swift
struct KeychainStore: SecretStoring {
    let service: String

    init(service: String = "com.kichinosukey.confighub") {
        self.service = service
    }
    // existing methods unchanged
}
```

- [ ] **Step 4: Wire migration into SettingsViewModel**

In `Sources/ConfigHub/ViewModels/SettingsViewModel.swift`, update `init`:

```swift
init(
    store: ConfigStore = ConfigStore(),
    secrets: SecretStoring = KeychainStore(),
    models: ModelDiscoveryClient = ModelDiscoveryClient(),
    migrator: LegacyConfigMigrator = LegacyConfigMigrator()
) {
    self.store = store
    self.secrets = secrets
    self.models = models
  do {
    _ = try migrator.migrateIfNeeded()
    self.config = try store.load()
  } catch {
    self.config = .empty
    self.errorMessage = error.localizedDescription
  }
}
```

- [ ] **Step 5: Run migration and Keychain tests**

Run: `cd /Users/kichinosukey-mba/projects/config-hub && swift test --filter 'LegacyConfigMigratorTests|KeychainStoreTests' -v`

Expected: PASS

- [ ] **Step 6: Commit**

```bash
cd /Users/kichinosukey-mba/projects/config-hub
git add Sources/ConfigHub/Services/LegacyConfigMigrator.swift \
        Sources/ConfigHub/Services/KeychainStore.swift \
        Sources/ConfigHub/ViewModels/SettingsViewModel.swift \
        Tests/ConfigHubTests/LegacyConfigMigratorTests.swift \
        Tests/ConfigHubTests/KeychainStoreTests.swift
git commit -m "feat: migrate legacy ClipMind config and Keychain secrets on first launch"
```

---

### Task 6: Bundle Config Hub.app

**Files:**
- Create: `ConfigHub/Info.plist`
- Create: `scripts/build-app.sh`
- Modify: `README.md`

- [ ] **Step 1: Add Info.plist template**

Create `ConfigHub/Info.plist`:

```xml
<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN" "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0">
<dict>
    <key>CFBundleDevelopmentRegion</key>
    <string>en</string>
    <key>CFBundleExecutable</key>
    <string>ConfigHub</string>
    <key>CFBundleIdentifier</key>
    <string>com.kichinosukey.confighub</string>
    <key>CFBundleName</key>
    <string>Config Hub</string>
    <key>CFBundlePackageType</key>
    <string>APPL</string>
    <key>CFBundleShortVersionString</key>
    <string>0.1.0</string>
    <key>CFBundleVersion</key>
    <string>1</string>
    <key>LSMinimumSystemVersion</key>
    <string>13.0</string>
    <key>LSUIElement</key>
    <true/>
    <key>NSHighResolutionCapable</key>
    <true/>
</dict>
</plist>
```

- [ ] **Step 2: Add bundle script**

Create `scripts/build-app.sh`:

```bash
#!/usr/bin/env bash
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
APP_NAME="Config Hub"
BUILD_CONFIG="${1:-release}"

cd "$ROOT"
swift build -c "$BUILD_CONFIG"
BIN="$ROOT/.build/$(swift build -c "$BUILD_CONFIG" --show-bin-path)/ConfigHub"
APP_DIR="$ROOT/$APP_NAME.app"
CONTENTS="$APP_DIR/Contents"
MACOS="$CONTENTS/MacOS"

rm -rf "$APP_DIR"
mkdir -p "$MACOS"
cp "$BIN" "$MACOS/ConfigHub"
cp "$ROOT/ConfigHub/Info.plist" "$CONTENTS/Info.plist"
chmod +x "$MACOS/ConfigHub"

echo "Built $APP_DIR"
```

```bash
chmod +x /Users/kichinosukey-mba/projects/config-hub/scripts/build-app.sh
```

- [ ] **Step 3: Build and smoke-test app bundle**

Run:

```bash
cd /Users/kichinosukey-mba/projects/config-hub
./scripts/build-app.sh release
/usr/libexec/PlistBuddy -c 'Print :CFBundleIdentifier' "Config Hub.app/Contents/Info.plist"
file "Config Hub.app/Contents/MacOS/ConfigHub"
```

Expected:
- `com.kichinosukey.confighub`
- `Mach-O 64-bit executable arm64` (or x86_64)

Launch manually (do not use `open` on raw binary):

```bash
open "/Users/kichinosukey-mba/projects/config-hub/Config Hub.app"
```

Expected: menu bar icon appears; first launch migrates config if needed.

- [ ] **Step 4: Document in README**

Add to `README.md`:

```markdown
# Config Hub

Shared LLM preset and per-app settings hub for ClipMind, Meeting Summary, and future consumers.

## Run (development)

swift run

## Build app bundle

./scripts/build-app.sh release
open "Config Hub.app"

Do not run `open .build/.../ConfigHub` directly — use the `.app` bundle.
```

- [ ] **Step 5: Commit**

```bash
cd /Users/kichinosukey-mba/projects/config-hub
git add ConfigHub/Info.plist scripts/build-app.sh README.md
git commit -m "feat: add unsigned Config Hub.app bundle script"
```

---

### Task 7: Login Item Toggle

**Files:**
- Create: `Sources/ConfigHub/Views/GeneralSettingsView.swift`
- Modify: `Sources/ConfigHub/Views/SettingsView.swift`
- Create: `Tests/ConfigHubTests/LoginItemSettingsTests.swift`

- [ ] **Step 1: Write failing Login Item status test**

Create `Tests/ConfigHubTests/LoginItemSettingsTests.swift`:

```swift
import XCTest
@testable import ConfigHub

@MainActor
final class LoginItemSettingsTests: XCTestCase {
    func testLoginItemControllerDefaultsToServiceStatus() {
        let controller = LoginItemController(service: DisabledLoginItemService())
        XCTAssertFalse(controller.isEnabled)
    }
}

private struct DisabledLoginItemService: LoginItemServicing {
    var isEnabled: Bool { false }
    func setEnabled(_ enabled: Bool) throws {}
}
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd /Users/kichinosukey-mba/projects/config-hub && swift test --filter LoginItemSettingsTests -v`

Expected: FAIL — types not found.

- [ ] **Step 3: Implement Login Item controller and view**

Create `Sources/ConfigHub/Services/LoginItemController.swift`:

```swift
import Foundation
import ServiceManagement

protocol LoginItemServicing {
    var isEnabled: Bool { get }
    func setEnabled(_ enabled: Bool) throws
}

struct SMAppLoginItemService: LoginItemServicing {
    var isEnabled: Bool {
        SMAppService.mainApp.status == .enabled
    }

    func setEnabled(_ enabled: Bool) throws {
        if enabled {
            try SMAppService.mainApp.register()
        } else {
            try SMAppService.mainApp.unregister()
        }
    }
}

@MainActor
final class LoginItemController: ObservableObject {
    @Published var isEnabled: Bool
    @Published var errorMessage: String?
    private let service: LoginItemServicing

    init(service: LoginItemServicing = SMAppLoginItemService()) {
        self.service = service
        self.isEnabled = service.isEnabled
    }

    func setEnabled(_ enabled: Bool) {
        do {
            try service.setEnabled(enabled)
            isEnabled = service.isEnabled
            errorMessage = nil
        } catch {
            errorMessage = error.localizedDescription
        }
    }
}
```

Create `Sources/ConfigHub/Views/GeneralSettingsView.swift`:

```swift
import SwiftUI

struct GeneralSettingsView: View {
    @StateObject private var loginItem = LoginItemController()

    var body: some View {
        Form {
            Toggle("Launch at login", isOn: Binding(
                get: { loginItem.isEnabled },
                set: { loginItem.setEnabled($0) }
            ))
            if let errorMessage = loginItem.errorMessage {
                Text(errorMessage).foregroundStyle(.secondary)
            }
        }
        .formStyle(.grouped)
        .padding()
    }
}
```

Add a `General` toolbar tab or section in `SettingsView.swift`:

```swift
TabView(selection: $settings.selectedSettingsTab) {
    // existing tabs ...
}
.safeAreaInset(edge: .bottom) {
    GeneralSettingsView()
        .frame(maxHeight: 120)
}
```

(Alternatively add `SettingsTab.general` — pick one approach and keep General visible without crowding; a dedicated top tab is fine.)

- [ ] **Step 4: Run tests**

Run: `cd /Users/kichinosukey-mba/projects/config-hub && swift test --filter LoginItemSettingsTests -v`

Expected: PASS

- [ ] **Step 5: Manual Login Item check**

Rebuild app, enable toggle, verify in System Settings → General → Login Items.

- [ ] **Step 6: Commit**

```bash
cd /Users/kichinosukey-mba/projects/config-hub
git add Sources/ConfigHub/Services/LoginItemController.swift \
        Sources/ConfigHub/Views/GeneralSettingsView.swift \
        Sources/ConfigHub/Views/SettingsView.swift \
        Tests/ConfigHubTests/LoginItemSettingsTests.swift
git commit -m "feat: add launch-at-login toggle for Config Hub"
```

---

### Task 8: Update clipmind Consumer Paths

**Files:**
- Modify: `clipmind/paths.py`
- Modify: `tests/unit/test_paths.py`
- Modify: `tests/unit/test_secrets.py`
- Modify: `README.md`

- [ ] **Step 1: Write failing path test expectations**

Replace `tests/unit/test_paths.py` subprocess snippet paths with:

```python
from clipmind.paths import (
    CLIPMIND_SUPPORT_DIR,
    CONFIG_PATH,
    CONFIG_SUPPORT_DIR,
    JOBS_DIR,
    KEYCHAIN_SERVICE,
    STATUS_DIR,
)
from pathlib import Path

config_expected = Path.home() / "Library" / "Application Support" / "ConfigHub"
clipmind_expected = Path.home() / "Library" / "Application Support" / "ClipMind"

assert CONFIG_SUPPORT_DIR == config_expected
assert CONFIG_PATH == config_expected / "config.json"
assert CLIPMIND_SUPPORT_DIR == clipmind_expected
assert JOBS_DIR == clipmind_expected / "jobs"
assert STATUS_DIR == JOBS_DIR
assert KEYCHAIN_SERVICE == "com.kichinosukey.confighub"
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd /Users/kichinosukey-mba/projects/clipmind && .venv/bin/python -m pytest tests/unit/test_paths.py -v`

Expected: FAIL — `CONFIG_SUPPORT_DIR` missing or old paths.

- [ ] **Step 3: Update `clipmind/paths.py`**

```python
CONFIG_SUPPORT_DIR = Path.home() / "Library" / "Application Support" / "ConfigHub"
CONFIG_PATH = CONFIG_SUPPORT_DIR / "config.json"
CLIPMIND_SUPPORT_DIR = Path.home() / "Library" / "Application Support" / "ClipMind"
JOBS_DIR = CLIPMIND_SUPPORT_DIR / "jobs"
KEYCHAIN_SERVICE = "com.kichinosukey.confighub"
STATUS_DIR = JOBS_DIR
```

Remove old `APPLICATION_SUPPORT_DIR` or keep as deprecated alias only if tests still need it — prefer delete and fix imports.

- [ ] **Step 4: Update secrets test service string**

In `tests/unit/test_secrets.py`, change expected service to `com.kichinosukey.confighub` and update test name accordingly.

- [ ] **Step 5: Run clipmind unit tests**

Run: `cd /Users/kichinosukey-mba/projects/clipmind && .venv/bin/python -m pytest tests/unit/test_paths.py tests/unit/test_secrets.py -v`

Expected: PASS

- [ ] **Step 6: Update README path references**

Replace `~/Library/Application Support/ClipMind/config.json` with `ConfigHub/config.json` and document Config Hub as the settings UI.

- [ ] **Step 7: Commit**

```bash
cd /Users/kichinosukey-mba/projects/clipmind
git add clipmind/paths.py tests/unit/test_paths.py tests/unit/test_secrets.py README.md
git commit -m "feat: read shared config from ConfigHub application support path"
```

---

### Task 9: Update Meeting Summary Consumer

**Files:**
- Modify: `mentalbase/projects/meeting-summary-local-llm/scripts/shared_llm_config.py`
- Modify: `mentalbase/projects/meeting-summary-local-llm/tests/test_shared_llm_config.py`

- [ ] **Step 1: Write failing default-path test**

Add to `tests/test_shared_llm_config.py`:

```python
def test_default_config_path_points_at_config_hub() -> None:
    expected = (
        Path.home()
        / "Library"
        / "Application Support"
        / "ConfigHub"
        / "config.json"
    )
    assert uut.DEFAULT_CONFIG_PATH == expected
    assert uut.KEYCHAIN_SERVICE == "com.kichinosukey.confighub"
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd /Users/kichinosukey-mba/mentalbase/projects/meeting-summary-local-llm && python -m pytest tests/test_shared_llm_config.py::test_default_config_path_points_at_config_hub -v`

Expected: FAIL

- [ ] **Step 3: Update shared_llm_config.py**

```python
KEYCHAIN_SERVICE = "com.kichinosukey.confighub"
DEFAULT_CONFIG_PATH = (
    Path.home() / "Library" / "Application Support" / "ConfigHub" / "config.json"
)
```

- [ ] **Step 4: Run meeting-summary tests**

Run: `cd /Users/kichinosukey-mba/mentalbase/projects/meeting-summary-local-llm && python -m pytest tests/test_shared_llm_config.py -v`

Expected: PASS

- [ ] **Step 5: Commit**

```bash
cd /Users/kichinosukey-mba/mentalbase/projects/meeting-summary-local-llm
git add scripts/shared_llm_config.py tests/test_shared_llm_config.py
git commit -m "feat: load shared LLM config from ConfigHub path"
```

---

### Task 10: Remove macos-app from clipmind and Final Verification

**Files:**
- Delete: `clipmind/macos-app/`
- Modify: `clipmind/README.md`
- Modify: `clipmind/.handoff/handoff_app-packaging-decision_20260609.md` (optional retrospective note)

- [ ] **Step 1: Verify config-hub full test suite**

Run: `cd /Users/kichinosukey-mba/projects/config-hub && swift test -v`

Expected: all tests PASS

- [ ] **Step 2: Production config safety check (before migration test on live files)**

Run:

```bash
python3 - <<'PY'
import json
from pathlib import Path
p = Path.home() / "Library/Application Support/ClipMind/config.json"
if p.exists():
    c = json.loads(p.read_text())
    presets = {x["id"]: x["model"] for x in c["presets"]}
    active = c["appProfiles"]["clipmind"]["activePresetId"]
    print("active preset model:", presets.get(active))
    print("has test preset first:", "first" in presets)
PY
```

Expected before migration: active model `google/gemma-4-12b`, no preset `first`.

- [ ] **Step 3: Launch Config Hub.app and confirm migration**

```bash
open "/Users/kichinosukey-mba/projects/config-hub/Config Hub.app"
ls -la ~/Library/Application\ Support/ConfigHub/
ls -la ~/Library/Application\ Support/ClipMind/
```

Expected:
- `ConfigHub/config.json` exists
- `ClipMind/config.json.migrated` exists (if legacy config existed)
- `ClipMind/jobs/` unchanged

- [ ] **Step 4: Re-run production config safety check on new path**

Same script with `ConfigHub/config.json`.

Expected: same model and no `first` preset.

- [ ] **Step 5: Verify ClipMind pipeline still works**

```bash
cd /Users/kichinosukey-mba/projects/clipmind
.venv/bin/python -m clipmind.repair pfhkimncbkbpekfooffdpmbinggfneab
```

Reload Chrome extension; run a short summarize job; confirm Activity tab updates.

- [ ] **Step 6: Remove macos-app from clipmind**

```bash
cd /Users/kichinosukey-mba/projects/clipmind
git rm -r macos-app
git commit -m "chore: remove macos-app after Config Hub extraction"
```

- [ ] **Step 7: Force-add plan doc and commit in clipmind**

```bash
cd /Users/kichinosukey-mba/projects/clipmind
git add -f docs/superpowers/plans/2026-06-09-config-hub-extraction.md
git commit -m "docs: add Config Hub extraction implementation plan"
```

---

## Manual Verification Checklist

- [ ] `Config Hub.app` launches from Finder without `swift run`
- [ ] Login Item survives reboot
- [ ] Settings tabs load migrated presets
- [ ] ClipMind Chrome pipeline runs against `ConfigHub/config.json`
- [ ] Meeting Summary resolves preset from new path
- [ ] `swift test` passes in config-hub
- [ ] `pytest tests/unit/test_paths.py` passes in clipmind

## Spec Coverage Self-Review

| Spec requirement | Task |
|------------------|------|
| New `config-hub` repo | Task 1 |
| Rename to Config Hub | Task 3 |
| Config path `ConfigHub/` | Task 2 |
| Jobs stay `ClipMind/jobs/` | Task 2 |
| Keychain `com.kichinosukey.confighub` | Task 4, 5 |
| Legacy migration | Task 5 |
| `.app` bundle unsigned | Task 6 |
| Login Item | Task 7 |
| clipmind consumer update | Task 8 |
| meeting-summary consumer update | Task 9 |
| Remove `macos-app/` | Task 10 |
| No signing/distribution | Tasks 6–7 only |
