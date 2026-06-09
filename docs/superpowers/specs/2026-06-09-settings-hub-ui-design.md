# Settings Hub UI Design

## Context

The LLM preset and app profile boundary work (2026-06-05) fixed configuration
ownership in schema and runtime. The menu bar app UI, however, still presents
settings as a flat collection of tabs and buttons without a coherent product
identity or interaction model.

Observed problems from live UI review (2026-06-09):

- The menu bar popover layout feels ad hoc and visually weak.
- Opening Settings from the popover leaves both windows visible and overlapping.
- `LLM Presets` exposes too many primary actions (`Save API Key`, `Save`,
  `Test Connection`, `Duplicate`, `Add Preset`) with unclear priority.
- `Apps` does not visually separate ClipMind from Meeting Summary, and a single
  `Save` button makes save scope ambiguous.
- `Shared` and `Status` are ClipMind-specific surfaces presented as generic
  top-level tabs, which conflicts with the shared LLM hub concept.

Continuing with piecemeal visual fixes would produce inconsistent UI behavior.
This design establishes product identity, information architecture, interaction
rules, and visual quality expectations before implementation.

## Relationship to Prior Designs

This design builds on:

- `2026-06-05-llm-preset-app-profile-boundary-design.md` — config ownership
- `2026-06-04-macos-menu-bar-management-design.md` — thin native shell over
  shared config and job status

It does not change the config schema or runtime resolution rules except for UI
placement of existing fields. `shared` config keys remain in `config.shared`;
only their Settings surface moves under `Apps > ClipMind`.

## Product Identity

The menu bar application is a **shared LLM hub**: a settings center that bundles
connection presets and per-app configuration for tools that consume
`~/Library/Application Support/ClipMind/config.json`.

ClipMind is one consumer app, not the organizing principle of the whole UI.
Meeting Summary is another consumer. Future apps should have an obvious place
to register without reshaping the top-level model.

The application name remains **ClipMind** in the menu bar and window title.

## Design Principles

### 1. Three-layer model

| Layer | Purpose | Settings home |
|---|---|---|
| Presets | Reusable LLM connection templates | `LLM Presets` tab |
| Apps | Per-app selection and owned settings | `Apps` tab |
| Activity | Runtime observability across consumers | `Activity` tab |

Every new setting must map to exactly one layer before UI work begins.

### 2. Touch-to-persist

Changes persist automatically. The UI does not use explicit `Save` buttons for
routine field edits. Destructive actions (`Delete preset`) require confirmation.

Secrets (API keys, webhooks) write to Keychain when the user commits the field
(on submit or focus loss), not through a separate save action.

### 3. Popover is a shortcut; Settings is canonical

The menu bar popover supports quick per-app preset switching and a one-line
activity summary. Full editing happens in Settings.

### 4. Native macOS quality bar

The UI must read as a first-party macOS settings experience, not a first Swift
project prototype. Concretely:

- Use system typography, spacing, and control styles (`.formStyle(.grouped)`,
  `LabeledContent`, `Picker` with `.menu` style, standard toolbar items).
- Align to Human Interface Guidelines for menu bar extras and settings windows.
- Prefer consistent vertical rhythm (8pt grid), generous section padding, and
  clear hierarchy over decorative chrome.
- Use `GroupBox` or grouped `Form` sections for app cards; avoid bare stacked
  fields without headers.
- Keep destructive actions in context menus or secondary placements.
- Avoid duplicate controls that perform the same action in different places.
- Popover width, padding, and divider spacing should match system menu density.

Quality is judged by side-by-side comparison with System Settings and other
Apple menu bar utilities, not by feature count.

## Information Architecture

### Top-level Settings tabs

```text
LLM Presets  |  Apps  |  Activity
```

Retired top-level tabs:

- `Shared` → content moves to `Apps > ClipMind > Runtime`
- `Status` → content moves to `Activity`

### Menu bar popover

```text
┌─────────────────────────────┐
│ ClipMind          [Default ▾]│
│ Meeting Summary   [Default ▾]│
├─────────────────────────────┤
│ ● 実行中 0  ·  直近: 完了 …  │  ← tap opens Activity tab
├─────────────────────────────┤
│      設定を開く…             │
│      終了                    │
└─────────────────────────────┘
```

Rules:

- One row per supported app: app display name, current preset name, preset
  picker bound to `appProfiles.<appId>.activePresetId`.
- Preset changes auto-save immediately through existing `ConfigStore`.
- Remove the global-only `プリセット` picker from the popover; per-app selection
  is the hub model.
- Activity summary is a single compact line, not a multi-line status block.
- Tapping the activity summary opens Settings on the `Activity` tab.
- `設定を開く…` must close the popover before presenting Settings so two
  windows never overlap.

## Screen Specifications

### LLM Presets

Purpose: manage shared connection templates only.

Layout:

- Left: preset list (standard sidebar width ~180pt).
- Right: detail pane for the selected preset.

Detail fields:

- Name
- Base URL
- Model (with optional discovered-models picker when available)
- API key (SecureField)

Primary actions:

- Toolbar or list header: `+` to add a preset (only entry point for creation).
- List item context menu: `Duplicate`, `Delete…` (with confirmation).

Secondary actions:

- `Test Connection` moves out of the primary button row. Place it as a link,
  trailing accessory, or `…` menu action labeled `接続を確認`.

Removed from primary UI:

- `Save`, `Save API Key`, standalone `Add Preset`, inline `Duplicate`,
  inline `Delete`.

Helper copy (one line, secondary style):

```text
LLM presets are shared connection settings. App-specific prompts and limits live under Apps.
```

### Apps

Purpose: per-app preset selection and app-owned settings.

Layout: vertically stacked app cards with clear visual separation.

#### ClipMind card

Sections inside the card:

1. **LLM** — preset picker
2. **Prompts** — summarize/translate system and user prompts
3. **Runtime** (relocated from old `Shared` tab):
   - Whisper binary path
   - Whisper model path
   - Output root
   - Destinations (Discord, Slack toggles and webhook secure fields)

#### Meeting Summary card

Sections:

1. **LLM** — preset picker
2. **Limits** — timeout, context length

Rules:

- No `Save` button anywhere on this tab.
- Webhook secrets persist on field commit, same as API keys.
- Section headers use `GroupBox` labels or grouped `Form` sections.
- Cards must be visually distinct (spacing + header typography), not one
  continuous form list.

### Activity

Purpose: cross-app runtime observability.

Initial content (ClipMind jobs only):

- Active job count
- Current job stage and title/source
- Most recent terminal job result
- Error summary when present

Future: Meeting Summary job reporting may feed this tab; out of scope for the
first implementation pass.

Entry points:

- Settings `Activity` tab
- Popover activity summary tap

## Interaction Model

### Auto-save

| User action | Persist behavior |
|---|---|
| Text field edit | Save config on commit (focus loss or Return) |
| Picker change | Save immediately |
| Toggle change | Save immediately |
| API key / webhook secure field | Write Keychain on commit; update config refs as today |
| Popover preset change | Save immediately via existing app profile binding |
| Delete preset | Confirm, then save |

### Error handling

- Inline validation messages appear adjacent to the offending field or below the
  section header.
- Failed save surfaces a non-blocking banner or inline error in the affected
  tab; do not use modal alerts for validation.

### Window lifecycle

- Opening Settings from the popover closes the menu bar extra window first.
- Settings opens on the tab appropriate to the entry point (default: last used
  tab; activity summary → `Activity`).

## Visual Specification

### Popover

- Fixed comfortable width (~280–320pt).
- App rows use `LabeledContent` or HStack with trailing `Picker`.
- Dividers between functional zones (apps / activity / actions).
- Action buttons use standard menu-bar button styling, not full-width stacked
  gray pills unless system style requires it.

### Settings window

- Minimum size remains similar to today (~680×520) but internal padding follows
  grouped form conventions.
- Tab bar uses standard `TabView` tab items with SF Symbols already in use.
- Sidebar list in `LLM Presets` uses `List` selection highlighting consistent
  with Finder/System Settings sidebars.
- Avoid floating unlabeled button clusters at the bottom of panes.

### Accessibility

- Every picker and field has a visible label (no placeholder-only labeling).
- Activity summary is a button with accessibility hint describing navigation to
  Activity tab.

## Non-Goals

- Renaming the app to `ClipMind Hub` or similar.
- Custom themes, non-system fonts, or non-native control chrome.
- Meeting Summary job ingestion into `Activity`.
- Moving Meeting Summary output, style, routing, Slack, or Notion settings into
  the hub.
- Plugin system for arbitrary third-party apps.
- Config schema version bump or destructive migration.
- App signing, distribution, or auto-update work.

## Testing

SwiftUI tests (existing patterns in `ClipMindMenuBarTests`):

- Popover view model bindings: per-app preset IDs update `appProfiles` and
  trigger save.
- Settings auto-save: field change invokes `ConfigStore.save` without a button.
- `LLM Presets` editor exposes only connection fields in the primary detail pane.
- `Apps` view renders separate ClipMind and Meeting Summary sections.
- Relocated runtime fields bind to `config.shared` unchanged.
- Opening Settings from popover calls popover dismiss before presentation (unit
  test via extracted coordinator or view-model hook).

Manual acceptance checks:

- Popover no longer overlaps Settings when opened.
- No `Save` buttons on `Apps` or `LLM Presets` primary surfaces.
- `Shared` and `Status` tabs are gone; their content is reachable in the new
  locations.
- UI side-by-side with System Settings does not feel prototype-grade.

## Implementation Order

1. Add a small UI coordinator for popover dismiss + Settings tab routing.
2. Redesign `MenuContentView` to per-app preset rows and compact activity line.
3. Restructure `SettingsView` to three tabs (`LLM Presets`, `Apps`, `Activity`).
4. Refactor `PresetEditorView` for auto-save and simplified actions.
5. Refactor `AppProfilesView` into separated app cards; move `SharedSettingsView`
   fields under ClipMind runtime section.
6. Move `StatusView` content to `ActivityView` (rename or new file).
7. Remove obsolete views/tabs and dead Save-button code paths.
8. Update `macos-app/README.md` tab descriptions to match new IA.
9. Run `swift build`, `swift test`, and manual UI acceptance pass.

## Risks

- `MenuBarExtra` with `.window` style may need AppKit hooks to reliably close
  the popover before opening Settings.
- Auto-save on every keystroke would be noisy; commit-on-blur must be implemented
  consistently across fields.
- Relocating `Shared` fields under ClipMind may surprise users who memorized the
  old tab; helper copy in `Apps` should mention the move once.
- High visual quality bar increases implementation time but reduces future
  rework from ambiguous design.

## Decision Log

| Date | Decision |
|---|---|
| 2026-06-09 | Product identity: shared LLM hub (not ClipMind-first shell) |
| 2026-06-09 | Popover: per-app preset quick switching |
| 2026-06-09 | Persistence: auto-save; no routine Save buttons |
| 2026-06-09 | Settings IA: `LLM Presets` / `Apps` / `Activity` |
| 2026-06-09 | App name stays `ClipMind` |
| 2026-06-09 | Visual bar: native macOS / museum-grade polish required |
