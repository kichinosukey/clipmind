# ClipMind macOS Menu Bar Management Design

## Summary

ClipMind will keep its current YouTube-focused Python pipeline and add a thin
native macOS menu bar application for configuration management and job progress
visibility.

The main problem is not that ClipMind lacks a macOS application. The problem is
that changing models, API endpoints, prompts, and delivery settings currently
requires editing the repository's `.env` file. A menu bar application is useful
because it provides a natural home for frequently changed settings, macOS
Keychain integration, and lightweight progress visibility.

The application will not become the execution engine or job controller.
Existing CLI, Chrome extension, and Alfred entry points will continue to invoke
the Python core directly. They will all use the same active preset and shared
configuration.

## Goals

- Replace routine `.env` editing with a native settings interface.
- Support selecting and editing named presets.
- Let each preset combine an LLM connection, model, and prompts.
- Fetch available models from an OpenAI-compatible endpoint and allow manual
  model entry if discovery fails.
- Store API keys and webhook URLs in macOS Keychain.
- Make the active preset apply immediately to CLI, Chrome, and Alfred jobs.
- Show the current pipeline stage and the most recent success or failure.
- Preserve the current YouTube processing scope and existing Python pipeline.
- Allow CLI, Chrome, and Alfred jobs to run while the menu bar app is closed.

## Non-Goals

- Supporting arbitrary URLs, selected text, or Finder files.
- Moving pipeline execution or job queue management into the macOS app.
- Cancelling or retrying jobs from the app.
- Displaying detailed logs or a long-term job history.
- Automatically importing values from `.env`.
- Falling back to `.env` after switching to the shared configuration system.
- App signing, distribution, automatic updates, or setup for other users.

## Selected Approach

Use a thin native SwiftUI menu bar application over a shared runtime
configuration and status directory. Keep the Python pipeline as the execution
engine.

Alternatives rejected:

- A local web management UI would be easy to keep in Python, but it introduces
  a local server lifecycle and provides weaker Keychain and menu bar
  integration.
- Making the macOS app the execution controller would provide centralized job
  management, but requires unnecessary IPC and a substantial redesign of the
  working CLI-based system.

## Architecture

```text
┌───────────────────────────────────────────┐
│ ClipMind Menu Bar App                     │
│                                           │
│ - Select and edit presets                 │
│ - Fetch endpoint model list               │
│ - Store secrets in Keychain               │
│ - Display pipeline progress and result    │
└─────────────────────┬─────────────────────┘
                      │ read, write, monitor
                      ▼
┌───────────────────────────────────────────┐
│ Shared Runtime                            │
│                                           │
│ ~/Library/Application Support/ClipMind/   │
│ - config.json                             │
│ - jobs/*.json                             │
│                                           │
│ macOS Keychain                            │
│ - API keys                                │
│ - Discord and Slack webhooks              │
└─────────────────────┬─────────────────────┘
                      │ read at job start
                      ▼
┌───────────────────────────────────────────┐
│ Python Core                               │
│                                           │
│ Config Loader                             │
│      ↓                                    │
│ yt-dlp: download audio                    │
│      ↓                                    │
│ whisper.cpp: transcribe                   │
│      ↓                                    │
│ OpenAI-compatible API: summarize          │
│      ↓                                    │
│ OpenAI-compatible API: translate          │
│      ↓                                    │
│ Discord / Slack: deliver                  │
│      ↓                                    │
│ Progress Reporter → jobs/*.json           │
└─────────────────────▲─────────────────────┘
                      │ invoke the same core
          ┌───────────┼───────────┐
          │           │           │
        CLI      Chrome host    Alfred
```

The menu bar app is a configuration editor and observer. It must not be
required for pipeline execution. Each job reads a complete configuration
snapshot when it starts, so changing the active preset affects new jobs but
does not mutate jobs already in progress.

## Configuration Model

Non-secret configuration is stored in:

```text
~/Library/Application Support/ClipMind/config.json
```

Secrets are stored in macOS Keychain. The JSON configuration stores stable
references to the corresponding Keychain items.

```text
ClipMindConfig
├── schemaVersion
├── activePresetId
├── presets[]
│   ├── id
│   ├── name
│   ├── baseURL
│   ├── model
│   ├── apiKeyRef
│   ├── summarizeSystemPrompt
│   ├── summarizeUserPrompt
│   ├── translateSystemPrompt
│   └── translateUserPrompt
└── shared
    ├── whisperBinaryPath
    ├── whisperModelPath
    ├── outputRoot
    ├── enabledDestinations[]
    ├── discordWebhookRef
    └── slackWebhookRef
```

Preset-scoped settings:

- OpenAI-compatible base URL
- API key reference
- Model
- Summarization system and user prompts
- Translation system and user prompts

Shared settings:

- `whisper-cli` path
- Whisper model path
- Output root
- Default enabled delivery destinations
- Discord and Slack webhook references

The app writes `config.json` using an atomic replacement. The Python core
validates and loads the selected preset once at job start. Entry points may
continue to supply an explicit destination list for a single job, as the Chrome
popup does today. When an entry point supplies no destination override, the
shared default destinations are used.

Keychain items use a stable ClipMind service name and the configuration
reference as the Keychain account name. Both Swift and Python access secrets
through adapters that implement the same get, set, and delete contract. Secret
values must never be copied into `config.json`, job status JSON, or logs.

## Initial Setup and Cutover

There is no automatic `.env` import and no `.env` fallback in the new
configuration path.

On first launch, the app shows which required settings are missing. The user
manually creates a preset, enters secrets into Keychain, selects Whisper paths,
and configures destinations.

The existing `.env` execution path remains usable until the shared
configuration implementation is ready for explicit cutover. After cutover, all
supported entry points use shared configuration only. Missing shared
configuration causes an actionable error rather than silently using `.env`.

## Menu Bar Application

The menu bar menu shows:

- Active preset name
- Current job stage and title when a job is running
- Most recent success or failure
- Preset selector
- Command to open settings
- Quit command

The settings window has three sections:

### Presets

- List, add, duplicate, and delete presets
- Select the active preset
- Edit endpoint, model, and prompts
- Save an API key to Keychain
- Fetch models from `{baseURL}/models`
- Select a discovered model or enter a model name manually
- Test the configured endpoint before saving

### Shared Settings

- Select and validate the Whisper binary
- Select and validate the Whisper model
- Select the output root
- Enable Discord and Slack destinations
- Save destination webhooks to Keychain

### Status

- Show the current job stage
- Show the most recent completed or failed job
- Show a concise error summary for failed jobs

## Progress Contract

Each invocation creates one JSON status file under:

```text
~/Library/Application Support/ClipMind/jobs/
```

The job state machine is:

```text
queued
  → downloading_audio
  → transcribing_with_whisper
  → summarizing
  → translating
  → delivering
  → completed | failed
```

Each job file contains:

- `schemaVersion`
- `jobId`
- `sourceURL`
- `title`, once known
- `stage`
- `startedAt`
- `updatedAt`
- `completedAt`, when terminal
- `failedStage`, when failed
- `errorSummary`, when failed
- `deliveryResults`, when delivery was attempted

The Python core updates status files atomically. The app monitors the directory
and treats the most recently updated non-terminal job as the current job.
Multiple simultaneous jobs may exist, but the initial UI only shows a count,
the most recently updated active job, and the most recent terminal result. To
prevent unbounded file growth, the Python core removes older terminal job files
after each completed or failed job, retaining the latest 20 terminal jobs.
Active job files are never removed by cleanup.

## Error Handling

- Missing or invalid configuration fails before expensive pipeline work starts
  and identifies the missing field.
- Keychain lookup failures are explicit errors and never trigger `.env`
  fallback.
- Model discovery failures preserve manual model entry.
- Whisper binary and model paths are validated from the settings UI and again
  before transcription.
- Pipeline failures update the job file to `failed`, including the failed stage
  and a concise error summary.
- Detailed command output remains in the existing job log mechanism rather
  than being copied into status JSON.
- Delivery errors remain isolated per destination and are recorded in
  `deliveryResults`.
- Job status and error summaries are sanitized so they do not include API keys,
  webhook URLs, or full Keychain command output.

## Testing Strategy

### Python

- Shared configuration parsing and validation
- Active preset resolution
- Keychain adapter behavior with a mocked command boundary
- Secret redaction from errors, job status, and logs
- Configuration snapshot behavior at job start
- Atomic progress writes and valid state transitions
- Terminal job retention cleanup without removing active jobs
- Failure reporting for each pipeline stage
- Regression tests for the existing YouTube pipeline and destinations

### Swift

- Preset create, update, duplicate, delete, and active selection
- Configuration validation and atomic save
- Keychain read, write, update, and delete
- Model discovery success, malformed responses, and connection failure
- Job status decoding and directory monitoring
- Menu bar display derived from job state

### Integration and Manual Verification

- CLI, Chrome, and Alfred use the same active preset.
- Explicit per-job destination selection overrides shared destination defaults.
- Changing the active preset affects the next job.
- Changing the active preset does not alter an in-progress job.
- A CLI job runs successfully while the menu bar app is closed.
- No new execution path reads or falls back to `.env`.

## Delivery Sequence

1. Add shared configuration types, validation, Keychain access boundary, and
   progress reporting to the Python core.
2. Add the explicit shared-configuration execution path and verify the CLI
   against it without removing the existing path prematurely.
3. Build the SwiftUI menu bar application with preset and shared settings
   management.
4. Add Keychain integration and model discovery.
5. Add job progress monitoring and menu bar status.
6. Verify Chrome Native Messaging and Alfred use the shared configuration path.
7. Perform explicit cutover and remove `.env` use from all supported new
   execution paths.

## Scope Review

This design is intentionally limited to configuration management and progress
visibility for the existing YouTube workflow. Job control, broader source
support, distribution, and detailed history are separate future projects.
