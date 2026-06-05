# Shared Local LLM Config Design

## Context

ClipMind recently moved from repository-local `.env` configuration to a macOS menu bar settings app backed by:

- `~/Library/Application Support/ClipMind/config.json`
- macOS Keychain service `com.kichinosukey.clipmind`

This solved a real personal workflow problem: model, base URL, API key, Whisper, output, and destination settings no longer require editing files in the repository.

The same problem exists in other local tools, especially `meeting-summary-local-llm`, which still relies on `.envrc`, `.env`, CLI flags, and YAML routing files. The broader product direction is therefore not "a ClipMind-only settings app", but a personal control surface for local AI tools.

## Decision

Keep the current ClipMind app, storage path, and Keychain service for now. Reinterpret the LLM preset portion of the config as a shared local LLM preset schema that other personal tools can read.

This is an incremental design:

1. First implementation step: share only LLM connection settings.
2. Near-term target: allow `meeting-summary-local-llm` to read the same active LLM preset.
3. Later target: move to a generic app and storage namespace if more tools adopt the schema.

## Goals

- Avoid editing repo-local `.env` or `.envrc` files just to switch model settings.
- Let ClipMind remain stable while the shared schema proves itself.
- Add a second consumer, `meeting-summary-local-llm`, without forcing a package split yet.
- Keep secrets out of JSON by storing secret values in Keychain and storing only references in config.
- Preserve existing CLI and environment-variable workflows during migration.

## Non-Goals

- Rename the app or storage namespace immediately.
- Build a generic plugin system for arbitrary tools.
- Replace every `meeting-summary-local-llm` setting in the first step.
- Remove `.envrc` or existing CLI overrides in the first step.
- Create a shared Python package before the schema has a second real consumer.

## Configuration Shape

The current ClipMind config remains the system of record:

```text
~/Library/Application Support/ClipMind/config.json
```

Conceptually it is split into two layers:

```text
ClipMind config
  |
  +-- shared LLM presets
  |     |
  |     +-- id
  |     +-- name
  |     +-- base_url
  |     +-- model
  |     +-- api_key_ref
  |     +-- timeout
  |     +-- context_length
  |
  +-- ClipMind-specific settings
        |
        +-- output_root
        +-- whisper_binary_path
        +-- whisper_model_path
        +-- enabled_destinations
        +-- destination secret refs
```

The first implementation should not require moving `output_root`, Whisper settings, or destination settings into a generic app profile. Those remain ClipMind-specific until a second tool needs the same setting.

## Read Precedence

For `meeting-summary-local-llm`, existing explicit controls must continue to win:

```text
CLI args
  > existing environment variables
  > shared ClipMind active LLM preset
  > existing defaults or auto-selection
```

This keeps current scripts, Alfred workflows, and launchd jobs compatible. The shared preset only fills values that are not explicitly supplied.

## Initial Integration

The first cross-repo integration should be deliberately small:

1. Add a thin config reader inside `meeting-summary-local-llm`.
2. Read the active LLM preset from ClipMind's config path.
3. Resolve the API key through the same Keychain reference convention where possible.
4. Apply values only for LLM connection fields:
   - base URL
   - model
   - API token
   - timeout
   - context length
5. Leave Slack, Notion, route, file, and output settings alone.

This reader should be local to `meeting-summary-local-llm` at first. Once the schema survives two consumers, extract a shared Python package.

## App UI Positioning

In the near term, the macOS app can still be presented as ClipMind. The settings UI should gradually distinguish:

```text
Settings
  |
  +-- LLM Presets
  |     shared across personal local AI tools
  |
  +-- ClipMind
        ClipMind-only paths, Whisper, and destinations
```

The UI does not need a full rename yet. The important change is making the shared nature of LLM presets clear enough that using them from another repo does not feel accidental.

## Error Handling

Consumers of the shared preset should fail softly:

- Missing config file: continue with existing environment/default behavior.
- Invalid config JSON: warn and continue with existing behavior.
- Missing active preset: warn and continue with existing behavior.
- Missing Keychain secret: treat API token as absent, then rely on env/default behavior.
- Unsupported schema version: warn and continue with existing behavior.

ClipMind itself can remain stricter because it owns the config writer and settings validation.

## Testing

ClipMind should keep its existing Swift and Python contract tests for the config schema.

`meeting-summary-local-llm` should add focused tests for:

- Shared preset fills missing LLM args.
- CLI args override shared preset.
- Environment variables override shared preset.
- Missing config does not fail the pipeline.
- Invalid config does not fail the pipeline.
- Missing Keychain value does not expose or fabricate a token.

The tests should not require real Keychain access. Use an adapter or seam that can be replaced in tests.

## Migration Plan

There is no automatic `.env` or `.envrc` migration in the first step.

Manual migration is preferable because the old files may include repo-specific settings, personal paths, and secrets. The shared config should only take over values the user intentionally saves through the menu bar app.

## Future Extraction

After `meeting-summary-local-llm` successfully consumes the same LLM preset, revisit extraction into a shared package or tool.

Candidate future namespace:

```text
~/Library/Application Support/LocalAI/config.json
Keychain service: com.kichinosukey.local-ai
```

That migration should happen only after at least two tools prove the schema is useful and stable.

## Risks

- The ClipMind path will temporarily carry generic settings, which is conceptually imperfect.
- Two local readers may duplicate some parsing code before package extraction.
- If the preset schema changes too quickly, cross-repo compatibility can become fragile.

These risks are acceptable because the first step preserves existing workflows and keeps the blast radius small.
