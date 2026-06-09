# Config Hub Extraction Design

## Context

The menu bar application manages shared LLM presets and per-app settings for
multiple consumers (ClipMind, Meeting Summary, and future apps). The 2026-06-09
Settings Hub UI design established this as a **shared LLM hub**, not a ClipMind
accessory.

Today the app lives at `clipmind/macos-app/` and reads/writes
`~/Library/Application Support/ClipMind/config.json`. This creates two problems:

1. **Launch friction** — dev-build only (`swift run`); users forget how to start
   the app; no `.app` bundle or Login Item.
2. **Product boundary mismatch** — the hub is not ClipMind-specific, but its
   repository location, config path, and branding imply otherwise.

This design extracts the hub into a new repository, renames it **Config Hub**,
migrates the shared config path, and packages it as a local `.app` with optional
Login Item registration.

## Relationship to Prior Designs

This design builds on:

- `2026-06-09-settings-hub-ui-design.md` — hub IA, auto-save, three-tab model
- `2026-06-05-llm-preset-app-profile-boundary-design.md` — config schema ownership
- `2026-06-04-macos-menu-bar-management-design.md` — thin native shell over shared config

It supersedes the 2026-06-09 design's application naming decision ("ClipMind"
in menu bar and window title) and its Non-Goal boundary for local packaging only
(signing/distribution remain out of scope).

## Decision Summary

| Item | Before | After |
|------|--------|-------|
| Repository | `clipmind/macos-app/` | `config-hub` (new repo) |
| App display name | ClipMind | **Config Hub** |
| `.app` name | (none) | **Config Hub.app** |
| Swift package / target | `ClipMindMenuBar` | `ConfigHub` |
| Bundle ID | (unset) | `com.kichinosukey.confighub` |
| Shared config path | `~/Library/Application Support/ClipMind/config.json` | `~/Library/Application Support/ConfigHub/config.json` |
| Keychain service | `com.kichinosukey.clipmind` | `com.kichinosukey.confighub` |
| ClipMind jobs path | `~/Library/Application Support/ClipMind/jobs/` | **unchanged** |
| `appProfiles` keys | `clipmind`, `meeting-summary-local-llm` | **unchanged** |
| Config schema | existing v1 | **unchanged** |

## Product Identity

**Config Hub** is a macOS menu bar settings center for shared LLM connection
presets and per-app configuration. ClipMind is one consumer app listed under
the `Apps` tab, not the organizing principle of the product.

The hub owns:

- `ConfigHub/config.json` — presets, appProfiles, shared runtime fields
- Keychain secrets referenced by preset `apiKeyRef` values

The hub reads but does not own:

- `ClipMind/jobs/` — ClipMind pipeline job status (Activity tab)

## Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│  config-hub (new repo)                                          │
│  ┌──────────────────┐                                           │
│  │  Config Hub.app  │  Menu Bar + Settings UI                   │
│  └────────┬─────────┘                                           │
└───────────┼─────────────────────────────────────────────────────┘
            │
            │  read/write                    read-only
            ▼                                  ▼
┌──────────────────────────┐      ┌──────────────────────────────┐
│ ~/Library/.../ConfigHub/ │      │ ~/Library/.../ClipMind/jobs/ │
│   config.json            │      │   (ClipMind runtime logs)    │
└──────────┬───────────────┘      └──────────────▲───────────────┘
           │                                     │
           │                                     │ write
           ▼                                     │
┌──────────────────────────┐      ┌──────────────┴───────────────┐
│ Keychain                 │      │ clipmind repo (existing)      │
│ com.kichinosukey.confighub│     │  Python / Chrome / native-host│
└──────────┬───────────────┘      └──────────────────────────────┘
           │
           │ read (secrets)
           ▼
┌──────────────────────────┐
│ meeting-summary repo     │
│  Meeting Summary         │
└──────────────────────────┘
```

### Data flow

```
[Config Hub.app]
    │
    ├─► ConfigHub/config.json     … presets, appProfiles (read/write)
    ├─► Keychain (confighub)      … API key, webhook (read/write)
    └─► ClipMind/jobs/            … Activity tab (read-only)

[clipmind Python]
    ├─► ConfigHub/config.json     … preset resolution (read)
    └─► ClipMind/jobs/            … job status (write)

[Meeting Summary]
    ├─► ConfigHub/config.json     … preset resolution (read)
    └─► Keychain (confighub)      … API token (read)
```

### Why jobs stay under ClipMind

`jobs/` is ClipMind pipeline runtime data, not shared hub configuration.
Splitting config (`ConfigHub/`) from ClipMind runtime logs (`ClipMind/jobs/`)
keeps the hub generic as new consumer apps are added.

## Components

### config-hub (new repository)

Responsibilities:

- SwiftUI menu bar app (`ConfigHub` executable → `Config Hub.app`)
- Config read/write with atomic save (existing `ConfigStore` behavior)
- Keychain read/write for preset secrets
- Job monitoring for Activity tab (read `ClipMind/jobs/`)
- One-time migration from legacy paths on first launch
- Login Item registration UI (`SMAppService`)
- Release build + bundle script (no codesign/notarization)

Source migration: move `clipmind/macos-app/` wholesale, then rename targets,
types, and constants.

### clipmind (existing repository)

Responsibilities after extraction:

- Python pipeline, Chrome extension, native-host (unchanged roles)
- `paths.py` splits `CONFIG_PATH` (ConfigHub) from `JOBS_DIR` (ClipMind)
- `KEYCHAIN_SERVICE` updated to `com.kichinosukey.confighub`
- README documents Config Hub as external dependency for settings UI
- Remove `macos-app/` after migration is verified

`clipmind.repair` remains responsible for Chrome native-host manifest only;
it does not manage the hub app.

### meeting-summary-local-llm (existing repository)

Responsibilities:

- `scripts/shared_llm_config.py` path and Keychain service updated
- Tests updated for new default config path

## Migration

### Trigger

Config Hub first launch when `ConfigHub/config.json` does not exist.

### Steps

```
初回起動 Config Hub.app
    │
    ├─ ConfigHub/config.json あり? ──Yes──► 通常起動
    │
    └─ No
         │
         ├─ ClipMind/config.json あり? ──No──► 新規 config 作成
         │
         └─ Yes
              ├─ config を ConfigHub/ へコピー
              ├─ Keychain secrets を旧→新 service へコピー
              │    (account 名は apiKeyRef 等そのまま)
              └─ 旧 config を config.json.migrated にリネーム
```

### Migration rules

- Copy, do not move, until the new config is successfully loaded and saved once.
- After successful first save under ConfigHub, rename legacy file to
  `config.json.migrated` in the old location.
- Do not migrate or relocate `ClipMind/jobs/`.
- If both old and new configs exist, prefer the new path; never overwrite
  an existing `ConfigHub/config.json`.
- Keychain migration copies generic passwords from `com.kichinosukey.clipmind`
  to `com.kichinosukey.confighub` for all accounts referenced by the migrated
  config's presets. Skip accounts that already exist in the new service.

### Production safety

Before and after migration, verify production config invariants:

- Active ClipMind preset model remains `google/gemma-4-12b`
- Test preset `first` is not present in production config

## Packaging and Launch

### Build output

- `swift build -c release` produces the executable
- A bundle script assembles `Config Hub.app` with `Info.plist` and icon
- Bundle ID: `com.kichinosukey.confighub`
- Built artifact is gitignored; not committed

### Login Item

- Offer Login Item toggle in Settings (General section or equivalent)
- Use `SMAppService` for macOS 13+
- Success criterion: app starts automatically after reboot without manual
  `swift run`

### Gatekeeper (unsigned local build)

- No codesign or notarization in this scope
- First launch may require right-click → Open
- Document this in README

## Rename Scope (Swift)

### User-visible

- Menu bar label: Config Hub
- Settings window title: Config Hub
- About / bundle display name: Config Hub

### Internal (mechanical rename during extraction)

| Before | After |
|--------|-------|
| `ClipMindMenuBar` (package/target) | `ConfigHub` |
| `ClipMindMenuBarApp` | `ConfigHubApp` |
| `ClipMindConfig` | `HubConfig` |
| `ClipMindRuntimeSection` | unchanged (ClipMind app section) |
| `RuntimePaths.applicationSupport` | split into `configSupport` + `clipMindJobs` |

Keep consumer-specific names (`ClipMindRuntimeSection`, `clipmind` app ID,
`defaultClipMind` settings) — these refer to the ClipMind consumer, not the hub
product.

## Consumer Path Updates

### clipmind/clipmind/paths.py

```python
CONFIG_SUPPORT_DIR = Path.home() / "Library" / "Application Support" / "ConfigHub"
CONFIG_PATH = CONFIG_SUPPORT_DIR / "config.json"
JOBS_DIR = Path.home() / "Library" / "Application Support" / "ClipMind" / "jobs"
KEYCHAIN_SERVICE = "com.kichinosukey.confighub"
```

Remove the old `APPLICATION_SUPPORT_DIR` single-path assumption.

### meeting-summary-local-llm/scripts/shared_llm_config.py

```python
KEYCHAIN_SERVICE = "com.kichinosukey.confighub"
DEFAULT_CONFIG_PATH = Path.home() / "Library" / "Application Support" / "ConfigHub" / "config.json"
```

## Implementation Phases

| Phase | Work | Repository |
|-------|------|------------|
| 1 | Create `config-hub` repo; move and rename `macos-app/` | config-hub |
| 2 | Update runtime paths, Keychain service, display names | config-hub |
| 3 | Add `.app` bundle script + Login Item | config-hub |
| 4 | Add first-launch migration (config + Keychain) | config-hub |
| 5 | Update consumer paths and tests | clipmind, meeting-summary |
| 6 | Remove `macos-app/` from clipmind; update READMEs | clipmind |

Phases 1–4 can ship independently for local dogfooding. Phase 5 must land
before consumers are used without the hub. Phase 6 is cleanup after verification.

## Error Handling

- Migration failure: show alert with legacy path; do not delete old config
- Keychain copy failure per account: log warning, continue other accounts;
  surface which preset secrets need manual re-entry
- Config load failure after migration: fall back to read-only display of error;
  do not corrupt existing files
- Login Item registration failure: non-blocking; show instruction to enable
  manually in System Settings

## Testing

### config-hub

- Unit tests for path constants (config vs jobs separation)
- Migration tests: old config present → new path populated; idempotent re-run
- Keychain migration tests with mocked store
- Existing Settings Hub UI tests (renamed imports)
- Bundle script smoke test: produces valid `.app` structure

### clipmind

- `test_paths.py` — CONFIG_PATH and JOBS_DIR point to separate directories
- Existing config resolution tests with updated paths

### meeting-summary-local-llm

- `test_shared_llm_config.py` — default path and Keychain service

### Manual verification

1. Migrate production config; confirm preset model unchanged
2. Launch Config Hub.app; confirm Settings tabs load
3. Run ClipMind pipeline; confirm jobs appear in Activity tab
4. Run Meeting Summary; confirm preset resolution works
5. Enable Login Item; reboot; confirm app is running
6. Run `clipmind.repair` + Chrome reload; confirm pipeline still works

## Non-Goals

- Apple codesign, notarization, or distribution (.dmg, App Store)
- Auto-update mechanism
- Config schema version bump or destructive migration
- Renaming `appProfiles` keys or ClipMind consumer settings
- Moving `ClipMind/jobs/` to ConfigHub
- Meeting Summary job ingestion into Activity tab
- Changing Chrome native-host manifest naming (`com.clipmind.host`)

## Success Criteria

1. Config Hub launches from `Config Hub.app` without `swift run`
2. Login Item enables automatic start after reboot
3. Shared config lives at `ConfigHub/config.json`; consumers read it
4. Existing production settings survive migration unchanged
5. `clipmind/macos-app/` is removed; hub development happens in `config-hub`
