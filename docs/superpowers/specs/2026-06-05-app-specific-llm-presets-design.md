# App-Specific LLM Presets Design

## Context

The shared local LLM config now lets `meeting-summary-local-llm` read ClipMind's active LLM preset. That proves the shared preset contract works, but it still exposes a usability gap: ClipMind and Meeting Summary currently appear to use the same active preset.

The intended mental model is app-specific preset selection:

```text
Apps
    ├─ ClipMind
    │    └─ active preset: X
    └─ Meeting Summary
         └─ active preset: Y
```

This design adds that selection layer without splitting preset definitions or renaming the app.

## Decision

Add `appProfiles` to the existing ClipMind config schema. Each app profile can point at one of the shared LLM presets.

The global `activePresetId` remains as a backward-compatible default. Existing configs without `appProfiles` continue to work.

## Goals

- Let ClipMind and Meeting Summary choose different LLM presets.
- Keep LLM preset definitions shared and reusable.
- Preserve existing config files by making `appProfiles` optional.
- Keep the first implementation limited to app-specific active LLM preset selection.
- Avoid moving Whisper, output, destinations, Slack, Notion, or style settings in this step.

## Non-Goals

- Rename ClipMind Menu Bar into a generic Local AI app.
- Add a plugin system for arbitrary apps.
- Split presets into per-app preset lists.
- Move ClipMind-specific settings under `Apps > ClipMind`.
- Move Meeting Summary output/style/routing settings into the menu bar app.

## Configuration Shape

Existing config shape remains valid:

```json
{
  "schemaVersion": 1,
  "activePresetId": "default",
  "presets": [
    {
      "id": "default",
      "name": "Default",
      "baseURL": "http://localhost:1234/v1",
      "model": "local-model",
      "apiKeyRef": "preset-default-api-key"
    }
  ],
  "shared": {}
}
```

New config may include:

```json
{
  "schemaVersion": 1,
  "activePresetId": "default",
  "presets": [
    {
      "id": "default",
      "name": "Default",
      "baseURL": "http://localhost:1234/v1",
      "model": "local-model",
      "apiKeyRef": "preset-default-api-key"
    },
    {
      "id": "clipmind-fast",
      "name": "ClipMind Fast",
      "baseURL": "http://localhost:1234/v1",
      "model": "fast-model",
      "apiKeyRef": "preset-clipmind-fast-api-key"
    },
    {
      "id": "meeting-long-context",
      "name": "Meeting Long Context",
      "baseURL": "http://localhost:1234/v1",
      "model": "long-context-model",
      "apiKeyRef": "preset-meeting-long-context-api-key"
    }
  ],
  "appProfiles": {
    "clipmind": {
      "activePresetId": "clipmind-fast"
    },
    "meeting-summary-local-llm": {
      "activePresetId": "meeting-long-context"
    }
  },
  "shared": {}
}
```

App IDs are stable strings:

```text
clipmind
meeting-summary-local-llm
```

Each `activePresetId` must either be empty or reference an existing preset. Empty means "use the global default".

## Resolution Rules

ClipMind resolves presets as:

```text
appProfiles.clipmind.activePresetId
  -> activePresetId
```

Meeting Summary resolves presets as:

```text
appProfiles.meeting-summary-local-llm.activePresetId
  -> activePresetId
  -> existing env/default behavior
```

Meeting Summary still preserves its outer precedence:

```text
CLI args
  > existing environment variables
  > app-specific shared preset
  > global shared preset
  > existing defaults or auto-selection
```

## UI Shape

The settings window gets an Apps tab:

```text
Settings
    ├─ LLM Presets
    │    ├─ preset A
    │    ├─ preset B
    │    └─ preset C
    │
    ├─ Apps
    │    ├─ ClipMind
    │    │    └─ LLM preset: preset A
    │    │
    │    └─ Meeting Summary
    │         └─ LLM preset: preset B
    │
    ├─ Shared
    └─ Status
```

The Apps tab only manages active LLM preset selection. It does not expose app-specific non-LLM settings yet.

Suggested controls:

```text
ClipMind
  LLM preset: [Default ▼]

Meeting Summary
  LLM preset: [Default ▼]
```

The dropdown values include:

```text
Default
<all configured preset names>
```

`Default` stores an empty app-specific preset ID and falls back to global `activePresetId`.

## Deletion Behavior

When a preset is deleted:

```text
if global activePresetId points to deleted preset:
    set global activePresetId to the first remaining preset

for each app profile:
    if app activePresetId points to deleted preset:
        clear app activePresetId
```

Clearing the app-specific ID makes that app fall back to the global default.

## Validation

Config writers should validate:

- `activePresetId` references an existing preset.
- Each non-empty `appProfiles.*.activePresetId` references an existing preset.
- Unknown app IDs are allowed for forward compatibility but ignored by current UI.
- `appProfiles` may be absent.

Config readers should fail softly where appropriate:

- ClipMind's writer remains strict when saving invalid preset references.
- Meeting Summary treats invalid, missing, or unknown app profile references as absent and falls back.

## Testing

ClipMind tests should cover:

- Decoding config without `appProfiles`.
- Decoding config with `appProfiles`.
- Saving preserves `appProfiles`.
- Validation rejects app profile preset IDs that do not exist.
- Deleting a preset clears app-specific references to it.
- Apps UI can select default or a concrete preset.

Meeting Summary tests should cover:

- `meeting-summary-local-llm` app profile overrides global active preset.
- Missing app profile falls back to global active preset.
- Empty app profile preset ID falls back to global active preset.
- Invalid app profile preset ID falls back to global active preset.
- CLI and env vars still override the app-specific preset.

## Migration

No automatic migration is required.

Existing configs do not have `appProfiles`; they behave exactly as today. The first save from the updated app may write an `appProfiles` object if the user changes Apps settings.

## Risks

- This makes the ClipMind config more general while the app is still named ClipMind.
- Unknown future apps may need more than just an active preset ID.
- The schema remains version `1`, so compatibility relies on optional fields rather than a hard version bump.

These risks are acceptable because the change is additive and keeps old configs readable.
