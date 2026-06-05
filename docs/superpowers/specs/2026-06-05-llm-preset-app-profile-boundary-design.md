# LLM Preset and App Profile Boundary Design

## Context

The current app-specific preset implementation lets ClipMind and Meeting Summary pick different active presets through `appProfiles.<appId>.activePresetId`.

That solves selection, but it leaves a deeper boundary problem:

- `presets` are described as shared LLM presets.
- `presets` also contain ClipMind-specific summary and translation prompts.
- Meeting Summary reads `timeout` and `contextLength` from preset objects, but the Swift schema and UI cannot create or edit those fields.
- The Settings tabs named `Shared` and `Status` are still ClipMind-specific surfaces.

This makes each new app-specific setting look like a one-off field added to the shared preset object. That path will keep producing inconsistent schema, UI, runtime, and documentation behavior.

## Decision

Separate shared LLM connection presets from app-specific profiles.

Shared LLM presets contain only app-independent connection details:

```json
{
  "id": "local-gemma",
  "name": "Local Gemma",
  "baseURL": "http://localhost:1234/v1",
  "model": "google/gemma-4-12b",
  "apiKeyRef": "preset-local-gemma-api-key"
}
```

App profiles contain app-specific selection and app-specific settings. App-specific
settings are namespaced by stable app-owned keys:

```json
{
  "appProfiles": {
    "clipmind": {
      "activePresetId": "local-gemma",
      "settings": {
        "summarizeSystemPrompt": "Summarize the transcript.",
        "summarizeUserPrompt": "{text}",
        "translateSystemPrompt": "Translate the summary into Japanese.",
        "translateUserPrompt": "{text}"
      }
    },
    "meeting-summary-local-llm": {
      "activePresetId": "local-gemma",
      "settings": {
        "timeout": 900,
        "contextLength": 32768
      }
    }
  }
}
```

The app-specific object is always named `settings` inside each app profile. The
meaning of that object is owned by the app ID. App-specific fields must not live
on shared preset objects.

## Goals

- Make `LLM Presets` mean shared model connection settings only.
- Give each supported app a place to store dedicated settings.
- Preserve existing config files by reading legacy prompt fields from presets during migration.
- Let Meeting Summary settings that are already supported by runtime be configured through the menu bar app.
- Make the UI communicate ownership clearly enough that future settings have an obvious home.

## Non-Goals

- Build a full plugin system for arbitrary apps.
- Move every ClipMind setting under `Apps > ClipMind` in one step.
- Move Meeting Summary output, style, routing, Slack, or Notion settings into the menu bar app.
- Remove compatibility with existing schema version 1 configs in the same change.
- Rename the whole menu bar app.

## Configuration Ownership

### Shared LLM Presets

Preset fields:

- `id`
- `name`
- `baseURL`
- `model`
- `apiKeyRef`

These are reusable across apps. Adding a field to `presets` requires it to be meaningful for every app that can select the preset.

### App Profiles

Every supported app may have:

- `activePresetId`: empty or missing means use global `activePresetId`
- `settings`: an app-owned object whose shape depends on the app ID

Supported app IDs remain:

- `clipmind`
- `meeting-summary-local-llm`

ClipMind profile settings:

- `summarizeSystemPrompt`
- `summarizeUserPrompt`
- `translateSystemPrompt`
- `translateUserPrompt`

Meeting Summary profile settings:

- `timeout`
- `contextLength`

Unknown app IDs remain allowed for forward compatibility, but current UI only edits known apps.

## Runtime Resolution

Runtime readers build an app-specific runtime snapshot from two sources:

```text
shared preset selected for this app
+ app profile settings for this app
```

ClipMind resolution:

```text
appProfiles.clipmind.activePresetId
  -> activePresetId

then:
  preset connection fields
  + appProfiles.clipmind.settings prompt fields
  + legacy prompt fields from selected preset only as compatibility fallback
```

Meeting Summary resolution:

```text
CLI args
  -> environment variables
  -> appProfiles.meeting-summary-local-llm active preset and settings
  -> global activePresetId
  -> existing defaults or auto-selection
```

Meeting Summary must stop treating `timeout` and `contextLength` on the selected preset as the primary location. It may read those legacy preset fields as a compatibility fallback during transition.

## UI Shape

`LLM Presets` edits shared connection fields only:

```text
Name
Base URL
Model
API key
Test Connection
```

`Apps` becomes the owner for app-specific settings:

```text
ClipMind
  LLM preset: [Default or preset name]
  Summary system prompt
  Summary user prompt
  Translation system prompt
  Translation user prompt

Meeting Summary
  LLM preset: [Default or preset name]
  Timeout
  Context length
```

The current `Shared` and `Status` tabs should be treated as ClipMind app surfaces, not generic shared config. The implementation can either:

- rename them to make ownership explicit, or
- keep labels for now but document that they are ClipMind-owned and not part of the shared LLM preset contract.

Renaming is preferable if it can be done without broad UI churn.

## Migration

No destructive migration is required.

When reading existing configs:

- If app profile prompt fields exist, ClipMind uses them.
- Otherwise ClipMind falls back to prompt fields on the selected preset.
- If Meeting Summary profile `timeout` or `contextLength` exists, Meeting Summary uses them.
- Otherwise Meeting Summary may fall back to legacy preset-level `timeout` and `contextLength`.

When saving from the updated menu bar app:

- shared preset objects should be written without app-specific fields;
- ClipMind prompt values should be written to `appProfiles.clipmind`;
- Meeting Summary dedicated values should be written to `appProfiles.meeting-summary-local-llm`;
- legacy preset-level app fields should not be reintroduced by normal UI saves.

This produces gradual cleanup without breaking existing config files.

## Validation

Config writer validation should enforce:

- preset IDs are unique;
- each preset has required shared connection fields;
- global `activePresetId` references an existing preset;
- each non-empty app profile `activePresetId` references an existing preset;
- ClipMind prompt fields are non-empty after fallback resolution;
- Meeting Summary `timeout` and `contextLength`, when present, are integers and not booleans.

Runtime readers should be strict for the settings they own and tolerant of unknown settings for other apps.

## Testing

ClipMind Swift tests should cover:

- decoding legacy preset-level prompt fields;
- saving moves or preserves prompt values under `appProfiles.clipmind`;
- `LLM Presets` model excludes app-specific fields;
- deleting a preset clears app-specific active preset references;
- validation rejects invalid app profile preset IDs;
- validation accepts Meeting Summary profile fields that are irrelevant to ClipMind runtime.

ClipMind Python tests should cover:

- prompt fields resolve from `appProfiles.clipmind`;
- legacy preset-level prompts remain a fallback;
- missing prompt fields produce a clear config error;
- selected app preset still overrides global preset.

Meeting Summary tests should cover:

- `timeout` and `contextLength` resolve from `appProfiles.meeting-summary-local-llm`;
- legacy preset-level `timeout` and `contextLength` remain a fallback;
- CLI and env vars still override shared config;
- invalid app profile values fall back or fail according to the existing Meeting Summary contract.

## Risks

- Keeping schema version 1 while moving field ownership relies on compatibility behavior rather than a hard migration.
- If UI save logic is careless, it may drop legacy prompt values before copying them into `appProfiles.clipmind`.
- Cross-repo coordination is required because ClipMind writes the config and Meeting Summary reads it.
- The menu bar app still contains ClipMind-specific settings next to shared LLM settings, so labels and docs must make ownership explicit.

## Implementation Order

1. Add model types for shared preset fields and app-specific profile settings.
2. Add compatibility decoding for legacy preset-level ClipMind prompt fields.
3. Move the LLM preset editor UI to connection fields only.
4. Expand the Apps UI with ClipMind prompt settings and Meeting Summary dedicated settings.
5. Update ClipMind runtime to compose selected preset plus ClipMind profile.
6. Update Meeting Summary runtime to read Meeting Summary profile settings first.
7. Update docs and tests after the boundary is represented in code.
